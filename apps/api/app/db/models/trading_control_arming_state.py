from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, CheckConstraint, DateTime, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class TradingControlArmingState(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Durable current-state row for trading control arming posture."""

    __tablename__ = "trading_control_arming_states"
    __table_args__ = (
        UniqueConstraint("scope", "trading_mode", name="uq_trading_control_arming_states_scope_mode"),
        CheckConstraint("state IN ('armed', 'disarmed')", name="ck_trading_control_arming_states_state"),
        CheckConstraint(
            "last_enablement_status IS NULL OR last_enablement_status IN ('ready', 'blocked', 'warning')",
            name="ck_trading_control_arming_states_enablement_status",
        ),
        CheckConstraint(
            "state <> 'armed' OR (armed_at IS NOT NULL AND armed_by IS NOT NULL AND expires_at IS NOT NULL)",
            name="ck_trading_control_arming_states_armed_fields",
        ),
        CheckConstraint(
            "state <> 'disarmed' OR expires_at IS NULL",
            name="ck_trading_control_arming_states_disarmed_expiry",
        ),
        Index("ix_trading_control_arming_states_state_expires_at", "state", "expires_at"),
        Index("ix_trading_control_arming_states_updated_at", "updated_at"),
    )

    scope: Mapped[str] = mapped_column(String(50), nullable=False)
    trading_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="disarmed", server_default="disarmed")
    armed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    armed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    arm_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_enablement_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_enablement_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    last_enablement_blockers: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    last_enablement_warnings: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    client_request_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    disarmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    disarmed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    disarm_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)