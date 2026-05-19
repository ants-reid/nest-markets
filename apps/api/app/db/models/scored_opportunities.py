"""ScoredOpportunity — all signals after composite scoring."""

from __future__ import annotations

import uuid
from typing import Optional
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import CreatedAtMixin, JSONBType, UUIDPrimaryKeyMixin


class ScoredOpportunity(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Composite-scored version of a signal ready for ranking."""

    __tablename__ = "scored_opportunities"
    __table_args__ = (
        Index("ix_scored_opp_signal_id", "signal_id"),
        Index("ix_scored_opp_asset_scored_at", "asset_id", "scored_at"),
    )

    signal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("signals.id", ondelete="CASCADE"), nullable=False
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    score: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    score_components: Mapped[Optional[dict]] = mapped_column(JSONBType, nullable=True)
    model_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("score_model_registry.id", ondelete="SET NULL"), nullable=True
    )
    regime_tag: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    bucket_assignment: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expected_move_pct: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    expected_drawdown_pct: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    do_not_trade_probability: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    scored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
