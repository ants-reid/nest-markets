"""Tests for MH-COCKPIT-03 cockpit mode route."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.services.cockpit_mode_service import reset_cockpit_mode_for_tests


def setup_function() -> None:
    reset_cockpit_mode_for_tests()


def test_cockpit_mode_get_returns_mode_inventory() -> None:
    client = TestClient(app)

    resp = client.get("/cockpit/mode")
    assert resp.status_code == 200, resp.text

    body = resp.json()
    assert body["current_mode"] == "learning"
    assert body["selectable_modes"] == ["learning", "manual", "auto_paper"]
    assert body["locked_modes"] == ["assisted_live", "live", "auto_live"]
    assert body["live_trading_enabled"] is False
    assert body["auto_live_enabled"] is False
    assert body["real_money_enabled"] is False


def test_cockpit_mode_post_accepts_manual() -> None:
    client = TestClient(app)

    resp = client.post("/cockpit/mode", json={"requested_mode": "manual"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["current_mode"] == "manual"
    assert body["global_safety_state"]["live_trading_enabled"] is False


def test_cockpit_mode_post_rejects_auto_live() -> None:
    client = TestClient(app)

    resp = client.post("/cockpit/mode", json={"requested_mode": "auto_live"})
    assert resp.status_code == 403, resp.text
    body = resp.json()
    assert body["detail"]["code"] == "cockpit_mode_locked"
    assert body["detail"]["requested_mode"] == "auto_live"