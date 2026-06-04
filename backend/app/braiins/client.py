"""
Authenticated async HTTP client for the Braiins Hash Power marketplace API.

Authentication uses a single API key passed as a Bearer token.
Generate your key at: hashpower.braiins.com → Account → Settings → API Keys

If requests return 401, open https://hashpower.braiins.com/api/ in your browser,
click Authorize, paste your key, fire a test request, and check the Network tab
to confirm the exact header name used (Bearer vs X-Api-Key, etc.).
"""

import logging
from decimal import Decimal
from typing import Any, Optional

import httpx

from app.config import get_settings
from app.braiins.models import (
    AccountBalance,
    CreateOrderRequest,
    Order,
    OrderBook,
    UpdateOrderRequest,
)

logger = logging.getLogger(__name__)

BASE_URL = "https://hashpower.braiins.com"
ALGORITHM = "SHA256"


def _auth_headers() -> dict[str, str]:
    cfg = get_settings()
    return {
        "Authorization": f"Bearer {cfg.braiins_api_key}",
        "Content-Type": "application/json",
    }


class BraiinsClient:
    """Thin async wrapper around the Braiins Hash Power REST API."""

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(base_url=BASE_URL, timeout=15.0)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _get(self, path: str, params: Optional[dict] = None) -> Any:
        resp = await self._client.get(path, params=params, headers=_auth_headers())
        resp.raise_for_status()
        return resp.json()

    async def _post(self, path: str, payload: dict) -> Any:
        resp = await self._client.post(path, json=payload, headers=_auth_headers())
        resp.raise_for_status()
        return resp.json()

    async def _put(self, path: str, payload: dict) -> Any:
        resp = await self._client.put(path, json=payload, headers=_auth_headers())
        resp.raise_for_status()
        return resp.json()

    async def _delete(self, path: str) -> None:
        resp = await self._client.delete(path, headers=_auth_headers())
        resp.raise_for_status()

    # ── Orders ────────────────────────────────────────────────────────────────

    async def get_my_orders(self) -> list[Order]:
        data = await self._get("/api/v2/hashpower/order/myOrders", {"algorithm": ALGORITHM, "size": 100})
        return [Order(**o) for o in (data.get("list") or [])]

    async def create_order(self, req: CreateOrderRequest) -> Order:
        payload = {
            "algorithm": {"algorithm": ALGORITHM},
            "amount": str(req.amount),
            "price": str(req.price),
            "limit": str(req.limit),
            "pool": {
                "host": req.poolHost,
                "port": req.poolPort,
                "username": req.poolUser,
                "password": req.poolPass,
            },
            "meta": {"notes": req.notes or ""},
        }
        data = await self._post("/api/v2/hashpower/order", payload)
        return Order(**data)

    async def update_order(self, order_id: str, req: UpdateOrderRequest) -> Order:
        payload: dict[str, Any] = {}
        if req.price is not None:
            payload["price"] = str(req.price)
        if req.limit is not None:
            payload["limit"] = str(req.limit)
        if req.amount is not None:
            payload["amount"] = str(req.amount)
        data = await self._put(f"/api/v2/hashpower/order/{order_id}", payload)
        return Order(**data)

    async def cancel_order(self, order_id: str) -> None:
        await self._delete(f"/api/v2/hashpower/order/{order_id}")

    # ── Market data ───────────────────────────────────────────────────────────

    async def get_order_book(self, size: int = 100) -> OrderBook:
        data = await self._get(
            "/api/v2/hashpower/order/book",
            {"algorithm": ALGORITHM, "size": size},
        )
        return OrderBook(**data)

    # ── Account ───────────────────────────────────────────────────────────────

    async def get_balance(self) -> AccountBalance:
        data = await self._get("/api/v2/accounting/accounts2")
        # Navigate the nested structure to find BTC balance
        for acct in data.get("list", []):
            for bal in acct.get("balances", []):
                if bal.get("currency", {}).get("enumName") == "BTC":
                    return AccountBalance(
                        totalBalance=Decimal(str(bal.get("totalBalance", "0"))),
                        available=Decimal(str(bal.get("available", "0"))),
                        pending=Decimal(str(bal.get("pending", "0"))),
                    )
        return AccountBalance()
