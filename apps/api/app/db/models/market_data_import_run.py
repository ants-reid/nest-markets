"""MarketDataImportRun — tracks a single historical bar import attempt."""

from __future__ import annotations

import uuid
from typing import Optional
from datetime import datetime

from sqlalchemy import DateTime, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class MarketDataImportRun(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One import attempt for a (provider, asset, timeframe, date range) tuple."""

    __tablename__ = "market_data_import_runs"

    # Groups multiple per-asset runs that belong to one POST /research/data/import request
    batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)

    provider: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    asset_symbol: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    from_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    to_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rows_requested: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rows_upserted: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rows_skipped: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    # status values: pending | running | complete | failed | partial
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Numeric(10, 3), nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
