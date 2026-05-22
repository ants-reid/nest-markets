from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.asset import Asset
from app.db.models.incident_log import IncidentLog
from app.db.models.paper_order import PaperOrder
from app.db.models.position import Position
from app.db.models.risk_decision import RiskDecision
from app.schemas.cockpit_daily_scoreboard import (
    CockpitDailyScoreboardActivitySchema,
    CockpitDailyScoreboardClosedPositionsSchema,
    CockpitDailyScoreboardContributorSchema,
    CockpitDailyScoreboardNoteSchema,
    CockpitDailyScoreboardOpenPositionsSchema,
    CockpitDailyScoreboardPerformanceSchema,
    CockpitDailyScoreboardResponseSchema,
    CockpitDailyScoreboardSummarySchema,
    CockpitDailyScoreboardTopContributorsSchema,
)

_PAPER_POSITION_OPENED_BY = {"auto_paper", "manual_paper", "unknown"}
_ATTENTION_SEVERITIES = {"warn", "error", "critical"}
_MONITOR_SOURCE_MARKERS = ("monitor", "feed", "health")


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _ensure_utc(value: datetime | None) -> datetime:
    if value is None:
        return _now_utc()
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _day_bounds(now_utc: datetime) -> tuple[datetime, datetime]:
    start = datetime.combine(now_utc.date(), time.min, tzinfo=UTC)
    end = start + timedelta(days=1)
    return start, end


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
    normalized = getattr(value, "value", value)
    return str(normalized).lower()


def _load_assets(session: Session) -> tuple[dict[str, str], dict[str, str | None]]:
    rows = session.execute(select(Asset.id, Asset.symbol, Asset.name)).all()
    symbols_by_id = {str(asset_id): symbol for asset_id, symbol, _ in rows}
    names_by_id = {str(asset_id): name for asset_id, _, name in rows}
    return symbols_by_id, names_by_id


def _asset_context_from_symbol(
    *,
    symbol: str,
    symbol_to_asset_id: dict[str, str],
    names_by_id: dict[str, str | None],
) -> dict[str, str | bool | None]:
    if not symbol or symbol == "unknown":
        return {
            "asset_id": None,
            "asset_name": None,
            "asset_detail_path": None,
            "has_asset_context": False,
        }
    asset_id = symbol_to_asset_id.get(symbol.upper())
    if asset_id is None:
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


def _load_risk_decisions(session: Session) -> list[RiskDecision]:
    statement = select(RiskDecision).order_by(RiskDecision.created_at.desc(), RiskDecision.id.desc())
    return list(session.execute(statement).scalars().all())


def _load_incidents(session: Session) -> list[IncidentLog]:
    statement = select(IncidentLog).order_by(IncidentLog.created_at.desc(), IncidentLog.id.desc())
    return list(session.execute(statement).scalars().all())


def _opened_today_count(orders: list[PaperOrder], start: datetime, end: datetime) -> int:
    count = 0
    for row in orders:
        created_at = row.submitted_at or row.created_at or row.timestamp
        if created_at is None:
            continue
        created = _ensure_utc(created_at)
        if start <= created < end:
            count += 1
    return count


def _active_open_positions(positions: list[Position]) -> list[Position]:
    return [row for row in positions if row.closed_at is None and _status_text(row.status) == "open"]


def _closed_today_positions(positions: list[Position], start: datetime, end: datetime) -> list[Position]:
    closed_today: list[Position] = []
    for row in positions:
        if row.closed_at is None:
            continue
        closed_at = _ensure_utc(row.closed_at)
        if start <= closed_at < end:
            closed_today.append(row)
    return closed_today


def _risk_and_monitor_notes(
    incidents: list[IncidentLog],
    risk_decisions: list[RiskDecision],
    start: datetime,
    end: datetime,
) -> list[CockpitDailyScoreboardNoteSchema]:
    notes: list[CockpitDailyScoreboardNoteSchema] = []

    for incident in incidents:
        created_at = _ensure_utc(incident.created_at) if incident.created_at is not None else None
        if created_at is None or not (start <= created_at < end):
            continue

        source = (incident.source or "").lower()
        code = (incident.code or "").lower()
        severity = (incident.severity or "info").lower()
        is_monitor = any(marker in source or marker in code for marker in _MONITOR_SOURCE_MARKERS)
        is_attention = severity in _ATTENTION_SEVERITIES

        if not is_monitor and not is_attention:
            continue

        label = "monitor_attention" if is_monitor else "review_required"
        notes.append(
            CockpitDailyScoreboardNoteSchema(
                label=label,
                title=incident.title,
                detail=incident.detail or incident.code,
                severity=severity,
                created_at=_iso(incident.created_at),
            )
        )

    for decision in risk_decisions:
        if decision.approved == "approved":
            continue
        reason = decision.block_reason_code or decision.blocking_rule or "unknown"
        signal_text = str(decision.signal_id) if decision.signal_id is not None else "unknown-signal"
        notes.append(
            CockpitDailyScoreboardNoteSchema(
                label="review_required",
                title="Risk decision requires review",
                detail=f"{signal_text}: {decision.approved} ({reason})",
                severity="warn",
                created_at=_iso(decision.created_at),
            )
        )

    return notes[:10]


