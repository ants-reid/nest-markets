"""Paper validation evidence model for MH-17."""

from __future__ import annotations

import uuid
from typing import Optional
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import JSONBType, TimestampMixin, UUIDPrimaryKeyMixin


class PaperValidationEvidence(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Evidence record linking paper execution data to a validation plan.

    This table is intentionally read-only for execution systems.
    Evidence is ingested manually or via the reconciliation service only.
    No live trading is affected by these records.
    """

    __tablename__ = "paper_validation_evidence"

    paper_validation_plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("paper_validation_plans.id"),
        nullable=False,
        index=True,
    )

    # Where the evidence came from
    source_type: Mapped[str] = mapped_column(
        String(50), nullable=False  # paper_order | paper_fill | signal_outcome | manual
    )
    source_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    # Confidence of the linkage to this plan
    confidence: Mapped[str] = mapped_column(
        String(20), nullable=False, default="manual"  # high | medium | low | manual
    )

    # Trade metadata
    asset: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    timeframe: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    side: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Timestamps
    opened_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Execution prices
    entry_price: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    exit_price: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)

    # P&L
    pnl_amount: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    pnl_pct: Mapped[Optional[float]] = mapped_column(Numeric(12, 6), nullable=True)
    r_multiple: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)

    # Outcome classification
    result: Mapped[str] = mapped_column(
        String(20), nullable=False, default="unknown"  # win | loss | breakeven | open | unknown
    )

    # Additional context
    payload: Mapped[Optional[dict]] = mapped_column(JSONBType, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Metric inclusion flag
    included_in_metrics: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
