"""MH-COCKPIT-13-A — Auto-paper status card aggregator (read-only).

Composes a cockpit-friendly status payload from existing trading-control state,
the file-backed worker run log, and persisted paper-order/position reads. This
module never enables anything; it surfaces the current drift-lock posture so
operators can see at a glance that Auto Paper stays simulation-only and that
live / auto-live remain locked.

Drift-lock guarantees:
- Pure read; no writes.
- Wraps existing services; no broker/LLM/trading-control code is touched.
- Output is operator-facing only and never feeds the trading path.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models.paper_order import PaperOrder
from app.db.models.position import Position
from app.db.session import SessionLocal
from app.services.cockpit_mode_service import get_cockpit_mode_state
from app.services.trading_control_service import TradingControlState, get_trading_mode
from app.services.worker_run_log_service import WorkerRunEntry, WorkerRunLogService


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
_DEFAULT_MAX_OPEN_POSITIONS = 5


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


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


def _load_open_paper_positions_count(session: Session) -> int:
    statement = select(Position).where(
        Position.closed_at.is_(None),
        or_(Position.close_reason == "auto_paper", Position.opened_by == "auto_paper"),
    )
    return len(session.execute(statement).scalars().all())


def _load_latest_paper_order(session: Session) -> Dict[str, Any] | None:
    statement = (
        select(PaperOrder)
        .where(PaperOrder.order_type == "auto_paper")
        .order_by(PaperOrder.submitted_at.desc(), PaperOrder.timestamp.desc(), PaperOrder.created_at.desc())
        .limit(1)
    )
    order = session.execute(statement).scalars().first()
    if order is None:
        return None

    return {
        "order_type": order.order_type,
        "status": order.status,
        "side": order.side,
        "direction": order.direction,
        "qty": _safe_float(order.qty if order.qty is not None else order.quantity),
        "notional": _safe_float(order.notional),
        "submitted_at": (
            order.submitted_at.isoformat()
            if order.submitted_at is not None
            else order.timestamp.isoformat() if order.timestamp is not None else None
        ),
        "signal_id": str(order.signal_id) if order.signal_id is not None else None,
        "asset_id": str(order.asset_id) if order.asset_id is not None else None,
        "broker_order_id": order.broker_order_id,
    }


def _load_paper_snapshot(session: Session | None) -> Dict[str, Any]:
    if session is not None:
        return {
            "open_paper_positions_count": _load_open_paper_positions_count(session),
            "latest_paper_order": _load_latest_paper_order(session),
        }

    try:
        with SessionLocal() as owned_session:
            return {
                "open_paper_positions_count": _load_open_paper_positions_count(owned_session),
                "latest_paper_order": _load_latest_paper_order(owned_session),
            }
    except Exception:
        return {
            "open_paper_positions_count": 0,
            "latest_paper_order": None,
        }


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


def _derive_last_decision(latest_run: Dict[str, Any] | None) -> str:
    if not latest_run:
        return "unknown"

    status = str(latest_run.get("status") or "").lower()
    message = str(latest_run.get("message") or "").lower()
    outcome_counts = latest_run.get("outcome_counts") or {}

    if status in {"error", "failed"} or "fatal error" in message:
        return "errored"
    if int(outcome_counts.get("accepted_count", 0)) > 0:
        return "accepted"
    if (
        int(outcome_counts.get("blocked_count", 0)) > 0
        or int(outcome_counts.get("risk_blocked_count", 0)) > 0
        or int(outcome_counts.get("gate_blocked_count", 0)) > 0
        or int(outcome_counts.get("rejected_count", 0)) > 0
        or int(outcome_counts.get("cancelled_count", 0)) > 0
    ):
        return "blocked"
    if "skipped" in message or int(outcome_counts.get("skipped_cap_count", 0)) > 0:
        return "skipped"
    return "unknown"


def _derive_last_block_reason(
    *,
    trading_control: Dict[str, Any],
    latest_run: Dict[str, Any] | None,
    open_paper_positions_count: int,
    max_open_paper_positions: int,
) -> str | None:
    if bool(trading_control.get("emergency_stop_active")):
        return "Emergency stop is active."

    reasons = trading_control.get("reasons") or []
    if reasons and not bool(trading_control.get("paper_order_submission_allowed")):
        return "; ".join(str(reason) for reason in reasons)

    if open_paper_positions_count >= max_open_paper_positions:
        return "Auto Paper position cap reached."

    if not latest_run:
        return None

    message = str(latest_run.get("message") or "")
    outcome_counts = latest_run.get("outcome_counts") or {}

    if int(outcome_counts.get("skipped_cap_count", 0)) > 0:
        return "Auto Paper skipped because the position cap was reached."
    if int(outcome_counts.get("risk_blocked_count", 0)) > 0:
        return "Risk gates blocked the latest Auto Paper run."
    if int(outcome_counts.get("gate_blocked_count", 0)) > 0:
        return "Broker-side paper gate blocked the latest Auto Paper run."
    if latest_run.get("status") in {"error", "failed"}:
        return message
    if "blocked" in message.lower() or "rejected" in message.lower():
        return message
    return None


def _build_risk_gate_summary(
    *,
    trading_control: Dict[str, Any],
    open_paper_positions_count: int,
    max_open_paper_positions: int,
    latest_run: Dict[str, Any] | None,
    near_capacity: bool,
) -> list[Dict[str, Any]]:
    summary = [
        {
            "label": "Paper submission gate",
            "status": "passing" if trading_control.get("paper_order_submission_allowed") else "blocked",
            "detail": "Paper submission remains inside backend trading-control rules.",
        },
        {
            "label": "Emergency stop",
            "status": "blocked" if trading_control.get("emergency_stop_active") else "passing",
            "detail": "Emergency stop halts all Auto Paper activity when active.",
        },
        {
            "label": "Open paper position cap",
            "status": "blocked" if open_paper_positions_count >= max_open_paper_positions else "passing",
            "detail": f"{open_paper_positions_count}/{max_open_paper_positions} open Auto Paper positions.",
        },
        {
            "label": "Worker run retention",
            "status": "warning" if near_capacity else "passing",
            "detail": "Run history is file-backed and trimmed to a bounded retention window.",
        },
        {
            "label": "Live trading lock",
            "status": "passing",
            "detail": "Live trading and auto-live remain locked in this build.",
        },
    ]

    if latest_run and latest_run.get("status") in {"error", "failed"}:
        summary.append(
            {
                "label": "Latest Auto Paper worker run",
                "status": "warning",
                "detail": str(latest_run.get("message") or "Latest run reported an error."),
            }
        )

    return summary


def _build_safety_notes() -> list[str]:
    return [
        "Auto Paper can simulate trades only.",
        "No real money orders can be placed from this mode.",
        "Risk checks still apply before any paper action.",
        "Live trading remains locked.",
        "Auto-live remains locked.",
    ]


def _derive_operator_next_action(
    *,
    selected_mode: str,
    trading_control: Dict[str, Any],
    open_paper_positions_count: int,
    max_open_paper_positions: int,
    last_decision: str,
    last_block_reason: str | None,
) -> str:
    if bool(trading_control.get("emergency_stop_active")):
        return "Review broker control and clear the emergency stop before relying on Auto Paper."
    if not bool(trading_control.get("paper_order_submission_allowed")):
        return "Paper submission is blocked. Review trading-control reasons before continuing."
    if open_paper_positions_count >= max_open_paper_positions:
        return "Position cap reached. Let existing paper positions close or review the cap before the next Auto Paper cycle."
    if last_decision == "blocked" and last_block_reason:
        return f"Review the latest block reason: {last_block_reason}"
    if last_decision == "errored":
        return "Inspect the latest Auto Paper worker run and worker-run log before the next check."
    if selected_mode != "auto_paper":
        return "Select Auto Paper mode in Cockpit if you want simulation-only automation posture."
    return "Continue monitoring Auto Paper from Cockpit. Simulation-only safeguards remain in force."


def get_auto_paper_status_card(
    *,
    trading_control_state: TradingControlState | None = None,
    run_log_service: WorkerRunLogService | None = None,
    session: Session | None = None,
) -> Dict[str, Any]:
    """Return the read-only Auto Paper status card payload.

    Parameters
    ----------
    trading_control_state:
        Optional injected state (test hook). Defaults to live read.
    run_log_service:
        Optional injected service (test hook). Defaults to live read.
    session:
        Optional injected DB session (test hook). Defaults to a safe read-only
        snapshot attempt and degrades gracefully when no DB is available.
    """
    settings = get_settings()
    state = trading_control_state or get_trading_mode()
    svc = run_log_service or WorkerRunLogService()
    mode_state = get_cockpit_mode_state(trading_control_state=state)
    selected_mode = mode_state.current_mode
    max_open_paper_positions = int(
        getattr(settings, "auto_paper_max_open_positions", _DEFAULT_MAX_OPEN_POSITIONS)
    )

    trading_control = _serialize_trading_control(state)
    retention = svc.get_retention_metadata()
    recent = svc.recent(limit=1)
    latest = recent[0] if recent else None
    latest_run = _serialize_run_entry(latest)
    paper_snapshot = _load_paper_snapshot(session)
    open_paper_positions_count = int(paper_snapshot["open_paper_positions_count"])
    latest_paper_order = paper_snapshot["latest_paper_order"]

    enforcement = {
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
    last_decision = _derive_last_decision(latest_run)
    last_block_reason = _derive_last_block_reason(
        trading_control=trading_control,
        latest_run=latest_run,
        open_paper_positions_count=open_paper_positions_count,
        max_open_paper_positions=max_open_paper_positions,
    )
    risk_gate_summary = _build_risk_gate_summary(
        trading_control=trading_control,
        open_paper_positions_count=open_paper_positions_count,
        max_open_paper_positions=max_open_paper_positions,
        latest_run=latest_run,
        near_capacity=bool(retention.get("near_capacity")),
    )
    safety_notes = _build_safety_notes()
    operator_next_action = _derive_operator_next_action(
        selected_mode=selected_mode,
        trading_control=trading_control,
        open_paper_positions_count=open_paper_positions_count,
        max_open_paper_positions=max_open_paper_positions,
        last_decision=last_decision,
        last_block_reason=last_block_reason,
    )

    return {
        "advisory": _ADVISORY,
        "mode": selected_mode,
        "auto_paper_selectable": "auto_paper" in mode_state.selectable_modes,
        "auto_paper_active": selected_mode == "auto_paper",
        "auto_paper_armed": selected_mode == "auto_paper" and state.arming_state == "armed",
        "live_trading_locked": True,
        "auto_live_locked": True,
        "posture": posture,
        "headline": headline,
        "subline": subline,
        "last_check_at": retention.get("latest_started_at"),
        "last_action_at": latest_paper_order.get("submitted_at") if latest_paper_order else None,
        "last_decision": last_decision,
        "last_block_reason": last_block_reason,
        "open_paper_positions_count": open_paper_positions_count,
        "max_open_paper_positions": max_open_paper_positions,
        "risk_gate_summary": risk_gate_summary,
        "safety_notes": safety_notes,
        "operator_next_action": operator_next_action,
        "enforcement": enforcement,
        "trading_control": trading_control,
        "latest_run": latest_run,
        "latest_paper_order": latest_paper_order,
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