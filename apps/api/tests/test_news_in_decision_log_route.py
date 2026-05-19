"""MH-NEWS-08-A2 — Tests for ``GET /news-in-decision-log/recent`` endpoint.

The MH-NEWS-08-A audit table has no production writer yet; these tests
seed rows directly via the ORM to exercise the read-only endpoint shape,
filters, ordering, and validation.

Drift-lock guarantee: tests do not invoke the worker, the broker, the
news ingestion pipeline, or any trading code.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.db.models.news_in_decision_log import NewsInDecisionLog
from app.db.session import SessionLocal
from app.main import create_app


@pytest.fixture(scope="module")
def client():
    return TestClient(create_app())


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


def _seed(rows: list[NewsInDecisionLog]) -> None:
    with SessionLocal() as session:
        for row in rows:
            session.add(row)
        session.commit()
        for row in rows:
            session.refresh(row)


def test_endpoint_returns_advisory_and_envelope(client):
    resp = client.get("/news-in-decision-log/recent")
    assert resp.status_code == 200
    body = resp.json()
    assert "advisory" in body and "no production writer" in body["advisory"]
    assert "items" in body
    assert "count" in body and body["count"] == len(body["items"])
    assert body["limit"] == 25


def test_invalid_limit_returns_422(client):
    resp = client.get("/news-in-decision-log/recent?limit=0")
    assert resp.status_code == 422
    resp2 = client.get("/news-in-decision-log/recent?limit=999")
    assert resp2.status_code == 422


def test_newest_first_ordering_and_filter(client, created_ids):
    sig = uuid.uuid4()
    other_sig = uuid.uuid4()
    base = datetime.now(timezone.utc)
    rows = [
        NewsInDecisionLog(
            decision_kind="signal_generation",
            signal_id=sig,
            headline_snapshot=f"hl-{i}",
            created_at=base - timedelta(minutes=10 - i),
        )
        for i in range(3)
    ]
    rows.append(
        NewsInDecisionLog(
            decision_kind="signal_generation",
            signal_id=other_sig,
            headline_snapshot="other",
            created_at=base + timedelta(minutes=1),
        )
    )
    _seed(rows)
    created_ids.extend([r.id for r in rows])

    # Filter to our signal_id only.
    resp = client.get(
        f"/news-in-decision-log/recent?signal_id={sig}&limit=10"
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 3
    headlines = [it["headline_snapshot"] for it in items]
    # Newest-first: hl-2 (base-min-8) > hl-1 (base-min-9) > hl-0 (base-min-10).
    assert headlines == ["hl-2", "hl-1", "hl-0"]
    # All carry default evidence_class.
    assert {it["evidence_class"] for it in items} == {"research_only"}


def test_decision_kind_filter_excludes_others(client, created_ids):
    art = uuid.uuid4()
    base = datetime.now(timezone.utc)
    a = NewsInDecisionLog(
        decision_kind="signal_generation",
        news_article_id=art,
        headline_snapshot="kind-a",
        created_at=base,
    )
    b = NewsInDecisionLog(
        decision_kind="risk_review",
        news_article_id=art,
        headline_snapshot="kind-b",
        created_at=base + timedelta(seconds=1),
    )
    _seed([a, b])
    created_ids.extend([a.id, b.id])

    resp = client.get(
        f"/news-in-decision-log/recent?news_article_id={art}"
        "&decision_kind=risk_review"
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["headline_snapshot"] == "kind-b"


def test_long_url_is_capped(client, created_ids):
    long_url = "https://example.com/" + ("x" * 2000)
    row = NewsInDecisionLog(
        decision_kind="signal_generation",
        url_snapshot=long_url[:1000],  # column max is 1000
        headline_snapshot="cap-test",
    )
    _seed([row])
    created_ids.append(row.id)
    resp2 = client.get("/news-in-decision-log/recent?limit=200")
    assert resp2.status_code == 200
    found = next(
        (
            it
            for it in resp2.json()["items"]
            if it["headline_snapshot"] == "cap-test"
        ),
        None,
    )
    assert found is not None
    # The seeded url is exactly 1000 chars (column max), so cap should not
    # add the truncation marker.
    assert found["url_snapshot"] is not None
    assert "[truncated]" not in found["url_snapshot"]
    # Touch time so module-level fixture cleanup has 