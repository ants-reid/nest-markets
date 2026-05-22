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

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query
from sqlalchemy import desc, select

from app.db.models.broker_submit_decision import BrokerSubmitDecision
from app.db.session import SessionLocal

router = APIRouter(prefix="/broker", tags=["broker-submit-decisions"])

DEFAULT_LIMIT = 25
MAX_LIMIT = 200

_REASON_TEXT_HARD_CAP = 500


def _cap_text(value: Optional[str], max_len: int) -> Optional[str]:
    if value is None:
        return None
    if len(value) <= max_len:
        return value
    return value[:max_len] + "...[truncated]"


def _serialize(row: BrokerSubmitDecision) -> Dict[str, Any]:
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
        "preflight_json": row.preflight_json,
    }


@router.get("/submit-decisions/recent")
def list_recent_broker_submit_decisions(
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    intent: Optional[str] = Query(None, max_length=32),
    would_block: Optional[bool] = Query(None),
) -> Dict[str, Any]:
    """Return up to ``limit`` recent broker-submit decisions, newest first.

    Filters:
    * ``intent``: exact-match on ``intent`` (e.g. ``"auto"``, ``"manual"``).
    * ``would_block``: exact-match on the boolean preflight outcome.

    The endpoint never modifies state. The table can be empty when no dry-run
    or submit attempts have been evaluated yet.
    """

    with SessionLocal() as session:
        stmt = select(BrokerSubmitDecision)
        if intent is not None:
            stmt = stmt.where(BrokerSubmitDecision.intent == intent)
        if would_block is not None:
            stmt = stmt.where(BrokerSubmitDecision.would_block == would_block)
        stmt = stmt.order_by(desc(BrokerSubmitDecision.created_at)).limit(limit)
        rows = session.execute(stmt).scalars().all()

        items: List[Dict[str, Any]] = [_serialize(row) for row in rows]

    return {
        "count": len(items),
        "limit": limit,
        "filters": {
            "intent": intent,
            "would_block": would_block,
        },
        "advisory": (
            "Audit feed for persisted broker preflight and submit decisions. "
            "Rows are append-only and emitted by safety enforcement paths."
        ),
        "items": items,
    }
