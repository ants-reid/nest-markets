"""BaselineCandidate — research-stage candidate from strategy lab results."""

from __future__ import annotations

import uuid
from typing import Optional
from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import JSONBType, TimestampMixin, UUIDPrimaryKeyMixin


class BaselineCandidate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Research-stage baseline candidate. Not an activation or live approval."""

    __tablename__ = "baseline_candidates"

    backtest_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    strategy_config_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    ai_backtest_report_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )

    asset: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    strategy_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    parameters: Mapped[dict] = mapped_column(JSONBType, nullable=False, default=dict)
    metrics: Mapped[dict] = mapped_column(JSONBType, nullable=False, default=dict)

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="watchlist_candidate",
        index=True,
    )
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
