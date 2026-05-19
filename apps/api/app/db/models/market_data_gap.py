"""MarketDataGap — records a detected gap in bar history for one asset/timeframe."""

from __future__ import annotations

import uuid
from typing import Optional
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class MarketDataGap(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """A detected gap in the bar sequence for (asset_symbol, timeframe)."""

    __tablename__ = "market_data_gaps"

    asset_symbol: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    provider: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # Inclusive gap boundaries
    gap_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    gap_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expected_candles_missing: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="low")
    # Resolution state
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="open")
    # status values: open | filling | resolved | ignored
    # Import run that created or resolved this gap record (nullable — may be manual)
    import_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
