from typing import Optional
from datetime import datetime

from sqlalchemy import DateTime, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import JSONBType, CreatedAtMixin, UUIDPrimaryKeyMixin


class PnlSnapshot(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Portfolio equity and drawdown snapshot."""

    __tablename__ = "pnl_snapshots"

    snapshot_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    equity: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    cash: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    gross_exposure: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    net_exposure: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    open_pnl: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    closed_pnl: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    drawdown_pct: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    win_rate_rolling: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    profit_factor_rolling: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONBType, nullable=True)
