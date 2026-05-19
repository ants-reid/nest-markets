import uuid
from typing import Optional
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.enums import RegimeType
from app.db.models.mixins import JSONBType, CreatedAtMixin, UUIDPrimaryKeyMixin


class FeatureSnapshot(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Engineered feature snapshot for one asset/timeframe/scan."""

    __tablename__ = "feature_snapshots"
    __table_args__ = (
        UniqueConstraint("asset_id", "timeframe", "scan_ts", name="uq_feature_snapshots_asset_timeframe_scan_ts"),
        Index("ix_feature_snapshots_asset_timeframe_scan_ts", "asset_id", "timeframe", "scan_ts"),
    )

    asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assets.id"), nullable=False)
    signal_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("signals.id"), nullable=True)
    scan_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    trend_score: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    momentum_score: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    volatility_score: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    liquidity_score: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    relative_strength_score: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    regime: Mapped[Optional[RegimeType]] = mapped_column(Enum(RegimeType, name="regime_type_enum"), nullable=True)
    atr: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    rsi: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    ema_fast: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    ema_slow: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    adx: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    distance_from_high_pct: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    distance_from_low_pct: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    market_quality_flag: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    features_json: Mapped[Optional[dict]] = mapped_column(JSONBType, nullable=True)
