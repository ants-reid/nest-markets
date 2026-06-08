import uuid
from typing import Optional
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.enums import OrderStatus
from app.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class PaperOrder(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Simulated order record."""

    __tablename__ = "paper_orders"

    signal_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("signals.id"), nullable=True)
    asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    risk_decision_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    order_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    side: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    direction: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    qty: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    quantity: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    filled_quantity: Mapped[float] = mapped_column(Numeric(18, 8), nullable=False, default=0.0, server_default="0.0")
    notional: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    limit_price: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    stop_price: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    status_raw: Mapped[str] = mapped_column("status", String(50), nullable=False, default="pending")
    timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    broker_order_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    commission: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    avg_fill_price: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    ibkr_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    @hybrid_property
    def status(self) -> OrderStatus:
        return OrderStatus(self.status_raw)

    @status.setter
    def status(self, value: OrderStatus | str) -> None:
        self.status_raw = value.value if hasattr(value, "value") else str(value)

    @status.expression
    def status(cls):
        return cls.status_raw
