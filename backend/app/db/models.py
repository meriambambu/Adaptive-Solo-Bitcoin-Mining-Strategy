from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class StrategyLog(Base):
    """One row per strategy evaluation cycle decision."""

    __tablename__ = "strategy_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    order_id: Mapped[str] = mapped_column(String(64), index=True)
    action: Mapped[str] = mapped_column(String(32))  # RAISE | LOWER | HOLD | IDLE | ERROR
    old_price: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    new_price: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    market_p_n: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    reason: Mapped[str] = mapped_column(Text, default="")


class BidSnapshot(Base):
    """Periodic snapshot of active bid state — used for history charts."""

    __tablename__ = "bid_snapshot"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    order_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32))
    price: Mapped[float] = mapped_column(Numeric(18, 8))
    accepted_speed: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    available_amount: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    is_in_top_n: Mapped[bool] = mapped_column(Boolean, default=False)
