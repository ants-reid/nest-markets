"""MH-COCKPIT-02-A — Tests for /asset-cards/snapshot route."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_snapshot_route_returns_expected_shape():
    client = TestClient(create_app())
    resp = client.get("/asset-cards/snapshot", params={"limit": 5})
    assert resp.status_code == 200
    body = resp.json()
    assert "as_of_utc" in body
    assert "advisory" in body
    assert "items" in body
    assert isinstance(body["items"], list)
    assert body["limit"] == 5
    for item in body["items"]:
        assert "symbol" in item
        assert "market_quality" in item
        assert item["market_quality"]["quality"] in {
            "fresh", "stale", "very_stale", "no_data",
        }


def test_snapshot_route_invalid_limit_rejected():
    client = TestClient(create_app())
    assert client.get("/asset-cards/snapshot", params={"limit": 0}).status_code == 422
    assert client.get("/asset-cards/snapshot", params={"limit": 99999}).status_code == 422
