"""MockTrade — individual simulated trade within a backtest run."""

from __future__ import annotations

import uuid
from typing import Optional
from datetime import datetime

from sqlalchemy import DateTime, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import JSONBType, TimestampMixin, UUIDPrimaryKeyMixin


class MockTrade(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Simulated trade recorded by the replay engine (MH-07+)."""

    __tablename__ = "mock_trades"

    backtest_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    strategy_config_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    asset: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    side: Mapped[str] = mapped_column(String(10), nullable=False)  # long | short
    entry_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    entry_price: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    stop_price: Mapped[Optional[float]] = mapped_column(Numeric(20, 8), nullable=True)
    target_price: Mapped[Optional[float]] = mapped_column(Numeric(20, 8), nullable=True)
    exit_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    exit_price: Mapped[Optional[float]] = mapped_column(Numeric(20, 8), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")  # open | closed | cancelled
    result: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # win | loss | breakeven | open | cancelled
    pnl_amount: Mapped[Optional[float]] = mapped_column(Numeric(20, 4), nullable=True)
    pnl_pct: Mapped[Optional[float]] = mapped_column(Numeric(10, 6), nullable=True)
    r_multiple: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    reason_for_entry: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reason_for_exit: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONBType, nullable=True)
