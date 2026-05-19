from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Boolean, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class RiskLimitConfig(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Configurable, future-facing risk limits for trading controls."""

    __tablename__ = "risk_limit_configs"

    scope: Mapped[str] = mapped_column(String(50), nullable=False, default="global", server_default="global")
    trading_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="paper", server_default="paper")
    max_order_notional: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    daily_loss_limit_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    daily_loss_limit_pct: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    max_open_positions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_total_exposure: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    max_symbol_exposure: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    max_trades_per_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    min_cash_buffer: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)