"""Broker submit-decision persistence service (MH-148-C).

Persists broker preflight/submit decisions into ``broker_submit_decisions`` as
audit rows. This service is write-only for decision capture plus read helpers;
it never executes broker orders and never alters trading guards.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models.broker_submit_decision import BrokerSubmitDecision

_MAX_REASON_CODE = 64
_MAX_REASON_TEXT = 500
_MAX_MESSAGE = 240


def _cap_text(value: str | None, max_len: int) -> str | None:
    if value is None:
        return None
    if len(value) <= max_len:
        return value
    return value[:max_len]


def _sanitize_items(items: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in items or []:
        out.append(
            {
                "code": item.get("code"),
                "message": _cap_text(str(item.get("message") or ""), _MAX_MESSAGE),
                "source": item.get("source"),
                "classification": item.get("classification"),
                "severity": item.get("severity"),
            }
        )
    return out


@dataclass(frozen=True)
class BrokerSubmitDecisionRecord:
    """Typed record contract for writing one broker submit-decision row."""

    intent: str
    would_block: bool
    decision_status: str
    allowed_to_submit: bool
    decision_reason: str | None
    blocked_reason_code: str | None
    blocked_reason_text: str | None
    blocked_reasons: list[dict[str, Any]]
    warnings: list[dict[str, Any]]
    execution_mode: str
    account_mode: str
    source: str
    submit_gate: str
    broker_order_id: str | None = None
    correlation_id: str | None = None
    risk_profile_id: str | None = None
    risk_block_reason: str | None = None
    signal_id: UUID | None = None


class BrokerSubmitDecisionService:
    """Persistence API for ``BrokerSubmitDecision`` audit rows."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def persist(self, record: BrokerSubmitDecisionRecord) -> BrokerSubmitDecision:
        """Insert one decision row with sanitized audit payload."""
        row = BrokerSubmitDecision(
            signal_id=record.signal_id,
            intent=record.intent,
            would_block=record.would_block,
            blocked_reason_code=_cap_text(record.blocked_reason_code, _MAX_REASON_CODE),
            blocked_reason_text=_cap_text(record.blocked_reason_text, _MAX_REASON_TEXT),
            preflight_json={
                "decision_status": record.decision_status,
                "allowed_to_submit": record.allowed_to_submit,
                "decision_reason": _cap_text(record.decision_reason, _MAX_REASON_TEXT),
                "blocked_reasons": _sanitize_items(record.blocked_reasons),
                "warnings": _sanitize_items(record.warnings),
                "execution_mode": record.execution_mode,
                "account_mode": record.account_mode,
                "source": record.source,
                "submit_gate": record.submit_gate,
                "broker_order_id": record.broker_order_id,
                "correlation_id": record.correlation_id,
                "risk_profile_id": record.risk_profile_id,
                "risk_block_reason": _cap_text(record.risk_block_reason, _MAX_REASON_TEXT),
            },
        )
        self._session.add(row)
        self._session.flush()
        self._session.refresh(row)
        return row
