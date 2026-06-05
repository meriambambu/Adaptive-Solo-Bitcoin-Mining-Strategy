from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.braiins.client import BraiinsClient
from app.braiins.models import EditBidRequest, PlaceBidRequest, SAT
from app.db.database import get_db
from app.db.models import BidSnapshot
from app.dependencies import get_client

router = APIRouter(prefix="/api/orders", tags=["orders"])

ACTIVE_STATUSES = {"BID_STATUS_ACTIVE", "BID_STATUS_CREATED"}


def _avg_speed(db: Session, order_id: str, now: datetime, minutes: int, fallback: float) -> float:
    cutoff = now - timedelta(minutes=minutes)
    rows = db.query(BidSnapshot.accepted_speed).filter(
        BidSnapshot.order_id == order_id,
        BidSnapshot.timestamp >= cutoff,
    ).all()
    if not rows:
        return fallback
    vals = [float(r.accepted_speed) for r in rows]
    return sum(vals) / len(vals)


def _format_item(item) -> dict:
    bid = item.bid
    state = item.state_estimate
    counters = item.counters_estimate
    return {
        "id": bid.id,
        "price_btc": round(bid.price_sat / SAT, 8),
        "price_sat": bid.price_sat,
        "amount_btc": round(bid.amount_sat / SAT, 8),
        "amount_sat": bid.amount_sat,
        "amount_remaining_btc": round(state.amount_remaining_sat / SAT, 8),
        "speed_limit_ph": bid.speed_limit_ph,
        "avg_speed_ph": state.avg_speed_ph,
        "progress_pct": state.progress_pct,
        "status": bid.status,
        "is_current": bid.is_current,
        "created": bid.created,
        "memo": bid.memo,
        "fee_rate_pct": bid.fee_rate_pct,
        "pool_url": bid.dest_upstream.url if bid.dest_upstream else None,
        "pool_identity": bid.dest_upstream.identity if bid.dest_upstream else None,
        "amount_consumed_btc": round(counters.amount_consumed_sat / SAT, 8),
        "shares_purchased_m": counters.shares_purchased_m,
        "counters_raw": counters.model_dump(),
    }


@router.get("")
async def list_orders(client: BraiinsClient = Depends(get_client)):
    items = await client.get_current_bids()
    return [_format_item(i) for i in items]


@router.get("/history")
async def list_order_history(
    limit: int = 100,
    client: BraiinsClient = Depends(get_client),
):
    items = await client.get_all_bids(limit=limit)
    return [_format_item(i) for i in items]


@router.get("/workers")
async def list_workers(
    client: BraiinsClient = Depends(get_client),
    db: Session = Depends(get_db),
):
    """
    All active bids formatted as worker cards, including time-windowed speed
    averages from bid_snapshot history. Shows even when current hashrate is 0.
    """
    items = await client.get_current_bids()
    now = datetime.utcnow()
    workers = []
    for item in items:
        bid = item.bid
        state = item.state_estimate
        if bid.status not in ACTIVE_STATUSES:
            continue
        workers.append({
            "id": bid.id,
            "name": bid.dest_upstream.identity if bid.dest_upstream else bid.id,
            "status": bid.status.replace("BID_STATUS_", ""),
            "created": bid.created,
            "speed_now_ph": state.avg_speed_ph,
            "speed_5m_ph": _avg_speed(db, bid.id, now, 5, state.avg_speed_ph),
            "speed_1h_ph": _avg_speed(db, bid.id, now, 60, state.avg_speed_ph),
            "speed_24h_ph": _avg_speed(db, bid.id, now, 1440, state.avg_speed_ph),
            "shares_m": item.counters_estimate.shares_purchased_m,
            "price_btc": round(bid.price_sat / SAT, 8),
            "progress_pct": state.progress_pct,
        })
    return workers


@router.post("")
async def place_order(
    req: PlaceBidRequest,
    client: BraiinsClient = Depends(get_client),
):
    result = await client.place_bid(req)
    return result


@router.put("/{order_id}/price")
async def update_price(
    order_id: str,
    new_price_btc: float,
    client: BraiinsClient = Depends(get_client),
):
    await client.edit_bid(EditBidRequest(bid_id=order_id, new_price_btc=new_price_btc))
    return {"ok": True}


@router.delete("/{order_id}", status_code=200)
async def cancel_order(
    order_id: str,
    client: BraiinsClient = Depends(get_client),
):
    return await client.cancel_bid(order_id)
