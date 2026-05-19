"""BacktestRun — persisted stub for a Strategy Lab backtest execution."""

from __future__ import annotations

from typing import Optional
from datetime import datetime

from sqlalchemy import DateTime, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import JSONBType, TimestampMixin, UUIDPrimaryKeyMixin


class BacktestRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One backtest execution record. Replay engine wired in MH-07."""

    __tablename__ = "backtest_runs"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="queued", index=True)
    date_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    date_to: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    requested_assets: Mapped[dict] = mapped_column(JSONBType, nullable=False, default=dict)
    requested_timeframes: Mapped[dict] = mapped_column(JSONBType, nullable=False, default=dict)
    strategy_config_ids: Mapped[dict] = mapped_column(JSONBType, nullable=False, default=dict)
    starting_capital: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False, default=10000)
    result_summary: Mapped[Optional[dict]] = mapped_column(JSONBType, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
