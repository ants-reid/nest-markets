"""MH-RISK-AUDIT-A — Read-only endpoint for ``risk_decisions`` audit table.

Exposes the most recent rows of the deterministic-risk-engine decision
table for operator audit visibility. Unlike sibling audit endpoints
shipped earlier this bucket (broker-submit-decisions, news-in-decision-log)
the underlying table is **already populated** by ``risk_service.py`` and
``persistence_signal_service.py`` via existing pipelines, so the
response generally returns real rows.

Drift-lock guarantee:
* Read-only — no INSERT/UPDATE/DELETE on any table.
* Never invokes the broker, the worker, the risk evaluator, or any
  trading code.
* Auto-paper enforcement, auto trading, and live trading remain OFF.
* ``assert_auto_trading_allowed()`` is unchanged.
* The endpoint never echoes secrets, prompts, or PII; it serializes only
  the deterministic risk-engine columns already present in the table.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import desc, select

from app.db.models.risk_decision import RiskDecision
from app.db.session import SessionLocal
from app.schemas.audit_feeds import RiskDecisionAuditResponseSchema

router = APIRouter(prefix="/risk-decisions", tags=["risk-decisions"])

DEFAULT_LIMIT = 25
MAX_LIMIT = 200


def _serialize(row: RiskDecision) -> Dict[str, Any]:
    return {
        "id": str(row.id),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "timestamp": row.timestamp.isoformat() if row.timestamp else None,
        "signal_id": str(row.signal_id) if row.signal_id else None,
        "approved": row.approved,
        "blocking_rule": row.blocking_rule,
        "block_reason_code": row.block_reason_code,
        "risk_profile_id": (
            str(row.risk_profile_id) if row.risk_profile_id else None
        ),
        "position_risk_pct": (
            float(row.position_risk_pct) if row.position_risk_pct is not None else None
        ),
        "notional_allowed": (
            float(row.notional_allowed) if row.notional_allowed is not None else None
        ),
        "correlation_bucket": row.correlation_bucket,
        "spread_ok": row.spread_ok,
        "session_ok": row.session_ok,
        "drawdown_ok": row.drawdown_ok,
        "cooldown_ok": row.cooldown_ok,
        "kill_switch_active": row.kill_switch_active,
        "blocked_reasons_json": row.blocked_reasons_json,
    }


@router.get("/recent", response_model=RiskDecisionAuditResponseSchema)
def list_recent_risk_decisions(
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    approved: Optional[str] = Query(None, max_length=20),
    signal_id: Optional[UUID] = Query(None),
    block_reason_code: Optional[str] = Query(None, max_length=64),
) -> Dict[str, Any]:
    """Return up to ``limit`` recent risk decisions, newest first.

    Filters:
    * ``approved``: exact-match on the approved-status string
      (e.g. ``"approved"``, ``"blocked"``, ``"pending"``).
    * ``signal_id``: exact UUID match.
    * ``block_reason_code``: exact-match on the structured-enum block code
      populated by the future MH-154-B writer.

    The endpoint never modifies state.
    """

    with SessionLocal() as session:
        stmt = select(RiskDecision)
        if approved is not None:
            stmt = stmt.where(RiskDecision.approved == approved)
        if signal_id is not None:
            stmt = stmt.where(RiskDecision.signal_id == signal_id)
        if block_reason_code is not None:
            stmt = stmt.where(RiskDecision.block_reason_code == block_reason_code)
        stmt = stmt.order_by(desc(RiskDecision.created_at)).limit(limit)
        rows = session.execute(stmt).scalars().all()

        items: List[Dict[str, Any]] = [_serialize(row) for row in rows]

    return {
        "count": len(items),
        "limit": limit,
        "filters": {
            "approved": approved,
            "signal_id": str(signal_id) if signal_id else None,
            "block_reason_code": block_reason_code,
        },
        "advisory": (
            "Read-only audit view of the deterministic risk-engine "
            "decision table. Source: risk_service.RiskEvaluator and "
            "persistence_signal_service. Drift-lock: this endpoint does "
            "not influence trading; auto-paper, auto, and live trading "
            "remain OFF."
        ),
        "items": items,
    }
