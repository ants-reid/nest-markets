import uuid
from typing import Optional
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import JSONBType, CreatedAtMixin, UUIDPrimaryKeyMixin


class EvalRun(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Evaluation run history."""

    __tablename__ = "eval_runs"

    prompt_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("prompt_versions.id"), nullable=True)
    model_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("model_versions.id"), nullable=True)
    provider_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    summary_score: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    pass_rate: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    output_json: Mapped[Optional[dict]] = mapped_column(JSONBType, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
