import uuid
from typing import Optional
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.enums import CatalystType, HorizonLabel, RegimeType, SetupType, SignalStatus, TradeDirection
from app.db.models.mixins import JSONBType, CreatedAtMixin, UUIDPrimaryKeyMixin


class Signal(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """AI-generated candidate trade signal."""

    __tablename__ = "signals"
    __table_args__ = (
        Index("ix_signals_asset_scan_ts", "asset_id", "scan_ts"),
        Index("ix_signals_status_scan_ts", "signal_status", "scan_ts"),
    )

    asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assets.id"), nullable=False)
    feature_snapshot_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("feature_snapshots.id"), nullable=True)
    prompt_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("prompt_versions.id"), nullable=True)
    model_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("model_versions.id"), nullable=True)

    provider_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    scan_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    signal_status: Mapped[SignalStatus] = mapped_column(Enum(SignalStatus, name="signal_status_enum"), nullable=False)
    direction: Mapped[TradeDirection] = mapped_column(Enum(TradeDirection, name="trade_direction_enum"), nullable=False)
    setup_type: Mapped[SetupType] = mapped_column(Enum(SetupType, name="setup_type_enum"), nullable=False)
    regime: Mapped[Optional[RegimeType]] = mapped_column(Enum(RegimeType, name="signal_regime_type_enum"), nullable=True)
    entry_min: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    entry_max: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    stop_price: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    target_price: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    horizon_label: Mapped[Optional[HorizonLabel]] = mapped_column(Enum(HorizonLabel, name="horizon_label_enum"), nullable=True)
    catalyst_type: Mapped[Optional[CatalystType]] = mapped_column(Enum(CatalystType, name="catalyst_type_enum"), nullable=True)
    catalyst_score: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    catalyst_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    thesis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    invalidators_json: Mapped[Optional[list]] = mapped_column(JSONBType, nullable=True)
    signal_score: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    raw_llm_json: Mapped[Optional[dict]] = mapped_column(JSONBType, nullable=True)
