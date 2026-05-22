from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.incident_log import IncidentLog
from app.db.models.paper_order import PaperOrder
from app.db.models.risk_decision import RiskDecision
from app.schemas.cockpit_alerts_needing_attention import (
    CockpitAlertsNeedingAttentionResponseSchema,
    CockpitAttentionGroupSchema,
    CockpitAttentionItemSchema,
    CockpitAttentionSummarySchema,
)
from app.services.health_registry import ServiceHealth, snapshot
from app.services.persistence_alert_service import ActiveAlertRecord, PersistenceAlertService
from app.services.persistence_notification_service import NotificationRecord, PersistenceNotificationService
from app.services.risk_limit_service import RiskLimitService
from app.services.trading_halt_service import TradingHaltService


_PAPER_ORDER_STALE_STATUSES = {"new", "pending", "submitted", "accepted"}
_PAPER_ORDER_STALE_HOURS = 6
_INCIDENT_LIMIT = 120
_RISK_DECISION_LIMIT = 80


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _ensure_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _iso(value: datetime | None) -> str | None:
    normalized = _ensure_utc(value)
    if normalized is None:
        return None
    return normalized.isoformat()


def _priority_rank(priority: str) -> int:
    if priority == "high":
        return 3
    if priority == "medium":
        return 2
    if priority == "low":
        return 1
    return 0


def _priority_from_incident_severity(severity: str | None) -> str:
    normalized = (severity or "").lower()
    if normalized in {"critical", "error"}:
        return "high"
    if normalized in {"warn", "warning"}:
        return "medium"
    if normalized == "info":
        return "low"
    return "unknown"


def _priority_from_alert_level(level: str | None, status: str | None) -> str:
    level_text = (level or "").lower()
    status_text = (status or "").lower()
    if level_text in {"critical", "error"}:
        return "high"
    if level_text in {"warn", "warning"}:
        return "medium"
    if status_text in {"rejected", "blocked"}:
        return "high"
    if status_text in {"submitted", "accepted", "pending"}:
        return "medium"
    if level_text == "info":
        return "low"
    return "unknown"


def _priority_from_probe_status(status: str | None) -> str:
    normalized = (status or "").lower()
    if normalized in {"down", "error"}:
        return "high"
    if normalized == "degraded":
        return "medium"
    if normalized == "unknown":
        return "unknown"
    return "low"


def _is_monitor_source(text: str | None) -> bool:
    lowered = (text or "").lower()
    return any(token in lowered for token in ("monitor", "feed", "provider", "health"))


def _contains_stale_text(*values: str | None) -> bool:
    merged = " ".join((value or "") for value in values).lower()
    return "stale" in merged or "lag" in merged or "outdated" in merged


def _load_active_alerts(session: Session) -> list[ActiveAlertRecord]:
    return PersistenceAlertService(session).list_active_alerts()


def _load_notifications(session: Session) -> list[NotificationRecord]:
    return PersistenceNotificationService(session).list_notifications()


def _load_incidents(session: Session) -> list[IncidentLog]:
    stmt = (
        select(IncidentLog)
        .order_by(IncidentLog.created_at.desc(), IncidentLog.id.desc())
        .limit(_INCIDENT_LIMIT)
    )
    return list(session.execute(stmt).scalars().all())


def _load_health_snapshot() -> list[ServiceHealth]:
    return snapshot()


def _load_stale_paper_orders(session: Session, *, now_utc: datetime) -> list[PaperOrder]:
    cutoff = now_utc - timedelta(hours=_PAPER_ORDER_STALE_HOURS)
    stmt = (
        select(PaperOrder)
        .order_by(PaperOrder.created_at.desc(), PaperOrder.id.desc())
        .limit(150)
    )
    rows = list(session.execute(stmt).scalars().all())
    stale: list[PaperOrder] = []
    for row in rows:
        status = (row.status or "").lower()
        if status not in _PAPER_ORDER_STALE_STATUSES:
            continue
        ts = _ensure_utc(row.submitted_at or row.timestamp or row.created_at)
        if ts is None:
            continue
        if ts <= cutoff:
            stale.append(row)
    return stale


def _load_risk_status(session: Session):
    return RiskLimitService(session).get_status(trading_mode="paper")


def _load_trading_halt_status(session: Session):
    return TradingHaltService(session).get_status(scope="global")


