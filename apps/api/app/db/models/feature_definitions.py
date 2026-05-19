"""FeatureDefinition — metadata about all engineered features."""

from __future__ import annotations

from sqlalchemy import Boolean, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin
from typing import Optional


class FeatureDefinition(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Registry of feature definitions with PIT-safety and normalization rules."""

    __tablename__ = "feature_definitions"

    feature_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    feature_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    computation_rule: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_data_types: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)
    pit_safe: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    lookback_bars: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    default_value: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    normalization_rule: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    na_handling: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
