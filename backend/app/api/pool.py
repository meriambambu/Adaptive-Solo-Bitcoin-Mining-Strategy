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


def _parse_hashrate_ph(val) -> float:
    """Parse solo.braiins.com hashrate strings (e.g. '72.2T', '2.44P') into PH/s."""
    if not val:
        return 0.0
    s = str(val).strip()
    try:
        if s.endswith('E'):
            return float(s[:-1]) * 1000        # EH/s → PH/s
        if s.endswith('P'):
            return float(s[:-1])               # already PH/s
        if s.endswith('T'):
            return float(s[:-1]) / 1000        # TH/s → PH/s
        if s.endswith('G'):
            return float(s[:-1]) / 1_000_000   # GH/s → PH/s
        return float(s) / 1e15                 # raw H/s → PH/s
    except ValueError:
        return 0.0


@router.get("/workers")
async def get_pool_workers():
    """
    Return solo pool workers that received hashrate in the last hour.
    Hashrate values are converted to PH/s to match the marketplace bid
    worker format used by WorkerCards. Username / wallet fields are never returned.
    Note: solo.braiins.com returns hashrates as strings (e.g. "72.2T", "2.44P").
    The "worker" key (singular) holds the array; "workers" (plural) is just a count.
    """
    cfg = get_settings()
    if not cfg.solo_wallet:
        return []

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(f"{SOLO_BASE}/{cfg.solo_wallet}")
        resp.raise_for_status()
        data = resp.json()

    raw_workers = data.get("worker") or []  # singular "worker" = array; "workers" = int count
    if not isinstance(raw_workers, list):
        raw_workers = []

    workers = []
    for w in raw_workers:
        if _parse_hashrate_ph(w.get("hashrate1hr")) <= 0:
            continue
        workers.append({
            "name": w.get("workername", ""),
            "source": "pool",
            "lastshare_ts": w.get("lastshare", 0),
            "speed_now_ph": _parse_hashrate_ph(w.get("hashrate1m")),
            "speed_5m_ph": _parse_hashrate_ph(w.get("hashrate5m")),
            "speed_1h_ph": _parse_hashrate_ph(w.get("hashrate1hr")),
            "speed_24h_ph": _parse_hashrate_ph(w.get("hashrate1d")),
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