def _contribution_label(value: float | None) -> str:
    if value is None:
        return "unknown"
    if value > 0:
        return "positive"
    if value < 0:
        return "negative"
    return "flat"


def _top_contributors(
    closed_today: list[Position],
    symbols_by_id: dict[str, str],
    names_by_id: dict[str, str | None],
) -> CockpitDailyScoreboardTopContributorsSchema:
    symbol_to_asset_id = {
        symbol.upper(): asset_id
        for asset_id, symbol in symbols_by_id.items()
        if symbol
    }
    by_symbol: dict[str, float] = {}
    unknown_symbols: set[str] = set()
    for row in closed_today:
        symbol = symbols_by_id.get(str(row.asset_id), "unknown")
        realized = _as_float(row.realized_pnl)
        if realized is None:
            unknown_symbols.add(symbol)
            continue
        by_symbol[symbol] = by_symbol.get(symbol, 0.0) + realized

    if not by_symbol:
        items: list[CockpitDailyScoreboardContributorSchema] = []
        for symbol in sorted(unknown_symbols):
            context = _asset_context_from_symbol(
                symbol=symbol,
                symbol_to_asset_id=symbol_to_asset_id,
                names_by_id=names_by_id,
            )
            items.append(
                CockpitDailyScoreboardContributorSchema(
                    symbol=symbol,
                    asset_id=context["asset_id"],
                    asset_name=context["asset_name"],
                    asset_detail_path=context["asset_detail_path"],
                    has_asset_context=context["has_asset_context"],
                    realized_pnl=None,
                    contribution_label="unknown",
                    evidence=["realized_pnl_missing"],
                )
            )
        return CockpitDailyScoreboardTopContributorsSchema(count=len(items), items=items[:2])

    ranked = sorted(by_symbol.items(), key=lambda kv: kv[1], reverse=True)
    top_positive = ranked[0]
    top_negative = min(ranked, key=lambda kv: kv[1])

    positive_context = _asset_context_from_symbol(
        symbol=top_positive[0],
        symbol_to_asset_id=symbol_to_asset_id,
        names_by_id=names_by_id,
    )
    items: list[CockpitDailyScoreboardContributorSchema] = [
        CockpitDailyScoreboardContributorSchema(
            symbol=top_positive[0],
            asset_id=positive_context["asset_id"],
            asset_name=positive_context["asset_name"],
            asset_detail_path=positive_context["asset_detail_path"],
            has_asset_context=positive_context["has_asset_context"],
            realized_pnl=top_positive[1],
            contribution_label=_contribution_label(top_positive[1]),
            evidence=["realized_pnl_sum_by_symbol", "closed_positions_today"],
        )
    ]

    if top_negative[0] != top_positive[0]:
        negative_context = _asset_context_from_symbol(
            symbol=top_negative[0],
            symbol_to_asset_id=symbol_to_asset_id,
            names_by_id=names_by_id,
        )
        items.append(
            CockpitDailyScoreboardContributorSchema(
                symbol=top_negative[0],
                asset_id=negative_context["asset_id"],
                asset_name=negative_context["asset_name"],
                asset_detail_path=negative_context["asset_detail_path"],
                has_asset_context=negative_context["has_asset_context"],
                realized_pnl=top_negative[1],
                contribution_label=_contribution_label(top_negative[1]),
                evidence=["realized_pnl_sum_by_symbol", "closed_positions_today"],
            )
        )

    return CockpitDailyScoreboardTopContributorsSchema(count=len(items), items=items)


def _day_status(
    *,
    realized_pnl_today: float | None,
    limitations: list[str],
    notes: list[CockpitDailyScoreboardNoteSchema],
) -> str:
    if any(note.label == "monitor_attention" for note in notes):
        return "monitor_attention"
    if any(note.label == "review_required" for note in notes):
        return "review_required"
    if limitations:
        return "data_incomplete"
    if realized_pnl_today is None:
        return "unknown"
    if realized_pnl_today > 0:
        return "green_day"
    if realized_pnl_today < 0:
        return "red_day"
    return "flat_day"


