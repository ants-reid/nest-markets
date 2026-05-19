"""MH-NEWS-08-A — ``news_in_decision_log`` table + ORM model smoke tests.

Verifies the table exists after migration, the ORM round-trips correctly
with all expected columns, and the DB CHECK constraint pinning
``evidence_class = 'research_only'`` actually rejects any other value.

There is no production writer in this phase (MH-NEWS-08-B is deferred);
these tests act as a structural smoke-check only.

Drift-lock guarantee: tests do not invoke the worker, the broker, the
news ingestion pipeline, or any trading code; auto-paper enforcement,
auto trading, and live trading all remain OFF.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from app.db.models.news_in_decision_log import NewsInDecisionLog
from app.db.session import SessionLocal


@pytest.fixture
def created_ids():
    ids: list[uuid.UUID] = []
    yield ids
    if not ids:
        return
    with SessionLocal() as session:
        session.query(NewsInDecisionLog).filter(
            NewsInDecisionLog.id.in_(ids)
        ).delete(synchronize_session=False)
        session.commit()


def test_model_columns_present():
    cols = {c.name for c in inspect(NewsInDecisionLog).columns}
    expected = {
        "id",
        "created_at",
        "decision_kind",
        "decision_id",
        "signal_id",
        "llm_request_log_id",
        "news_article_id",
        "news_item_id",
        "evidence_class",
        "headline_snapshot",
        "source_snapshot",
        "url_snapshot",
        "published_at_snapshot",
        "context_json",
    }
    missing = expected - cols
    assert not missing, f"missing columns: {missing}"


def test_round_trip_default_evidence_class(created_ids):
    row = NewsInDecisionLog(
        decision_kind="signal_generation",
        signal_id=uuid.uuid4(),
        news_article_id=uuid.uuid4(),
        headline_snapshot="Example headline",
        source_snapshot="reuters",
        url_snapshot="https://example.com/a",
        published_at_snapshot=datetime.now(timezone.utc),
        context_json={"window_seconds": 600, "rationale": "smoke"},
    )
    with SessionLocal() as session:
        session.add(row)
        session.commit()
        session.refresh(row)
        created_ids.append(row.id)
        assert row.evidence_class == "research_only"
        assert row.headline_snapshot == "Example headline"
        assert row.context_json["window_seconds"] == 600


def test_check_constraint_rejects_non_research_only(created_ids):
    bad = NewsInDecisionLog(
        decision_kind="signal_generation",
        evidence_class="trading_evidence",
    )
    with SessionLocal() as session:
        session.add(bad)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
