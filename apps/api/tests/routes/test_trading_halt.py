"""Route tests for the MH-39 trading halt foundation."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_status_is_clear_when_no_active_halt_exists(client: TestClient):
    response = client.get("/trading/halt/status?scope=route-clear")

    assert response.status_code == 200
    data = response.json()
    assert data["emergency_stop_active"] is False
    assert data["status"] == "clear"
    assert data["enforcement_enabled"] is True


def test_create_manual_halt(client: TestClient):
    response = client.post(
        "/trading/halt",
        json={
            "halt_type": "manual",
            "scope": "route-create",
            "trading_mode": "paper",
            "reason": "manual operator stop",
            "triggered_by": "qa",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "active"
    assert data["reason"] == "manual operator stop"


def test_status_shows_active_halt(client: TestClient):
    created = client.post(
        "/trading/halt",
        json={
            "halt_type": "manual",
            "scope": "route-active",
            "trading_mode": "paper",
            "reason": "risk check requested stop",
        },
    ).json()

    response = client.get("/trading/halt/status?scope=route-active")

    assert response.status_code == 200
    data = response.json()
    assert data["emergency_stop_active"] is True
    assert data["active_halt"]["id"] == created["id"]
    assert "risk check requested stop" in (data["blocked_reason"] or "")
    assert data["enforcement_enabled"] is True


def test_list_halts(client: TestClient):
    client.post(
        "/trading/halt",
        json={
            "halt_type": "manual",
            "scope": "route-list",
            "reason": "manual stop for listing",
        },
    )

    response = client.get("/trading/halt?status=active")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


def test_resolve_halt(client: TestClient):
    created = client.post(
        "/trading/halt",
        json={
            "halt_type": "system",
            "scope": "route-resolve",
            "reason": "system maintenance",
        },
    ).json()

    response = client.post(
        f"/trading/halt/{created['id']}/resolve",
        json={"resolved_by": "ops", "resolution_notes": "cleared"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "resolved"
    assert data["resolved_by"] == "ops"


def test_status_returns_clear_after_resolve(client: TestClient):
    created = client.post(
        "/trading/halt",
        json={
            "halt_type": "broker",
            "scope": "route-clear-after-resolve",
            "reason": "broker issue",
        },
    ).json()
    client.post(f"/trading/halt/{created['id']}/resolve", json={"resolved_by": "ops"})

    response = client.get("/trading/halt/status?scope=route-clear-after-resolve")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "clear"
    assert data["emergency_stop_active"] is False


def test_cannot_resolve_unknown_halt(client: TestClient):
    response = client.post(
        "/trading/halt/00000000-0000-0000-0000-000000000000/resolve",
        json={"resolved_by": "ops"},
    )

    assert response.status_code == 404


def test_creating_halt_requires_reason(client: TestClient):
    response = client.post(
        "/trading/halt",
        json={
            "halt_type": "manual",
            "scope": "route-no-reason",
            "reason": "",
        },
    )

    assert response.status_code == 422


def test_latest_active_halt_is_returned_when_multiple_exist(client: TestClient):
    client.post(
        "/trading/halt",
        json={
            "halt_type": "manual",
            "scope": "route-latest-active",
            "reason": "first stop",
        },
    )
    latest = client.post(
        "/trading/halt",
        json={
            "halt_type": "risk",
            "scope": "route-latest-active",
            "reason": "latest stop",
        },
    ).json()

    response = client.get("/trading/halt/status?scope=route-latest-active")

    assert response.status_code == 200
    data = response.json()
    assert data["active_halt"]["id"] == latest["id"]
    assert data["enforcement_enabled"] is True