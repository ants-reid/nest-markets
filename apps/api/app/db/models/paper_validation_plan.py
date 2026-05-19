"""Paper validation plan model for MH-16 gate workflow."""

from __future__ import annotations

import uuid
from typing import Optional
from datetime import datetime

from sqlalchemy import DateTime, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import JSONBType, TimestampMixin, UUIDPrimaryKeyMixin


class PaperValidationPlan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Validation gate plan linking a baseline candidate to paper proof requirements."""

    __tablename__ = "paper_validation_plans"

    baseline_candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    backtest_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    strategy_config_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )

    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending", index=True
    )

    required_trades: Mapped[int] = mapped_column(nullable=False, default=100)
    minimum_days: Mapped[int] = mapped_column(nullable=False, default=30)

    target_profit_factor: Mapped[Optional[float]] = mapped_column(Numeric(12, 6), nullable=True)
    max_drawdown_pct: Mapped[Optional[float]] = mapped_column(Numeric(12, 6), nullable=True)
    max_daily_loss_pct: Mapped[Optional[float]] = mapped_column(Numeric(12, 6), nullable=True)
    starting_paper_capital: Mapped[float] = mapped_column(
        Numeric(18, 4), nullable=False, default=200000
    )

    backtest_metrics: Mapped[Optional[dict]] = mapped_column(JSONBType, nullable=True)
    paper_metrics: Mapped[Optional[dict]] = mapped_column(JSONBType, nullable=True)
    progress: Mapped[Optional[dict]] = mapped_column(JSONBType, nullable=True)
    pass_fail_reasons: Mapped[Optional[list | dict]] = mapped_column(JSONBType, nullable=True)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
