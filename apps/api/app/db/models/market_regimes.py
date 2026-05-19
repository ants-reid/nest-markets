"""MarketRegime — historical and current market regime classifications."""

from __future__ import annotations

from typing import Optional
from datetime import date

from sqlalchemy import Date, Enum, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.enums import MarketRegimeType
from app.db.models.mixins import CreatedAtMixin, JSONBType, UUIDPrimaryKeyMixin


class MarketRegime(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Classification of market condition for a specific time window."""

    __tablename__ = "market_regimes"
    __table_args__ = (
        UniqueConstraint("regime_name", "start_date", name="uq_market_regimes_name_start"),
        Index("ix_market_regimes_start_date", "start_date"),
    )

    regime_name: Mapped[str] = mapped_column(String(100), nullable=False)
    regime_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    characteristics: Mapped[Optional[dict]] = mapped_column(JSONBType, nullable=True)
    volatility_percentile: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    trend_direction: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    liquidity_condition: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    regime_type: Mapped[MarketRegimeType] = mapped_column(
        Enum(MarketRegimeType, name="market_regime_type_enum"), nullable=False
    )
