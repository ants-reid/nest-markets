from sqlalchemy import Boolean, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from typing import Optional


class RiskProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """User-defined risk profile and capital caps."""

    __tablename__ = "risk_profiles"

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    is_active: Mapped[str] = mapped_column(String(20), nullable=False, default="inactive", server_default="inactive")
    max_capital_allocated: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    max_risk_per_trade_pct: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    max_daily_drawdown_pct: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    max_open_positions: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    max_correlated_positions: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    max_correlated_bucket_exposure: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    min_confidence: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    min_signal_score: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    max_spread_bps_fx: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    max_spread_bps_equity: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    cooldown_after_3_losses_min: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    auto_trade_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    confirm_before_trade_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    kill_switch_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
