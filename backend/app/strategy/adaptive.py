"""
Adaptive bidding strategy.

Adjusts price on ACTIVE bids to stay in cheapest TOP_N asks of the order book.
Never creates or cancels orders — only price edits.
Prices in .env / settings are BTC/EH/day; converted to satoshi when calling API.
"""

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.braiins.client import BraiinsClient
from app.braiins.models import BidResponseItem, EditBidRequest, SAT
from app.config import get_settings
from app.db.models import BidSnapshot, StrategyLog

logger = logging.getLogger(__name__)

ACTIVE_STATUSES = {"BID_STATUS_ACTIVE", "BID_STATUS_CREATED"}


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

        # 2. Order book — cheapest bids first (these are OTHER buyers we compete with)
        book = await client.get_order_book()
        sorted_bids = sorted(book.bids, key=lambda b: b.price_sat)

        # P_N in satoshi
        n = cfg.top_n
        p_n_sat = sorted_bids[n - 1].price_sat if len(sorted_bids) >= n else (
            sorted_bids[-1].price_sat if sorted_bids else 0
        )
        p_n_btc = p_n_sat / SAT

        # Strategy params in satoshi
        max_sat = float(cfg.max_bid_price) * SAT
        min_sat = float(cfg.min_bid_price) * SAT
        upper_buf_sat = float(cfg.upper_buffer) * SAT
        lower_margin_sat = float(cfg.lower_margin) * SAT
        price_step_sat = float(cfg.price_step) * SAT

        # 3. Evaluate each active bid
        for item in active:
            result = await _evaluate(
                item, p_n_sat, max_sat, min_sat,
                upper_buf_sat, lower_margin_sat, price_step_sat,
                client, db, cfg,
            )
            results.append(result)
            _snapshot(db, item, p_n_sat)

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
    upper_buf_sat: float,
    lower_margin_sat: float,
    price_step_sat: float,
    client: BraiinsClient,
    db: Session,
    cfg,
) -> dict:
    bid = item.bid
    my_sat = bid.price_sat
    target_sat: float | None = None
    action = "HOLD"
    reason = f"Price {my_sat/SAT:.5f} BTC within competitive band (P{cfg.top_n}={p_n_sat/SAT:.5f} BTC)"

    if my_sat > max_sat:
        target_sat = max_sat
        action = "LOWER"
        reason = f"Price {my_sat/SAT:.5f} exceeds MAX {max_sat/SAT:.5f} BTC — hard cap"

    elif p_n_sat > 0 and my_sat > p_n_sat + upper_buf_sat:
        target_sat = max(p_n_sat - lower_margin_sat, min_sat)
        action = "LOWER"
        reason = f"Price {my_sat/SAT:.5f} > P{cfg.top_n} ({p_n_sat/SAT:.5f}) + buffer — lowering to {target_sat/SAT:.5f} BTC"

    elif p_n_sat > 0 and my_sat < p_n_sat:
        target_sat = min(p_n_sat + price_step_sat, max_sat)
        action = "RAISE"
        reason = f"Price {my_sat/SAT:.5f} < P{cfg.top_n} ({p_n_sat/SAT:.5f}) — raising to {target_sat/SAT:.5f} BTC"

    is_in_top_n = (my_sat <= p_n_sat) if p_n_sat > 0 else False

    if target_sat is not None and abs(target_sat - my_sat) > 1:
        try:
            await client.edit_bid(EditBidRequest(
                bid_id=bid.id,
                new_price_btc=target_sat / SAT,
            ))
            _log(db, order_id=bid.id, action=action,
                 old_price=my_sat / SAT, new_price=target_sat / SAT,
                 market_p_n=p_n_sat / SAT, reason=reason)
            logger.info("Bid %s: %s %.5f → %.5f BTC (P%d=%.5f)",
                        bid.id, action, my_sat/SAT, target_sat/SAT, cfg.top_n, p_n_sat/SAT)
            return {"bid_id": bid.id, "action": action,
                    "old_price_btc": round(my_sat/SAT, 8),
                    "new_price_btc": round(target_sat/SAT, 8),
                    "reason": reason, "is_in_top_n": target_sat <= p_n_sat}
        except Exception as exc:
            logger.error("Failed to edit bid %s: %s", bid.id, exc)
            _log(db, order_id=bid.id, action="ERROR",
                 old_price=my_sat/SAT, market_p_n=p_n_sat/SAT,
                 reason=f"Edit failed: {exc}")
            return {"bid_id": bid.id, "action": "ERROR", "reason": str(exc)}

    _log(db, order_id=bid.id, action="HOLD",
         old_price=my_sat/SAT, market_p_n=p_n_sat/SAT, reason=reason)
    return {"bid_id": bid.id, "action": "HOLD",
            "price_btc": round(my_sat/SAT, 8), "reason": reason, "is_in_top_n": is_in_top_n}


def _log(db: Session, order_id: str, action: str,
         old_price: float | None = None, new_price: float | None = None,
         market_p_n: float | None = None, reason: str = "") -> None:
    db.add(StrategyLog(order_id=order_id, action=action,
                       old_price=old_price, new_price=new_price,
                       market_p_n=market_p_n, reason=reason))


def _snapshot(db: Session, item: BidResponseItem, p_n_sat: float) -> None:
    bid = item.bid
    db.add(BidSnapshot(
        order_id=bid.id,
        status=bid.status,
        price=bid.price_sat / SAT,
        accepted_speed=item.state_estimate.avg_speed_ph,
        available_amount=item.state_estimate.amount_remaining_sat / SAT,
        is_in_top_n=bid.price_sat <= p_n_sat if p_n_sat > 0 else False,
    ))
