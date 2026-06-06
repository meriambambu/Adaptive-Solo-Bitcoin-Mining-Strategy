"""
Braiins Hash Power API client.

Base URL:  https://hashpower.braiins.com/v1
Auth:      apikey: <BRAIINS_API_KEY>  (header, lowercase)

All prices in the API are in satoshi (integer).
Helper SAT = 100_000_000 converts BTC ↔ sat.
Speed is always in PH/s (1 EH/s = 1000 PH/s).
"""

import logging
import uuid
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

BASE_URL = "https://hashpower.braiins.com/v1"


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

    async def _delete(self, path: str) -> Any:
        resp = await self._http.delete(path, headers=_headers())
        resp.raise_for_status()
        if not resp.content:
            return None
        return self._parse(resp)

    # ── Bids ──────────────────────────────────────────────────────────────────

    def _parse_bid_items(self, raw_items: list) -> list[BidResponseItem]:
        from app.braiins.models import BidCounters, BidState, SpotBid, UpstreamSpec
        result = []
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            nested = item.get("bid") or {}
            state_est = item.get("state_estimate") or {}
            counters_est = item.get("counters_estimate") or {}
            m = {**item, **nested}  # inner bid overrides outer on collision
            upstream = None
            if isinstance(m.get("dest_upstream"), dict):
                upstream = UpstreamSpec(**m["dest_upstream"])
            amount_sat = float(m.get("amount_sat") or 0)
            consumed_sat = float(counters_est.get("amount_consumed_sat") or 0)
            bid = SpotBid(
                id=str(m.get("id") or m.get("bid_id") or ""),
                price_sat=float(m.get("price_sat") or 0),
                status=str(m.get("status") or m.get("state") or ""),
                amount_sat=amount_sat,
                speed_limit_ph=float(m.get("speed_limit_ph") or 0),
                created=m.get("created"),
                memo=str(m.get("memo") or ""),
                fee_rate_pct=float(m.get("fee_rate_pct") or 0),
                dest_upstream=upstream,
            )
            state = BidState(
                avg_speed_ph=float(state_est.get("avg_speed_ph") or 0),
                amount_remaining_sat=float(state_est.get("amount_remaining_sat") or max(0.0, amount_sat - consumed_sat)),
                progress_pct=float(state_est.get("progress_pct") or 0),
            )
            counters = BidCounters(
                amount_consumed_sat=consumed_sat,
                shares_purchased_m=float(counters_est.get("shares_purchased_m") or 0),
            )
            result.append(BidResponseItem(bid=bid, state_estimate=state, counters_estimate=counters))
        return result

    async def get_current_bids(self) -> list[BidResponseItem]:
        data = await self._get("/spot/bid/current")
        raw_items = data.get("items") or []
        for item in raw_items:
            nested = item.get("bid") or {}
            raw_status = nested.get("status") or item.get("status") or item.get("state") or "?"
            logger.debug("bid id=%s raw_status=%r", nested.get("id") or item.get("id"), raw_status)
        return self._parse_bid_items(raw_items)

    async def get_all_bids(self, limit: int = 100) -> list[BidResponseItem]:
        data = await self._get("/spot/bid", {"limit": limit})
        return self._parse_bid_items(data.get("items") or [])

    async def place_bid(self, req: PlaceBidRequest) -> dict:
        """Create bid via POST /spot/bid — direct, no confirmation required."""
        payload: dict[str, Any] = {
            "cl_order_id": str(uuid.uuid4()),
            "price_sat": round(req.price_btc * SAT),
            "amount_sat": round(req.amount_btc * SAT),
            "dest_upstream": {"url": req.pool_url, "identity": req.pool_identity},
        }
        if req.speed_limit_ph > 0:
            payload["speed_limit_ph"] = req.speed_limit_ph
        if req.memo:
            payload["memo"] = req.memo
        return await self._post("/spot/bid", payload)

    async def edit_bid(self, req: EditBidRequest) -> None:
        payload: dict[str, Any] = {"bid_id": req.bid_id}
        if req.new_price_btc is not None:
            payload["new_price_sat"] = round(req.new_price_btc * SAT)
        if req.new_amount_btc is not None:
            payload["new_amount_sat"] = round(req.new_amount_btc * SAT)
        if req.new_speed_limit_ph is not None:
            payload["new_speed_limit_ph"] = {"value": req.new_speed_limit_ph}
        resp = await self._http.put("/spot/bid", json=payload, headers=_headers())
        if not resp.is_success:
            logger.error("edit_bid failed — bid_id=%r status=%d body=%r",
                         req.bid_id, resp.status_code, resp.text[:500])
        resp.raise_for_status()

    async def cancel_bid(self, order_id: str) -> dict:
        resp = await self._http.delete("/spot/bid", params={"order_id": order_id}, headers=_headers())
        resp.raise_for_status()
        if not resp.content:
            return {}
        return self._parse(resp)

    # ── Market ────────────────────────────────────────────────────────────────

    async def get_order_book(self) -> OrderBook:
        data = await self._get("/spot/orderbook")
        return OrderBook(**data)

    async def get_market_settings(self) -> dict:
        return await self._get("/spot/settings")

    async def get_market_stats(self) -> dict:
        return await self._get("/spot/stats")

    # ── Account ───────────────────────────────────────────────────────────────

    async def get_balance(self) -> AccountBalance:
        data = await self._get("/account/balance")
        resp = BalancesResponse(**data)
        for acct in resp.accounts:
            return acct
        return AccountBalance()
