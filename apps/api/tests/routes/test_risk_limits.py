"""Route tests for the MH-38 risk-limit foundation."""
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


def test_create_risk_config(client: TestClient):
    response = client.post(
        "/risk/limits",
        json={
            "scope": "global",
            "trading_mode": "paper",
            "max_order_notional": 5000,
            "max_open_positions": 5,
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["max_order_notional"] == 5000.0
    assert data["max_open_positions"] == 5


def test_list_risk_configs(client: TestClient):
    client.post(
        "/risk/limits",
        json={
            "scope": "global",
            "trading_mode": "paper",
            "max_order_notional": 5000,
        },
    )

    response = client.get("/risk/limits")
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_update_risk_config(client: TestClient):
    created = client.post(
        "/risk/limits",
        json={
            "scope": "global",
            "trading_mode": "paper",
            "max_order_notional": 5000,
        },
    ).json()

    response = client.patch(
        f"/risk/limits/{created['id']}",
        json={"max_total_exposure": 25000},
    )

    assert response.status_code == 200
    assert response.json()["max_total_exposure"] == 25000.0


def test_get_risk_status(client: TestClient):
    client.post(
        "/risk/limits",
        json={
            "scope": "global",
            "trading_mode": "paper",
            "max_order_notional": 5000,
        },
    )

    response = client.get("/risk/limits/status?trading_mode=paper")
    assert response.status_code == 200
    data = response.json()
    assert data["enforcement_enabled"] is False
    assert data["has_max_order_notional"] is True


def test_status_reports_missing_limits_when_not_configured(client: TestClient):
    response = client.get("/risk/limits/status?trading_mode=paper")
    assert response.status_code == 200
    data = response.json()
    assert data["enforcement_enabled"] is False
    assert data["risk_limits_configured"] is False or "max_total_exposure" in data["missing_limits"]


def test_evaluate_order_passes_when_under_configured_limits(client: TestClient):
    client.post(
        "/risk/limits",
        json={
            "scope": "global",
            "trading_mode": "paper",
            "max_order_notional": 10000,
        },
    )

    response = client.post(
        "/risk/limits/evaluate",
        json={
            "ticker": "AAPL",
            "side": "BUY",
            "quantity": 10,
            "estimated_notional": 1000,
            "trading_mode": "paper",
        },
    )
    assert response.status_code == 200
    assert response.json()["allowed"] is True


def test_evaluate_order_returns_violation_when_notional_exceeds_limit(client: TestClient):
    client.post(
        "/risk/limits",
        json={
            "scope": "global",
            "trading_mode": "paper",
            "max_order_notional": 500,
        },
    )

    response = client.post(
        "/risk/limits/evaluate",
        json={
            "ticker": "AAPL",
            "side": "BUY",
            "quantity": 10,
            "estimated_notional": 1000,
            "trading_mode": "paper",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["allowed"] is False
    assert any(v["code"] == "max_order_notional_exceeded" for v in data["violations"])


def test_evaluate_order_returns_violation_when_total_exposure_exceeds_limit(client: TestClient):
    client.post(
        "/risk/limits",
        json={
            "scope": "global",
            "trading_mode": "paper",
            "max_total_exposure": 5000,
        },
    )

    response = client.post(
        "/risk/limits/evaluate",
        json={
            "ticker": "AAPL",
            "side": "BUY",
            "quantity": 10,
            "estimated_notional": 2000,
            "current_total_exposure": 4000,
            "trading_mode": "paper",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["allowed"] is False
    assert any(v["code"] == "max_total_exposure_exceeded" for v in data["violations"])


def test_invalid_negative_limit_rejected(client: TestClient):
    response = client.post(
        "/risk/limits",
        json={
            "scope": "global",
            "trading_mode": "paper",
            "max_order_notional": -1,
        },
    )
    assert response.status_code == 422