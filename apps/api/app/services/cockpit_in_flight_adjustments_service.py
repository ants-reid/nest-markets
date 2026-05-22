from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.asset import Asset
from app.db.models.incident_log import IncidentLog
from app.db.models.paper_order import PaperOrder
from app.db.models.paper_recommendation import PaperRecommendation
from app.db.models.position import Position
from app.db.models.risk_decision import RiskDecision
from app.schemas.cockpit_in_flight_adjustments import (
    CockpitInFlightAdjustmentsResponseSchema,
    CockpitInFlightItemSchema,
    CockpitInFlightNoteSchema,
    CockpitInFlightSummarySchema,
)

_PAPER_POSITION_OPENED_BY = {"auto_paper", "manual_paper", "unknown"}
_ACTIVE_ORDER_STATUSES = {"pending", "new", "accepted", "filled"}
_ACTIVE_RECOMMENDATION_STATUSES = {"draft", "reviewed", "approved"}


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return _ensure_utc(value).isoformat()


def _as_float(value: float | Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _status_text(value: object | None) -> str:
    if value is None:
        return "unknown"
    status = getattr(value, "value", value)
    return str(status).lower()


def _load_assets(session: Session) -> tuple[dict[str, str], dict[str, str | None], dict[str, str]]:
    rows = session.execute(select(Asset.id, Asset.symbol, Asset.name)).all()
    symbols_by_id = {str(asset_id): symbol for asset_id, symbol, _ in rows}
    names_by_id = {str(asset_id): name for asset_id, _, name in rows}
    ids_by_symbol = {
        symbol.upper(): str(asset_id)
        for asset_id, symbol, _ in rows
        if symbol
    }
    return symbols_by_id, names_by_id, ids_by_symbol


def _asset_context_from_asset_id(
    *,
    asset_id: str | None,
    names_by_id: dict[str, str | None],
) -> dict[str, str | bool | None]:
    if not asset_id:
        return {
            "asset_id": None,
            "asset_name": None,
            "asset_detail_path": None,
            "has_asset_context": False,
        }
    return {
        "asset_id": asset_id,
        "asset_name": names_by_id.get(asset_id),
        "asset_detail_path": f"/asset-cards/{asset_id}",
        "has_asset_context": True,
    }


def _asset_context_from_symbol(
    *,
    symbol: str | None,
    ids_by_symbol: dict[str, str],
    names_by_id: dict[str, str | None],
) -> dict[str, str | bool | None]:
    if not symbol:
        return {
            "asset_id": None,
            "asset_name": None,
            "asset_detail_path": None,
            "has_asset_context": False,
        }
    asset_id = ids_by_symbol.get(symbol.upper())
    return _asset_context_from_asset_id(asset_id=asset_id, names_by_id=names_by_id)


def _load_positions(session: Session) -> list[Position]:
    statement = (
        select(Position)
        .where(Position.opened_by.in_(_PAPER_POSITION_OPENED_BY))
        .order_by(Position.created_at.desc(), Position.id.desc())
    )
    return list(session.execute(statement).scalars().all())


def _load_paper_orders(session: Session) -> list[PaperOrder]:
    statement = select(PaperOrder).order_by(PaperOrder.created_at.desc(), PaperOrder.id.desc())
    return list(session.execute(statement).scalars().all())


def _load_paper_recommendations(session: Session) -> list[PaperRecommendation]:
    statement = select(PaperRecommendation).order_by(PaperRecommendation.created_at.desc(), PaperRecommendation.id.desc())
    return list(session.execute(statement).scalars().all())


def _load_risk_decisions(session: Session) -> list[RiskDecision]:
    statement = select(RiskDecision).order_by(RiskDecision.created_at.desc(), RiskDecision.id.desc())
    return list(session.execute(statement).scalars().all())


def _load_incidents(session: Session) -> list[IncidentLog]:
    statement = select(IncidentLog).order_by(IncidentLog.created_at.desc(), IncidentLog.id.desc())
    return list(session.execute(statement).scalars().all())


def _active_positions(positions: Iterable[Position]) -> list[Position]:
    active: list[Position] = []
    for position in positions:
        if _status_text(position.status) == "open":
            active.append(position)
    return active


def _active_orders(orders: Iterable[PaperOrder]) -> list[PaperOrder]:
    active: list[PaperOrder] = []
    for order in orders:
        if _status_text(order.status) in _ACTIVE_ORDER_STATUSES:
            active.append(order)
    return active


def _active_recommendations(recommendations: Iterable[PaperRecommendation]) -> list[PaperRecommendation]:
    active: list[PaperRecommendation] = []
    for recommendation in recommendations:
        if _status_text(recommendation.status) in _ACTIVE_RECOMMENDATION_STATUSES:
            active.append(recommendation)
    return active


def _attention_level(label: str, missing_data: list[str]) -> str:
    if label in {"risk_attention", "monitor_issue"}:
        return "high"
    if label in {"review_required", "stale_data", "missing_context"}:
        return "medium"
    if label == "watch_only" and not missing_data:
        return "low"
    return "unknown"


def _position_item(
    position: Position,
    *,
    now_utc: datetime,
    symbols_by_id: dict[str, str],
    names_by_id: dict[str, str | None],
    risk_by_signal: dict[str, RiskDecision],
    monitor_block: bool,
) -> CockpitInFlightItemSchema:
    asset_id = str(position.asset_id) if position.asset_id is not None else None
    symbol = symbols_by_id.get(asset_id or "", "unknown")
    context = _asset_context_from_asset_id(asset_id=asset_id, names_by_id=names_by_id)
    missing_data: list[str] = []
    evidence = [f"position_status={_status_text(position.status)}", f"side={position.side}"]
    if position.stop_price is None:
        missing_data.append("stop_price")
    if position.target_price is None:
        missing_data.append("target_price")
    if position.current_price is None:
        missing_data.append("current_price")

    label = "watch_only"
    reason = "Open paper position is currently stable and should be monitored."

    opened_at = _ensure_utc(position.opened_at) if position.opened_at else None
    if opened_at and now_utc - opened_at > timedelta(hours=24):
        label = "stale_data"
        reason = "Open paper position has remained open for more than 24 hours and should be reviewed."

    unrealized = _as_float(position.unrealized_pnl)
    if unrealized is not None:
        evidence.append(f"unrealized_pnl={unrealized:.2f}")
        if unrealized < 0:
            label = "risk_attention"
            reason = "Open paper position has negative unrealized P&L and may require risk review."
    else:
        missing_data.append("unrealized_pnl")

    if missing_data and label == "watch_only":
        label = "missing_context"
        reason = "Open paper position is missing required context for a confident adjustment review."

    if monitor_block:
        label = "monitor_issue"
        reason = "Monitor incidents are active; review this open paper position with feed/health context."

    if position.signal_id is not None:
        decision = risk_by_signal.get(str(position.signal_id))
        if decision and decision.approved != "approved":
            label = "risk_attention"
            block_reason = decision.block_reason_code or decision.blocking_rule or "unknown"
            reason = "Related risk decision is not approved and needs operator risk review."
            evidence.append(f"risk_decision={decision.approved}")
            evidence.append(f"risk_block_reason={block_reason}")

    summary = (
        f"{symbol} {position.side} qty={_as_float(position.qty) if position.qty is not None else 'unknown'} "
        f"entry={_as_float(position.avg_entry_price) if position.avg_entry_price is not None else 'unknown'}"
    )

    return CockpitInFlightItemSchema(
        id=str(position.id),
        item_type="paper_position",
        symbol=symbol,
        asset_id=context["asset_id"],
        asset_name=context["asset_name"],
        asset_detail_path=context["asset_detail_path"],
        has_asset_context=context["has_asset_context"],
        status=_status_text(position.status),
        opened_at=_iso(position.opened_at),
        created_at=_iso(position.created_at),
        current_state_summary=summary,
        attention_level=_attention_level(label, missing_data),
        adjustment_label=label,
        reason=reason,
        evidence=evidence,
        missing_data=missing_data,
        recommended_review_action=(
            "Review position risk context, stop/target geometry, and monitor health before next paper check."
        ),
        is_actionable=False,
    )


def _order_item(
    order: PaperOrder,
    *,
    now_utc: datetime,
    symbols_by_id: dict[str, str],
    names_by_id: dict[str, str | None],
    risk_by_signal: dict[str, RiskDecision],
) -> CockpitInFlightItemSchema:
    asset_id = str(order.asset_id) if order.asset_id is not None else None
    symbol = symbols_by_id.get(asset_id or "", "unknown")
    context = _asset_context_from_asset_id(asset_id=asset_id, names_by_id=names_by_id)
    created_at = order.submitted_at or order.created_at or order.timestamp
    created_dt = _ensure_utc(created_at) if created_at else None

    missing_data: list[str] = []
    evidence = [f"order_status={_status_text(order.status)}"]
    if order.qty is None and order.quantity is None:
        missing_data.append("quantity")
    if not order.side:
        missing_data.append("side")

    label = "watch_only"
    reason = "Paper order is in-flight and currently informational."

    if created_dt and now_utc - created_dt > timedelta(minutes=30):
        label = "stale_data"
        reason = "Paper order has remained in an active state for over 30 minutes."

    if missing_data:
        label = "missing_context"
        reason = "Paper order is missing context required for a confident review."

    if order.signal_id is not None:
        decision = risk_by_signal.get(str(order.signal_id))
        if decision and decision.approved != "approved":
            label = "risk_attention"
            block_reason = decision.block_reason_code or decision.blocking_rule or "unknown"
            reason = "Related risk decision is not approved and needs operator review."
            evidence.append(f"risk_decision={decision.approved}")
            evidence.append(f"risk_block_reason={block_reason}")

    qty = _as_float(order.qty if order.qty is not None else order.quantity)
    summary = (
        f"{symbol} {order.side or 'unknown'} qty={qty if qty is not None else 'unknown'} "
        f"type={order.order_type or 'unknown'}"
    )

    return CockpitInFlightItemSchema(
        id=str(order.id),
        item_type="paper_order",
        symbol=symbol,
        asset_id=context["asset_id"],
        asset_name=context["asset_name"],
        asset_detail_path=context["asset_detail_path"],
        has_asset_context=context["has_asset_context"],
        status=_status_text(order.status),
        opened_at=None,
        created_at=_iso(created_at),
        current_state_summary=summary,
        attention_level=_attention_level(label, missing_data),
        adjustment_label=label,
        reason=reason,
        evidence=evidence,
        missing_data=missing_data,
        recommended_review_action=(
            "Review order lifecycle and risk gate notes before deciding whether to keep monitoring."
        ),
        is_actionable=False,
    )


def _recommendation_item(
    recommendation: PaperRecommendation,
    *,
    now_utc: datetime,
    ids_by_symbol: dict[str, str],
    names_by_id: dict[str, str | None],
    risk_by_signal: dict[str, RiskDecision],
) -> CockpitInFlightItemSchema:
    missing_data: list[str] = []
    evidence = [f"recommendation_status={_status_text(recommendation.status)}"]
    if recommendation.rationale is None:
        missing_data.append("rationale")
    if recommendation.confidence is None:
        missing_data.append("confidence")

    label = "watch_only"
    reason = "Paper recommendation is active for read-focused operator review."

    age = now_utc - _ensure_utc(recommendation.created_at)
    if age > timedelta(hours=6):
        label = "stale_data"
        reason = "Paper recommendation is still active after 6 hours and should be re-checked."

    confidence = _as_float(recommendation.confidence)
    risk_score = _as_float(recommendation.risk_score)
    if confidence is not None:
        evidence.append(f"confidence={confidence:.2f}")
        if confidence < 0.55:
            label = "review_required"
            reason = "Recommendation confidence is low and requires manual review."
    if risk_score is not None:
        evidence.append(f"risk_score={risk_score:.2f}")
        if risk_score >= 0.70:
            label = "risk_attention"
            reason = "Recommendation risk score is elevated and should be reviewed carefully."

    if recommendation.signal_id is not None:
        decision = risk_by_signal.get(str(recommendation.signal_id))
        if decision and decision.approved != "approved":
            label = "risk_attention"
            block_reason = decision.block_reason_code or decision.blocking_rule or "unknown"
            reason = "Linked risk decision indicates unresolved gating concerns."
            evidence.append(f"risk_decision={decision.approved}")
            evidence.append(f"risk_block_reason={block_reason}")

    if missing_data and label == "watch_only":
        label = "missing_context"
        reason = "Recommendation context is incomplete for safe in-flight adjustment analysis."

    summary = (
        f"{recommendation.ticker} {recommendation.side} qty={_as_float(recommendation.quantity)} "
        f"order_type={recommendation.order_type}"
    )

    context = _asset_context_from_symbol(
        symbol=recommendation.ticker,
        ids_by_symbol=ids_by_symbol,
        names_by_id=names_by_id,
    )

    return CockpitInFlightItemSchema(
        id=str(recommendation.id),
        item_type="paper_recommendation",
        symbol=recommendation.ticker,
        asset_id=context["asset_id"],
        asset_name=context["asset_name"],
        asset_detail_path=context["asset_detail_path"],
        has_asset_context=context["has_asset_context"],
        status=_status_text(recommendation.status),
        opened_at=None,
        created_at=_iso(recommendation.created_at),
        current_state_summary=summary,
        attention_level=_attention_level(label, missing_data),
        adjustment_label=label,
        reason=reason,
        evidence=evidence,
        missing_data=missing_data,
        recommended_review_action=(
            "Review recommendation rationale, confidence, and linked risk decision evidence in paper mode."
        ),
        is_actionable=False,
    )


def _monitor_notes(incidents: list[IncidentLog]) -> list[CockpitInFlightNoteSchema]:
    notes: list[CockpitInFlightNoteSchema] = []
    for incident in incidents:
        source = (incident.source or "").lower()
        code = (incident.code or "").lower()
        if not ("monitor" in source or "feed" in source or "monitor" in code or "feed" in code):
            continue
        notes.append(
            CockpitInFlightNoteSchema(
                title=incident.title,
                detail=incident.detail or incident.code,
                severity=(incident.severity or "info").lower(),
                created_at=_iso(incident.created_at),
            )
        )
    return notes[:8]


def _risk_notes(risk_decisions: list[RiskDecision]) -> list[str]:
    notes: list[str] = []
    for decision in risk_decisions:
        if decision.approved == "approved":
            continue
        reason = decision.block_reason_code or decision.blocking_rule or "unknown"
        signal_text = str(decision.signal_id) if decision.signal_id else "unknown-signal"
        notes.append(f"Risk decision {decision.approved} for {signal_text}: {reason}.")
    if not notes:
        notes.append("No explicit rejected risk decisions were found in the recent dataset.")
    return notes[:8]


def get_cockpit_in_flight_adjustments(
    session: Session,
    *,
    now_utc: datetime | None = None,
) -> CockpitInFlightAdjustmentsResponseSchema:
    current_time = _ensure_utc(now_utc or _now_utc())

    symbols_by_id, names_by_id, ids_by_symbol = _load_assets(session)
    positions = _active_positions(_load_positions(session))
    orders = _active_orders(_load_paper_orders(session))
    recommendations = _active_recommendations(_load_paper_recommendations(session))
    risk_decisions = _load_risk_decisions(session)
    incidents = _load_incidents(session)

    risk_by_signal: dict[str, RiskDecision] = {}
    for decision in risk_decisions:
        if decision.signal_id is None:
            continue
        key = str(decision.signal_id)
        if key not in risk_by_signal:
            risk_by_signal[key] = decision

    monitor_notes = _monitor_notes(incidents)
    monitor_alert_active = any(note.severity in {"error", "critical", "warn"} for note in monitor_notes)

    items: list[CockpitInFlightItemSchema] = []
    items.extend(
        _position_item(
            position,
            now_utc=current_time,
            symbols_by_id=symbols_by_id,
            names_by_id=names_by_id,
            risk_by_signal=risk_by_signal,
            monitor_block=monitor_alert_active,
        )
        for position in positions
    )
    items.extend(
        _order_item(
            order,
            now_utc=current_time,
            symbols_by_id=symbols_by_id,
            names_by_id=names_by_id,
            risk_by_signal=risk_by_signal,
        )
        for order in orders
    )
    items.extend(
        _recommendation_item(
            recommendation,
            now_utc=current_time,
            ids_by_symbol=ids_by_symbol,
            names_by_id=names_by_id,
            risk_by_signal=risk_by_signal,
        )
        for recommendation in recommendations
    )

    items.sort(key=lambda item: (item.attention_level, item.created_at or "", item.id), reverse=True)

    label_counts: dict[str, int] = {}
    high_attention = 0
    for item in items:
        label_counts[item.adjustment_label] = label_counts.get(item.adjustment_label, 0) + 1
        if item.attention_level == "high":
            high_attention += 1

    limitations: list[str] = []
    if not items:
        limitations.append("No in-flight paper items were found in persisted positions, orders, or recommendations.")
    if not monitor_notes:
        limitations.append("No monitor/feed incidents were available; monitor_issue labeling may be incomplete.")
    if not risk_decisions:
        limitations.append("No recent risk decisions were available; risk_attention context may be limited.")

    recommended_review_actions = [
        "Start with high-attention items, then move through review_required and stale_data labels.",
        "Cross-check item evidence with the risk and monitor sections before making any manual paper decisions.",
        "Treat this surface as visibility only; use execution controls separately for any non-read workflow.",
    ]

    return CockpitInFlightAdjustmentsResponseSchema(
        generated_at=current_time.isoformat(),
        mode="paper",
        summary=CockpitInFlightSummarySchema(
            headline="Read-only in-flight paper adjustments watchlist for operator review.",
            total_items=len(items),
            open_positions=len(positions),
            open_orders=len(orders),
            active_recommendations=len(recommendations),
            watch_only=label_counts.get("watch_only", 0),
            review_required=label_counts.get("review_required", 0) + label_counts.get("risk_attention", 0),
            high_attention=high_attention,
        ),
        items=items,
        monitor_notes=monitor_notes,
        risk_notes=_risk_notes(risk_decisions),
        limitations=limitations,
        recommended_review_actions=recommended_review_actions,
    )
