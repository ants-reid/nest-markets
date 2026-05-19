"""MH-COCKPIT-01-A — Tests for /markets/snapshot endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_snapshot_endpoint_returns_expected_shape():
    client = TestClient(create_app())
    resp = client.get("/markets/snapshot")
    assert resp.status_code == 200
    body = resp.json()
    assert "as_of_utc" in body
    assert "advisory" in body
    assert isinstance(body["markets"], list)
    codes = {m["code"] for m in body["markets"]}
    assert {"FX", "NYSE", "LSE", "TSE"} <= codes
    for market in body["markets"]:
        assert isinstance(market["is_open"], bool)
        assert "label" in market
        assert "local_time" in market
        assert "notes" in market
