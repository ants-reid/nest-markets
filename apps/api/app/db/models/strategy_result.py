"""StrategyResult — aggregate performance metrics for a backtest run."""

from __future__ import annotations

import uuid

from sqlalchemy import Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import JSONBType, TimestampMixin, UUIDPrimaryKeyMixin
from typing import Optional


class StrategyResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Aggregate performance metrics produced by the replay engine (MH-07+)."""

    __tablename__ = "strategy_results"

    backtest_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    strategy_config_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    asset: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    timeframe: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    total_trades: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    wins: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    losses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    breakeven: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    win_rate: Mapped[Optional[float]] = mapped_column(Numeric(10, 6), nullable=True)
    average_win: Mapped[Optional[float]] = mapped_column(Numeric(20, 4), nullable=True)
    average_loss: Mapped[Optional[float]] = mapped_column(Numeric(20, 4), nullable=True)
    profit_factor: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    expectancy: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    total_return_pct: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    max_drawdown_pct: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    score: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    metrics: Mapped[Optional[dict]] = mapped_column(JSONBType, nullable=True)
