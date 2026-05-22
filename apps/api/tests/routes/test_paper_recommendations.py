"""Tests for paper trading recommendation service (MH-36)."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db.models import TradingHalt
from app.db.models.broker_submit_decision import BrokerSubmitDecision
from app.db.models.risk_limit_config import RiskLimitConfig
from app.db.session import SessionLocal
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


@pytest.fixture(autouse=True)
def _clear_safety_side_effect_rows():
    """Keep recommendation route tests isolated from shared risk/halt state."""
    with SessionLocal() as session:
        session.query(TradingHalt).filter(
            TradingHalt.scope == "global",
            TradingHalt.status == "active",
        ).delete(synchronize_session=False)
        session.query(RiskLimitConfig).delete(synchronize_session=False)
        session.query(BrokerSubmitDecision).delete(synchronize_session=False)
        session.commit()
    yield
    with SessionLocal() as session:
        session.query(TradingHalt).filter(
            TradingHalt.scope == "global",
            TradingHalt.status == "active",
        ).delete(synchronize_session=False)
        session.query(RiskLimitConfig).delete(synchronize_session=False)
        session.query(BrokerSubmitDecision).delete(synchronize_session=False)
        session.commit()


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


def test_get_serious_paper_route_check_resolves_to_broker_orders_in_paper_mode(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("LIVE_EXECUTION_ENABLED", "false")
    monkeypatch.setenv("BROKER_MODE", "paper")
    monkeypatch.setenv("IBKR_ACCOUNT_TYPE", "paper")
    get_settings.cache_clear()

    post_response = client.post(
        "/paper/recommendations",
        json={
            "ticker": "AAPL",
            "side": "BUY",
            "quantity": 10.0,
            "order_type": "MARKET",
            "risk_score": 0.2,
        },
    )
    rec_id = post_response.json()["id"]
    client.patch(f"/paper/recommendations/{rec_id}/review", json={"approved": True})

    with patch(
        "app.services.broker_service.BrokerService.submit_order", new_callable=AsyncMock
    ) as submit_order, patch(
        "app.services.paper_execution_service.PaperExecutionService.submit_order"
    ) as simulator_submit:
        response = client.get(f"/paper/recommendations/{rec_id}/serious-paper-route-check")

    assert response.status_code == 200
    data = response.json()
    assert data["recommendation_id"] == rec_id
    assert data["recommendation_status"] == "approved"
    assert data["route_check_status"] == "eligible"
    assert data["resolved_route"] == "/broker/orders"
    assert data["resolved_execution_source"] == "ibkr_paper"
    assert data["execution_source"] == "recommendation_route_check"
    assert data["serious_paper_source"] == "ibkr_paper"
    assert data["is_canonical_paper"] is True
    assert data["broker_account_mode"] == "paper"
    assert data["would_block"] is False
    assert data["workers_allowed_to_submit"] is False
    assert data["live_trading_enabled"] is False
    assert data["is_submit"] is False
    assert data["missing_data"] == []
    submit_order.assert_not_called()
    simulator_submit.assert_not_called()


def test_get_serious_paper_route_check_blocks_in_live_mode(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("LIVE_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("BROKER_MODE", "live")
    monkeypatch.setenv("IBKR_ACCOUNT_TYPE", "live")
    get_settings.cache_clear()

    post_response = client.post(
        "/paper/recommendations",
        json={
            "ticker": "MSFT",
            "side": "SELL",
            "quantity": 5.0,
            "order_type": "MARKET",
        },
    )
    rec_id = post_response.json()["id"]
    client.patch(f"/paper/recommendations/{rec_id}/review", json={"approved": True})

    response = client.get(f"/paper/recommendations/{rec_id}/serious-paper-route-check")

    assert response.status_code == 200
    data = response.json()
    assert data["route_check_status"] == "blocked"
    assert data["resolved_route"] is None
    assert data["resolved_execution_source"] is None
    assert data["broker_account_mode"] == "live"
    assert data["live_state"] == "ibkr_live_locked"
    assert data["would_block"] is True
    assert "live" in (data["blocked_reason"] or "").lower()
    assert data["workers_allowed_to_submit"] is False
    assert data["live_trading_enabled"] is False


def test_get_serious_paper_route_check_blocks_in_unknown_mode(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("LIVE_EXECUTION_ENABLED", "false")
    monkeypatch.setenv("BROKER_MODE", "paper")
    monkeypatch.setenv("IBKR_ACCOUNT_TYPE", "live")
    get_settings.cache_clear()

    post_response = client.post(
        "/paper/recommendations",
        json={
            "ticker": "TSLA",
            "side": "BUY",
            "quantity": 2.0,
            "order_type": "MARKET",
        },
    )
    rec_id = post_response.json()["id"]
    client.patch(f"/paper/recommendations/{rec_id}/review", json={"approved": True})

    response = client.get(f"/paper/recommendations/{rec_id}/serious-paper-route-check")

    assert response.status_code == 200
    data = response.json()
    assert data["route_check_status"] == "blocked"
    assert data["resolved_route"] is None
    assert data["resolved_execution_source"] is None
    assert data["broker_account_mode"] == "unknown"
    assert data["live_state"] == "ibkr_live_locked"
    assert data["would_block"] is True
    assert "coherently paper" in (data["blocked_reason"] or "").lower()


def test_get_serious_paper_route_check_returns_missing_context_for_unapproved_recommendation(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("LIVE_EXECUTION_ENABLED", "false")
    monkeypatch.setenv("BROKER_MODE", "paper")
    monkeypatch.setenv("IBKR_ACCOUNT_TYPE", "paper")
    get_settings.cache_clear()

    post_response = client.post(
        "/paper/recommendations",
        json={
            "ticker": "NVDA",
            "side": "BUY",
            "quantity": 3.0,
            "order_type": "MARKET",
        },
    )
    rec_id = post_response.json()["id"]

    response = client.get(f"/paper/recommendations/{rec_id}/serious-paper-route-check")

    assert response.status_code == 200
    data = response.json()
    assert data["recommendation_status"] == "draft"
    assert data["route_check_status"] == "missing_context"
    assert data["resolved_route"] is None
    assert data["resolved_execution_source"] is None
    assert data["would_block"] is True
    assert data["blocked_reason"] is None
    assert data["missing_data"] == [
        "operator approval is required before manual IBKR paper submit"
    ]
    assert "operator approval" in data["next_required_action"].lower()


def test_get_serious_paper_route_check_flags_missing_stop_price_for_stop_orders(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("LIVE_EXECUTION_ENABLED", "false")
    monkeypatch.setenv("BROKER_MODE", "paper")
    monkeypatch.setenv("IBKR_ACCOUNT_TYPE", "paper")
    get_settings.cache_clear()

    post_response = client.post(
        "/paper/recommendations",
        json={
            "ticker": "NVDA",
            "side": "BUY",
            "quantity": 3.0,
            "order_type": "STOP",
        },
    )
    rec_id = post_response.json()["id"]
    client.patch(f"/paper/recommendations/{rec_id}/review", json={"approved": True})

    response = client.get(f"/paper/recommendations/{rec_id}/serious-paper-route-check")

    assert response.status_code == 200
    data = response.json()
    assert data["route_check_status"] == "missing_context"
    assert any("stop_price" in entry for entry in data["missing_data"])


def test_post_broker_dry_run_preview_runs_guarded_dry_run_for_eligible_recommendation(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("LIVE_EXECUTION_ENABLED", "false")
    monkeypatch.setenv("BROKER_MODE", "paper")
    monkeypatch.setenv("IBKR_ACCOUNT_TYPE", "paper")
    get_settings.cache_clear()

    post_response = client.post(
        "/paper/recommendations",
        json={
            "ticker": "AAPL",
            "side": "BUY",
            "quantity": 10.0,
            "order_type": "LIMIT",
            "limit_price": 180.5,
            "risk_score": 0.2,
        },
    )
    rec_id = post_response.json()["id"]
    client.patch(f"/paper/recommendations/{rec_id}/review", json={"approved": True})

    response = client.post(f"/paper/recommendations/{rec_id}/broker-dry-run-preview")

    assert response.status_code == 200
    data = response.json()
    assert data["recommendation_id"] == rec_id
    assert data["route_check_status"] == "eligible"
    assert data["dry_run_status"] == "ready"
    assert data["dry_run_only"] is True
    assert data["dry_run_executed"] is True
    assert data["allowed_to_submit"] is True
    assert data["is_submit"] is False
    assert data["would_block"] is False
    assert data["dry_run_execution_source"] == "broker_dry_run"
    assert data["balance_source"] == "ibkr_paper"
    assert data["positions_source"] == "ibkr_paper"
    assert data["serious_paper_source"] == "ibkr_paper"
    assert data["canonical_paper_route"] == "/broker/orders"
    assert data["preflight_decision"]["submit_gate"] == "not_applied"
    assert data["workers_allowed_to_submit"] is False
    assert data["live_trading_enabled"] is False


def test_post_broker_dry_run_preview_persists_existing_dry_run_decision_row(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("LIVE_EXECUTION_ENABLED", "false")
    monkeypatch.setenv("BROKER_MODE", "paper")
    monkeypatch.setenv("IBKR_ACCOUNT_TYPE", "paper")
    get_settings.cache_clear()

    post_response = client.post(
        "/paper/recommendations",
        json={
            "ticker": "AAPL",
            "side": "BUY",
            "quantity": 10.0,
            "order_type": "LIMIT",
            "limit_price": 180.5,
        },
    )
    rec_id = post_response.json()["id"]
    client.patch(f"/paper/recommendations/{rec_id}/review", json={"approved": True})

    response = client.post(f"/paper/recommendations/{rec_id}/broker-dry-run-preview")
    assert response.status_code == 200

    from app.db.models.broker_submit_decision import BrokerSubmitDecision
    from app.db.session import SessionLocal

    with SessionLocal() as session:
        row = (
            session.query(BrokerSubmitDecision)
            .order_by(BrokerSubmitDecision.created_at.desc())
            .first()
        )
        assert row is not None
        assert row.intent == "manual"
        assert row.preflight_json["source"] == "dry_run"
        assert row.preflight_json["execution_source"] == "broker_dry_run"


def test_post_broker_dry_run_preview_blocks_before_dry_run_in_live_mode(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("LIVE_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("BROKER_MODE", "live")
    monkeypatch.setenv("IBKR_ACCOUNT_TYPE", "live")
    get_settings.cache_clear()

    post_response = client.post(
        "/paper/recommendations",
        json={
            "ticker": "MSFT",
            "side": "SELL",
            "quantity": 5.0,
            "order_type": "MARKET",
        },
    )
    rec_id = post_response.json()["id"]
    client.patch(f"/paper/recommendations/{rec_id}/review", json={"approved": True})

    with patch("app.services.broker_service.BrokerService.dry_run_order") as dry_run_order, patch(
        "app.services.broker_service.BrokerService.submit_order", new_callable=AsyncMock
    ) as submit_order:
        response = client.post(f"/paper/recommendations/{rec_id}/broker-dry-run-preview")

    assert response.status_code == 200
    data = response.json()
    assert data["route_check_status"] == "blocked"
    assert data["dry_run_status"] == "blocked"
    assert data["dry_run_executed"] is False
    assert data["allowed_to_submit"] is False
    assert data["dry_run_execution_source"] is None
    dry_run_order.assert_not_called()
    submit_order.assert_not_called()


def test_post_broker_dry_run_preview_blocks_before_dry_run_when_context_missing(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("LIVE_EXECUTION_ENABLED", "false")
    monkeypatch.setenv("BROKER_MODE", "paper")
    monkeypatch.setenv("IBKR_ACCOUNT_TYPE", "paper")
    get_settings.cache_clear()

    post_response = client.post(
        "/paper/recommendations",
        json={
            "ticker": "TSLA",
            "side": "BUY",
            "quantity": 2.0,
            "order_type": "MARKET",
        },
    )
    rec_id = post_response.json()["id"]

    with patch("app.services.broker_service.BrokerService.dry_run_order") as dry_run_order, patch(
        "app.services.broker_service.BrokerService.submit_order", new_callable=AsyncMock
    ) as submit_order:
        response = client.post(f"/paper/recommendations/{rec_id}/broker-dry-run-preview")

    assert response.status_code == 200
    data = response.json()
    assert data["route_check_status"] == "missing_context"
    assert data["dry_run_status"] == "missing_context"
    assert data["dry_run_executed"] is False
    assert data["allowed_to_submit"] is False
    dry_run_order.assert_not_called()
    submit_order.assert_not_called()


def test_post_broker_dry_run_preview_never_calls_submit_order(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("LIVE_EXECUTION_ENABLED", "false")
    monkeypatch.setenv("BROKER_MODE", "paper")
    monkeypatch.setenv("IBKR_ACCOUNT_TYPE", "paper")
    get_settings.cache_clear()

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
    client.patch(f"/paper/recommendations/{rec_id}/review", json={"approved": True})

    with patch("app.services.broker_service.BrokerService.submit_order", new_callable=AsyncMock) as submit_order:
        response = client.post(f"/paper/recommendations/{rec_id}/broker-dry-run-preview")

    assert response.status_code == 200
    submit_order.assert_not_called()


def test_get_serious_paper_route_check_does_not_mutate_recommendation_state(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("LIVE_EXECUTION_ENABLED", "false")
    monkeypatch.setenv("BROKER_MODE", "paper")
    monkeypatch.setenv("IBKR_ACCOUNT_TYPE", "paper")
    get_settings.cache_clear()

    post_response = client.post(
        "/paper/recommendations",
        json={
            "ticker": "AMD",
            "side": "BUY",
            "quantity": 7.0,
            "order_type": "MARKET",
        },
    )
    rec_id = post_response.json()["id"]
    review_response = client.patch(
        f"/paper/recommendations/{rec_id}/review",
        json={"approved": True, "review_notes": "operator approved for manual paper follow-up"},
    )
    reviewed = review_response.json()

    response = client.get(f"/paper/recommendations/{rec_id}/serious-paper-route-check")
    after = client.get(f"/paper/recommendations/{rec_id}")

    assert response.status_code == 200
    assert after.status_code == 200
    data = after.json()
    assert data["status"] == reviewed["status"] == "approved"
    assert data["reviewed_at"] == reviewed["reviewed_at"]
    assert data["review_notes"] == reviewed["review_notes"]
    assert data["executed_at"] is None
    assert data["paper_order_ids"] is None
