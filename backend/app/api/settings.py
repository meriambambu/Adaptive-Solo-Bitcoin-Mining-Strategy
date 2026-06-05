from decimal import Decimal
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import get_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


class StrategySettingsUpdate(BaseModel):
    top_n: Optional[int] = None
    max_bid_price: Optional[Decimal] = None
    poll_interval: Optional[int] = None
    rank_check_interval: Optional[int] = None
    strategy_enabled: Optional[bool] = None
    rank_drop_threshold: Optional[int] = None
    lower_cooldown: Optional[int] = None


@router.get("")
async def get_settings_endpoint():
    cfg = get_settings()
    return {
        "top_n": cfg.top_n,
        "max_bid_price": str(cfg.max_bid_price),
        "poll_interval": cfg.poll_interval,
        "rank_check_interval": cfg.rank_check_interval,
        "strategy_enabled": cfg.strategy_enabled,
        "rank_drop_threshold": cfg.rank_drop_threshold,
        "lower_cooldown": cfg.lower_cooldown,
    }


@router.patch("")
async def update_settings(update: StrategySettingsUpdate):
    """
    Update strategy parameters at runtime without restart.
    Changes are applied in-memory; to persist across restarts update .env too.
    """
    cfg = get_settings()
    changed = {}
    for field, value in update.model_dump(exclude_none=True).items():
        if hasattr(cfg, field):
            object.__setattr__(cfg, field, value)
            changed[field] = str(value)
    return {"updated": changed}
