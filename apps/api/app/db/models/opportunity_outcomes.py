"""OpportunityOutcome — execution outcome labels for learning loop."""

from __future__ import annotations

import uuid
from typing import Optional
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.enums import ExecutionOutcomeStatus
from app.db.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class OpportunityOutcome(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Realized outcome for an executed opportunity (labels for training)."""

    __tablename__ = "opportunity_outcomes"
    __table_args__ = (
        Index("ix_opp_outcomes_opportunity_id", "opportunity_id"),
    )

    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scored_opportunities.id", ondelete="CASCADE"), nullable=False
    )
    signal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("signals.id", ondelete="CASCADE"), nullable=False
    )
    execution_status: Mapped[ExecutionOutcomeStatus] = mapped_column(
        Enum(ExecutionOutcomeStatus, name="execution_outcome_status_enum"), nullable=False
    )
    outcome_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    entry_price: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    exit_price: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    realized_pnl: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    realized_pnl_pct: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    expected_pnl_pct: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    slippage_pct: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    mfe_pct: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    mae_pct: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    r_multiple: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    exit_reason: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    execution_quality_score: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    outcome_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
