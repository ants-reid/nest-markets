from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.asset import Asset
from app.db.models.paper_order import PaperOrder
from app.db.models.position import Position
from app.db.models.risk_decision import RiskDecision
from app.db.models.signal_outcome import SignalOutcome
from app.schemas.cockpit_trade_close_explanations import (
    CockpitTradeCloseExplanationSchema,
    CockpitTradeCloseExplanationsResponseSchema,
    CockpitTradeCloseSummarySchema,
)

_PAPER_POSITION_OPENED_BY = {"auto_paper", "manual_paper", "unknown"}
_MAX_ROWS = 150


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


def _as_float(value: float | Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _status_text(value: object | None) -> str:
    if value is None:
        return "unknown"
    normalized = getattr(value, "value", value)
    return str(normalized).lower()


def _load_assets(session: Session) -> dict[str, str]:
    rows = session.execute(select(Asset.id, Asset.symbol)).all()
    return {str(asset_id): symbol for asset_id, symbol in rows}


def _load_closed_positions(session: Session) -> list[Position]:
    statement = (
        select(Position)
        .where(Position.opened_by.in_(_PAPER_POSITION_OPENED_BY))
        .order_by(Position.closed_at.desc(), Position.created_at.desc(), Position.id.desc())
    )
    rows = list(session.execute(statement).scalars().all())
    closed: list[Position] = []
    for row in rows:
        status = _status_text(row.status)
        if row.closed_at is not None or status == "closed":
            closed.append(row)
    return closed


def _load_paper_orders(session: Session) -> list[PaperOrder]:
    statement = select(PaperOrder).order_by(PaperOrder.created_at.desc(), PaperOrder.id.desc())
    return list(session.execute(statement).scalars().all())


def _load_signal_outcomes(session: Session) -> list[SignalOutcome]:
    statement = select(SignalOutcome).order_by(SignalOutcome.closed_at.desc(), SignalOutcome.created_at.desc(), SignalOutcome.id.desc())
    return list(session.execute(statement).scalars().all())


def _load_risk_decisions(session: Session) -> list[RiskDecision]:
    statement = select(RiskDecision).order_by(RiskDecision.created_at.desc(), RiskDecision.id.desc())
    return list(session.execute(statement).scalars().all())


def _close_label_from_reason(reason: str | None) -> str:
    if not reason:
        return "unknown"
    lowered = reason.lower()
    if "target" in lowered:
        return "target_hit"
    if "stop" in lowered:
        return "stop_hit"
    if "manual" in lowered or "operator" in lowered or lowered == "paper_order_closed":
        return "manual_close"
    if "timeout" in lowered or "stale" in lowered or "expired" in lowered or "horizon" in lowered:
        return "timeout_or_stale"
    if "validation" in lowered or "invalidat" in lowered or "geometry" in lowered:
        return "validation_close"
    if "risk" in lowered or "kill_switch" in lowered or "drawdown" in lowered or "limit" in lowered:
        return "risk_close"
    return "unknown"


def _price_close_match(a: float | None, b: float | None) -> bool:
    if a is None or b is None:
        return False
    tolerance = max(0.01, abs(b) * 0.003)
    return abs(a - b) <= tolerance


def _infer_close_label(
    *,
    position: Position,
    risk_decision: RiskDecision | None,
) -> tuple[str, str | None]:
    explicit = _close_label_from_reason(position.close_reason)
    if explicit != "unknown":
        return explicit, position.close_reason

    close_price = _as_float(getattr(position, "close_price", None))
    if _price_close_match(close_price, _as_float(position.target_price)):
        return "target_hit", "inferred_from_close_price_vs_target"
    if _price_close_match(close_price, _as_float(position.stop_price)):
        return "stop_hit", "inferred_from_close_price_vs_stop"

    if risk_decision is not None and risk_decision.approved != "approved":
        return "risk_close", risk_decision.block_reason_code or risk_decision.blocking_rule

    return "unknown", position.close_reason


def _outcome_match(
    *,
    position: Position,
    outcome: SignalOutcome | None,
) -> tuple[str, str | None]:
    if outcome is not None and outcome.predicted_direction_correct is not None:
        matched = bool(outcome.predicted_direction_correct)
        return ("matched" if matched else "mismatched"), "signal_outcome.predicted_direction_correct"

    realized = _as_float(position.realized_pnl)
    if realized is None:
        return "unknown", None
    if realized > 0:
        return "matched", "realized_pnl_positive"
    if realized < 0:
        return "mismatched", "realized_pnl_negative"
    return "unknown", "realized_pnl_flat"


def _find_order_for_position(position: Position, by_signal: dict[str, list[PaperOrder]]) -> PaperOrder | None:
    if position.signal_id is None:
        return None
    candidates = by_signal.get(str(position.signal_id), [])
    if not candidates:
        return None

    closed = [row for row in candidates if _status_text(row.status) == "closed"]
    if closed:
        return closed[0]
    return candidates[0]


def _learning_note(close_label: str, realized_pnl: float | None, outcome_match: str) -> str:
    if close_label == "target_hit":
        return "Target-aligned exits can be reviewed for repeatable setup quality before increasing confidence."
    if close_label == "stop_hit":
        return "Stop-based exits can be reviewed to check whether entry quality or volatility context degraded."
    if close_label == "risk_close":
        return "Risk-driven exits should be compared with risk rules to confirm expected protective behavior."
    if close_label in {"timeout_or_stale", "validation_close"}:
        return "Non-price exits should be reviewed with horizon and validation evidence before drawing conclusions."

    if realized_pnl is None:
        return "Outcome context is incomplete; preserve this close for later review once missing fields are available."
    if outcome_match == "matched":
        return "The close aligned with setup direction; capture what conditions were stable at entry and exit."
    if outcome_match == "mismatched":
        return "The close diverged from setup direction; review signal quality and risk context for similar patterns."
    return "Treat this close as neutral evidence until more context is available."


def _result_summary(close_label: str, realized_pnl: float | None, outcome_match: str) -> str:
    pnl_text = "realized P&L unknown"
    if realized_pnl is not None:
        if realized_pnl > 0:
            pnl_text = f"realized gain {realized_pnl:.2f}"
        elif realized_pnl < 0:
            pnl_text = f"realized loss {realized_pnl:.2f}"
        else:
            pnl_text = "flat realized P&L"
    return f"Close label {close_label}; {pnl_text}; setup match {outcome_match}."


def get_cockpit_trade_close_explanations(
    session: Session,
    *,
    now_utc: datetime | None = None,
) -> CockpitTradeCloseExplanationsResponseSchema:
    current_time = _ensure_utc(now_utc) or _now_utc()

    assets = _load_assets(session)
    positions = _load_closed_positions(session)
    orders = _load_paper_orders(session)
    outcomes = _load_signal_outcomes(session)
    risk_decisions = _load_risk_decisions(session)

    orders_by_signal: dict[str, list[PaperOrder]] = {}
    for row in orders:
        if row.signal_id is None:
            continue
        orders_by_signal.setdefault(str(row.signal_id), []).append(row)

    outcomes_by_signal: dict[str, SignalOutcome] = {}
    for row in outcomes:
        key = str(row.signal_id)
        if key not in outcomes_by_signal:
            outcomes_by_signal[key] = row

    risk_by_signal: dict[str, RiskDecision] = {}
    for row in risk_decisions:
        if row.signal_id is None:
            continue
        key = str(row.signal_id)
        if key not in risk_by_signal:
            risk_by_signal[key] = row

    explanations: list[CockpitTradeCloseExplanationSchema] = []

    for position in positions[:_MAX_ROWS]:
        symbol = assets.get(str(position.asset_id), "unknown")
        linked_order = _find_order_for_position(position, orders_by_signal)
        linked_outcome = outcomes_by_signal.get(str(position.signal_id)) if position.signal_id is not None else None
        linked_risk = risk_by_signal.get(str(position.signal_id)) if position.signal_id is not None else None

        close_label, close_reason = _infer_close_label(position=position, risk_decision=linked_risk)
        outcome_match, outcome_match_evidence = _outcome_match(position=position, outcome=linked_outcome)

        realized_pnl = _as_float(position.realized_pnl)
        evidence = [f"position_status={_status_text(position.status)}"]
        if position.close_reason:
            evidence.append(f"position.close_reason={position.close_reason}")
        if linked_order is not None:
            evidence.append(f"paper_order.status={_status_text(linked_order.status)}")
        if linked_outcome is not None and linked_outcome.actual_pnl_pct is not None:
            evidence.append(f"signal_outcome.actual_pnl_pct={_as_float(linked_outcome.actual_pnl_pct):.4f}")
        if outcome_match_evidence:
            evidence.append(f"setup_match_basis={outcome_match_evidence}")
        if linked_risk is not None and linked_risk.approved != "approved":
            reason = linked_risk.block_reason_code or linked_risk.blocking_rule or "unknown"
            evidence.append(f"risk_decision={linked_risk.approved}:{reason}")

        missing_data: list[str] = []
        if position.closed_at is None:
            missing_data.append("closed_at")
        if position.opened_at is None:
            missing_data.append("opened_at")
        if position.close_reason is None:
            missing_data.append("close_reason")
        if linked_order is None:
            missing_data.append("paper_order_link")
        if linked_outcome is None:
            missing_data.append("signal_outcome")

        explanations.append(
            CockpitTradeCloseExplanationSchema(
                id=str(position.id),
                paper_order_id=str(linked_order.id) if linked_order is not None else None,
                position_id=str(position.id),
                symbol=symbol,
                opened_at=_iso(position.opened_at),
                closed_at=_iso(position.closed_at),
                status=_status_text(position.status),
                close_label=close_label,
                close_reason=close_reason,
                result_summary=_result_summary(close_label, realized_pnl, outcome_match),
                realized_pnl=realized_pnl,
                outcome_match=outcome_match,
                evidence=evidence,
                missing_data=missing_data,
                learning_note=_learning_note(close_label, realized_pnl, outcome_match),
                is_actionable=False,
            )
        )

    known_close_labels = sum(1 for row in explanations if row.close_label != "unknown")
    unknown_close_labels = len(explanations) - known_close_labels
    profitable = sum(1 for row in explanations if row.realized_pnl is not None and row.realized_pnl > 0)
    losing = sum(1 for row in explanations if row.realized_pnl is not None and row.realized_pnl < 0)
    flat = sum(1 for row in explanations if row.realized_pnl == 0)

    setup_matched = sum(1 for row in explanations if row.outcome_match == "matched")
    setup_mismatched = sum(1 for row in explanations if row.outcome_match == "mismatched")
    setup_unknown = sum(1 for row in explanations if row.outcome_match == "unknown")

    limitations: list[str] = []
    if not explanations:
        limitations.append("No closed paper trades were found in persisted paper positions.")
    if any("paper_order_link" in row.missing_data for row in explanations):
        limitations.append("Some closed positions could not be linked to a paper order id.")
    if any("signal_outcome" in row.missing_data for row in explanations):
        limitations.append("Some closed trades are missing signal-outcome records, limiting setup-match evidence.")
    if any(row.close_label == "unknown" for row in explanations):
        limitations.append("Unknown close labels are returned when evidence is insufficient for safe inference.")

    recommended_review_actions = [
        "Review unknown and risk_close labels first, then compare evidence with execution and risk logs.",
        "Use close explanations as audit context only; any trading action remains outside this read-only surface.",
        "Track repeated close patterns across setup types before adjusting paper strategy assumptions.",
    ]

    return CockpitTradeCloseExplanationsResponseSchema(
        generated_at=current_time.isoformat(),
        mode="paper",
        summary=CockpitTradeCloseSummarySchema(
            headline="Read-only explanations for recently closed paper trades.",
            total_closed_trades=len(explanations),
            known_close_labels=known_close_labels,
            unknown_close_labels=unknown_close_labels,
            profitable_trades=profitable,
            losing_trades=losing,
            flat_trades=flat,
            setup_matched=setup_matched,
            setup_mismatched=setup_mismatched,
            setup_unknown=setup_unknown,
        ),
        explanations=explanations,
        limitations=limitations,
        recommended_review_actions=recommended_review_actions,
    )
