"""
Adaptive bidding strategy.

Keeps each active bid within the competitive zone around P_N:

  RAISE  – bid < P_N                     → step up by PRICE_STEP toward P_N
  HOLD   – P_N ≤ bid ≤ P_N + UPPER_BUFFER  → no action (hysteresis zone)
  LOWER  – bid > P_N + UPPER_BUFFER       → lower to P_N − LOWER_MARGIN
                                             (subject to LOWER_COOLDOWN rate-limit)

Hard limits:
  MIN_BID_PRICE ≤ any target ≤ MAX_BID_PRICE

P_N is the Nth cheapest bid in the active (hr_matched_ph > 0) orderbook.
"""

import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.braiins.client import BraiinsClient
from app.braiins.models import BidResponseItem, EditBidRequest, SAT
from app.config import get_settings
from app.db.models import BidSnapshot, StrategyLog

logger = logging.getLogger(__name__)

ACTIVE_STATUSES = {"BID_STATUS_ACTIVE", "BID_STATUS_CREATED"}

# Per-bid timestamp of last successful LOWER edit (in-memory, resets on restart)
_last_lowered: dict[str, datetime] = {}


async def run_strategy_cycle(client: BraiinsClient, db: Session) -> dict:
    cfg = get_settings()

    if not cfg.strategy_enabled:
        logger.info("Strategy disabled — skipping cycle")
        return {"action": "DISABLED", "timestamp": datetime.utcnow().isoformat()}

    results: list[dict] = []

    try:
        # 1. Active bids only
        all_items = await client.get_current_bids()
        active = [item for item in all_items if item.bid.status in ACTIVE_STATUSES]

        if not active:
            _log(db, order_id="none", action="IDLE",
                 reason="No active bids — strategy idle until a bid is created manually")
            db.commit()
            return {"action": "IDLE", "timestamp": datetime.utcnow().isoformat()}

        # 2. Order book — prefer bids with active hashrate, fall back to full book
        book = await client.get_order_book()
        active_book = [b for b in book.bids if b.hr_matched_ph > 0]
        if not active_book:
            logger.warning("No orderbook bids with hashrate — falling back to full book")
            active_book = book.bids
        sorted_bids = sorted(active_book, key=lambda b: b.price_sat)

        n = cfg.top_n
        p_n_sat = sorted_bids[n - 1].price_sat if len(sorted_bids) >= n else (
            sorted_bids[-1].price_sat if sorted_bids else 0
        )
        p_n_btc = p_n_sat / SAT

        # Convert config limits to satoshi
        max_sat = float(cfg.max_bid_price) * SAT
        min_sat = float(cfg.min_bid_price) * SAT
        upper_buffer_sat = float(cfg.upper_buffer) * SAT
        lower_margin_sat = float(cfg.lower_margin) * SAT
        price_step_sat = float(cfg.price_step) * SAT

        # 3. Evaluate each active bid
        for item in active:
            result = await _evaluate(
                item, p_n_sat, max_sat, min_sat,
                upper_buffer_sat, lower_margin_sat, price_step_sat,
                cfg.lower_cooldown, cfg.top_n,
                client, db, cfg,
            )
            results.append(result)
            _snapshot(db, item, p_n_sat, upper_buffer_sat)

        db.commit()
        return {
            "action": "CYCLE_COMPLETE",
            "timestamp": datetime.utcnow().isoformat(),
            "market_p_n_btc": round(p_n_btc, 8),
            "market_p_n_sat": p_n_sat,
            "orders": results,
        }

    except Exception as exc:
        logger.error("Strategy cycle error: %s", exc)
        _log(db, order_id="none", action="ERROR", reason=str(exc))
        db.commit()
        return {"action": "ERROR", "timestamp": datetime.utcnow().isoformat(), "error": str(exc)}


