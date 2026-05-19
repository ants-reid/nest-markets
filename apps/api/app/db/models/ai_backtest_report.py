"""AIBacktestReport — persisted AI research report for a backtest run."""

from __future__ import annotations

import uuid

from sqlalchemy import Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import JSONBType, TimestampMixin, UUIDPrimaryKeyMixin
from typing import Optional


class AIBacktestReport(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Persisted AI research report generated for a strategy backtest run."""

    __tablename__ = "ai_backtest_reports"

    backtest_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    report_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="comparison_review"
    )
    focus: Mapped[str] = mapped_column(
        String(50), nullable=False, default="balanced"
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="completed", index=True
    )
    model_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    input_summary: Mapped[Optional[dict]] = mapped_column(JSONBType, nullable=True)
    report_json: Mapped[Optional[dict]] = mapped_column(JSONBType, nullable=True)
    plain_english_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
