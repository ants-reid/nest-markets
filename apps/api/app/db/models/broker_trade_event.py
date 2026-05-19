from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import JSONBType, CreatedAtMixin, UUIDPrimaryKeyMixin


class BrokerTradeEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Normalized broker trade/fill event with stable provenance."""

    __tablename__ = "broker_trade_events"
    __table_args__ = (
        UniqueConstraint("event_fingerprint", name="uq_broker_trade_event_fingerprint"),
    )

    broker_provider: Mapped[str] = mapped_column(String(50), nullable=False, default="ibkr")
    account_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(80), nullable=False, default="broker_account_trades")

    event_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    external_trade_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    broker_order_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)

    symbol: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    side: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    quantity: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    fill_price: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    commission: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    net_amount: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    realized_pnl: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)

    trade_ts: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONBType, nullable=True)
    raw_json: Mapped[Optional[dict]] = mapped_column(JSONBType, nullable=True)
