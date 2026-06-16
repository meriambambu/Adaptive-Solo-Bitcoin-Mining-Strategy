from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.braiins.client import BraiinsClient
from app.db.database import get_db
from app.db.models import StrategyLog
from app.dependencies import get_client
from app.strategy.adaptive import run_strategy_cycle

router = APIRouter(prefix="/api/strategy", tags=["strategy"])


@router.post("/evaluate")
async def manual_evaluate(
    client: BraiinsClient = Depends(get_client),
    db: Session = Depends(get_db),
):
    """Manually trigger one strategy evaluation cycle."""
    result = await run_strategy_cycle(client, db)
    return result


@router.get("/logs")
async def get_logs(limit: int = 50, db: Session = Depends(get_db)):
    logs = (
        db.query(StrategyLog)
        .order_by(StrategyLog.timestamp.desc())
        .limit(min(limit, 200))
        .all()
    )
    return [
        {
            "id": log.id,
            "timestamp": log.timestamp.isoformat() + "Z",
            "order_id": log.order_id,
            "action": log.action,
            "old_price": str(log.old_price) if log.old_price else None,
            "new_price": str(log.new_price) if log.new_price else None,
            "market_p_n": str(log.market_p_n) if log.market_p_n else None,
            "reason": log.reason,
        }
        for log in logs
    ]
