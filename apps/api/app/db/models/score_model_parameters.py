"""ScoreModelParameters — configurable scoring weights per bucket and regime."""

from __future__ import annotations

import uuid
from typing import Optional
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class ScoreModelParameters(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Configurable scoring parameters per model, bucket, and regime."""

    __tablename__ = "score_model_parameters"
    __table_args__ = (
        UniqueConstraint("model_registry_id", "parameter_name", "regime_tag",
                         name="uq_smp_model_param_regime"),
    )

    model_registry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("score_model_registry.id", ondelete="RESTRICT"), nullable=False
    )
    parameter_name: Mapped[str] = mapped_column(String(255), nullable=False)
    parameter_value: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    min_value: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    max_value: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    parameter_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    regime_tag: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    effective_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    deprecated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
