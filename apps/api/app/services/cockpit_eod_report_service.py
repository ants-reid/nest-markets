"""MH-COCKPIT-05 — Read-only end-of-day report aggregator for paper trading.

Builds an operator-facing EOD snapshot using existing persisted paper-order,
position, signal-outcome, and incident-log data. The service is read-only and
never calls any broker, execution, or trading-control mutation path.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.asset import Asset
from app.db.models.incident_log import IncidentLog
from app.db.models.paper_order import PaperOrder
from app.db.models.position import Position
from app.db.models.signal_outcome import SignalOutcome
from app.schemas.cockpit_eod_report import (
    CockpitEodClosedPositionsSchema,
    CockpitEodIncidentItemSchema,
    CockpitEodLessonSchema,
    CockpitEodMonitorNoteSchema,
    CockpitEodOpenPositionItemSchema,
    CockpitEodOpenPositionsSchema,
    CockpitEodPaperActivitySchema,
    CockpitEodPnlSchema,
    CockpitEodReportResponseSchema,
    CockpitEodSummarySchema,
    CockpitEodTradeItemSchema,
)

_ATTENTION_SEVERITIES = {"warn", "error", "critical"}
_MONITOR_SOURCE_MARKERS = ("monitor", "feed", "health")
_PAPER_POSITION_OPENED_BY = {"auto_paper", "manual_paper", "unknown"}
_CLOSED_LIMIT = 5
_OPEN_LIMIT = 5
_INCIDENT_LIMIT = 5
_MONITOR_LIMIT = 5


def _ensure_utc(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _day_bounds(now_utc: datetime) -> tuple[datetime, datetime]:
    start = datetime.combine(now_utc.date(), time.min, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    return start, end


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _as_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _load_assets(session: Session) -> tuple[dict[str, str], dict[str, str | None]]:
    rows = session.execute(select(Asset.id, Asset.symbol, Asset.name)).all()
    symbols_by_id = {str(asset_id): symbol for asset_id, symbol, _ in rows}
    names_by_id = {str(asset_id): name for asset_id, _, name in rows}
    return symbols_by_id, names_by_id


def _load_paper_orders(session: Session) -> list[PaperOrder]:
    statement = select(PaperOrder).order_by(PaperOrder.created_at.desc(), PaperOrder.id.desc())
    return list(session.execute(statement).scalars().all())


def _load_positions(session: Session) -> list[Position]:
    statement = (
        select(Position)
        .where(Position.opened_by.in_(_PAPER_POSITION_OPENED_BY))
        .order_by(Position.created_at.desc(), Position.id.desc())
    )
    return list(session.execute(statement).scalars().all())


def _load_signal_outcomes(session: Session) -> list[SignalOutcome]:
    statement = select(SignalOutcome).order_by(SignalOutcome.created_at.desc(), SignalOutcome.id.desc())
    return list(session.execute(statement).scalars().all())


def _load_incidents(session: Session) -> list[IncidentLog]:
    statement = select(IncidentLog).order_by(IncidentLog.created_at.desc(), IncidentLog.id.desc())
    return list(session.execute(statement).scalars().all())


def _opened_today_count(orders: Iterable[PaperOrder], start: datetime, end: datetime) -> int:
    count = 0
    for order in orders:
        created_at = order.submitted_at or order.created_at or order.timestamp
        if created_at is None:
            continue
        created_at = _ensure_utc(created_at)
        if start <= created_at < end:
            count += 1
    return count


def _position_asset_symbol(position: Position, symbols_by_id: dict[str, str]) -> str:
    return symbols_by_id.get(str(position.asset_id), "unknown")


def _asset_context_from_position(
    position: Position,
    *,
    names_by_id: dict[str, str | None],
) -> dict[str, str | bool | None]:
    if position.asset_id is None:
        return {
            "asset_id": None,
            "asset_name": None,
            "asset_detail_path": None,
            "has_asset_context": False,
        }
    asset_id = str(position.asset_id)
    return {
        "asset_id": asset_id,
        "asset_name": names_by_id.get(asset_id),
        "asset_detail_path": f"/asset-cards/{asset_id}",
        "has_asset_context": True,
    }


def _trade_item(
    position: Position,
    symbols_by_id: dict[str, str],
    names_by_id: dict[str, str | None],
) -> CockpitEodTradeItemSchema:
    context = _asset_context_from_position(position, names_by_id=names_by_id)
    return CockpitEodTradeItemSchema(
        asset_symbol=_position_asset_symbol(position, symbols_by_id),
        asset_id=context["asset_id"],
        asset_name=context["asset_name"],
        asset_detail_path=context["asset_detail_path"],
        has_asset_context=context["has_asset_context"],
        side=position.side,
        opened_at=_iso(position.opened_at),
        closed_at=_iso(position.closed_at),
        realized_pnl=_as_float(position.realized_pnl),
        close_reason=position.close_reason,
    )


def _build_lessons(outcomes: list[SignalOutcome]) -> list[CockpitEodLessonSchema]:
    if not outcomes:
        return []

    lessons: list[CockpitEodLessonSchema] = []
    known_direction = [row for row in outcomes if row.predicted_direction_correct is not None]
    if known_direction:
        wins = sum(1 for row in known_direction if bool(row.predicted_direction_correct))
        lessons.append(
            CockpitEodLessonSchema(
                title="Directional accuracy",
                detail=f"{wins}/{len(known_direction)} closed outcomes matched the predicted direction today.",
                evidence_count=len(known_direction),
            )
        )

    pnl_known = [row for row in outcomes if _as_float(row.actual_pnl_pct) is not None]
    if pnl_known:
        best = max(pnl_known, key=lambda row: _as_float(row.actual_pnl_pct) or float("-inf"))
        worst = min(pnl_known, key=lambda row: _as_float(row.actual_pnl_pct) or float("inf"))
        lessons.append(
            CockpitEodLessonSchema(
                title="Best closed signal outcome",
                detail=f"Best recorded outcome closed at {_as_float(best.actual_pnl_pct):.2f}% P&L.",
                evidence_count=len(pnl_known),
            )
        )
        if worst is not best:
            lessons.append(
                CockpitEodLessonSchema(
                    title="Weakest closed signal outcome",
                    detail=f"Weakest recorded outcome closed at {_as_float(worst.actual_pnl_pct):.2f}% P&L.",
                    evidence_count=len(pnl_known),
                )
            )

    return lessons[:3]


def get_cockpit_eod_report(
    session: Session,
    *,
    now_utc: datetime | None = None,
) -> CockpitEodReportResponseSchema:
    now = _ensure_utc(now_utc)
    start, end = _day_bounds(now)
    symbols_by_id, names_by_id = _load_assets(session)
    orders = _load_paper_orders(session)
    positions = _load_positions(session)
    outcomes = _load_signal_outcomes(session)
    incidents = _load_incidents(session)

    opened_today = _opened_today_count(orders, start, end)

    open_positions_rows = [row for row in positions if row.closed_at is None]
    open_positions_items = [
        (
            lambda context: CockpitEodOpenPositionItemSchema(
                asset_symbol=_position_asset_symbol(row, symbols_by_id),
                asset_id=context["asset_id"],
                asset_name=context["asset_name"],
                asset_detail_path=context["asset_detail_path"],
                has_asset_context=context["has_asset_context"],
                side=row.side,
                qty=_as_float(row.qty),
                opened_at=_iso(row.opened_at),
                unrealized_pnl=_as_float(row.unrealized_pnl),
            )
        )(_asset_context_from_position(row, names_by_id=names_by_id))
        for row in open_positions_rows[:_OPEN_LIMIT]
    ]

    closed_today_rows = [
        row for row in positions
        if row.closed_at is not None and start <= _ensure_utc(row.closed_at) < end
    ]

    realized_values = [_as_float(row.realized_pnl) for row in closed_today_rows]
    realized_known = [value for value in realized_values if value is not None]
    realized_day = sum(realized_known) if len(realized_known) == len(closed_today_rows) else None

    unrealized_values = [_as_float(row.unrealized_pnl) for row in open_positions_rows]
    unrealized_known = [value for value in unrealized_values if value is not None]
    unrealized_snapshot = (
        sum(unrealized_known) if len(unrealized_known) == len(open_positions_rows) else None
    )

    best_trade_row = None
    worst_trade_row = None
    closed_with_realized = [row for row in closed_today_rows if _as_float(row.realized_pnl) is not None]
    if closed_with_realized:
        best_trade_row = max(closed_with_realized, key=lambda row: _as_float(row.realized_pnl) or float("-inf"))
        worst_trade_row = min(closed_with_realized, key=lambda row: _as_float(row.realized_pnl) or float("inf"))

    wins = losses = flat = None
    if len(closed_with_realized) == len(closed_today_rows):
        wins = sum(1 for row in closed_today_rows if (_as_float(row.realized_pnl) or 0.0) > 0)
        losses = sum(1 for row in closed_today_rows if (_as_float(row.realized_pnl) or 0.0) < 0)
        flat = sum(1 for row in closed_today_rows if (_as_float(row.realized_pnl) or 0.0) == 0)

    today_incidents = [
        row for row in incidents
        if row.created_at is not None and start <= _ensure_utc(row.created_at) < end
    ]
    attention_rows = [row for row in today_incidents if row.severity in _ATTENTION_SEVERITIES][:_INCIDENT_LIMIT]
    monitor_rows = [
        row for row in today_incidents
        if any(marker in (row.source or "").lower() or marker in (row.code or "").lower() for marker in _MONITOR_SOURCE_MARKERS)
    ][:_MONITOR_LIMIT]

    today_outcomes = [
        row for row in outcomes
        if row.closed_at is not None and start <= _ensure_utc(row.closed_at) < end
    ]
    lessons = _build_lessons(today_outcomes)

    limitations: list[str] = []
    if realized_day is None and closed_today_rows:
        limitations.append("Realized paper P&L is incomplete because one or more closed positions lack realized_pnl.")
    if unrealized_snapshot is None and open_positions_rows:
        limitations.append("Unrealized paper P&L snapshot is incomplete because one or more open positions lack unrealized_pnl.")
    if not today_outcomes:
        limitations.append("No closed signal outcomes were available for today, so lessons are limited.")
    if not monitor_rows:
        limitations.append("No monitor/feed incidents were recorded today, so monitor notes may be empty.")

    recommended_actions: list[str] = []
    if attention_rows:
        recommended_actions.append("Review the highest-severity incidents in Cockpit Notifications before the next paper session.")
    if open_positions_rows:
        recommended_actions.append("Review open paper positions and unrealized P&L on the Execution page before tomorrow's open.")
    if not today_outcomes:
        recommended_actions.append("Wait for more paper trades to close before drawing strong learning conclusions from the day.")
    if not recommended_actions:
        recommended_actions.append("No urgent EOD issues detected. Review the paper summary and carry forward the current paper-only safeguards.")

    return CockpitEodReportResponseSchema(
        report_date=now.date().isoformat(),
        generated_at=now.isoformat(),
        mode="paper",
        summary=CockpitEodSummarySchema(
            headline="Paper-mode end-of-day recap for operator review.",
            opened_today=opened_today,
            closed_today=len(closed_today_rows),
            open_positions_now=len(open_positions_rows),
            alerts_needing_attention=len(attention_rows),
            lessons_available=len(lessons),
        ),
        paper_activity=CockpitEodPaperActivitySchema(
            opened_today=opened_today,
            closed_today=len(closed_today_rows),
            current_open_positions=len(open_positions_rows),
        ),
        pnl=CockpitEodPnlSchema(
            realized_day=realized_day,
            unrealized_snapshot=unrealized_snapshot,
            realized_basis="closed_positions_today" if realized_day is not None else "unknown",
            unrealized_basis="open_positions_snapshot" if unrealized_snapshot is not None else "unknown",
        ),
        open_positions=CockpitEodOpenPositionsSchema(
            count=len(open_positions_rows),
            items=open_positions_items,
        ),
        closed_positions=CockpitEodClosedPositionsSchema(
            count=len(closed_today_rows),
            wins=wins,
            losses=losses,
            flat=flat,
            unknown=len(closed_today_rows) - len(closed_with_realized),
            best_trade=(
                _trade_item(best_trade_row, symbols_by_id, names_by_id)
                if best_trade_row is not None
                else None
            ),
            worst_trade=(
                _trade_item(worst_trade_row, symbols_by_id, names_by_id)
                if worst_trade_row is not None
                else None
            ),
            items=[_trade_item(row, symbols_by_id, names_by_id) for row in closed_today_rows[:_CLOSED_LIMIT]],
        ),
        alerts_or_incidents=[
            CockpitEodIncidentItemSchema(
                severity=row.severity,
                code=row.code,
                title=row.title,
                source=row.source,
                created_at=_iso(row.created_at),
                detail=row.detail,
            )
            for row in attention_rows
        ],
        monitor_notes=[
            CockpitEodMonitorNoteSchema(
                title=row.title,
                detail=row.detail or row.code,
                severity=row.severity,
                created_at=_iso(row.created_at),
            )
            for row in monitor_rows
        ],
        lessons=lessons,
        recommended_actions=recommended_actions,
        limitations=limitations,
    )