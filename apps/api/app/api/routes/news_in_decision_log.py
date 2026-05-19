"""MH-NEWS-08-A2 — Read-only endpoint for ``news_in_decision_log`` audit table.

Returns the most recent rows from the audit table created in MH-NEWS-08-A.
The table is empty until the future MH-NEWS-08-B writer is wired (paired
with MH-NEWS-04 advisory-flag wiring); the response includes an advisory
note that surfaces this state to operators.

Drift-lock guarantee:
* Read-only — no INSERT/UPDATE/DELETE on any table.
* Never invokes the broker, the worker, the news ingestion pipeline, or
  any trading code.
* Auto-paper enforcement, auto trading, and live trading remain OFF.
* ``assert_auto_trading_allowed()`` is unchanged.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import desc, select

from app.db.models.news_in_decision_log import NewsInDecisionLog
from app.db.session import SessionLocal

router = APIRouter(prefix="/news-in-decision-log", tags=["news-in-decision-log"])

DEFAULT_LIMIT = 25
MAX_LIMIT = 200

_HEADLINE_HARD_CAP = 500
_URL_HARD_CAP = 1000


def _cap(value: Optional[str], max_len: int) -> Optional[str]:
    if value is None:
        return None
    if len(value) <= max_len:
        return value
    return value[:max_len] + "...[truncated]"


def _serialize(row: NewsInDecisionLog) -> Dict[str, Any]:
    return {
        "id": str(row.id),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "decision_kind": row.decision_kind,
        "decision_id": str(row.decision_id) if row.decision_id else None,
        "signal_id": str(row.signal_id) if row.signal_id else None,
        "llm_request_log_id": (
            str(row.llm_request_log_id) if row.llm_request_log_id else None
        ),
        "news_article_id": (
            str(row.news_article_id) if row.news_article_id else None
        ),
        "news_item_id": str(row.news_item_id) if row.news_item_id else None,
        "evidence_class": row.evidence_class,
        "headline_snapshot": _cap(row.headline_snapshot, _HEADLINE_HARD_CAP),
        "source_snapshot": row.source_snapshot,
        "url_snapshot": _cap(row.url_snapshot, _URL_HARD_CAP),
        "published_at_snapshot": (
            row.published_at_snapshot.isoformat()
            if row.published_at_snapshot
            else None
        ),
        "context_json": row.context_json,
    }


@router.get("/recent")
def list_recent_news_in_decision_log(
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    decision_kind: Optional[str] = Query(None, max_length=32),
    signal_id: Optional[UUID] = Query(None),
    news_article_id: Optional[UUID] = Query(None),
) -> Dict[str, Any]:
    """Return up to ``limit`` recent audit rows, newest first.

    Filters:
    * ``decision_kind``: exact-match (e.g. ``"signal_generation"``).
    * ``signal_id``: exact UUID match.
    * ``news_article_id``: exact UUID match.

    The endpoint never modifies state. The table may be empty (no writer
    is wired in the current cycle); the response will then be ``items: []``.
    """

    with SessionLocal() as session:
        stmt = select(NewsInDecisionLog)
        if decision_kind is not None:
            stmt = stmt.where(NewsInDecisionLog.decision_kind == decision_kind)
        if signal_id is not None:
            stmt = stmt.where(NewsInDecisionLog.signal_id == signal_id)
        if news_article_id is not None:
            stmt = stmt.where(
                NewsInDecisionLog.news_article_id == news_article_id
            )
        stmt = stmt.order_by(desc(NewsInDecisionLog.created_at)).limit(limit)
        rows = session.execute(stmt).scalars().all()

        items: List[Dict[str, Any]] = [_serialize(row) for row in rows]

    return {
        "count": len(items),
        "limit": limit,
        "filters": {
            "decision_kind": decision_kind,
            "signal_id": str(signal_id) if signal_id else None,
            "news_article_id": (
                str(news_article_id) if news_article_id else None
            ),
        },
        "advisory": (
            "Audit-only table; no production writer is wired yet. The "
            "MH-NEWS-08-B suffix (paired with MH-NEWS-04) will populate "
            "this surface."
        ),
        "items": items,
    }
