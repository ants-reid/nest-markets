"""QualityReviewAudit — append-only audit trail for data quality triage decisions (MH-13)."""

from __future__ import annotations

from typing import Optional
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class QualityReviewAudit(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One audit entry per review decision on a quality report.

    Append-only: new row per save, never updated in-place.
    """

    __tablename__ = "quality_review_audits"

    report_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("market_data_quality_reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asset_symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    provider: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    previous_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    new_status: Mapped[str] = mapped_column(String(50), nullable=False)
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
