"""MH-NEWS-07-A — Read-only endpoint surfacing persisted news articles.

Returns the most recent rows from ``news_articles`` (the MH-NEWS-02 store)
for operator review on the news-archive surface. All rows in this table are
locked to ``evidence_class = 'research_only'`` by a DB CHECK constraint
(MH-NEWS-06); this endpoint surfaces that field verbatim so the UI can
always render an unambiguous research-only badge.

Drift-lock guarantee:
* Read-only — no INSERT/UPDATE/DELETE on any table.
* Never invokes a news provider, LLM provider, or any trading code.
* Never relaxes risk controls; consumers may only use the data advisorily.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query
from sqlalchemy import desc, select

from app.db.models.news_article import NewsArticle
from app.db.session import SessionLocal

router = APIRouter(prefix="/news-articles", tags=["news-articles"])

# Defensive caps on text fields. The DB columns are bounded
# (headline String(500), source_name String(255), url String(1000)) but
# summary/body_text are unbounded TEXT. Cap them at the wire boundary so a
# single huge article cannot dominate the response payload.
_HEADLINE_HARD_CAP = 500
_SUMMARY_HARD_CAP = 1500
_BODY_HARD_CAP = 4000
_SOURCE_HARD_CAP = 255
_URL_HARD_CAP = 1000

DEFAULT_LIMIT = 25
MAX_LIMIT = 200

# Cap citations list size to avoid pathological payloads.
_MAX_CITATIONS = 25
_MAX_TICKERS = 50
_MAX_SECTOR_TAGS = 50


def _cap_text(value: Optional[str], max_len: int) -> Optional[str]:
    if value is None:
        return None
    if len(value) <= max_len:
        return value
    return value[:max_len] + "...[truncated]"


def _cap_list(value: Any, max_items: int) -> Optional[list]:
    if value is None:
        return None
    if not isinstance(value, list):
        return None
    if len(value) <= max_items:
        return value
    return value[:max_items]


def _serialize(row: NewsArticle) -> Dict[str, Any]:
    return {
        "id": str(row.id),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "published_at": row.published_at.isoformat() if row.published_at else None,
        "headline": _cap_text(row.headline, _HEADLINE_HARD_CAP),
        "summary": _cap_text(row.summary, _SUMMARY_HARD_CAP),
        "body_text": _cap_text(row.body_text, _BODY_HARD_CAP),
        "source_name": _cap_text(row.source_name, _SOURCE_HARD_CAP),
        "url": _cap_text(row.url, _URL_HARD_CAP),
        "provider_article_id": row.provider_article_id,
        "sentiment_provider": row.sentiment_provider,
        "evidence_class": row.evidence_class,
        "tickers": _cap_list(row.tickers_json, _MAX_TICKERS),
        "sector_tags": _cap_list(row.sector_tags_json, _MAX_SECTOR_TAGS),
        "citations": _cap_list(row.citations_json, _MAX_CITATIONS),
        "authors": _cap_list(row.authors_json, _MAX_TICKERS),
    }


@router.get("/recent")
def list_recent_news_articles(
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    source: Optional[str] = Query(None, max_length=_SOURCE_HARD_CAP),
    ticker: Optional[str] = Query(None, max_length=32),
) -> Dict[str, Any]:
    """Return up to ``limit`` recent news articles, newest published first.

    Filters:
    * ``source``: exact-match on ``source_name``.
    * ``ticker``: case-insensitive containment in ``tickers_json``.

    All rows are research-only. The endpoint never modifies state.
    """

    ticker_normalised = ticker.strip().upper() if ticker else None

    with SessionLocal() as session:
        stmt = select(NewsArticle).order_by(desc(NewsArticle.published_at)).limit(limit)
        if source:
            stmt = select(NewsArticle).where(
                NewsArticle.source_name == source
            ).order_by(desc(NewsArticle.published_at)).limit(limit)
        rows = session.execute(stmt).scalars().all()

        items: List[Dict[str, Any]] = []
        for row in rows:
            if ticker_normalised is not None:
                tickers = row.tickers_json or []
                if not isinstance(tickers, list):
                    continue
                upper_tickers = [
                    t.upper() for t in tickers if isinstance(t, str)
                ]
                if ticker_normalised not in upper_tickers:
                    continue
            items.append(_serialize(row))

    return {
        "count": len(items),
        "limit": limit,
        "filters": {
            "source": source,
            "ticker": ticker_normalised,
        },
        "items": items,
    }
