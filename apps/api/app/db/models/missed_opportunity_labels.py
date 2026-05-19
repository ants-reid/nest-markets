"""MissedOpportunityLabel — hypothetical outcomes for non-executed opportunities."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin
from typing import Optional


class MissedOpportunityLabel(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Counterfactual labels for opportunities that were NOT executed."""

    __tablename__ = "missed_opportunity_labels"

    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scored_opportunities.id", ondelete="CASCADE"), nullable=False
    )
    signal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("signals.id", ondelete="CASCADE"), nullable=False
    )
    reason_not_executed: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    hypothetical_entry: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    hypothetical_exit: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    hypothetical_pnl_pct: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    hypothetical_drawdown: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    actual_market_move_pct: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    opportunity_value_label: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