async def _evaluate(
    item: BidResponseItem,
    p_n_sat: float,
    max_sat: float,
    min_sat: float,
    upper_buffer_sat: float,
    lower_margin_sat: float,
    price_step_sat: float,
    lower_cooldown: int,
    top_n: int,
    client: BraiinsClient,
    db: Session,
    cfg,
) -> dict:
    bid = item.bid
    my_sat = bid.price_sat
    target_sat: float | None = None
    action = "HOLD"

    lower_threshold_sat = p_n_sat + upper_buffer_sat
    lower_target_sat = max(min_sat, p_n_sat - lower_margin_sat)

    last = _last_lowered.get(bid.id)
    rate_limit_ok = (last is None) or (datetime.utcnow() - last >= timedelta(seconds=lower_cooldown))

    # ── Hard cap ──────────────────────────────────────────────────────────────
    if my_sat > max_sat:
        target_sat = max_sat
        action = "LOWER"
        reason = f"Price {my_sat/SAT:.5f} exceeds MAX {max_sat/SAT:.5f} — lowering to cap"

    # ── Above hysteresis zone → LOWER ─────────────────────────────────────────
    elif p_n_sat > 0 and my_sat > lower_threshold_sat:
        if rate_limit_ok:
            target_sat = lower_target_sat
            action = "LOWER"
            reason = (
                f"Price {my_sat/SAT:.5f} > P{top_n}+buffer ({lower_threshold_sat/SAT:.5f})"
                f" — lowering to {lower_target_sat/SAT:.5f}"
            )
        else:
            reason = (
                f"Price {my_sat/SAT:.5f} above zone (P{top_n}={p_n_sat/SAT:.5f}"
                f"+{upper_buffer_sat/SAT:.5f}) — rate-limited, waiting"
            )

    # ── Below P_N → RAISE ────────────────────────────────────────────────────
    elif p_n_sat > 0 and my_sat < p_n_sat:
        if price_step_sat > 0:
            target_sat = min(my_sat + price_step_sat, p_n_sat, max_sat)
        else:
            target_sat = min(p_n_sat, max_sat)
        action = "RAISE"
        reason = (
            f"Price {my_sat/SAT:.5f} < P{top_n} ({p_n_sat/SAT:.5f})"
            f" — raising to {target_sat/SAT:.5f}"  # type: ignore[union-attr]
        )

    # ── Inside hysteresis zone [P_N, P_N+upper_buffer] → HOLD ────────────────
    else:
        reason = (
            f"Price {my_sat/SAT:.5f} within zone"
            f" [{p_n_sat/SAT:.5f} – {lower_threshold_sat/SAT:.5f}] — holding"
        )

    is_in_zone = p_n_sat <= my_sat <= lower_threshold_sat if p_n_sat > 0 else False

    if target_sat is not None and abs(target_sat - my_sat) > 1:
        try:
            await client.edit_bid(EditBidRequest(
                bid_id=bid.id,
                new_price_btc=target_sat / SAT,
            ))
            if action == "LOWER":
                _last_lowered[bid.id] = datetime.utcnow()
            _log(db, order_id=bid.id, action=action,
                 old_price=my_sat / SAT, new_price=target_sat / SAT,
                 market_p_n=p_n_sat / SAT, reason=reason)
            logger.info("Bid %s: %s %.5f → %.5f BTC (P%d=%.5f)",
                        bid.id, action, my_sat/SAT, target_sat/SAT, top_n, p_n_sat/SAT)
            return {"bid_id": bid.id, "action": action,
                    "old_price_btc": round(my_sat/SAT, 8),
                    "new_price_btc": round(target_sat/SAT, 8),
                    "reason": reason, "is_in_zone": is_in_zone}
        except Exception as exc:
            logger.error("Failed to edit bid %s: %s", bid.id, exc)
            _log(db, order_id=bid.id, action="ERROR",
                 old_price=my_sat/SAT, market_p_n=p_n_sat/SAT,
                 reason=f"Edit failed: {exc}")
            return {"bid_id": bid.id, "action": "ERROR", "reason": str(exc)}

    _log(db, order_id=bid.id, action="HOLD",
         old_price=my_sat/SAT, market_p_n=p_n_sat/SAT, reason=reason)
    return {"bid_id": bid.id, "action": "HOLD",
            "price_btc": round(my_sat/SAT, 8),
            "reason": reason, "is_in_zone": is_in_zone}


