"""Tests for MH-COCKPIT-13-A ``GET /cockpit/auto-paper/status`` route."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_status_card_route_returns_payload():
    client = TestClient(app)
    resp = client.get("/cockpit/auto-paper/status")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    for key in (
        "advisory",
        "posture",
        "headline",
        "subline",
        "enforcement",
        "trading_control",
        "run_log_summary",
        "links",
    ):
        assert key in body, f"missing key: {key}"

    # Drift-lock invariants surfaced by the card
    assert body["enforcement"]["auto_paper_enforcement_enabled"] is False
    assert body["enforcement"]["auto_trading_enabled"] is False
    # In paper test runs live submission must remain disallowed
    assert body["enforcement"]["live_order_submission_allowed"] is False
