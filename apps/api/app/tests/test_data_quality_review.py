"""MH-12/13 tests for Data Quality Review / Outlier Inspection endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models.market_data_quality_report import MarketDataQualityReport
from app.db.session import SessionLocal, engine, get_db_session
from app.main import app


@pytest.fixture()
def db_session() -> Session:  # type: ignore[misc]
    schema_name = f"test_dq_review_{uuid4().hex}"

    admin_conn = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
    admin_conn.execute(text(f'CREATE SCHEMA "{schema_name}"'))
    admin_conn.close()

    conn = engine.connect()
    conn.execute(text(f'SET search_path TO "{schema_name}"'))
    conn.commit()
    Base.metadata.create_all(bind=conn)

    session = SessionLocal(bind=conn)
    try:
        yield session
    finally:
        session.close()
        conn.close()
        cleanup = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
        cleanup.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))
        cleanup.close()


@pytest.fixture()
def client(db_session: Session) -> TestClient:  # type: ignore[misc]
    app.dependency_overrides[get_db_session] = lambda: db_session
    return TestClient(app)


def _make_report(
    session: Session,
    asset_symbol: str = "AAPL",
    timeframe: str = "1d",
    quality_score: float = 95.0,
    suspicious_spike_bars: int = 0,
    review_status: str = "unreviewed",
) -> MarketDataQualityReport:
    """Insert a minimal quality report row and return it."""
    row = MarketDataQualityReport(
        asset_symbol=asset_symbol,
        timeframe=timeframe,
        provider="yfinance",
        evaluated_at=datetime.now(timezone.utc),
        actual_bars=100,
        total_bars=100,
        missing_bars=0,
        duplicate_bars=0,
        bad_price_bars=0,
        suspicious_spike_bars=suspicious_spike_bars,
        stale_bars=0,
        quality_score=quality_score,
        approved_for_backtest=quality_score >= 90.0,
        review_status=review_status,
        review_notes=None,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


# ---------------------------------------------------------------------------


def test_outliers_empty_returns_empty_list(client: TestClient) -> None:
    """GET /research/data/quality/outliers with no data returns empty list."""
    resp = client.get("/research/data/quality/outliers")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


def test_outliers_spike_report_is_returned(client: TestClient, db_session: Session) -> None:
    """A report with suspicious_spike_bars > 0 should appear in the outliers list."""
    _make_report(db_session, asset_symbol="BTC-USD", suspicious_spike_bars=3)
    # Clean record should NOT appear
    _make_report(db_session, asset_symbol="AAPL", quality_score=98.0, suspicious_spike_bars=0)

    resp = client.get("/research/data/quality/outliers")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    symbols = [item["asset_symbol"] for item in data["items"]]
    assert "BTC-USD" in symbols
    assert "AAPL" not in symbols


def test_outliers_low_score_report_is_returned(client: TestClient, db_session: Session) -> None:
    """A report with quality_score < 90 should appear in the outliers list."""
    _make_report(db_session, asset_symbol="USDJPY", timeframe="1d", quality_score=89.84)

    resp = client.get("/research/data/quality/outliers")
    assert resp.status_code == 200
    data = resp.json()
    symbols = [item["asset_symbol"] for item in data["items"]]
    assert "USDJPY" in symbols


def test_outliers_filter_by_review_status(client: TestClient, db_session: Session) -> None:
    """Filter by review_status returns only matching rows."""
    _make_report(db_session, asset_symbol="USDJPY", quality_score=89.84, review_status="unreviewed")
    _make_report(db_session, asset_symbol="^VIX", suspicious_spike_bars=5, review_status="bad_data")

    resp = client.get("/research/data/quality/outliers?review_status=bad_data")
    assert resp.status_code == 200
    data = resp.json()
    assert all(item["review_status"] == "bad_data" for item in data["items"])
    symbols = [item["asset_symbol"] for item in data["items"]]
    assert "^VIX" in symbols
    assert "USDJPY" not in symbols


def test_review_outlier_sets_status_and_notes(client: TestClient, db_session: Session) -> None:
    """POST /research/data/quality/outliers/{id}/review saves review_status and notes."""
    row = _make_report(db_session, asset_symbol="USDJPY", quality_score=89.84)

    payload = {
        "review_status": "valid_market_move",
        "review_notes": "Confirmed: USD strength event on 2024-01-15",
    }
    resp = client.post(f"/research/data/quality/outliers/{row.id}/review", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["review_status"] == "valid_market_move"
    assert data["review_notes"] == "Confirmed: USD strength event on 2024-01-15"
    assert data["asset_symbol"] == "USDJPY"

    # Verify it persisted — re-fetch via list endpoint
    list_resp = client.get("/research/data/quality/outliers?review_status=valid_market_move")
    assert list_resp.status_code == 200
    saved_symbols = [item["asset_symbol"] for item in list_resp.json()["items"]]
    assert "USDJPY" in saved_symbols


def test_review_outlier_not_found_returns_404(client: TestClient) -> None:
    """POST review with a non-existent UUID returns 404."""
    fake_id = str(uuid4())
    payload = {"review_status": "bad_data"}
    resp = client.post(f"/research/data/quality/outliers/{fake_id}/review", json=payload)
    assert resp.status_code == 404


def test_review_all_statuses_accepted(client: TestClient, db_session: Session) -> None:
    """All four review statuses are accepted by the endpoint."""
    statuses = ["valid_market_move", "bad_data", "needs_provider_check", "ignore_for_now"]
    for status in statuses:
        row = _make_report(
            db_session,
            asset_symbol=f"TEST_{status[:3].upper()}",
            suspicious_spike_bars=1,
        )
        resp = client.post(
            f"/research/data/quality/outliers/{row.id}/review",
            json={"review_status": status},
        )
        assert resp.status_code == 200, f"Status {status} rejected"
        assert resp.json()["review_status"] == status


# ---------------------------------------------------------------------------
# MH-13 — reviewed_by/at persistence, audit trail, summary, new filters
# ---------------------------------------------------------------------------


def test_review_sets_reviewed_by_and_at(client: TestClient, db_session: Session) -> None:
    """POST review with reviewed_by persists it and returns reviewed_at."""
    row = _make_report(db_session, asset_symbol="GBPUSD", suspicious_spike_bars=2)

    payload = {
        "review_status": "bad_data",
        "review_notes": "Corrupted candle",
        "reviewed_by": "alice",
    }
    resp = client.post(f"/research/data/quality/outliers/{row.id}/review", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["reviewed_by"] == "alice"
    assert data["reviewed_at"] is not None


def test_audit_trail_empty_before_any_review(client: TestClient, db_session: Session) -> None:
    """GET audit endpoint returns empty list before any review has been saved."""
    row = _make_report(db_session, asset_symbol="EURUSD", suspicious_spike_bars=1)
    resp = client.get(f"/research/data/quality/outliers/{row.id}/audit")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["entries"] == []


def test_audit_trail_grows_with_each_review(client: TestClient, db_session: Session) -> None:
    """Each review call adds one entry to the audit trail."""
    row = _make_report(db_session, asset_symbol="NZDUSD", suspicious_spike_bars=4)

    for status in ["valid_market_move", "bad_data"]:
        resp = client.post(
            f"/research/data/quality/outliers/{row.id}/review",
            json={"review_status": status, "reviewed_by": "bob"},
        )
        assert resp.status_code == 200

    audit_resp = client.get(f"/research/data/quality/outliers/{row.id}/audit")
    assert audit_resp.status_code == 200
    data = audit_resp.json()
    assert data["total"] == 2
    # Most recent first
    assert data["entries"][0]["new_status"] == "bad_data"
    assert data["entries"][1]["new_status"] == "valid_market_move"


def test_audit_trail_records_previous_status(client: TestClient, db_session: Session) -> None:
    """Audit entry captures the previous_status before the change."""
    row = _make_report(db_session, asset_symbol="AUDUSD", suspicious_spike_bars=1, review_status="unreviewed")

    client.post(
        f"/research/data/quality/outliers/{row.id}/review",
        json={"review_status": "bad_data"},
    )
    audit_resp = client.get(f"/research/data/quality/outliers/{row.id}/audit")
    entry = audit_resp.json()["entries"][0]
    assert entry["previous_status"] == "unreviewed"
    assert entry["new_status"] == "bad_data"


def test_summary_endpoint_returns_counts(client: TestClient, db_session: Session) -> None:
    """GET /quality/outliers/summary returns counts grouped by status."""
    _make_report(db_session, asset_symbol="A1", suspicious_spike_bars=1, review_status="unreviewed")
    _make_report(db_session, asset_symbol="A2", suspicious_spike_bars=1, review_status="unreviewed")
    _make_report(db_session, asset_symbol="A3", suspicious_spike_bars=1, review_status="bad_data")

    resp = client.get("/research/data/quality/outliers/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_flagged"] >= 3
    assert data["unreviewed"] >= 2
    assert data["by_status"].get("unreviewed", 0) >= 2
    assert data["by_status"].get("bad_data", 0) >= 1


def test_filter_by_asset(client: TestClient, db_session: Session) -> None:
    """GET outliers with ?asset= filters to a single asset."""
    _make_report(db_session, asset_symbol="TSLA", suspicious_spike_bars=1)
    _make_report(db_session, asset_symbol="NVDA", suspicious_spike_bars=1)

    resp = client.get("/research/data/quality/outliers?asset=TSLA")
    assert resp.status_code == 200
    data = resp.json()
    symbols = [item["asset_symbol"] for item in data["items"]]
    assert "TSLA" in symbols
    assert "NVDA" not in symbols


def test_filter_by_timeframe(client: TestClient, db_session: Session) -> None:
    """GET outliers with ?timeframe= filters by timeframe."""
    _make_report(db_session, asset_symbol="META", timeframe="1h", suspicious_spike_bars=1)
    _make_report(db_session, asset_symbol="META", timeframe="1d", suspicious_spike_bars=1)

    resp = client.get("/research/data/quality/outliers?timeframe=1h")
    assert resp.status_code == 200
    data = resp.json()
    assert all(item["timeframe"] == "1h" for item in data["items"])
