"""Paper trading recommendation draft model."""
import uuid
from typing import Optional
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import JSONBType, CreatedAtMixin, UUIDPrimaryKeyMixin


class PaperRecommendationStatus(str, Enum):
    """Status lifecycle for recommendation drafts."""

    DRAFT = "draft"  # Initial state; can be edited
    REVIEWED = "reviewed"  # Reviewed by operator; awaiting decision
    APPROVED = "approved"  # Approved for execution
    REJECTED = "rejected"  # Rejected; will not execute
    EXECUTED = "executed"  # Orders from this recommendation have been submitted


class PaperRecommendation(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Draft recommendation for paper trading, generated from a strategy or opportunity."""

    __tablename__ = "paper_recommendations"
    __table_args__ = (
        Index("ix_paper_recommendations_signal", "signal_id"),
        Index("ix_paper_recommendations_model", "model_version_id"),
        Index("ix_paper_recommendations_status_ts", "status", "created_at"),
    )

    # Foreign keys to source entities
    signal_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("signals.id"), nullable=True)
    model_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("model_versions.id"), nullable=True
    )

    # Recommended order details
    ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    side: Mapped[str] = mapped_column(String(20), nullable=False)  # BUY or SELL
    quantity: Mapped[float] = mapped_column(Numeric(18, 8), nullable=False)
    order_type: Mapped[str] = mapped_column(String(50), nullable=False)  # MARKET, LIMIT, etc.
    limit_price: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)

    # Metrics and context
    confidence: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)  # 0.0-1.0
    risk_score: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)  # Higher = riskier
    estimated_notional: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Status and review
    status: Mapped[str] = mapped_column(String(50), nullable=False, default=PaperRecommendationStatus.DRAFT)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Operator username
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Execution tracking
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    paper_order_ids: Mapped[list[str] | None] = mapped_column(JSONBType, nullable=True)  # IDs of submitted orders

    # Audit/source info (JSON for flexibility)
    source_metadata: Mapped[Optional[dict]] = mapped_column(JSONBType, nullable=True)
