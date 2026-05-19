"""Tests for MH-MON-08-A ``GET /monitor/health-history`` route."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_health_history_snapshot_shape():
    client = TestClient(app)
    resp = client.get("/monitor/health-history?hours=4&bucket_minutes=60")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    for key in (
        "as_of_utc",
        "window_start_utc",
        "hours",
        "bucket_minutes",
        "filters",
        "advisory",
        "totals",
        "last_per_source",
        "timeseries",
    ):
        assert key in body, f"missing key: {key}"
    assert body["hours"] == 4
    assert body["bucket_minutes"] == 60
    assert isinstance(body["timeseries"], list)
    assert len(body["timeseries"]) == 4


def test_health_history_invalid_bucket_rejected():
    client = TestClient(app)
    resp = client.get("/monitor/health-history?hours=4&bucket_minutes=7")
    assert resp.status_code == 400
