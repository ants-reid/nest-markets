"""MH-COCKPIT-04-API — Read-only endpoint surfacing redacted LLM round-trips.

Returns the most recent rows from ``llm_request_logs`` for operator review
("plain-English explainer" support surface). All previews are already
length-capped and control-stripped at write time by
``llm_request_log_sink.redact_preview``; this endpoint adds a defensive
re-cap and never echoes raw secrets.

Drift-lock guarantee:
* Read-only — no INSERT/UPDATE/DELETE on any table.
* Never invokes any LLM provider.
* Never touches trading state, ``trading_control_service``, or the broker.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query
from sqlalchemy import desc, select

from app.db.models.llm_request_log import LLMRequestLog
from app.db.session import SessionLocal
from app.schemas.audit_feeds import LlmLogAuditResponseSchema

router = APIRouter(prefix="/llm-logs", tags=["llm-logs"])

# Defensive re-cap. Sink already enforces 500-char previews, but if a row
# was inserted by a different code path we still bound the wire payload.
_PREVIEW_HARD_CAP = 1000
_RESPONSE_PAYLOAD_HARD_CAP = 4000

DEFAULT_LIMIT = 25
MAX_LIMIT = 200


def _cap_text(value: Optional[str], max_len: int) -> Optional[str]:
    if value is None:
        return None
    if len(value) <= max_len:
        return value
    return value[:max_len] + "...[truncated]"


def _serialize(row: LLMRequestLog) -> Dict[str, Any]:
    response_payload: Optional[Any] = row.response_payload_json
    # Defensive: never serialise an unbounded JSON blob to the wire.
    serialized_payload: Optional[str] = None
    if response_payload is not None:
        as_str = str(response_payload)
        serialized_payload = _cap_text(as_str, _RESPONSE_PAYLOAD_HARD_CAP)
    return {
        "id": str(row.id),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "provider": row.provider,
        "model_requested": row.model_requested,
        "model_returned": row.model_returned,
        "system_prompt_hash": row.system_prompt_hash,
        "user_prompt_hash": row.user_prompt_hash,
        "system_prompt_preview": _cap_text(row.system_prompt_preview, _PREVIEW_HARD_CAP),
        "user_prompt_preview": _cap_text(row.user_prompt_preview, _PREVIEW_HARD_CAP),
        "prompt_version_id": str(row.prompt_version_id) if row.prompt_version_id else None,
        "stop_reason": row.stop_reason,
        "prompt_tokens": row.prompt_tokens,
        "completion_tokens": row.completion_tokens,
        "total_tokens": row.total_tokens,
        "latency_ms": row.latency_ms,
        "error_class": row.error_class,
        "error_message": _cap_text(row.error_message, _PREVIEW_HARD_CAP),
        "correlation_id": row.correlation_id,
        "response_payload_preview": serialized_payload,
    }


@router.get("/recent", response_model=LlmLogAuditResponseSchema)
def list_recent_llm_logs(
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    provider: Optional[str] = Query(None, max_length=50),
    correlation_id: Optional[str] = Query(None, max_length=100),
    only_errors: bool = Query(False),
) -> Dict[str, Any]:
    """Return the most recent LLM round-trip rows, newest first.

    All response fields are already redacted at write time. This endpoint
    only reads; it never invokes any LLM provider and never mutates state.
    """
    session = SessionLocal()
    try:
        stmt = select(LLMRequestLog).order_by(
            desc(LLMRequestLog.created_at)
        ).limit(limit)
        if provider:
            stmt = stmt.where(LLMRequestLog.provider == provider)
        if correlation_id:
            stmt = stmt.where(LLMRequestLog.correlation_id == correlation_id)
        if only_errors:
            stmt = stmt.where(LLMRequestLog.error_class.is_not(None))
        rows: List[LLMRequestLog] = list(session.execute(stmt).scalars().all())
    finally:
        session.close()

    return {
        "count": len(rows),
        "limit": limit,
        "filters": {
            "provider": provider,
            "correlation_id": correlation_id,
            "only_errors": only_errors,
        },
        "items": [_serialize(r) for r in rows],
    }
