"""ProviderAssetCoverage — per (provider, asset, timeframe) coverage row.

MH-02: One row per provider+asset+timeframe combination, upserted after
each import run. Stores actual available date range and candle counts.
Unique on (provider, asset_symbol, timeframe) so subsequent imports update
the same row rather than appending duplicates.
"""

from __future__ import annotations

import uuid
from typing import Optional
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ProviderAssetCoverage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Granular per-provider, per-asset, per-timeframe coverage record.

    Distinct from ``ProviderCoverageReport`` (which is an aggregate snapshot
    across ALL assets for a provider). This table has one row per unique
    (provider, asset_symbol, timeframe) tuple and is updated in-place on
    each import run.
    """

    __tablename__ = "provider_asset_coverage"
    __table_args__ = (
        UniqueConstraint("provider", "asset_symbol", "timeframe", name="uq_pac_provider_asset_tf"),
    )

    provider: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    asset_symbol: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)

    # Date range requested during last import
    requested_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    requested_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Actual date range available from provider (may be less than requested)
    available_from: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    available_to: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    candle_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    missing_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    approved_for_backtest: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    limitations: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # FK-style reference (soft, no FK constraint to avoid cascade headaches)
    last_import_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    evaluated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
