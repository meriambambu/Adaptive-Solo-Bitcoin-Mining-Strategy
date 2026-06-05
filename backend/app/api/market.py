from fastapi import APIRouter, Depends

from app.braiins.client import BraiinsClient
from app.braiins.models import SAT
from app.dependencies import get_client

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/orderbook")
async def get_order_book(client: BraiinsClient = Depends(get_client)):
    book = await client.get_order_book()
    return {
        "bids": [
            {
                "price_sat": b.price_sat,
                "price_btc": round(b.price_sat / SAT, 8),
                "amount_sat": b.amount_sat,
                "hr_matched_ph": b.hr_matched_ph,
                "speed_limit_ph": b.speed_limit_ph,
            }
            for b in sorted(book.bids, key=lambda b: b.price_sat)
        ],
        "asks": [
            {
                "price_sat": a.price_sat,
                "price_btc": round(a.price_sat / SAT, 8),
                "hr_matched_ph": a.hr_matched_ph,
                "hr_available_ph": a.hr_available_ph,
            }
            for a in sorted(book.asks, key=lambda a: a.price_sat)
        ],
    }


@router.get("/balance")
async def get_balance(client: BraiinsClient = Depends(get_client)):
    acct = await client.get_balance()
    return {
        "total_btc": round(acct.total_balance_sat / SAT, 8),
        "available_btc": round(acct.available_balance_sat / SAT, 8),
        "blocked_btc": round(acct.blocked_balance_sat / SAT, 8),
        "total_sat": acct.total_balance_sat,
        "available_sat": acct.available_balance_sat,
        "currency": acct.currency,
    }


@router.get("/stats")
async def get_stats(client: BraiinsClient = Depends(get_client)):
    data = await client.get_market_stats()
    return {
        **data,
        "best_bid_btc": round(data.get("best_bid_sat", 0) / SAT, 8),
        "best_ask_btc": round(data.get("best_ask_sat", 0) / SAT, 8),
        "last_avg_price_btc": round(data.get("last_avg_price_sat", 0) / SAT, 8),
    }
