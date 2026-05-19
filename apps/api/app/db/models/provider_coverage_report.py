"""ProviderCoverageReport — per-provider coverage snapshot across all tracked assets."""

from __future__ import annotations

from typing import Optional
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import CreatedAtMixin, JSONBType, UUIDPrimaryKeyMixin


class ProviderCoverageReport(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Coverage snapshot for one provider across assets and timeframes."""

    __tablename__ = "provider_coverage_reports"

    provider: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Total assets tracked in the universe at evaluation time
    total_assets: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Assets for which this provider has at least one bar
    covered_assets: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Aggregate percentage of covered assets
    coverage_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # Earliest and latest bars available across ALL assets for this provider
    earliest_bar_ts: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    latest_bar_ts: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    # Total bar rows held
    total_bars: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONBType, nullable=True)
