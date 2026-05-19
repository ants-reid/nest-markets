"""MH-NEWS-06 — DB-layer enforcement of ``evidence_class='research_only'``.

Verifies that:
* The default value is applied when a row is inserted without it.
* The CHECK constraint rejects any other value.

The constraint is the drift-lock at the storage layer: news must never
silently escalate to a trading-decision evidence class without an explicit
unlock migration.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.db.models.news_article import NewsArticle
from app.db.session import SessionLocal


@pytest.fixture(autouse=True)
def _clean_table():
    s = SessionLocal()
    try:
        s.query(NewsArticle).filter(
            NewsArticle.provider_article_id.in_(
                ["mh-news-06-default", "mh-news-06-explicit", "mh-news-06-bad"]
            )
        ).delete(synchronize_session=False)
        s.commit()
    finally:
        s.close()
    yield
    s = SessionLocal()
    try:
        s.query(NewsArticle).filter(
            NewsArticle.provider_article_id.in_(
                ["mh-news-06-default", "mh-news-06-explicit", "mh-news-06-bad"]
            )
        ).delete(synchronize_session=False)
        s.commit()
    finally:
        s.close()


def _make_article(provider_id: str, *, evidence_class: str | None = None) -> NewsArticle:
    kwargs = dict(
        provider_article_id=provider_id,
        published_at=datetime.now(timezone.utc),
        headline="MH-NEWS-06 test article",
    )
    if evidence_class is not None:
        kwargs["evidence_class"] = evidence_class
    return NewsArticle(**kwargs)


def test_default_evidence_class_is_research_only():
    s = SessionLocal()
    try:
        article = _make_article("mh-news-06-default")
        s.add(article)
        s.commit()
        s.refresh(article)
        assert article.evidence_class == "research_only"
    finally:
        s.close()


def test_explicit_research_only_accepted():
    s = SessionLocal()
    try:
        article = _make_article("mh-news-06-explicit", evidence_class="research_only")
        s.add(article)
        s.commit()
        s.refresh(article)
        assert article.evidence_class == "research_only"
    finally:
        s.close()


def test_check_constraint_rejects_other_values():
    s = SessionLocal()
    try:
        article = _make_article("mh-news-06-bad", evidence_class="trading_signal")
        s.add(article)
        with pytest.raises(IntegrityError):
            s.commit()
        s.rollback()
    finally:
        s.close()
