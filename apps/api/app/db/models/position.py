import uuid
from typing import Optional
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.enums import PositionStatus
from app.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Position(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Paper or live position record."""

    __tablename__ = "positions"

    asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assets.id"), nullable=False)
    signal_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("signals.id"), nullable=True)
    status: Mapped[PositionStatus] = mapped_column(Enum(PositionStatus, name="position_status_enum"), nullable=False)
    side: Mapped[str] = mapped_column(String(20), nullable=False)
    avg_entry_price: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    current_price: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    stop_price: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    target_price: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    qty: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    opened_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    close_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    realized_pnl: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    unrealized_pnl: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    max_favorable_excursion: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    max_adverse_excursion: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    broker_order_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ibkr_con_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    market_value: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    commission_paid: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    # Set to actual broker fill price when available; close worker falls back to target proxy
    close_price: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    # MH-146 — open-time attribution. Distinguishes auto_paper / manual_paper / live / unknown.
    # Default 'unknown' so legacy rows backfill safely. NEW writes should set this explicitly.
    opened_by: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="unknown", default="unknown"
    )
