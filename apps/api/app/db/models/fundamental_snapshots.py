"""FundamentalSnapshot — company fundamentals at a point in time."""

from __future__ import annotations

import uuid
from typing import Optional
from datetime import date

from sqlalchemy import Date, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import CreatedAtMixin, JSONBType, UUIDPrimaryKeyMixin


class FundamentalSnapshot(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Point-in-time fundamentals snapshot for an asset."""

    __tablename__ = "fundamental_snapshots"
    __table_args__ = (
        UniqueConstraint("asset_id", "snapshot_date", name="uq_fundamental_snapshots_asset_date"),
    )

    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    pe_ratio: Mapped[Optional[float]] = mapped_column(Numeric(18, 4), nullable=True)
    price_to_book: Mapped[Optional[float]] = mapped_column(Numeric(18, 4), nullable=True)
    debt_to_equity: Mapped[Optional[float]] = mapped_column(Numeric(18, 4), nullable=True)
    current_ratio: Mapped[Optional[float]] = mapped_column(Numeric(18, 4), nullable=True)
    roa: Mapped[Optional[float]] = mapped_column(Numeric(18, 4), nullable=True)
    roe: Mapped[Optional[float]] = mapped_column(Numeric(18, 4), nullable=True)
    gross_margin: Mapped[Optional[float]] = mapped_column(Numeric(18, 4), nullable=True)
    net_margin: Mapped[Optional[float]] = mapped_column(Numeric(18, 4), nullable=True)
    dividend_yield: Mapped[Optional[float]] = mapped_column(Numeric(18, 4), nullable=True)
    free_cash_flow: Mapped[Optional[float]] = mapped_column(Numeric(18, 4), nullable=True)
    revenue: Mapped[Optional[float]] = mapped_column(Numeric(24, 2), nullable=True)
    earnings: Mapped[Optional[float]] = mapped_column(Numeric(24, 2), nullable=True)
    extra_metadata: Mapped[Optional[dict]] = mapped_column(JSONBType, nullable=True)
