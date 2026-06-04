from fastapi import APIRouter, Depends

from app.braiins.client import BraiinsClient
from app.dependencies import get_client

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/orderbook")
async def get_order_book(
    size: int = 100,
    client: BraiinsClient = Depends(get_client),
):
    book = await client.get_order_book(size=size)
    return book.model_dump()


@router.get("/balance")
async def get_balance(client: BraiinsClient = Depends(get_client)):
    balance = await client.get_balance()
    return balance.model_dump()
