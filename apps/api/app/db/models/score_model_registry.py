"""ScoreModelRegistry — trained scoring model registry."""

from __future__ import annotations

from typing import Optional
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.enums import ModelRegistryStatus
from app.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ScoreModelRegistry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Registry of all trained scoring models."""

    __tablename__ = "score_model_registry"
    __table_args__ = (
        UniqueConstraint("strategy_bucket", "asset_class", "version_number",
                         name="uq_smr_bucket_asset_version"),
        Index("ix_smr_status", "status"),
        Index("ix_smr_is_active", "is_active"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    strategy_bucket: Mapped[str] = mapped_column(String(100), nullable=False)
    asset_class: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    training_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    trained_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[ModelRegistryStatus] = mapped_column(
        Enum(ModelRegistryStatus, name="model_registry_status_enum"), nullable=False,
        default=ModelRegistryStatus.CANDIDATE,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    promoted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    promoted_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
