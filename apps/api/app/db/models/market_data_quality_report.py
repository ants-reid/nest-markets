"""MarketDataQualityReport — per-asset/timeframe quality summary snapshot."""

from __future__ import annotations

from typing import Optional
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column


from app.db.base import Base
from app.db.models.mixins import CreatedAtMixin, JSONBType, UUIDPrimaryKeyMixin


class MarketDataQualityReport(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Snapshot of bar quality metrics for one (asset_symbol, timeframe) pair."""

    __tablename__ = "market_data_quality_reports"

    asset_symbol: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    provider: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expected_bars: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    actual_bars: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_bars: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Completeness: ratio of bars present vs expected in date range
    completeness_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # Missing / duplicate / stale counts
    missing_bars: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate_bars: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bad_price_bars: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    suspicious_spike_bars: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stale_bars: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Date span of available data
    earliest_bar_ts: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    latest_bar_ts: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    # Freeform quality notes or anomaly description
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # MH-02 quality scoring
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    approved_for_backtest: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Optional extra metadata
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONBType, nullable=True)
    # MH-12 / MH-13 triage review
    review_status: Mapped[str] = mapped_column(String(50), nullable=False, default="unreviewed", server_default="unreviewed")
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
