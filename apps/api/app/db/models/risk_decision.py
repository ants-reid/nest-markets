import uuid
from typing import Optional
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import JSONBType, CreatedAtMixin, UUIDPrimaryKeyMixin


class RiskDecision(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Deterministic risk engine decision."""

    __tablename__ = "risk_decisions"

    signal_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("signals.id"), nullable=True, unique=False)
    approved_raw: Mapped[str] = mapped_column("approved", String(20), nullable=False, default="pending")
    timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    blocking_rule: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    blocked_reasons_json: Mapped[Optional[list]] = mapped_column(JSONBType, nullable=True)
    position_risk_pct: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    notional_allowed: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    correlation_bucket: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    spread_ok: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    session_ok: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    drawdown_ok: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    cooldown_ok: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    kill_switch_active: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    decision_json: Mapped[Optional[dict]] = mapped_column(JSONBType, nullable=True)
    # MH-153-A — denormalised risk-profile-id snapshot. Nullable; no FK on
    # purpose so historical rows survive profile deletion/replacement. No
    # writer is wired yet (MH-153-B will populate this).
    risk_profile_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    # MH-154-A — queryable structured-enum block-reason code. Nullable; pairs
    # with the existing free-text ``blocking_rule`` column. No writer is wired
    # yet (MH-154-B will populate this).
    block_reason_code: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True
    )

    @hybrid_property
    def approved(self) -> bool:
        raw = self.approved_raw
        if isinstance(raw, bool):
            return raw
        value = str(raw).strip().lower()
        return value in {"approved", "true", "1", "yes"}

    @approved.setter
    def approved(self, value: bool | str) -> None:
        if isinstance(value, bool):
            self.approved_raw = "approved" if value else "rejected"
        else:
            self.approved_raw = str(value)

    @approved.expression
    def approved(cls):
        return cls.approved_raw
