"""DrawdownPeriod — one identified drawdown window within a backtest run."""

from __future__ import annotations

import uuid
from typing import Optional
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class DrawdownPeriod(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Identified underwater period written by the replay engine (MH-07+)."""

    __tablename__ = "drawdown_periods"

    backtest_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    trough_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    max_drawdown_pct: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    duration_candles: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    recovered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