def get_cockpit_daily_scoreboard(
    session: Session,
    *,
    now_utc: datetime | None = None,
) -> CockpitDailyScoreboardResponseSchema:
    now = _ensure_utc(now_utc)
    start, end = _day_bounds(now)

    symbols_by_id, names_by_id = _load_assets(session)
    orders = _load_paper_orders(session)
    positions = _load_positions(session)
    risk_decisions = _load_risk_decisions(session)
    incidents = _load_incidents(session)

    opened_today = _opened_today_count(orders, start, end)
    open_rows = _active_open_positions(positions)
    closed_today = _closed_today_positions(positions, start, end)

    realized_values = [_as_float(row.realized_pnl) for row in closed_today]
    realized_known = [value for value in realized_values if value is not None]
    realized_pnl_today = sum(realized_known) if len(realized_known) == len(closed_today) else None

    unrealized_values = [_as_float(row.unrealized_pnl) for row in open_rows]
    unrealized_known = [value for value in unrealized_values if value is not None]
    unrealized_pnl_snapshot = (
        sum(unrealized_known) if len(unrealized_known) == len(open_rows) else None
    )

    net_pnl_today = None
    if realized_pnl_today is not None and unrealized_pnl_snapshot is not None:
        net_pnl_today = realized_pnl_today + unrealized_pnl_snapshot

    wins = losses = flat = None
    if len(realized_known) == len(closed_today):
        wins = sum(1 for row in closed_today if (_as_float(row.realized_pnl) or 0.0) > 0)
        losses = sum(1 for row in closed_today if (_as_float(row.realized_pnl) or 0.0) < 0)
        flat = sum(1 for row in closed_today if (_as_float(row.realized_pnl) or 0.0) == 0)

    unknown = len(closed_today) - len(realized_known)

    long_count = sum(1 for row in open_rows if str(row.side).lower() == "long")
    short_count = sum(1 for row in open_rows if str(row.side).lower() == "short")

    contributors = _top_contributors(closed_today, symbols_by_id, names_by_id)
    notes = _risk_and_monitor_notes(incidents, risk_decisions, start, end)

    limitations: list[str] = []
    if not closed_today:
        limitations.append("No closed paper positions were found for today.")
    if realized_pnl_today is None and closed_today:
        limitations.append("Realized paper P&L is incomplete because one or more closed positions lack realized_pnl.")
    if unrealized_pnl_snapshot is None and open_rows:
        limitations.append("Unrealized paper P&L snapshot is incomplete because one or more open positions lack unrealized_pnl.")
    if not notes:
        limitations.append("No risk or monitor notes were detected for today.")
    if not contributors.items:
        limitations.append("Top contributors are unavailable because realized P&L evidence is missing.")

    review_priorities: list[str] = []
    if any(note.label == "monitor_attention" for note in notes):
        review_priorities.append("Review monitor/feed incidents first before interpreting scoreboard performance.")
    if any(note.label == "review_required" for note in notes):
        review_priorities.append("Review unresolved risk decisions and blocked signals before the next paper session.")
    if contributors.items:
        review_priorities.append("Review top positive and negative contributors to compare setup quality and exit behavior.")
    if unrealized_pnl_snapshot is not None and open_rows:
        review_priorities.append("Review open paper positions and unrealized exposure before carrying risk into the next session.")
    if not review_priorities:
        review_priorities.append("No urgent scoreboard review priorities were detected; maintain current paper safeguards.")

    day_status = _day_status(
        realized_pnl_today=realized_pnl_today,
        limitations=limitations,
        notes=notes,
    )

    return CockpitDailyScoreboardResponseSchema(
        report_date=now.date().isoformat(),
        generated_at=now.isoformat(),
        mode="paper",
        summary=CockpitDailyScoreboardSummarySchema(
            headline="Read-only daily paper-trading scoreboard for operator review.",
            day_status=day_status,
            trades_opened_today=opened_today,
            trades_closed_today=len(closed_today),
            open_positions_now=len(open_rows),
        ),
        performance=CockpitDailyScoreboardPerformanceSchema(
            realized_pnl_today=realized_pnl_today,
            unrealized_pnl_snapshot=unrealized_pnl_snapshot,
            net_pnl_today=net_pnl_today,
            win_count=wins,
            loss_count=losses,
            flat_count=flat,
            unknown_count=unknown,
        ),
        activity=CockpitDailyScoreboardActivitySchema(
            trades_opened_today=opened_today,
            trades_closed_today=len(closed_today),
            open_positions_now=len(open_rows),
        ),
        open_positions=CockpitDailyScoreboardOpenPositionsSchema(
            count=len(open_rows),
            long_count=long_count,
            short_count=short_count,
        ),
        closed_positions=CockpitDailyScoreboardClosedPositionsSchema(
            count=len(closed_today),
            wins=wins,
            losses=losses,
            flat=flat,
            unknown=unknown,
        ),
        top_contributors=contributors,
        risk_and_monitor_notes=notes,
        review_priorities=review_priorities,
        limitations=limitations,
    )
