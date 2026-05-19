"""SignalOutcome model — records actual result of each auto-paper trade."""

from __future__ import annotations

import uuid
from typing import Optional
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.enums import CatalystType, HorizonLabel, RegimeType, SetupType, TradeDirection
from app.db.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class SignalOutcome(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Captures the actual outcome of an auto-paper trade for AI learning input."""

    __tablename__ = "signal_outcomes"

    signal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("signals.id"), nullable=False, index=True
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id"), nullable=False
    )

    # Signal attributes at time of trade (denormalised for query convenience)
    setup_type: Mapped[Optional[SetupType]] = mapped_column(
        Enum(SetupType, name="setup_type_enum"), nullable=True
    )
    direction: Mapped[Optional[TradeDirection]] = mapped_column(
        Enum(TradeDirection, name="trade_direction_enum"), nullable=True
    )
    horizon_label: Mapped[Optional[HorizonLabel]] = mapped_column(
        Enum(HorizonLabel, name="horizon_label_enum"), nullable=True
    )
    catalyst_type: Mapped[Optional[CatalystType]] = mapped_column(
        Enum(CatalystType, name="catalyst_type_enum"), nullable=True
    )
    regime_at_entry: Mapped[Optional[RegimeType]] = mapped_column(
        Enum(RegimeType, name="signal_regime_type_enum"), nullable=True
    )

    # Trade prices
    entry_price: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    exit_price: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)

    # Outcome flags
    predicted_direction_correct: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    actual_pnl_pct: Mapped[Optional[float]] = mapped_column(Numeric(10, 6), nullable=True)
    # Risk-adjusted quality metrics
    # r_multiple  = (exit - entry) / abs(entry - stop); >1 means reward exceeded risk
    # mae_pct     = max_adverse_excursion / entry_price (worst intra-trade drawdown %)
    # mfe_pct     = max_favorable_excursion / entry_price (best intra-trade gain %)
    r_multiple: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    mae_pct: Mapped[Optional[float]] = mapped_column(Numeric(10, 6), nullable=True)
    mfe_pct: Mapped[Optional[float]] = mapped_column(Numeric(10, 6), nullable=True)

    # Timestamps
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
