"""MH-148-A — ``BrokerSubmitDecision`` ORM model (audit-only, no writers yet).

A durable record of the preflight decision computed before any broker submit
attempt. **No production code path writes to this table in this phase.** A
future suffix (MH-148-C, paired with the MH-147 unified ``would_block``
enforcement semantics) will wire writes.

Drift-lock guarantee: read-only model in the current cycle. Worker behaviour,
``BrokerService.submit_auto_order``, and ``assert_auto_trading_allowed()`` are
all unchanged.
"""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import CreatedAtMixin, JSONBType, UUIDPrimaryKeyMixin


class BrokerSubmitDecision(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One row per broker-submit preflight observation.

    All columns except ``intent`` and ``would_block`` are nullable so the
    future writer can persist whatever subset of preflight context is
    available without forcing schema-level coupling to any particular
    enforcement pipeline.
    """

    __tablename__ = "broker_submit_decisions"

    signal_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    intent: Mapped[str] = mapped_column(String(32), nullable=False)
    would_block: Mapped[bool] = mapped_column(Boolean, nullable=False)
    blocked_reason_code: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True
    )
    blocked_reason_text: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )
    preflight_json: Mapped[Optional[dict]] = mapped_column(
        JSONBType, nullable=True
    )
