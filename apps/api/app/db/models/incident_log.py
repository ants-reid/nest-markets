"""MH-MON-05 — Incident log: append-only record of operational/safety incidents.

Pure additive table. No production code path consumes this yet; the model and
read endpoint exist so operators can persistently record and review incidents
(e.g. "auto-paper enforcement attempted while disabled", "broker probe down",
"LLM provider 5xx burst"). Future phases (MH-MON-06 frontend, MH-COCKPIT-06
notifications) will surface these.

Drift-lock guarantee: this module never enables, disables, or mutates any
trading control. It is write-once / read-many.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import CreatedAtMixin, JSONBType, UUIDPrimaryKeyMixin


class IncidentLog(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One row per recorded incident."""

    __tablename__ = "incident_logs"

    # severity: info | warn | error | critical
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    # short stable code, e.g. "broker.gateway_down"
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    # short human title
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    # full detail
    detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # which subsystem reported it (e.g. "broker", "llm", "worker", "monitor")
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    # optional structured payload
    extra_json: Mapped[Optional[dict]] = mapped_column(JSONBType, nullable=True)
    # optional correlation
    correlation_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # explicit time the incident *occurred* (vs created_at = persistence time)
    occurred_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
