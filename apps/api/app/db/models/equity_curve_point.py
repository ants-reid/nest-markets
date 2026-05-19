"""EquityCurvePoint — one snapshot of portfolio equity during a backtest run."""

from __future__ import annotations

import uuid
from typing import Optional
from datetime import datetime

from sqlalchemy import DateTime, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class EquityCurvePoint(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Single equity snapshot written by the replay engine (MH-07+)."""

    __tablename__ = "equity_curve_points"

    backtest_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    equity: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False)
    cash: Mapped[Optional[float]] = mapped_column(Numeric(20, 4), nullable=True)
    open_pnl: Mapped[Optional[float]] = mapped_column(Numeric(20, 4), nullable=True)
    drawdown_pct: Mapped[Optional[float]] = mapped_column(Numeric(10, 6), nullable=True)
