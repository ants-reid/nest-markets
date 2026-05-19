from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class TradingHalt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Recorded trading halt state for future enforcement phases."""

    __tablename__ = "trading_halts"

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", server_default="active")
    halt_type: Mapped[str] = mapped_column(String(20), nullable=False, default="manual", server_default="manual")
    scope: Mapped[str] = mapped_column(String(50), nullable=False, default="global", server_default="global")
    trading_mode: Mapped[str | None] = mapped_column(String(20), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    triggered_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)