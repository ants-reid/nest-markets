"""Tests for paper trading recommendation service (MH-36)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app


@pytest.fixture
def client():
    """Test client for the FastAPI app."""
    app = create_app()
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    """Clear settings cache before/after each test."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


# ---------------------------------------------------------------------------
# Route tests
# ---------------------------------------------------------------------------


def test_post_draft_recommendation(client: TestClient):
    """Test POST /paper/recommendations endpoint."""
    response = client.post(
        "/paper/recommendations",
        json={
            "ticker": "AAPL",
            "side": "BUY",
            "quantity": 10.0,
            "order_type": "MARKET",
            "confidence": 0.8,
            "risk_score": 0.2,
            "rationale": "Uptrend confirmed",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "AAPL"
    assert data["side"] == "BUY"
    assert data["quantity"] == 10.0
    assert data["status"] == "draft"
    assert data["id"] is not None


def test_post_draft_recommendation_limit_order(client: TestClient):
    """Test drafting a LIMIT order via API."""
    response = client.post(
        "/paper/recommendations",
        json={
            "ticker": "MSFT",
            "side": "SELL",
            "quantity": 5.0,
            "order_type": "LIMIT",
            "limit_price": 350.0,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["order_type"] == "LIMIT"
    assert data["limit_price"] == 350.0


def test_post_draft_recommendation_missing_limit_price(client: TestClient):
    """Test that LIMIT orders require limit_price."""
    response = client.post(
        "/paper/recommendations",
        json={
            "ticker": "MSFT",
            "side": "SELL",
            "quantity": 5.0,
            "order_type": "LIMIT",
        },
    )

    assert response.status_code == 400


def test_get_list_recommendations(client: TestClient):
    """Test GET /paper/recommendations endpoint."""
    # Draft two recommendations
    client.post(
        "/paper/recommendations",
        json={
            "ticker": "AAPL",
            "side": "BUY",
            "quantity": 10.0,
            "order_type": "MARKET",
        },
    )
    client.post(
        "/paper/recommendations",
        json={
            "ticker": "MSFT",
            "side": "SELL",
            "quantity": 5.0,
            "order_type": "MARKET",
        },
    )

    # List all
    response = client.get("/paper/recommendations")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 2
    assert len(data["items"]) >= 2


def test_get_recommendation_by_id(client: TestClient):
    """Test GET /paper/recommendations/{id} endpoint."""
    # Draft a recommendation
    post_response = client.post(
        "/paper/recommendations",
        json={
            "ticker": "AAPL",
            "side": "BUY",
            "quantity": 10.0,
            "order_type": "MARKET",
        },
    )
    rec_id = post_response.json()["id"]

    # Retrieve it
    response = client.get(f"/paper/recommendations/{rec_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == rec_id
    assert data["ticker"] == "AAPL"


def test_patch_review_recommendation_approve(client: TestClient):
    """Test PATCH /paper/recommendations/{id}/review endpoint (approve)."""
    # Draft a recommendation
    post_response = client.post(
        "/paper/recommendations",
        json={
            "ticker": "AAPL",
            "side": "BUY",
            "quantity": 10.0,
            "order_type": "MARKET",
        },
    )
    rec_id = post_response.json()["id"]

    # Review and approve
    response = client.patch(
        f"/paper/recommendations/{rec_id}/review",
        json={"approved": True, "review_notes": "Approved by QA"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "approved"
    assert data["review_notes"] == "Approved by QA"
