from decimal import Decimal
from typing import Optional
from pydantic import BaseModel


class PoolConfig(BaseModel):
    host: str
    port: int
    username: str
    password: Optional[str] = None


class OrderMeta(BaseModel):
    isSolo: Optional[bool] = False
    notes: Optional[str] = None


class Order(BaseModel):
    id: str
    price: Decimal
    limit: Decimal = Decimal("0")
    amount: Decimal
    availableAmount: Decimal = Decimal("0")
    payedAmount: Decimal = Decimal("0")
    type: str = "STANDARD"
    status: str  # ACTIVE | PENDING | EXPIRED | CANCELLED | DEAD
    acceptedSpeed: Decimal = Decimal("0")
    estimatedDurationInSeconds: Optional[int] = None
    endTs: Optional[int] = None
    alive: bool = True
    pool: Optional[PoolConfig] = None
    meta: Optional[OrderMeta] = None
    createdTs: Optional[int] = None


class OrderBookEntry(BaseModel):
    price: Decimal
    speed: Decimal
    type: str = "STANDARD"


class OrderBook(BaseModel):
    list: list[OrderBookEntry] = []


class AccountBalance(BaseModel):
    totalBalance: Decimal = Decimal("0")
    available: Decimal = Decimal("0")
    pending: Decimal = Decimal("0")
    currency: str = "BTC"


class CreateOrderRequest(BaseModel):
    price: Decimal
    limit: Decimal = Decimal("0")
    amount: Decimal
    poolHost: str
    poolPort: int
    poolUser: str
    poolPass: str = "x"
    notes: Optional[str] = None


class UpdateOrderRequest(BaseModel):
    price: Optional[Decimal] = None
    limit: Optional[Decimal] = None
    amount: Optional[Decimal] = None
