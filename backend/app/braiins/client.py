"""
Braiins Hash Power API client.

Base URL:  https://hashpower.braiins.com/api/v1
Auth:      Authorization: Bearer <BRAIINS_API_KEY>
Spec:      https://hashpower.braiins.com/api/openapi.yml

All prices in the API are in satoshi (integer).
Helper SAT = 100_000_000 converts BTC ↔ sat.
Speed is always in PH/s (1 EH/s = 1000 PH/s).
"""

import logging
from typing import Any, Optional

import httpx

from app.config import get_settings
from app.braiins.models import (
    AccountBalance,
    BalancesResponse,
    BidsResponse,
    BidResponseItem,
    EditBidRequest,
    OrderBook,
    PlaceBidRequest,
    SAT,
)

logger = logging.getLogger(__name__)

BASE_URL = "https://hashpower.braiins.com"


def _headers() -> dict[str, str]:
    return {
        "apikey": get_settings().braiins_api_key,
        "Content-Type": "application/json",
    }


class BraiinsClient:
    def __init__(self) -> None:
        self._http = httpx.AsyncClient(base_url=BASE_URL, timeout=15.0)

    async def aclose(self) -> None:
        await self._http.aclose()

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _parse(self, resp: httpx.Response) -> Any:
        try:
            return resp.json()
        except Exception:
            logger.error(
                "Non-JSON response %s %s — status=%d body=%r",
                resp.request.method, resp.request.url,
                resp.status_code, resp.text[:500],
            )
            raise

    async def _get(self, path: str, params: Optional[dict] = None) -> Any:
        resp = await self._http.get(path, params=params, headers=_headers())
        resp.raise_for_status()
        return self._parse(resp)

    async def _post(self, path: str, payload: dict) -> Any:
        resp = await self._http.post(path, json=payload, headers=_headers())
        resp.raise_for_status()
        return self._parse(resp)

    async def _put(self, path: str, payload: dict) -> Any:
        resp = await self._http.put(path, json=payload, headers=_headers())
        resp.raise_for_status()
        return self._parse(resp)

    async def _delete(self, path: str, params: Optional[dict] = None) -> Any:
        resp = await self._http.delete(path, params=params, headers=_headers())
        resp.raise_for_status()
        return self._parse(resp)

    # ── Bids ──────────────────────────────────────────────────────────────────

    async def get_current_bids(self) -> list[BidResponseItem]:
        data = await self._get("/webapi/spot/bid/current")
        # Response: {"bids": [...]}
        raw_bids = data.get("bids") or []
        return [BidResponseItem(**b) for b in raw_bids]

    async def get_all_bids(self, limit: int = 100) -> list[BidResponseItem]:
        data = await self._get("/webapi/spot/bid", {"limit": limit})
        raw_bids = data.get("bids") or data.get("items") or []
        return [BidResponseItem(**b) for b in raw_bids]

    async def place_bid(self, req: PlaceBidRequest) -> dict:
        """
        Create bid via /webapi/confirmation/create (requires a two-step confirmation).
        Returns the confirmation token for display to the user.
        """
        bid_data: dict[str, Any] = {
            "price_sat": round(req.price_btc * SAT),
            "amount_sat": round(req.amount_btc * SAT),
            "dest_upstream": {"url": req.pool_url, "identity": req.pool_identity},
        }
        if req.speed_limit_ph > 0:
            bid_data["speed_limit_ph"] = req.speed_limit_ph
        if req.memo:
            bid_data["memo"] = req.memo

        payload = {
            "requestType": "spot_bid_create",
            "requestData": bid_data,
        }
        return await self._post("/webapi/confirmation/create", payload)

    async def edit_bid(self, req: EditBidRequest) -> None:
        payload: dict[str, Any] = {
            "bid_id": req.bid_id,
            "audit_source": "adaptive_bot",
        }
        if req.new_price_btc is not None:
            payload["new_price_sat"] = round(req.new_price_btc * SAT)
        if req.new_amount_btc is not None:
            payload["new_amount_sat"] = round(req.new_amount_btc * SAT)
        if req.new_speed_limit_ph is not None:
            payload["new_speed_limit_ph"] = req.new_speed_limit_ph
        await self._put("/webapi/spot/bid", payload)

    async def cancel_bid(self, order_id: str) -> dict:
        return await self._delete("/webapi/spot/bid", {"bid_id": order_id})

    # ── Market ────────────────────────────────────────────────────────────────

    async def get_order_book(self) -> OrderBook:
        data = await self._get("/webapi/orderbook")
        return OrderBook(**data)

    async def get_market_settings(self) -> dict:
        return await self._get("/webapi/spot/settings")

    async def get_market_stats(self) -> dict:
        return await self._get("/webapi/spot/stats")

    # ── Account ───────────────────────────────────────────────────────────────

    async def get_balance(self) -> AccountBalance:
        data = await self._get("/webapi/account/balance")
        resp = BalancesResponse(**data)
        for acct in resp.accounts:
            return acct
        return AccountBalance()
