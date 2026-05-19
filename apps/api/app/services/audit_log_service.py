"""Append-only audit log for all trade and approval actions.

Writes one JSON line per event to a rotating log file.
Never updates or deletes entries — append-only by design.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_logger = logging.getLogger(__name__)

_AUDIT_LOG_PATH = Path(os.getenv("AUDIT_LOG_PATH", "logs/audit.jsonl"))


def _append(event: dict[str, Any]) -> None:
    """Append a single event dict as a JSON line. Thread-safe via append mode."""
    _AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(event, default=str)
    with _AUDIT_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def log_trade_submitted(
    *,
    endpoint: str,
    asset: str,
    side: str,
    qty: float | None,
    notional: float | None,
    idempotency_key: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Record a paper or live trade submission."""
    _append({
        "ts": datetime.now(UTC).isoformat(),
        "event": "trade_submitted",
        "endpoint": endpoint,
        "asset": asset,
        "side": side,
        "qty": qty,
        "notional": notional,
        "idempotency_key": idempotency_key,
        **(extra or {}),
    })


def log_approval_action(
    *,
    approval_id: str,
    action: str,
    asset: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Record an approval create, approve, reject, or expire event."""
    _append({
        "ts": datetime.now(UTC).isoformat(),
        "event": "approval_action",
        "approval_id": approval_id,
        "action": action,
        "asset": asset,
        **(extra or {}),
    })


def log_workflow_run(
    *,
    asset: str,
    timeframe: str,
    execution_mode: str,
    outcome: str,
    idempotency_key: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Record a workflow run (signal → risk → execution path)."""
    _append({
        "ts": datetime.now(UTC).isoformat(),
        "event": "workflow_run",
        "asset": asset,
        "timeframe": timeframe,
        "execution_mode": execution_mode,
        "outcome": outcome,
        "idempotency_key": idempotency_key,
        **(extra or {}),
    })


def log_broker_order_event(
    *,
    action: str,
    ticker: str,
    side: str,
    quantity: float | None,
    status: str,
    broker_order_id: str | None = None,
    reason: str | None = None,
    dry_run: bool = False,
    issues: list[dict[str, Any]] | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Record broker paper-order lifecycle events (submit/dry-run/outcome)."""
    _append(
        {
            "ts": datetime.now(UTC).isoformat(),
            "event": "broker_order_event",
            "action": action,
            "ticker": ticker,
            "side": side,
            "quantity": quantity,
            "status": status,
            "broker_order_id": broker_order_id,
            "reason": reason,
            "dry_run": dry_run,
            "issues": issues or [],
            **(extra or {}),
        }
    )


def log_auto_paper_arming_action(
    *,
    action: str,
    requested_by: str,
    reason: str,
    result_status: str,
    client_request_id: str | None = None,
    failure_reasons: list[str] | None = None,
    warning_codes: list[str] | None = None,
    enablement_checked_at: str | None = None,
    enablement_status: str | None = None,
    enablement_blockers: list[str] | None = None,
    enablement_warnings: list[str] | None = None,
    trading_mode: str | None = None,
    execution_control: str | None = None,
    arming_state_before: str | None = None,
    arming_state_after: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Record an auto-paper arming decision event."""
    _append(
        {
            "ts": datetime.now(UTC).isoformat(),
            "event": "auto_paper_arming_action",
            "action": action,
            "requested_by": requested_by,
            "reason": reason,
            "result_status": result_status,
            "client_request_id": client_request_id,
            "failure_reasons": failure_reasons or [],
            "warning_codes": warning_codes or [],
            "enablement_checked_at": enablement_checked_at,
            "enablement_status": enablement_status,
            "enablement_blockers": enablement_blockers or [],
            "enablement_warnings": enablement_warnings or [],
            "trading_mode": trading_mode,
            "execution_control": execution_control,
            "arming_state_before": arming_state_before,
            "arming_state_after": arming_state_after,
            **(extra or {}),
        }
    )


def get_latest_auto_paper_arming_action() -> dict[str, Any] | None:
    """Return the most recent auto-paper arming decision event, if any."""
    if not _AUDIT_LOG_PATH.exists():
        return None

    latest: dict[str, Any] | None = None
    with _AUDIT_LOG_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            raw = line.strip()
            if not raw:
                continue
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if event.get("event") != "auto_paper_arming_action":
                continue
            if latest is None or str(event.get("ts", "")) >= str(latest.get("ts", "")):
                latest = event

    return latest


def list_broker_order_events(limit: int = 50) -> list[dict[str, Any]]:
    """Return most recent broker paper-order audit events from audit log file."""
    if limit <= 0:
        return []
    if not _AUDIT_LOG_PATH.exists():
        return []

    entries: list[dict[str, Any]] = []
    with _AUDIT_LOG_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            raw = line.strip()
            if not raw:
                continue
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if event.get("event") != "broker_order_event":
                continue
            entries.append(event)

    entries.sort(key=lambda e: str(e.get("ts", "")), reverse=True)
    return entries[:limit]
