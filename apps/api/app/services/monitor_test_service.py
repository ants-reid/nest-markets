"""MH-MON-10 — Operator dry-probe execution service.

Read-only, fail-closed runner for a single registered health probe.
Never modifies trading state, never submits broker orders, and never
enables auto/live execution controls.
"""

from __future__ import annotations

from typing import Any

from app.schemas.monitor_test import (
    MonitorDryProbeCategory,
    MonitorDryProbeResponseSchema,
    MonitorDryProbeStatus,
)
from app.services.health_registry import list_registered, run_registered

_SECRET_KEY_FRAGMENTS = ("api_key", "secret", "token", "password")


class MonitorDryProbeError(ValueError):
    """Raised when a dry-probe request cannot be served safely."""


def _classify_category(service_id: str) -> MonitorDryProbeCategory:
    if service_id.startswith("feeds_in."):
        return "feeds_in"
    if service_id.startswith("feeds_out."):
        return "feeds_out"
    return "infrastructure"


def _to_status(probe_status: str) -> MonitorDryProbeStatus:
    mapping: dict[str, MonitorDryProbeStatus] = {
        "ok": "healthy",
        "degraded": "degraded",
        "down": "down",
        "error": "down",
        "unknown": "unknown",
    }
    return mapping.get((probe_status or "").lower(), "unknown")


def _scrub_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    if not evidence:
        return {}
    cleaned: dict[str, Any] = {}
    for key, value in evidence.items():
        lowered = str(key).lower()
        if any(fragment in lowered for fragment in _SECRET_KEY_FRAGMENTS):
            continue
        cleaned[key] = value
    return cleaned


def _recommended_action(status: MonitorDryProbeStatus, service_id: str) -> str:
    if status == "healthy":
        return "No immediate action required."
    if status == "degraded":
        return f"Review configuration and recent incidents for {service_id}."
    if status == "down":
        return (
            f"Treat {service_id} as unavailable and investigate before relying "
            "on this dependency."
        )
    return f"Probe result for {service_id} is unknown; validate service registration and health coverage."


def run_operator_dry_probe(service_id: str) -> MonitorDryProbeResponseSchema:
    """Run one registered probe and return an operator-safe dry result."""
    known = set(list_registered())
    if service_id not in known:
        raise MonitorDryProbeError(f"unknown service_id '{service_id}'")

    row = run_registered(service_id)
    status = _to_status(row.status)

    evidence = _scrub_evidence(dict(row.extra or {}))
    if row.detail:
        evidence["detail"] = row.detail

    message = row.detail or "Dry probe completed."
    if row.status == "error" and not row.detail:
        message = "Probe raised an internal error during dry run."

    return MonitorDryProbeResponseSchema(
        service_id=row.name,
        service_name=row.name,
        category=_classify_category(row.name),
        status=status,
        dry_probe=True,
        checked_at=row.checked_at,
        latency_ms=row.latency_ms,
        message=message,
        recommended_action=_recommended_action(status, row.name),
        evidence=evidence,
        safety_notes=[
            "Dry-probe only: no trading controls or broker execution paths are modified.",
            "No order submission or live execution call paths are invoked by this endpoint.",
        ],
    )
