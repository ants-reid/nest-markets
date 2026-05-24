"""MH-148-B — Read endpoint surfacing persisted broker-submit decisions.

Returns the most recent rows from ``broker_submit_decisions`` (MH-148-A table,
written by the MH-148-C suffix).

Drift-lock guarantee:
* Read-only — no INSERT/UPDATE/DELETE on any table.
* Never invokes the broker, the worker, or any trading code.
* Never relaxes risk controls; the data is audit-only.
* Auto-paper enforcement, auto trading, and live trading remain OFF.
"""

from __future__ import annotations

from uuid import UUID

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query
from sqlalchemy import desc, select

from app.db.models.broker_submit_decision import BrokerSubmitDecision
from app.db.session import SessionLocal
from app.schemas.broker_schemas import BrokerSubmitDecisionsResponseSchema

router = APIRouter(prefix="/broker", tags=["broker-submit-decisions"])

DEFAULT_LIMIT = 25
MAX_LIMIT = 200

_REASON_TEXT_HARD_CAP = 500
_CORRELATION_ID_HARD_CAP = 160
_REFERENCE_HARD_CAP = 240


def _safe_preflight_dict(row: BrokerSubmitDecision) -> Dict[str, Any]:
    payload = row.preflight_json
    if isinstance(payload, dict):
        return payload
    return {}


def _optional_str(value: Any, *, max_len: int | None = None) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    if max_len is None or len(value) <= max_len:
        return value
    return value[:max_len] + "...[truncated]"


def _optional_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    return None


def _optional_number(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def _optional_uuid(value: Any) -> Optional[str]:
    if value is None:
        return None
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError):
        return None


def _sanitize_items(items: Any) -> List[Dict[str, Optional[str]]]:
    out: List[Dict[str, Optional[str]]] = []
    if not isinstance(items, list):
        return out
    for item in items:
        if not isinstance(item, dict):
            continue
        out.append(
            {
                "code": _optional_str(item.get("code"), max_len=64),
                "message": _optional_str(item.get("message"), max_len=240),
                "source": _optional_str(item.get("source"), max_len=64),
                "classification": _optional_str(
                    item.get("classification"), max_len=32
                ),
                "severity": _optional_str(item.get("severity"), max_len=32),
            }
        )
    return out


def _request_summary(payload: Dict[str, Any]) -> Dict[str, Any] | None:
    request_summary = payload.get("request_summary")
    if not isinstance(request_summary, dict):
        return None
    summary = {
        "ticker": _optional_str(request_summary.get("ticker"), max_len=32),
        "side": _optional_str(request_summary.get("side"), max_len=16),
        "quantity": _optional_number(request_summary.get("quantity")),
        "order_type": _optional_str(request_summary.get("order_type"), max_len=32),
        "limit_price": _optional_number(request_summary.get("limit_price")),
        "stop_price": _optional_number(request_summary.get("stop_price")),
    }
    if any(value is not None for value in summary.values()):
        return summary
    return None


def _cap_text(value: Optional[str], max_len: int) -> Optional[str]:
    if value is None:
        return None
    if len(value) <= max_len:
        return value
    return value[:max_len] + "...[truncated]"


