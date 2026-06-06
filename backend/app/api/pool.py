"""Braiins Solo pool notable shares and BTC network difficulty."""

import httpx
from fastapi import APIRouter, HTTPException

from app.config import get_settings

router = APIRouter(prefix="/api/pool", tags=["pool"])

SOLO_BASE = "https://solo.braiins.com/users"
DIFFICULTY_URL = "https://blockchain.info/q/getdifficulty"


@router.get("/stats")
async def get_pool_stats():
    """
    Fetch notable shares and summary stats from solo.braiins.com.
    The wallet address is read from SOLO_WALLET in .env and never returned
    in any response field.
    """
    cfg = get_settings()
    if not cfg.solo_wallet:
        raise HTTPException(status_code=503, detail="SOLO_WALLET not configured in .env")

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(f"{SOLO_BASE}/{cfg.solo_wallet}")
        resp.raise_for_status()
        data = resp.json()

    # Strip username/wallet fields from each notable share before returning
    shares = [
        {
            "timestamp": s["timestamp"],
            "diff": s["diff"],
            "worker": s.get("worker", ""),
            "hashrate5m": s.get("hashrate5m", 0),
        }
        for s in (data.get("notable_shares") or [])
    ]

    return {
        "notable_shares": shares,
        "bestshare": data.get("bestshare", 0),
        "bestever": data.get("bestever", 0),
        "hashrate1m": data.get("hashrate1m", 0),
        "hashrate1hr": data.get("hashrate1hr", 0),
        "hashrate1d": data.get("hashrate1d", 0),
    }


@router.get("/workers")
async def get_pool_workers():
    """
    Return solo pool workers that received hashrate in the last hour.
    Hashrate values are converted from raw H/s → PH/s to match the
    marketplace bid worker format used by WorkerCards.
    Username / wallet fields are never returned.
    """
    cfg = get_settings()
    if not cfg.solo_wallet:
        return []

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(f"{SOLO_BASE}/{cfg.solo_wallet}")
        resp.raise_for_status()
        data = resp.json()

    PH = 1e15  # raw H/s → PH/s

    raw_workers = data.get("workers") or []
    if not isinstance(raw_workers, list):
        raw_workers = []

    workers = []
    for w in raw_workers:
        if w.get("hashrate1hr", 0) <= 0:
            continue
        workers.append({
            "name": w.get("workername", ""),
            "source": "pool",
            "lastshare_ts": w.get("lastshare", 0),
            "speed_now_ph": w.get("hashrate1m", 0) / PH,
            "speed_5m_ph": w.get("hashrate5m", 0) / PH,
            "speed_1h_ph": w.get("hashrate1hr", 0) / PH,
            "speed_24h_ph": w.get("hashrate1d", 0) / PH,
            "shares_m": w.get("shares", 0) / 1e6,
            "bestshare": w.get("bestshare", 0),
        })
    return workers


@router.get("/difficulty")
async def get_btc_difficulty():
    """Current Bitcoin network difficulty from blockchain.info."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(DIFFICULTY_URL)
        resp.raise_for_status()
        return {"difficulty": float(resp.text.strip())}
