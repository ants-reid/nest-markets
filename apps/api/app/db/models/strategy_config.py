"""StrategyConfig — persisted configuration for a Strategy Lab strategy."""

from __future__ import annotations

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import JSONBType, TimestampMixin, UUIDPrimaryKeyMixin


class StrategyConfig(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Defines one named strategy with its parameters and risk settings."""

    __tablename__ = "strategy_configs"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    strategy_type: Mapped[str] = mapped_column(String(100), nullable=False)
    asset: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    parameters: Mapped[dict] = mapped_column(JSONBType, nullable=False, default=dict)
    risk_settings: Mapped[dict] = mapped_column(JSONBType, nullable=False, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