def _serialize(row: BrokerSubmitDecision) -> Dict[str, Any]:
    payload = _safe_preflight_dict(row)
    return {
        "id": str(row.id),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "signal_id": str(row.signal_id) if row.signal_id else None,
        "intent": row.intent,
        "would_block": row.would_block,
        "blocked_reason_code": row.blocked_reason_code,
        "blocked_reason_text": _cap_text(
            row.blocked_reason_text, _REASON_TEXT_HARD_CAP
        ),
        "decision_status": _optional_str(payload.get("decision_status"), max_len=32),
        "allowed_to_submit": _optional_bool(payload.get("allowed_to_submit")),
        "decision_reason": _optional_str(
            payload.get("decision_reason"), max_len=_REASON_TEXT_HARD_CAP
        ),
        "source": _optional_str(payload.get("source"), max_len=64),
        "submit_gate": _optional_str(payload.get("submit_gate"), max_len=32),
        "broker_order_id": _optional_str(payload.get("broker_order_id"), max_len=128),
        "correlation_id": _optional_str(
            payload.get("correlation_id"), max_len=_CORRELATION_ID_HARD_CAP
        ),
        "recommendation_id": _optional_uuid(payload.get("recommendation_id")),
        "route_check_reference": _optional_str(
            payload.get("route_check_reference"), max_len=_REFERENCE_HARD_CAP
        ),
        "dry_run_reference": _optional_str(
            payload.get("dry_run_reference"), max_len=_REFERENCE_HARD_CAP
        ),
        "execution_mode": _optional_str(payload.get("execution_mode"), max_len=64),
        "account_mode": _optional_str(payload.get("account_mode"), max_len=64),
        "risk_profile_id": _optional_str(payload.get("risk_profile_id"), max_len=128),
        "risk_block_reason": _optional_str(
            payload.get("risk_block_reason"), max_len=_REASON_TEXT_HARD_CAP
        ),
        "execution_source": _optional_str(payload.get("execution_source"), max_len=64),
        "serious_paper_source": _optional_str(
            payload.get("serious_paper_source"), max_len=64
        ),
        "canonical_paper_route": _optional_str(
            payload.get("canonical_paper_route"), max_len=64
        ),
        "broker_account_mode": _optional_str(
            payload.get("broker_account_mode"), max_len=32
        ),
        "live_state": _optional_str(payload.get("live_state"), max_len=64),
        "request_summary": _request_summary(payload),
        "warnings": _sanitize_items(payload.get("warnings")),
        "blocked_reasons": _sanitize_items(payload.get("blocked_reasons")),
        "preflight_json": payload or None,
    }


def _matches_filters(
    item: Dict[str, Any],
    *,
    source: Optional[str],
    decision_status: Optional[str],
    correlation_id: Optional[str],
    recommendation_id: Optional[UUID],
) -> bool:
    if source is not None and item.get("source") != source:
        return False
    if decision_status is not None and item.get("decision_status") != decision_status:
        return False
    if correlation_id is not None and item.get("correlation_id") != correlation_id:
        return False
    if recommendation_id is not None and item.get("recommendation_id") != str(recommendation_id):
        return False
    return True


@router.get("/submit-decisions/recent", response_model=BrokerSubmitDecisionsResponseSchema)
def list_recent_broker_submit_decisions(
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    intent: Optional[str] = Query(None, max_length=32),
    would_block: Optional[bool] = Query(None),
    source: Optional[str] = Query(None, max_length=64),
    decision_status: Optional[str] = Query(None, max_length=32),
    correlation_id: Optional[str] = Query(None, max_length=_CORRELATION_ID_HARD_CAP),
    recommendation_id: Optional[UUID] = Query(None),
) -> Dict[str, Any]:
    """Return up to ``limit`` recent broker-submit decisions, newest first.

    Filters:
    * ``intent``: exact-match on ``intent`` (e.g. ``"auto"``, ``"manual"``).
    * ``would_block``: exact-match on the boolean preflight outcome.
        * ``source``: exact-match on the persisted decision source (e.g. ``"dry_run"``,
            ``"submit_preflight"``, ``"submit_attempt"``).
        * ``decision_status``: exact-match on the normalized decision status.
        * ``correlation_id``: exact-match on the persisted decision correlation id.
        * ``recommendation_id``: exact-match on the persisted recommendation UUID.

    The endpoint never modifies state. The table can be empty when no dry-run
    or submit attempts have been evaluated yet.
    """

    with SessionLocal() as session:
        stmt = select(BrokerSubmitDecision)
        if intent is not None:
            stmt = stmt.where(BrokerSubmitDecision.intent == intent)
        if would_block is not None:
            stmt = stmt.where(BrokerSubmitDecision.would_block == would_block)
        stmt = stmt.order_by(desc(BrokerSubmitDecision.created_at))
        rows = session.execute(stmt).scalars().all()

        items = [
            item
            for item in (_serialize(row) for row in rows)
            if _matches_filters(
                item,
                source=source,
                decision_status=decision_status,
                correlation_id=correlation_id,
                recommendation_id=recommendation_id,
            )
        ][:limit]

    return {
        "count": len(items),
        "limit": limit,
        "filters": {
            "intent": intent,
            "would_block": would_block,
            "source": source,
            "decision_status": decision_status,
            "correlation_id": correlation_id,
            "recommendation_id": str(recommendation_id) if recommendation_id else None,
        },
        "advisory": (
            "Audit feed for persisted broker preflight and submit decisions. "
            "Rows are append-only and emitted by safety enforcement paths."
        ),
        "items": items,
    }