async def run_rank_check(client: BraiinsClient, db: Session) -> dict:
    """
    Fast rank check (every RANK_CHECK_INTERVAL seconds).
    Raises bids that have fallen below P_N, stepping by PRICE_STEP if configured.
    Never lowers.
    """
    cfg = get_settings()

    if not cfg.strategy_enabled:
        return {"action": "SKIPPED", "reason": "strategy disabled"}

    try:
        all_items = await client.get_current_bids()
        active = [item for item in all_items if item.bid.status in ACTIVE_STATUSES]

        if not active:
            return {"action": "SKIPPED", "reason": "no active bids"}

        book = await client.get_order_book()
        active_book = [b for b in book.bids if b.hr_matched_ph > 0]
        if not active_book:
            active_book = book.bids
        sorted_bids = sorted(active_book, key=lambda b: b.price_sat)

        n = cfg.top_n
        p_n_sat = sorted_bids[n - 1].price_sat if len(sorted_bids) >= n else (
            sorted_bids[-1].price_sat if sorted_bids else 0
        )

        if not p_n_sat:
            return {"action": "SKIPPED", "reason": "empty orderbook"}

        max_sat = float(cfg.max_bid_price) * SAT
        price_step_sat = float(cfg.price_step) * SAT
        raises = []

        for item in active:
            bid = item.bid
            my_sat = bid.price_sat

            if my_sat < p_n_sat:
                if price_step_sat > 0:
                    target_sat = min(my_sat + price_step_sat, p_n_sat, max_sat)
                else:
                    target_sat = min(p_n_sat, max_sat)
                if abs(target_sat - my_sat) <= 1:
                    continue
                reason = (
                    f"[fast] Price {my_sat/SAT:.5f} < P{n} ({p_n_sat/SAT:.5f})"
                    f" — stepping to {target_sat/SAT:.5f}"
                )
                try:
                    await client.edit_bid(EditBidRequest(
                        bid_id=bid.id,
                        new_price_btc=target_sat / SAT,
                    ))
                    _log(db, order_id=bid.id, action="RAISE",
                         old_price=my_sat / SAT, new_price=target_sat / SAT,
                         market_p_n=p_n_sat / SAT, reason=reason)
                    raises.append(bid.id)
                    logger.info("Fast raise bid %s: %.5f → %.5f BTC (P%d=%.5f)",
                                bid.id, my_sat/SAT, target_sat/SAT, n, p_n_sat/SAT)
                except Exception as exc:
                    logger.error("Fast raise failed for %s: %s", bid.id, exc)

        db.commit()
        return {"action": "RAISE", "raised": raises} if raises else {"action": "HOLD"}

    except Exception as exc:
        logger.error("Fast rank check error: %s", exc)
        return {"action": "ERROR", "error": str(exc)}


def _log(db: Session, order_id: str, action: str,
         old_price: float | None = None, new_price: float | None = None,
         market_p_n: float | None = None, reason: str = "") -> None:
    db.add(StrategyLog(order_id=order_id, action=action,
                       old_price=old_price, new_price=new_price,
                       market_p_n=market_p_n, reason=reason))


def _snapshot(db: Session, item: BidResponseItem, p_n_sat: float, upper_buffer_sat: float) -> None:
    bid = item.bid
    in_zone = (p_n_sat <= bid.price_sat <= p_n_sat + upper_buffer_sat) if p_n_sat > 0 else False
    db.add(BidSnapshot(
        order_id=bid.id,
        status=bid.status,
        price=bid.price_sat / SAT,
        accepted_speed=item.state_estimate.avg_speed_ph,
        available_amount=item.state_estimate.amount_remaining_sat / SAT,
        is_in_top_n=in_zone,
    ))
