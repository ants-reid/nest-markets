import uuid
from typing import Optional
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class Bar(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """OHLCV bar history."""

    __tablename__ = "bars"
    __table_args__ = (
        UniqueConstraint("asset_id", "timeframe", "ts", name="uq_bars_asset_timeframe_ts"),
        Index("ix_bars_asset_timeframe_ts", "asset_id", "timeframe", "ts"),
    )

    asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assets.id"), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    open: Mapped[float] = mapped_column(Numeric(18, 8), nullable=False)
    high: Mapped[float] = mapped_column(Numeric(18, 8), nullable=False)
    low: Mapped[float] = mapped_column(Numeric(18, 8), nullable=False)
    close: Mapped[float] = mapped_column(Numeric(18, 8), nullable=False)
    volume: Mapped[Optional[float]] = mapped_column(Numeric(22, 8), nullable=True)
    vwap: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
