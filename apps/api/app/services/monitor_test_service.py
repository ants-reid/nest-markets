"""MH-MON-10 — Operator dry-probe execution service.

Read-only, fail-closed runner for a single registered health probe.
Never modifies trading state, never submits broker orders, and never
enables auto/live execution controls.
"""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from datetime import UTC, datetime
from typing import Any

from app.schemas.monitor_test import (
    MonitorDryProbeCategory,
    MonitorDryProbeResponseSchema,
    MonitorDryProbeStatus,
)
from app.db.session import SessionLocal
from app.services.health_registry import list_registered, run_registered
from app.services.incident_log_service import record_incident

_SECRET_KEY_FRAGMENTS = (
    "api_key",
    "token",
    "secret",
    "password",
    "authorization",
    "cookie",
    "access_token",
    "refresh_token",
)
_ALLOWED_SERVICE_PREFIXES = ("database", "feeds_in.", "feeds_out.")
_DEFAULT_PROBE_TIMEOUT_SECONDS = 2.0
_DEFAULT_COOLDOWN_SECONDS = 5.0
_COOLDOWN_LOCK = threading.Lock()
_LAST_PROBE_AT_MONOTONIC: dict[str, float] = {}


class MonitorDryProbeError(ValueError):
    """Raised when a dry-probe request cannot be served safely."""


class MonitorDryProbeUnsupportedError(MonitorDryProbeError):
    """Raised when a registered probe is not on the MH-MON-10 safe allow-list."""


class MonitorDryProbeCooldownError(MonitorDryProbeError):
    """Raised when a per-service dry-probe cooldown is still active."""

    def __init__(self, *, service_id: str, retry_after_seconds: float) -> None:
        self.service_id = service_id
        self.retry_after_seconds = max(0.0, retry_after_seconds)
        super().__init__(
            f"cooldown_active service_id='{service_id}' retry_after_seconds={self.retry_after_seconds:.2f}"
        )


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


def _is_secret_key(key: str) -> bool:
    lowered = str(key).lower()
    return any(fragment in lowered for fragment in _SECRET_KEY_FRAGMENTS)


def _redact_text(value: str) -> str:
    out = value
    for fragment in _SECRET_KEY_FRAGMENTS:
        out = out.replace(fragment, "[redacted-key]")
        out = out.replace(fragment.upper(), "[REDACTED-KEY]")
    return out


def _scrub_value(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, nested in value.items():
            if _is_secret_key(str(key)):
                continue
            cleaned[str(key)] = _scrub_value(nested)
        return cleaned
    if isinstance(value, list):
        return [_scrub_value(item) for item in value]
    if isinstance(value, tuple):
        return [_scrub_value(item) for item in value]
    if isinstance(value, str):
        return _redact_text(value)
    return value


def _scrub_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    if not evidence:
        return {}
    scrubbed = _scrub_value(evidence)
    if isinstance(scrubbed, dict):
        return scrubbed
    return {}


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


def _is_allowed_service(service_id: str) -> bool:
    return any(
        service_id == prefix or service_id.startswith(prefix)
        for prefix in _ALLOWED_SERVICE_PREFIXES
    )


def _enforce_cooldown(
    service_id: str,
    *,
    now_monotonic: float,
    cooldown_seconds: float,
) -> None:
    if cooldown_seconds <= 0:
        return
    with _COOLDOWN_LOCK:
        last = _LAST_PROBE_AT_MONOTONIC.get(service_id)
        if last is not None:
            elapsed = now_monotonic - last
            if elapsed < cooldown_seconds:
                raise MonitorDryProbeCooldownError(
                    service_id=service_id,
                    retry_after_seconds=cooldown_seconds - elapsed,
                )
        _LAST_PROBE_AT_MONOTONIC[service_id] = now_monotonic


def _run_with_timeout(service_id: str, timeout_seconds: float):
    if timeout_seconds <= 0:
        return run_registered(service_id)
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(run_registered, service_id)
        return future.result(timeout=timeout_seconds)


def _safe_message(*, probe_status: str, detail: str | None) -> str:
    if probe_status == "error":
        # Fail closed: do not expose raw exception traces to the operator API.
        return "Dry probe failed safely. Inspect incident logs for error classification."
    if detail:
        return _redact_text(detail)
    return "Dry probe completed."


def _record_probe_incident(
    *,
    service_id: str,
    status: str,
    message: str,
    latency_ms: float | None,
    dry_probe: bool,
) -> None:
    severity = "info"
    if status in {"degraded", "unknown"}:
        severity = "warn"
    if status in {"down", "error"}:
        severity = "error"
    session = SessionLocal()
    try:
        record_incident(
            session,
            severity=severity,
            code="monitor_dry_probe",
            title=f"monitor dry probe {status}",
            source="monitor_test",
            detail=message,
            extra={
                "service_id": service_id,
                "dry_probe": dry_probe,
                "status": status,
                "latency_ms": latency_ms,
            },
        )
        session.commit()
    except Exception:  # noqa: BLE001 - logging failures must not break probe endpoint
        session.rollback()
    finally:
        session.close()


def reset_monitor_test_cooldowns() -> None:
    """Test helper: clear per-service cooldown timestamps."""
    with _COOLDOWN_LOCK:
        _LAST_PROBE_AT_MONOTONIC.clear()


def run_operator_dry_probe(
    service_id: str,
    *,
    timeout_seconds: float = _DEFAULT_PROBE_TIMEOUT_SECONDS,
    cooldown_seconds: float = _DEFAULT_COOLDOWN_SECONDS,
    now_monotonic: float | None = None,
) -> MonitorDryProbeResponseSchema:
    """Run one registered probe and return an operator-safe dry result."""
    known = set(list_registered())
    if service_id not in known:
        raise MonitorDryProbeError(f"unknown service_id '{service_id}'")
    if not _is_allowed_service(service_id):
        raise MonitorDryProbeUnsupportedError(
            f"unsupported service_id '{service_id}' for monitor dry probe"
        )

    _enforce_cooldown(
        service_id,
        now_monotonic=time.monotonic() if now_monotonic is None else now_monotonic,
        cooldown_seconds=cooldown_seconds,
    )

    try:
        row = _run_with_timeout(service_id, timeout_seconds)
    except FutureTimeoutError:
        status = "down"
        message = "Dry probe timed out safely before completion."
        _record_probe_incident(
            service_id=service_id,
            status=status,
            message=message,
            latency_ms=None,
            dry_probe=True,
        )
        return MonitorDryProbeResponseSchema(
            service_id=service_id,
            service_name=service_id,
            category=_classify_category(service_id),
            status=status,
            dry_probe=True,
            checked_at=datetime.now(UTC).isoformat(),
            latency_ms=None,
            message=message,
            recommended_action=_recommended_action(status, service_id),
            evidence={"timeout_seconds": timeout_seconds},
            safety_notes=[
                "Dry-probe only: no trading controls or broker execution paths are modified.",
                "No order submission or live execution call paths are invoked by this endpoint.",
            ],
        )

    status = _to_status(row.status)

    evidence = _scrub_evidence(dict(row.extra or {}))
    if row.detail and row.status != "error":
        evidence["detail"] = _redact_text(row.detail)

    message = _safe_message(probe_status=row.status, detail=row.detail)

    _record_probe_incident(
        service_id=row.name,
        status=status,
        message=message,
        latency_ms=row.latency_ms,
        dry_probe=True,
    )

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
