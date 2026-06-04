"""
Authenticated async HTTP client for the Braiins Hash Power marketplace API.

Authentication uses HMAC-SHA256 request signing (same pattern as NiceHash v2).
Verify the exact signature format by opening https://hashpower.braiins.com/api/
→ Authorize → execute a test request → inspect the Network tab for actual headers.
"""

import hashlib
import hmac
import time
import uuid
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


def _build_signature(
    api_key_id: str,
    api_secret: str,
    request_id: str,
    ts: str,
    nonce: str,
    method: str,
    path: str,
    query: str = "",
    body: str = "",
) -> str:
    """Build HMAC-SHA256 signature for Braiins API authentication."""
    msg = "\0".join([
        api_key_id, ts, nonce, "", "", "", "",
        f"{method}\n{path}\n{query}\n{body}",
    ])
    digest = hmac.new(
        api_secret.encode("utf-8"),
        msg.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return digest


def _auth_headers(method: str, path: str, query: str = "", body: str = "") -> dict[str, str]:
    cfg = get_settings()
    request_id = str(uuid.uuid4())
    ts = str(int(time.time() * 1000))
    nonce = str(uuid.uuid4())
    sig = _build_signature(
        cfg.braiins_api_key_id,
        cfg.braiins_api_secret,
        request_id,
        ts,
        nonce,
        method,
        path,
        query,
        body,
    )
    return {
        "X-Request-Id": request_id,
        "X-Time": ts,
        "X-Nonce": nonce,
        "X-Organization-Id": cfg.braiins_org_id,
        "X-Auth": f"{cfg.braiins_api_key_id}:{sig}",
        "Content-Type": "application/json",
    }


class BraiinsClient:
    """Thin async wrapper around the Braiins Hash Power REST API."""

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(base_url=BASE_URL, timeout=15.0)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _get(self, path: str, params: Optional[dict] = None) -> Any:
        query = "&".join(f"{k}={v}" for k, v in (params or {}).items())
        headers = _auth_headers("GET", path, query)
        url = path + (f"?{query}" if query else "")
        resp = await self._client.get(url, headers=headers)
        resp.raise_for_status()
        return resp.json()

    async def _post(self, path: str, payload: dict) -> Any:
        import json
        body = json.dumps(payload, separators=(",", ":"))
        headers = _auth_headers("POST", path, "", body)
        resp = await self._client.post(path, content=body, headers=headers)
        resp.raise_for_status()
        return resp.json()

    async def _put(self, path: str, payload: dict) -> Any:
        import json
        body = json.dumps(payload, separators=(",", ":"))
        headers = _auth_headers("PUT", path, "", body)
        resp = await self._client.put(path, content=body, headers=headers)
        resp.raise_for_status()
        return resp.json()

    async def _delete(self, path: str) -> None:
        headers = _auth_headers("DELETE", path)
        resp = await self._client.delete(path, headers=headers)
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
