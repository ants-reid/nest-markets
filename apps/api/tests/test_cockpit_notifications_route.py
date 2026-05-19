"""Tests for MH-COCKPIT-06-A ``GET /cockpit/notifications/digest`` route."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_digest_snapshot_shape():
    client = TestClient(app)
    resp = client.get("/cockpit/notifications/digest?hours=4&min_severity=warn&limit=5")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    for key in (
        "as_of_utc",
        "window_start_utc",
        "hours",
        "min_severity",
        "limit",
        "advisory",
        "totals",
        "attention_count",
        "highest_severity",
        "attention",
    ):
        assert key in body, f"missing key: {key}"
    assert body["hours"] == 4
    assert body["min_severity"] == "warn"
    assert body["limit"] == 5
    assert isinstance(body["attention"], list)


def test_digest_invalid_min_severity_rejected():
    client = TestClient(app)
    resp = client.get("/cockpit/notifications/digest?min_severity=bogus")
    assert resp.status_code == 400
