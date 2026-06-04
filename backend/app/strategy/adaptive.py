"""
Adaptive bidding strategy: adjusts price on existing active orders to stay
in the cheapest TOP_N bids in the Braiins order book.

This module NEVER creates or cancels orders — only price updates.
Order lifecycle (create/cancel) is always a manual user action via the dashboard.
"""

import logging
from datetime import datetime
from decimal import Decimal, ROUND_DOWN

from sqlalchemy.orm import Session

from app.braiins.client import BraiinsClient
from app.braiins.models import Order, UpdateOrderRequest
from app.config import get_settings
from app.db.models import BidSnapshot, StrategyLog

logger = logging.getLogger(__name__)

PRICE_PRECISION = Decimal("0.00001")


def _quantize(price: Decimal) -> Decimal:
    return price.quantize(PRICE_PRECISION, rounding=ROUND_DOWN)


async def run_strategy_cycle(client: BraiinsClient, db: Session) -> dict:
    """
    Execute one adaptive bidding cycle.

    Returns a summary dict that is broadcast to all WebSocket clients.
    """
    cfg = get_settings()

    if not cfg.strategy_enabled:
        logger.info("Strategy disabled — skipping cycle")
        return {"action": "DISABLED", "timestamp": datetime.utcnow().isoformat()}

    results: list[dict] = []

    try:
        # 1. Fetch active orders
        orders = await client.get_my_orders()
        active = [o for o in orders if o.status == "ACTIVE"]

        if not active:
            _log(db, order_id="none", action="IDLE", reason="No active orders — strategy idle until manual order is created")
            return {"action": "IDLE", "timestamp": datetime.utcnow().isoformat(), "orders": []}

        # 2. Fetch order book (exclude our own orders by id)
        my_ids = {o.id for o in active}
        book = await client.get_order_book(size=200)
        other_bids = sorted(
            [e for e in book.list if True],  # all public bids (may include ours)
            key=lambda e: e.price,
        )

        # Identify P_N: the Nth cheapest price from OTHER bidders
        # If fewer than TOP_N bids exist, use the last available
        n = cfg.top_n
        p_n = other_bids[n - 1].price if len(other_bids) >= n else (other_bids[-1].price if other_bids else Decimal("0"))

        # 3. Evaluate each active order
        for order in active:
            result = await _evaluate_order(order, p_n, client, db, cfg)
            results.append(result)
            _snapshot(db, order, p_n, result.get("is_in_top_n", False))

        db.commit()
        return {
            "action": "CYCLE_COMPLETE",
            "timestamp": datetime.utcnow().isoformat(),
            "market_p_n": str(p_n),
            "orders": results,
        }

    except Exception as exc:
        logger.error("Strategy cycle error: %s", exc)
        _log(db, order_id="none", action="ERROR", reason=str(exc))
        db.commit()
        return {"action": "ERROR", "timestamp": datetime.utcnow().isoformat(), "error": str(exc)}


async def _evaluate_order(
    order: Order,
    p_n: Decimal,
    client: BraiinsClient,
    db: Session,
    cfg,
) -> dict:
    my_price = order.price
    target: Decimal | None = None
    action = "HOLD"
    reason = f"Price {my_price} is within competitive band (P{cfg.top_n}={p_n})"

    # Hard cap override — always checked first
    if my_price > cfg.max_bid_price:
        target = _quantize(cfg.max_bid_price)
        action = "LOWER"
        reason = f"Price {my_price} exceeds MAX_BID_PRICE {cfg.max_bid_price} — hard cap applied"

    # Overpriced: we're paying more than needed, lower to save budget
    elif p_n > Decimal("0") and my_price > p_n + cfg.upper_buffer:
        raw = p_n - cfg.lower_margin
        target = _quantize(max(raw, cfg.min_bid_price))
        action = "LOWER"
        reason = f"Price {my_price} > P{cfg.top_n} ({p_n}) + buffer ({cfg.upper_buffer}) — lowering to {target}"

    # Not competitive: raise price to get back into top N
    elif p_n > Decimal("0") and my_price < p_n:
        raw = p_n + cfg.price_step
        target = _quantize(min(raw, cfg.max_bid_price))
        action = "RAISE"
        reason = f"Price {my_price} < P{cfg.top_n} ({p_n}) — raising to {target}"

    is_in_top_n = my_price <= p_n if p_n > 0 else False

    if target is not None and target != my_price:
        try:
            updated = await client.update_order(order.id, UpdateOrderRequest(price=target))
            _log(db, order_id=order.id, action=action, old_price=float(my_price),
                 new_price=float(target), market_p_n=float(p_n), reason=reason)
            logger.info("Order %s: %s — %s → %s (P%d=%s)", order.id, action, my_price, target, cfg.top_n, p_n)
            return {"order_id": order.id, "action": action, "old_price": str(my_price),
                    "new_price": str(target), "reason": reason, "is_in_top_n": target <= p_n}
        except Exception as exc:
            logger.error("Failed to update order %s: %s", order.id, exc)
            _log(db, order_id=order.id, action="ERROR", old_price=float(my_price),
                 market_p_n=float(p_n), reason=f"Update failed: {exc}")
            return {"order_id": order.id, "action": "ERROR", "reason": str(exc)}
    else:
        _log(db, order_id=order.id, action="HOLD", old_price=float(my_price),
             market_p_n=float(p_n), reason=reason)
        return {"order_id": order.id, "action": "HOLD", "price": str(my_price),
                "reason": reason, "is_in_top_n": is_in_top_n}


def _log(
    db: Session,
    order_id: str,
    action: str,
    old_price: float | None = None,
    new_price: float | None = None,
    market_p_n: float | None = None,
    reason: str = "",
) -> None:
    db.add(StrategyLog(
        order_id=order_id,
        action=action,
        old_price=old_price,
        new_price=new_price,
        market_p_n=market_p_n,
        reason=reason,
    ))


def _snapshot(db: Session, order: Order, p_n: Decimal, is_in_top_n: bool) -> None:
    db.add(BidSnapshot(
        order_id=order.id,
        status=order.status,
        price=float(order.price),
        accepted_speed=float(order.acceptedSpeed),
        available_amount=float(order.availableAmount),
        is_in_top_n=is_in_top_n,
    ))
