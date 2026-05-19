"""ScoreModelEvaluation — validation results from training pipeline runs."""

from __future__ import annotations

import uuid
from typing import Optional
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import CreatedAtMixin, JSONBType, UUIDPrimaryKeyMixin


class ScoreModelEvaluation(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Validation results for a trained scoring model."""

    __tablename__ = "score_model_evaluations"
    __table_args__ = (
        UniqueConstraint("model_registry_id", "evaluation_run_id", "metric_name",
                         name="uq_sme_model_run_metric"),
    )

    model_registry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("score_model_registry.id", ondelete="RESTRICT"), nullable=False
    )
    evaluation_run_id: Mapped[str] = mapped_column(String(255), nullable=False)
    evaluation_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    validation_strategy: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    metric_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    metric_value: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    metric_details: Mapped[Optional[dict]] = mapped_column(JSONBType, nullable=True)
    passed_gates: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    gate_failures: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)
    evaluated_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
