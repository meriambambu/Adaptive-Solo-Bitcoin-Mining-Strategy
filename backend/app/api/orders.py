from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.braiins.client import BraiinsClient
from app.braiins.models import CreateOrderRequest, UpdateOrderRequest
from app.db.database import get_db
from app.dependencies import get_client

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.get("")
async def list_orders(client: BraiinsClient = Depends(get_client)):
    orders = await client.get_my_orders()
    return [o.model_dump() for o in orders]


@router.post("")
async def create_order(
    req: CreateOrderRequest,
    client: BraiinsClient = Depends(get_client),
):
    order = await client.create_order(req)
    return order.model_dump()


@router.put("/{order_id}")
async def update_order(
    order_id: str,
    req: UpdateOrderRequest,
    client: BraiinsClient = Depends(get_client),
):
    order = await client.update_order(order_id, req)
    return order.model_dump()


@router.delete("/{order_id}", status_code=204)
async def cancel_order(
    order_id: str,
    client: BraiinsClient = Depends(get_client),
):
    await client.cancel_order(order_id)
