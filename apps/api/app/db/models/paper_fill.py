import uuid
from typing import Optional
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class PaperFill(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Simulated fill record."""

    __tablename__ = "paper_fills"

    paper_order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("paper_orders.id"), nullable=False)
    fill_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fill_price: Mapped[float] = mapped_column(Numeric(18, 8), nullable=False)
    fill_qty: Mapped[float] = mapped_column(Numeric(18, 8), nullable=False)
    slippage_bps: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    fee_amount: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