def _load_recent_risk_decisions(session: Session) -> list[RiskDecision]:
    stmt = (
        select(RiskDecision)
        .order_by(RiskDecision.created_at.desc(), RiskDecision.id.desc())
        .limit(_RISK_DECISION_LIMIT)
    )
    return list(session.execute(stmt).scalars().all())


def _group_by(items: list[CockpitAttentionItemSchema], attr: str) -> list[CockpitAttentionGroupSchema]:
    grouped: dict[str, list[str]] = {}
    for item in items:
        key = getattr(item, attr)
        grouped.setdefault(key, []).append(item.id)

    if attr == "priority":
        order = ["high", "medium", "low", "unknown"]
        keys = [key for key in order if key in grouped]
    elif attr == "source":
        order = ["alert", "incident", "monitor", "risk", "trading_halt", "notification", "paper", "unknown"]
        keys = [key for key in order if key in grouped]
    else:
        keys = sorted(grouped.keys())

    return [
        CockpitAttentionGroupSchema(group=key, count=len(grouped[key]), item_ids=grouped[key])
        for key in keys
    ]


def get_cockpit_alerts_needing_attention(
    session: Session,
    *,
    now_utc: datetime | None = None,
) -> CockpitAlertsNeedingAttentionResponseSchema:
    current_time = _ensure_utc(now_utc or _now_utc()) or _now_utc()

    limitations: list[str] = []
    monitor_notes: list[str] = []
    risk_notes: list[str] = []
    items: list[CockpitAttentionItemSchema] = []

    try:
        active_alerts = _load_active_alerts(session)
    except Exception as exc:  # noqa: BLE001
        active_alerts = []
        limitations.append(f"Active alert records unavailable: {type(exc).__name__}.")

    try:
        notifications = _load_notifications(session)
    except Exception as exc:  # noqa: BLE001
        notifications = []
        limitations.append(f"Notification records unavailable: {type(exc).__name__}.")

    try:
        incidents = _load_incidents(session)
    except Exception as exc:  # noqa: BLE001
        incidents = []
        limitations.append(f"Incident records unavailable: {type(exc).__name__}.")

    try:
        health_rows = _load_health_snapshot()
    except Exception as exc:  # noqa: BLE001
        health_rows = []
        limitations.append(f"Health probe snapshot unavailable: {type(exc).__name__}.")

    try:
        stale_paper_orders = _load_stale_paper_orders(session, now_utc=current_time)
    except Exception as exc:  # noqa: BLE001
        stale_paper_orders = []
        limitations.append(f"Stale paper-order scan unavailable: {type(exc).__name__}.")

    try:
        risk_status = _load_risk_status(session)
    except Exception as exc:  # noqa: BLE001
        risk_status = None
        limitations.append(f"Risk-limit status unavailable: {type(exc).__name__}.")

    try:
        halt_status = _load_trading_halt_status(session)
    except Exception as exc:  # noqa: BLE001
        halt_status = None
        limitations.append(f"Trading-halt status unavailable: {type(exc).__name__}.")

    try:
        risk_decisions = _load_recent_risk_decisions(session)
    except Exception as exc:  # noqa: BLE001
        risk_decisions = []
        limitations.append(f"Recent risk decisions unavailable: {type(exc).__name__}.")

    for alert in active_alerts:
        items.append(
            CockpitAttentionItemSchema(
                id=f"alert:{alert.alert_id}",
                source="alert",
                title=f"Active alert for {alert.asset}",
                message=alert.message,
                priority=_priority_from_alert_level(alert.level, alert.status),
                status=(alert.status or "unknown").lower(),
                detected_at=None,
                attention_type="active_alert",
                evidence=[
                    f"rule_id:{alert.rule_id}",
                    f"execution_id:{alert.execution_id}",
                ],
                missing_data=["detected_at unavailable in active alert record"],
                recommended_review_action=(
                    "Review related paper execution context and risk notes before taking any manual next step."
                ),
                is_actionable=False,
            )
        )

    for notification in notifications:
        if notification.is_read:
            continue
        items.append(
            CockpitAttentionItemSchema(
                id=f"notification:{notification.notification_id}",
                source="notification",
                title=f"Unread notification for {notification.asset}",
                message=notification.message,
                priority=_priority_from_alert_level(notification.level, notification.status),
                status="unread",
                detected_at=None,
                attention_type="active_alert",
                evidence=[
                    f"alert_id:{notification.alert_id}",
                    f"rule_id:{notification.rule_id}",
                ],
                missing_data=["notification created_at not persisted in read model"],
                recommended_review_action="Review notification context in read-only mode and verify evidence sources.",
                is_actionable=False,
            )
        )

    for incident in incidents:
        incident_priority = _priority_from_incident_severity(incident.severity)
        source = "monitor" if _is_monitor_source(incident.source) else "incident"
        attention_type = "monitor_degraded" if source == "monitor" else "unresolved_incident"
        if _contains_stale_text(incident.code, incident.title, incident.detail):
            attention_type = "stale_data"
            source = "incident"

        if incident_priority not in {"high", "medium"} and attention_type == "unresolved_incident":
            continue

        items.append(
            CockpitAttentionItemSchema(
                id=f"incident:{incident.id}",
                source=source,
                title=incident.title,
                message=incident.detail or incident.code,
                priority=incident_priority,
                status="observed",
                detected_at=_iso(incident.occurred_at or incident.created_at),
                attention_type=attention_type,
                evidence=[
                    f"severity:{incident.severity}",
                    f"source:{incident.source}",
                    f"code:{incident.code}",
                ],
                missing_data=[],
                recommended_review_action=(
                    "Cross-check this incident with monitor and risk summaries; keep this surface read-only."
                ),
                is_actionable=False,
            )
        )

    for row in health_rows:
        if row.status not in {"degraded", "down", "error", "unknown"}:
            continue
        items.append(
            CockpitAttentionItemSchema(
                id=f"monitor:{row.name}",
                source="monitor",
                title=f"Monitor status {row.status}: {row.name}",
                message=row.detail or "Monitor probe reported a non-ok state.",
                priority=_priority_from_probe_status(row.status),
                status=row.status,
                detected_at=row.checked_at,
                attention_type="monitor_degraded",
                evidence=[
                    f"probe:{row.name}",
                    f"status:{row.status}",
                    f"latency_ms:{row.latency_ms}",
                ],
                missing_data=[] if row.latency_ms is not None else ["latency unavailable"],
                recommended_review_action="Review monitor probe diagnostics and confirm feed/provider stability.",
                is_actionable=False,
            )
        )

    for order in stale_paper_orders:
        order_status = (order.status or "unknown").lower()
        detected = _iso(order.submitted_at or order.timestamp or order.created_at)
        evidence = [f"order_status:{order_status}"]
        if order.asset_id is not None:
            evidence.append(f"asset_id:{order.asset_id}")
        items.append(
            CockpitAttentionItemSchema(
                id=f"paper-order:{order.id}",
                source="paper",
                title="Stale paper order needs review",
                message=(
                    f"Paper order remained in '{order_status}' beyond {_PAPER_ORDER_STALE_HOURS}h visibility threshold."
                ),
                priority="medium",
                status=order_status,
                detected_at=detected,
                attention_type="stale_data",
                evidence=evidence,
                missing_data=[] if detected is not None else ["order timestamp unavailable"],
                recommended_review_action="Review the paper order timeline and related incident notes before manual follow-up.",
                is_actionable=False,
            )
        )

    if risk_status is not None:
        missing_limits = list(risk_status.missing_limits)
        if not risk_status.risk_limits_configured or missing_limits:
            priority = "high" if not risk_status.risk_limits_configured else "medium"
            items.append(
                CockpitAttentionItemSchema(
                    id="risk:limits-status",
                    source="risk",
                    title="Risk limits need attention",
                    message=(
                        "Risk limits are not fully configured for paper monitoring visibility."
                        if not risk_status.risk_limits_configured
                        else "One or more risk limit dimensions are missing from the active paper profile."
                    ),
                    priority=priority,
                    status="review_required",
                    detected_at=None,
                    attention_type="risk_attention",
                    evidence=[
                        f"configured_limits:{len(risk_status.configured_limits)}",
                        f"missing_limits:{','.join(missing_limits) if missing_limits else 'none'}",
                    ],
                    missing_data=[] if missing_limits else ["no explicit missing risk-limit dimensions reported"],
                    recommended_review_action="Review risk-limit coverage and keep enforcement decisions outside this read-only page.",
                    is_actionable=False,
                )
            )

        risk_notes.append(risk_status.note)

    rejected_decisions = [
        decision
        for decision in risk_decisions
        if (decision.approved or "").lower() in {"rejected", "denied", "blocked"}
    ]
    for decision in rejected_decisions[:6]:
        reason = decision.block_reason_code or decision.blocking_rule or "unknown"
        signal_id = str(decision.signal_id) if decision.signal_id else "unknown"
        items.append(
            CockpitAttentionItemSchema(
                id=f"risk-decision:{decision.id}",
                source="risk",
                title="Recent risk rejection observed",
                message=f"Risk decision blocked signal {signal_id}: {reason}.",
                priority="medium",
                status=(decision.approved or "unknown").lower(),
                detected_at=_iso(decision.timestamp or decision.created_at),
                attention_type="risk_attention",
                evidence=[
                    f"signal_id:{signal_id}",
                    f"block_reason:{reason}",
                ],
                missing_data=[] if decision.signal_id else ["signal_id unavailable"],
                recommended_review_action="Review recent risk rejections and related rationale for paper-strategy tuning only.",
                is_actionable=False,
            )
        )

    if halt_status is not None and halt_status.emergency_stop_active:
        halt_reason = halt_status.blocked_reason or "Trading halt is active with no explicit reason text."
        items.append(
            CockpitAttentionItemSchema(
                id="trading-halt:global",
                source="trading_halt",
                title="Trading halt active",
                message=halt_reason,
                priority="high",
                status="active",
                detected_at=_iso(halt_status.active_halt.triggered_at) if halt_status.active_halt else None,
                attention_type="trading_halt",
                evidence=[
                    "scope:global",
                    f"status:{halt_status.status}",
                ],
                missing_data=[] if halt_status.active_halt else ["active halt details unavailable"],
                recommended_review_action="Treat this as an operator safety signal; do not mutate halt state from this page.",
                is_actionable=False,
            )
        )

    if halt_status is not None and halt_status.blocked_reason:
        risk_notes.append(halt_status.blocked_reason)

    if not active_alerts:
        limitations.append("No active alerts were available from persisted alert rules and paper execution records.")
    if not notifications:
        limitations.append("No unread alert notifications were available from the persisted notification projection.")
    if not incidents:
        limitations.append("No incidents were available; unresolved-incident visibility may be limited.")
    if not health_rows:
        limitations.append("No monitor probe rows were available; monitor degradation visibility may be limited.")
    if not stale_paper_orders:
        limitations.append("No stale paper orders were detected in the current dataset.")
    if risk_status is None:
        limitations.append("Risk-limit status could not be loaded for this report.")
    if halt_status is None:
        limitations.append("Trading-halt status could not be loaded for this report.")

    priority_counts = {"high": 0, "medium": 0, "low": 0, "unknown": 0}
    type_counts = {
        "active_alert": 0,
        "unresolved_incident": 0,
        "monitor_degraded": 0,
        "stale_data": 0,
        "risk_attention": 0,
        "trading_halt": 0,
        "missing_context": 0,
    }
    for item in items:
        priority_counts[item.priority] += 1
        type_counts[item.attention_type] += 1

    items.sort(
        key=lambda item: (
            _priority_rank(item.priority),
            item.detected_at or "",
            item.id,
        ),
        reverse=True,
    )

    if not items:
        limitations.append("No attention items were found from current paper, monitor, risk, and incident sources.")

    recommended_review_actions = [
        "Start with high-priority items, then work through medium-priority monitor and risk notes.",
        "Use this page for read-focused triage only; do not execute, close, modify, approve, acknowledge, or resolve here.",
        "Cross-check evidence with cockpit audit pages before any separate manual operator workflow.",
    ]

    return CockpitAlertsNeedingAttentionResponseSchema(
        generated_at=current_time.isoformat(),
        mode="paper",
        summary=CockpitAttentionSummarySchema(
            headline="Read-only paper attention queue for alerts, incidents, monitor health, and risk context.",
            total_items=len(items),
            high_priority=priority_counts["high"],
            medium_priority=priority_counts["medium"],
            low_priority=priority_counts["low"],
            unknown_priority=priority_counts["unknown"],
            active_alerts=type_counts["active_alert"],
            unresolved_incidents=type_counts["unresolved_incident"],
            monitor_degraded=type_counts["monitor_degraded"],
            stale_data=type_counts["stale_data"],
            risk_attention=type_counts["risk_attention"],
            trading_halt=type_counts["trading_halt"],
            missing_context=type_counts["missing_context"],
        ),
        attention_items=items,
        grouped_by_priority=_group_by(items, "priority"),
        grouped_by_source=_group_by(items, "source"),
        monitor_notes=monitor_notes[:12],
        risk_notes=risk_notes[:12],
        limitations=limitations[:20],
        recommended_review_actions=recommended_review_actions,
    )
