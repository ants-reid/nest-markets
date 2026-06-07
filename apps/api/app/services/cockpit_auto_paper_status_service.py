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

from collections import Counter
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from typing import Any, Dict

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.enums import SignalStatus
from app.db.models.asset import Asset
from app.db.models.broker_submit_decision import BrokerSubmitDecision
from app.db.models.paper_order import PaperOrder
from app.db.models.position import Position
from app.db.models.signal import Signal
from app.db.session import SessionLocal
from app.services.auto_paper_gate_service import AutoPaperGateService
from app.services.cockpit_mode_service import get_cockpit_mode_state
from app.services.opportunity_ranker_service import OpportunityRankerService
from app.services.trading_control_service import TradingControlState, get_trading_mode
from app.services.visual_seed import provider_filter
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
_QUEUE_RECENCY_HOURS = 8
_QUEUE_MIN_SIGNAL_SCORE = 50.0
_MANUAL_SEED_PROVIDER = "manual_scheduler_seed"


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


def _to_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _age_minutes(scan_ts: datetime | None, now_utc: datetime) -> int | None:
    utc_scan = _to_utc(scan_ts)
    if utc_scan is None:
        return None
    return max(0, int((now_utc - utc_scan).total_seconds() // 60))


def _age_bucket(minutes: int | None) -> str:
    if minutes is None:
        return "unknown"
    if minutes <= 30:
        return "fresh_le_30m"
    if minutes <= 120:
        return "recent_30m_2h"
    if minutes <= (_QUEUE_RECENCY_HOURS * 60):
        return "aging_2h_8h"
    return "stale_gt_8h"


def _load_candidate_queue_snapshot(
    *,
    session: Session,
    max_items: int = 5,
) -> Dict[str, Any]:
    now_utc = datetime.now(UTC)
    cutoff = now_utc - timedelta(hours=_QUEUE_RECENCY_HOURS)

    # Eligible candidates use the same base filters as OpportunityRankerService.
    eligible_rows = (
        session.execute(
            select(Signal, Asset)
            .join(Asset, Signal.asset_id == Asset.id)
            .where(Signal.signal_status == SignalStatus.CANDIDATE)
            .where(Signal.scan_ts >= cutoff)
            .where(Signal.signal_score >= _QUEUE_MIN_SIGNAL_SCORE)
            .where(provider_filter(Signal.provider_name, include_visual_seed=False))
            .order_by(Signal.signal_score.desc())
        )
        .all()
    )

    ranked = OpportunityRankerService(session).rank(
        limit=max_items,
        recency_hours=_QUEUE_RECENCY_HOURS,
    )
    ranked_by_id = {op.signal_id: op for op in ranked}

    by_symbol = Counter(asset.symbol for _, asset in eligible_rows)
    top_candidates: list[Dict[str, Any]] = []

    for signal, asset in eligible_rows[:max_items]:
        age_mins = _age_minutes(signal.scan_ts, now_utc)
        provider = signal.provider_name or "unknown"
        rank = ranked_by_id.get(signal.id)
        top_candidates.append(
            {
                "signal_id": str(signal.id),
                "asset": asset.symbol,
                "provider_name": provider,
                "signal_status": signal.signal_status.value,
                "signal_score": _safe_float(signal.signal_score),
                "confidence": _safe_float(signal.confidence),
                "composite_score": rank.score if rank is not None else None,
                "scan_ts": signal.scan_ts.isoformat() if signal.scan_ts is not None else None,
                "age_minutes": age_mins,
                "age_bucket": _age_bucket(age_mins),
                "stale_manual_seed": (
                    provider == _MANUAL_SEED_PROVIDER and (age_mins or 0) > (_QUEUE_RECENCY_HOURS * 60)
                ),
                "duplicate_symbol_candidate": by_symbol.get(asset.symbol, 0) > 1,
            }
        )

    selection_explanation = (
        "Eligible candidates must be CANDIDATE, scan_ts within recency window, "
        "signal_score >= 50, and pass provider filters; worker traversal starts from highest signal_score."
    )
    if top_candidates:
        first = top_candidates[0]
        if first["provider_name"] == _MANUAL_SEED_PROVIDER:
            selection_explanation += " Top candidate is a manual scheduler seed based on score ordering."

    return {
        "recency_hours": _QUEUE_RECENCY_HOURS,
        "min_signal_score": _QUEUE_MIN_SIGNAL_SCORE,
        "eligible_count": len(eligible_rows),
        "top_candidates": top_candidates,
        "selection_explanation": selection_explanation,
    }


def _load_candidate_queue_hygiene(
    *,
    session: Session,
    max_open_paper_positions: int,
    open_paper_positions_count: int,
    controlled_gate_decision: Dict[str, Any],
    controlled_gate_snapshot: Dict[str, Any],
) -> Dict[str, Any]:
    now_utc = datetime.now(UTC)
    candidate_rows = (
        session.execute(
            select(Signal, Asset)
            .join(Asset, Signal.asset_id == Asset.id)
            .where(Signal.signal_status == SignalStatus.CANDIDATE)
            .where(provider_filter(Signal.provider_name, include_visual_seed=False))
        )
        .all()
    )

    age_buckets: Dict[str, int] = {
        "fresh_le_30m": 0,
        "recent_30m_2h": 0,
        "aging_2h_8h": 0,
        "stale_gt_8h": 0,
        "unknown": 0,
    }
    symbols: list[str] = []
    stale_manual_seed_count = 0

    for signal, asset in candidate_rows:
        age_mins = _age_minutes(signal.scan_ts, now_utc)
        bucket = _age_bucket(age_mins)
        age_buckets[bucket] = age_buckets.get(bucket, 0) + 1
        provider = signal.provider_name or "unknown"
        if provider == _MANUAL_SEED_PROVIDER and bucket == "stale_gt_8h":
            stale_manual_seed_count += 1
        symbols.append(asset.symbol)

    symbol_counts = Counter(symbols)
    duplicate_symbol_candidate_count = sum(count - 1 for count in symbol_counts.values() if count > 1)

    already_submitted_rows = (
        session.execute(
            select(Signal, Asset)
            .join(Asset, Signal.asset_id == Asset.id)
            .where(Signal.signal_status == SignalStatus.PAPER_SUBMITTED)
            .where(provider_filter(Signal.provider_name, include_visual_seed=False))
        )
        .all()
    )
    submitted_symbols = {asset.symbol for _, asset in already_submitted_rows}
    already_submitted_count = sum(1 for symbol in symbols if symbol in submitted_symbols)

    allowlist = set(controlled_gate_snapshot.get("symbol_allowlist") or [])
    allowlist_blocked_count = 0
    if allowlist:
        allowlist_blocked_count = sum(1 for symbol in symbols if symbol.upper() not in allowlist)

    cap_blocked = open_paper_positions_count >= max_open_paper_positions
    decision_blocked = not bool(controlled_gate_decision.get("allowed", False))
    recommendations: list[str] = []
    if stale_manual_seed_count > 0:
        recommendations.append(
            f"Review/expire {stale_manual_seed_count} stale manual seed candidate(s) older than {_QUEUE_RECENCY_HOURS}h."
        )
    if duplicate_symbol_candidate_count > 0:
        recommendations.append(
            f"Deduplicate {duplicate_symbol_candidate_count} same-symbol candidate(s) before the next cycle."
        )
    if allowlist_blocked_count > 0:
        recommendations.append(
            f"{allowlist_blocked_count} candidate(s) are outside the current symbol allowlist."
        )
    if cap_blocked:
        recommendations.append(
            "Open-position cap is currently reached; no new auto-paper entries will open until slots free up."
        )
    if decision_blocked:
        gate_name = controlled_gate_decision.get("blocking_gate") or "unknown_gate"
        reason = controlled_gate_decision.get("reason") or "no reason supplied"
        recommendations.append(f"Controlled gate is blocked at {gate_name}: {reason}")

    return {
        "stale_manual_seed_count": stale_manual_seed_count,
        "duplicate_symbol_candidate_count": duplicate_symbol_candidate_count,
        "already_submitted_count": already_submitted_count,
        "allowlist_blocked_count": allowlist_blocked_count,
        "cap_blocked": cap_blocked,
        "controlled_gate_blocked": decision_blocked,
        "age_bucket_counts": age_buckets,
        "cleanup_recommendations": recommendations,
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
        "ibkr_status": getattr(order, "ibkr_status", None),
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


def _load_submit_decision_count(session: Session | None) -> int | None:
    """Return persisted broker submit-decision row count when available."""
    statement = select(func.count()).select_from(BrokerSubmitDecision)

    if session is not None:
        try:
            return int(session.execute(statement).scalar_one())
        except Exception:
            return None

    try:
        with SessionLocal() as owned_session:
            return int(owned_session.execute(statement).scalar_one())
    except Exception:
        return None


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
    submit_decision_count = _load_submit_decision_count(session)

    enforcement = {
        "auto_paper_enforcement_enabled": False,
        "auto_trading_enabled": bool(state.auto_trading_allowed),
        "live_trading_enabled": bool(settings.live_execution_enabled),
        "live_order_submission_allowed": bool(state.live_order_submission_allowed),
    }

    gate_service = AutoPaperGateService(settings)
    controlled_gate_snapshot: dict[str, Any]
    controlled_gate_decision: dict[str, Any]
    owned_for_queue: Session | None = None
    active_session = session
    if session is not None:
        controlled_gate_snapshot = gate_service.snapshot(session)
        decision = gate_service.evaluate_run(session)
        controlled_gate_decision = {
            "allowed": decision.allowed,
            "blocking_gate": decision.blocking_gate,
            "reason": decision.reason,
        }
    else:
        try:
            owned_for_queue = SessionLocal()
            active_session = owned_for_queue
            controlled_gate_snapshot = gate_service.snapshot(owned_for_queue)
            decision = gate_service.evaluate_run(owned_for_queue)
            controlled_gate_decision = {
                "allowed": decision.allowed,
                "blocking_gate": decision.blocking_gate,
                "reason": decision.reason,
            }
        except Exception:
            if owned_for_queue is not None:
                owned_for_queue.close()
                owned_for_queue = None
            active_session = None
            controlled_gate_snapshot = gate_service.snapshot(None)
            controlled_gate_decision = {
                "allowed": False,
                "blocking_gate": "snapshot_unavailable",
                "reason": "Unable to evaluate controlled-run gate without DB session.",
            }

    if active_session is not None:
        try:
            candidate_queue = _load_candidate_queue_snapshot(session=active_session)
            queue_hygiene = _load_candidate_queue_hygiene(
                session=active_session,
                max_open_paper_positions=max_open_paper_positions,
                open_paper_positions_count=open_paper_positions_count,
                controlled_gate_decision=controlled_gate_decision,
                controlled_gate_snapshot=controlled_gate_snapshot,
            )
        except Exception:
            candidate_queue = {
                "recency_hours": _QUEUE_RECENCY_HOURS,
                "min_signal_score": _QUEUE_MIN_SIGNAL_SCORE,
                "eligible_count": 0,
                "top_candidates": [],
                "selection_explanation": "Candidate queue snapshot unavailable.",
            }
            queue_hygiene = {
                "stale_manual_seed_count": 0,
                "duplicate_symbol_candidate_count": 0,
                "already_submitted_count": 0,
                "allowlist_blocked_count": 0,
                "cap_blocked": open_paper_positions_count >= max_open_paper_positions,
                "controlled_gate_blocked": not bool(controlled_gate_decision.get("allowed", False)),
                "age_bucket_counts": {
                    "fresh_le_30m": 0,
                    "recent_30m_2h": 0,
                    "aging_2h_8h": 0,
                    "stale_gt_8h": 0,
                    "unknown": 0,
                },
                "cleanup_recommendations": [
                    "Queue hygiene snapshot unavailable; verify DB connectivity and retry.",
                ],
            }
    else:
        candidate_queue = {
            "recency_hours": _QUEUE_RECENCY_HOURS,
            "min_signal_score": _QUEUE_MIN_SIGNAL_SCORE,
            "eligible_count": 0,
            "top_candidates": [],
            "selection_explanation": "Candidate queue snapshot unavailable.",
        }
        queue_hygiene = {
            "stale_manual_seed_count": 0,
            "duplicate_symbol_candidate_count": 0,
            "already_submitted_count": 0,
            "allowlist_blocked_count": 0,
            "cap_blocked": open_paper_positions_count >= max_open_paper_positions,
            "controlled_gate_blocked": not bool(controlled_gate_decision.get("allowed", False)),
            "age_bucket_counts": {
                "fresh_le_30m": 0,
                "recent_30m_2h": 0,
                "aging_2h_8h": 0,
                "stale_gt_8h": 0,
                "unknown": 0,
            },
            "cleanup_recommendations": [
                "Queue hygiene snapshot unavailable; verify DB connectivity and retry.",
            ],
        }

    if owned_for_queue is not None:
        owned_for_queue.close()

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

    run_log_entry_count = int(retention.get("current_entry_count", 0))
    warning_codes: list[str] = []
    if latest_paper_order and run_log_entry_count == 0:
        warning_codes.append("latest_paper_order_without_run_log")
    if latest_paper_order and submit_decision_count == 0:
        warning_codes.append("latest_paper_order_without_submit_decision")
    status = "warning" if warning_codes else "ok"

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
        "controlled_gate": {
            "decision": controlled_gate_decision,
            "snapshot": controlled_gate_snapshot,
        },
        "trading_control": trading_control,
        "latest_run": latest_run,
        "latest_paper_order": latest_paper_order,
        "audit_alignment": {
            "status": status,
            "warning_codes": warning_codes,
            "run_log_entry_count": run_log_entry_count,
            "submit_decision_count": submit_decision_count,
            "latest_paper_order_present": bool(latest_paper_order),
        },
        "candidate_queue": candidate_queue,
        "queue_hygiene": queue_hygiene,
        "run_log_summary": {
            "current_entry_count": run_log_entry_count,
            "max_entries": retention.get("max_entries", 0),
            "utilization_pct": retention.get("utilization_pct", 0.0),
            "near_capacity": bool(retention.get("near_capacity", False)),
            "retention_status": retention.get("retention_status"),
            "latest_started_at": retention.get("latest_started_at"),
        },
        "links": dict(_LINKS),
    }