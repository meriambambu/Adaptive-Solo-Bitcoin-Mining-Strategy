from fastapi import APIRouter, Depends, HTTPException

from app.braiins.client import BraiinsClient
from app.braiins.models import EditBidRequest, PlaceBidRequest, SAT
from app.dependencies import get_client

router = APIRouter(prefix="/api/orders", tags=["orders"])


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
