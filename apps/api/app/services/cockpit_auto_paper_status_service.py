"""MH-COCKPIT-13-A — Auto-paper status card aggregator (read-only).

Composes a small cockpit-friendly card payload from the existing trading-control
service and the file-backed worker run log. This module never enables anything;
it surfaces the current drift-lock posture so operators can see at a glance
that auto-paper / auto / live remain OFF.

Drift-lock guarantees:
- Pure read; no writes.
- Wraps existing services; no broker/LLM/trading-control code is touched.
- Output is operator-facing only and never feeds the trading path.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict

from app.config import get_settings
from app.services.trading_control_service import (
    TradingControlState,
    get_trading_mode,
)
from app.services.worker_run_log_service import (
    WorkerRunEntry,
    WorkerRunLogService,
)


_LINKS = {
    "readiness": "/market-data/auto-paper/readiness",
    "scheduler": "/market-data/auto-paper/scheduler/status",
    "worker_run_log": "/monitor/worker-run-log/overview",
    "broker_control": "/broker/control",
    "broker_health": "/broker/health",
}

_ADVISORY = (
    "Auto-paper status card is read-only. It surfaces the current "
    "drift-lock posture and does not enable, arm, or change any "
    "trading control."
)


def _serialize_trading_control(state: TradingControlState) -> Dict[str, Any]:
    return {
        "trading_mode": state.trading_mode,
        "execution_control": state.execution_control,
        "arming_state": state.arming_state,
        "auto_trading_allowed": state.auto_trading_allowed,
        "paper_order_submission_allowed": state.paper_order_submission_allowed,
        "live_order_submission_allowed": state.live_order_submission_allowed,
        "emergency_stop_active": state.emergency_stop_active,
        "reasons": list(state.reasons),
    }


def _serialize_run_entry(entry: WorkerRunEntry | None) -> Dict[str, Any] | None:
    if entry is None:
        return None
    return asdict(entry)


def _derive_posture(
    *,
    trading_control: Dict[str, Any],
    near_capacity: bool,
    latest_status: str | None,
) -> tuple[str, str, str]:
    """Return ``(posture, headline, subline)``.

    Posture is one of ``ok | warning | blocked``. The card surfaces the most
    operator-relevant view of "is the auto-paper subsystem healthy?" without
    making any control decisions.
    """
    trading_mode = trading_control.get("trading_mode", "paper")
    paper_allowed = bool(trading_control.get("paper_order_submission_allowed"))
    live_allowed = bool(trading_control.get("live_order_submission_allowed"))
    emergency = bool(trading_control.get("emergency_stop_active"))

    if emergency:
        return ("blocked", "Emergency stop is active", "All trading is halted.")

    if live_allowed:
        # Drift-lock: this should never happen in current build, but if it
        # ever appears, surface it loudly.
        return (
            "blocked",
            "Unexpected live-submission allowance detected",
            "Investigate broker control immediately.",
        )

    if trading_mode != "paper":
        return (
            "warning",
            f"Trading mode is {trading_mode}",
            "Auto-paper review applies to paper mode only.",
        )

    if not paper_allowed:
        return (
            "warning",
            "Paper submission is not allowed",
            "Manual paper trading is currently blocked by trading control.",
        )

    if near_capacity:
        return (
            "warning",
            "Worker run log is near capacity",
            "Review retention before continuing auto-paper review.",
        )

    if latest_status and latest_status.lower() in {"error", "failed"}:
        return (
            "warning",
            "Latest auto-paper run errored",
            "Inspect the worker run log for details.",
        )

    return (
        "ok",
        "Auto-paper subsystem is in review-only state",
        "Auto-paper enforcement remains OFF; manual paper trading is allowed.",
    )


def get_auto_paper_status_card(
    *,
    trading_control_state: TradingControlState | None = None,
    run_log_service: WorkerRunLogService | None = None,
) -> Dict[str, Any]:
    """Return the read-only auto-paper status card payload.

    Parameters
    ----------
    trading_control_state:
        Optional injected state (test hook). Defaults to live read.
    run_log_service:
        Optional injected service (test hook). Defaults to live read.
    """
    settings = get_settings()
    state = trading_control_state or get_trading_mode()
    svc = run_log_service or WorkerRunLogService()

    trading_control = _serialize_trading_control(state)
    retention = svc.get_retention_metadata()
    recent = svc.recent(limit=1)
    latest = recent[0] if recent else None

    enforcement = {
        # Drift-lock: auto-paper enforcement is wired OFF in this build.
        "auto_paper_enforcement_enabled": False,
        "auto_trading_enabled": bool(state.auto_trading_allowed),
        "live_trading_enabled": bool(settings.live_execution_enabled),
        "live_order_submission_allowed": bool(state.live_order_submission_allowed),
    }

    posture, headline, subline = _derive_posture(
        trading_control=trading_control,
        near_capacity=bool(retention.get("near_capacity")),
        latest_status=(latest.status if latest else None),
    )

    return {
        "advisory": _ADVISORY,
        "posture": posture,
        "headline": headline,
        "subline": subline,
        "enforcement": enforcement,
        "trading_control": trading_control,
        "latest_run": _serialize_run_entry(latest),
        "run_log_summary": {
            "current_entry_count": retention.get("current_entry_count", 0),
            "max_entries": retention.get("max_entries", 0),
            "utilization_pct": retention.get("utilization_pct", 0.0),
            "near_capacity": bool(retention.get("near_capacity", False)),
            "retention_status": retention.get("retention_status"),
            "latest_started_at": retention.get("latest_started_at"),
        },
        "links": dict(_LINKS),
    }
