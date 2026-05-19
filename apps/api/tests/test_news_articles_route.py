"""MH-NEWS-07-A — Tests for /news-articles/recent."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.db.models.news_article import NewsArticle
from app.db.session import SessionLocal
from app.main import create_app


_TEST_SOURCE_A = "test-news07-source-a"
_TEST_SOURCE_B = "test-news07-source-b"
_TEST_SOURCES = [_TEST_SOURCE_A, _TEST_SOURCE_B]


@pytest.fixture
def client():
    return TestClient(create_app())


def _insert(session, *, published_at: datetime, **kwargs) -> NewsArticle:
    defaults = dict(
        headline="Headline",
        summary="Summary",
        body_text=None,
        source_name=_TEST_SOURCE_A,
        url="https://example.test/article",
        tickers_json=None,
        sector_tags_json=None,
        citations_json=None,
        evidence_class="research_only",
    )
    defaults.update(kwargs)
    row = NewsArticle(published_at=published_at, **defaults)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@pytest.fixture(autouse=True)
def _clean_table():
    s = SessionLocal()
    try:
        s.query(NewsArticle).filter(
            NewsArticle.source_name.in_(_TEST_SOURCES)
        ).delete(synchronize_session=False)
        s.commit()
    finally:
        s.close()
    yield
    s = SessionLocal()
    try:
        s.query(NewsArticle).filter(
            NewsArticle.source_name.in_(_TEST_SOURCES)
        ).delete(synchronize_session=False)
        s.commit()
    finally:
        s.close()


def test_endpoint_returns_recent_rows_newest_first(client):
    base = datetime.now(timezone.utc)
    s = SessionLocal()
    try:
        for i in range(3):
            _insert(
                s,
                published_at=base - timedelta(hours=i),
                headline=f"Article {i}",
            )
    finally:
        s.close()

    resp = client.get(
        "/news-articles/recent",
        params={"source": _TEST_SOURCE_A, "limit": 10},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 3
    headlines = [item["headline"] for item in body["items"]]
    assert headlines == ["Article 0", "Article 1", "Article 2"]


def test_filter_by_source(client):
    base = datetime.now(timezone.utc)
    s = SessionLocal()
    try:
        _insert(s, published_at=base, source_name=_TEST_SOURCE_A, headline="A")
        _insert(s, published_at=base, source_name=_TEST_SOURCE_B, headline="B")
    finally:
        s.close()

    resp = client.get(
        "/news-articles/recent",
        params={"source": _TEST_SOURCE_B, "limit": 50},
    )
    assert resp.status_code == 200
    body = resp.json()
    sources = {item["source_name"] for item in body["items"]}
    assert sources == {_TEST_SOURCE_B}
    assert body["filters"]["source"] == _TEST_SOURCE_B


def test_filter_by_ticker_case_insensitive(client):
    base = datetime.now(timezone.utc)
    s = SessionLocal()
    try:
        _insert(
            s,
            published_at=base,
            headline="EUR",
            tickers_json=["EURUSD", "GBPUSD"],
        )
        _insert(
            s,
            published_at=base,
            headline="JPY",
            tickers_json=["USDJPY"],
        )
    finally:
        s.close()

    resp = client.get(
        "/news-articles/recent",
        params={"source": _TEST_SOURCE_A, "ticker": "eurusd", "limit": 50},
    )
    assert resp.status_code == 200
    body = resp.json()
    headlines = {item["headline"] for item in body["items"]}
    assert headlines == {"EUR"}
    assert body["filters"]["ticker"] == "EURUSD"


def test_evidence_class_is_surfaced(client):
    base = datetime.now(timezone.utc)
    s = SessionLocal()
    try:
        _insert(s, published_at=base, headline="evidence-check")
    finally:
        s.close()

    resp = client.get(
        "/news-articles/recent",
        params={"source": _TEST_SOURCE_A, "limit": 5},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] >= 1
    for item in body["items"]:
        assert item["evidence_class"] == "research_only"


def test_citations_passed_through(client):
    base = datetime.now(timezone.utc)
    citations = [
        {"title": "src1", "url": "https://example.test/1"},
        {"title": "src2", "url": "https://example.test/2"},
    ]
    s = SessionLocal()
    try:
        _insert(
            s,
            published_at=base,
            headline="cite",
            citations_json=citations,
        )
    finally:
        s.close()

    resp = client.get(
        "/news-articles/recent",
        params={"source": _TEST_SOURCE_A, "limit": 5},
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert any(item["citations"] == citations for item in items)


def test_limit_enforced(client):
    base = datetime.now(timezone.utc)
    s = SessionLocal()
    try:
        for i in range(5):
            _insert(
                s,
                published_at=base - timedelta(minutes=i),
                headline=f"row-{i}",
            )
    finally:
        s.close()

    resp = client.get(
        "/news-articles/recent",
        params={"source": _TEST_SOURCE_A, "limit": 2},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 2
    assert body["limit"] == 2


def test_invalid_limit_rejected(client):
    resp_low = client.get("/news-articles/recent", params={"limit": 0})
    assert resp_low.status_code == 422

    resp_high = client.get("/news-articles/recent", params={"limit": 99999})
    assert resp_high.status_code == 422


def test_long_summary_is_capped(client):
    base = datetime.now(timezone.utc)
    long_summary = "x" * 5000
    s = SessionLocal()
    try:
        _insert(
            s,
            published_at=base,
            headline="long",
            summary=long_summary,
        )
    finally:
        s.close()

    resp = client.get(
        "/news-articles/recent",
        params={"source": _TEST_SOURCE_A, "limit": 5},
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    target = next(item for item in items if item["headline"] == "long")
    assert target["summary"] is not None
    assert len(target["summary"]) <= 1600
    assert target["summary"].endswith("[truncated]")
