import uuid
from typing import Optional
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class Quote(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Latest quote and spread quality."""

    __tablename__ = "quotes"
    __table_args__ = (
        Index("ix_quotes_asset_ts", "asset_id", "ts"),
    )

    asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assets.id"), nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    bid: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    ask: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    mid: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    spread_abs: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    spread_bps: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
