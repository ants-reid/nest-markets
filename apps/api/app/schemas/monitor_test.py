"""Schemas for MH-MON-10 operator dry-probe endpoint."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

MonitorDryProbeStatus = Literal["healthy", "degraded", "down", "unknown"]
MonitorDryProbeCategory = Literal["feeds_in", "feeds_out", "infrastructure"]


class MonitorDryProbeResponseSchema(BaseModel):
    service_id: str
    service_name: str
    category: MonitorDryProbeCategory
    status: MonitorDryProbeStatus
    dry_probe: bool
    checked_at: str
    latency_ms: float | None = None
    message: str
    recommended_action: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    safety_notes: list[str] = Field(default_factory=list)
