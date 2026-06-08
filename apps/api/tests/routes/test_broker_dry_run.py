"""Route tests for broker paper order dry-run verification (MH-30)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import ProgrammingError
from unittest.mock import ANY, MagicMock, patch

from app.db.models.broker_submit_decision import BrokerSubmitDecision
from app.db.models import TradingHalt
from app.db.session import SessionLocal, ensure_public_search_path
from app.main import create_app
from app.config import get_settings


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _clear_active_global_halts():
    with SessionLocal() as session:
        ensure_public_search_path(session)
        try:
            session.query(TradingHalt).filter(
                TradingHalt.scope == "global",
                TradingHalt.status == "active",
            ).delete(synchronize_session=False)
            session.commit()
        except ProgrammingError:
            session.rollback()
    yield
    with SessionLocal() as session:
        ensure_public_search_path(session)
        try:
            session.query(TradingHalt).filter(
                TradingHalt.scope == "global",
                TradingHalt.status == "active",
            ).delete(synchronize_session=False)
            session.commit()
        except ProgrammingError:
            session.rollback()


@pytest.fixture(autouse=True)
def _clear_submit_decisions():
    with SessionLocal() as session:
        ensure_public_search_path(session)
        try:
            session.query(BrokerSubmitDecision).delete(synchronize_session=False)
            session.commit()
        except ProgrammingError:
            session.rollback()
    yield
    with SessionLocal() as session:
        ensure_public_search_path(session)
        try:
            session.query(BrokerSubmitDecision).delete(synchronize_session=False)
            session.commit()
        except ProgrammingError:
            session.rollback()


def _payload(**overrides):
    base = {
        "ticker": "AAPL",
        "side": "BUY",
        "quantity": 10,
        "order_type": "LIMIT",
        "limit_price": 180.5,
    }
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_dry_run_ready_response(client):
    """Dry-run returns ready for valid request in paper mode."""
    response = client.post("/broker/orders/dry-run", json=_payload())

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["mode_guard_ok"] is True
    assert data["request_valid"] is True
    assert data["estimated_notional"] == 1805.0
    assert data["issues"] == []
    assert isinstance(data["warnings"], list)
    assert data["preflight_decision"]["submit_gate"] == "not_applied"
    assert data["preflight_decision"]["decision_status"] in {"advisory", "allowed", "would_block"}
    assert data["execution_source"] == "broker_dry_run"
    assert data["balance_source"] == "ibkr_paper"
    assert data["fees_source"] == "pending_broker_report"
    assert data["fills_source"] == "pending_broker_fill"
    assert data["positions_source"] == "ibkr_paper"
    assert data["serious_paper_source"] == "ibkr_paper"
    assert data["is_canonical_paper"] is True
    assert data["canonical_paper_route"] == "/broker/orders"
    assert data["broker_account_mode"] == "paper"
    assert data["live_state"] == "ibkr_live_locked"


@pytest.mark.asyncio
async def test_dry_run_persists_submit_decision_row(client):
    response = client.post("/broker/orders/dry-run", json=_payload())

    assert response.status_code == 200
    with SessionLocal() as session:
        row = (
            session.query(BrokerSubmitDecision)
            .order_by(BrokerSubmitDecision.created_at.desc())
            .first()
        )
        assert row is not None
        assert row.intent == "manual"
        assert row.preflight_json["source"] == "dry_run"
        assert row.preflight_json["submit_gate"] == "not_applied"
        assert row.preflight_json["execution_source"] == "broker_dry_run"
        assert row.preflight_json["canonical_paper_route"] == "/broker/orders"
        assert row.preflight_json["broker_account_mode"] == "paper"


@pytest.mark.asyncio
async def test_dry_run_invalid_request(client):
    """Dry-run marks request invalid and returns specific issue codes."""
    response = client.post("/broker/orders/dry-run", json=_payload(quantity=0))

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "invalid"
    assert data["request_valid"] is False
    assert any(issue["code"] == "invalid_quantity" for issue in data["issues"])
    assert data["preflight_decision"]["decision_status"] == "blocked"
    assert any(item["code"] == "invalid_quantity" for item in data["preflight_decision"]["blocking_items"])


@pytest.mark.asyncio
async def test_dry_run_blocked_when_live_guard_trips(client, monkeypatch):
    """Dry-run returns blocked when live execution config is detected."""
    monkeypatch.setenv("LIVE_EXECUTION_ENABLED", "true")
    get_settings.cache_clear()

    response = client.post("/broker/orders/dry-run", json=_payload())

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "blocked"
    assert data["mode_guard_ok"] is False
    assert any(issue["code"] == "mode_guard_blocked" for issue in data["issues"])
    assert data["preflight_decision"]["decision_status"] == "blocked"
    assert any(item["code"] == "mode_guard_blocked" for item in data["preflight_decision"]["blocking_items"])


@pytest.mark.asyncio
async def test_dry_run_allowed_for_full_live_config(monkeypatch):
    """Dry-run stays available in fully configured live mode because it never submits orders."""
    monkeypatch.setenv("LIVE_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("BROKER_MODE", "live")
    monkeypatch.setenv("IBKR_ACCOUNT_TYPE", "live")
    get_settings.cache_clear()

    client = TestClient(create_app())
    response = client.post("/broker/orders/dry-run", json=_payload())

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["mode_guard_ok"] is True
    assert data["request_valid"] is True
    assert data["execution_source"] == "broker_dry_run"
    assert data["balance_source"] == "ibkr_live_locked"
    assert data["positions_source"] == "ibkr_live_locked"
    assert data["is_canonical_paper"] is False
    assert data["broker_account_mode"] == "live"
    assert data["live_state"] == "ibkr_live_locked"


@pytest.mark.asyncio
async def test_dry_run_does_not_execute_submit_order(client):
    """Dry-run route must never invoke broker submit_order."""
    fake_service = MagicMock()
    fake_service.dry_run_order.return_value = {
        "status": "ready",
        "mode_guard_ok": True,
        "request_valid": True,
        "estimated_notional": 1805.0,
        "issues": [],
        "warnings": [],
        "preflight_decision": {
            "decision_status": "allowed",
            "submit_gate": "not_applied",
            "advisory_count": 0,
            "would_block_count": 0,
            "blocking_count": 0,
            "advisory_items": [],
            "would_block_items": [],
            "blocking_items": [],
        },
        "preflight_context": {},
        "broker_mode": {
            "broker": "ibkr",
            "mode": "paper",
            "live_execution_enabled": False,
            "paper_trading_enabled": True,
        },
    }

    with patch("app.api.routes.broker.get_broker_service", return_value=fake_service):
        response = client.post("/broker/orders/dry-run", json=_payload())

    assert response.status_code == 200
    fake_service.dry_run_order.assert_called_once_with(
        ANY,
        portfolio_context=None,
        persist_decision=True,
        decision_source="dry_run",
        intent="manual",
        decision_metadata={
            "correlation_id": None,
            "recommendation_id": None,
            "route_check_reference": None,
            "dry_run_reference": None,
            "ticker": "AAPL",
            "side": "BUY",
            "quantity": 10,
            "order_type": "LIMIT",
            "limit_price": 180.5,
            "stop_price": None,
        },
    )
    # If this attribute exists on the double, ensure it was never touched.
    submit = getattr(fake_service, "submit_order", None)
    if submit is not None:
        submit.assert_not_called()


@pytest.mark.asyncio
async def test_dry_run_persists_optional_timeline_metadata(client):
    response = client.post(
        "/broker/orders/dry-run",
        json=_payload(
            recommendation_id="5b0fdb26-75e2-4693-8d1b-a5a19b3ea4fd",
            route_check_reference="recommendation_route_check:eligible",
            dry_run_reference="broker_dry_run:allowed",
            submit_decision_correlation_id="manual_paper_submit_corr_dry_run",
        ),
    )

    assert response.status_code == 200

    with SessionLocal() as session:
        rows = session.query(BrokerSubmitDecision).all()

    assert len(rows) == 1
    row = rows[0]
    assert row.preflight_json["source"] == "dry_run"
    assert row.preflight_json["correlation_id"] == "manual_paper_submit_corr_dry_run"
    assert row.preflight_json["recommendation_id"] == "5b0fdb26-75e2-4693-8d1b-a5a19b3ea4fd"
    assert row.preflight_json["route_check_reference"] == "recommendation_route_check:eligible"
    assert row.preflight_json["dry_run_reference"] == "broker_dry_run:allowed"
    assert row.preflight_json["request_summary"] == {
        "ticker": "AAPL",
        "side": "BUY",
        "quantity": 10.0,
        "order_type": "LIMIT",
        "limit_price": 180.5,
        "stop_price": None,
    }


@pytest.mark.asyncio
async def test_dry_run_surfaces_active_halt_as_blocking_finding(client):
    halt_response = client.post(
        "/trading/halt",
        json={
            "halt_type": "manual",
            "scope": "global",
            "trading_mode": "paper",
            "reason": "operator requested emergency pause",
        },
    )
    assert halt_response.status_code == 201

    response = client.post("/broker/orders/dry-run", json=_payload())

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert any(warning["code"] == "emergency_stop_active" for warning in data["warnings"])
    assert data["preflight_decision"]["decision_status"] == "blocked"
    assert any(item["code"] == "emergency_stop_active" for item in data["preflight_decision"]["blocking_items"])


@pytest.mark.asyncio
async def test_dry_run_surfaces_risk_limit_warning_without_blocking(client):
    risk_response = client.post(
        "/risk/limits",
        json={
            "scope": "global",
            "trading_mode": "paper",
            "max_order_notional": 500,
        },
    )
    assert risk_response.status_code == 201

    response = client.post("/broker/orders/dry-run", json=_payload())

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert any(warning["code"] == "max_order_notional_exceeded" for warning in data["warnings"])
    assert data["preflight_decision"]["decision_status"] == "would_block"
    assert any(item["code"] == "max_order_notional_exceeded" for item in data["preflight_decision"]["would_block_items"])


@pytest.mark.asyncio
async def test_dry_run_preflight_context_null_without_context(client):
    """preflight_context fields are null when no portfolio context is supplied."""
    response = client.post("/broker/orders/dry-run", json=_payload())

    assert response.status_code == 200
    data = response.json()
    ctx = data["preflight_context"]
    assert ctx is not None  # schema is always present
    assert ctx["cash_balance"] is None
    assert ctx["buying_power"] is None
    assert ctx["open_position_count"] is None
    assert ctx["current_symbol_exposure"] is None
    assert ctx["estimated_post_trade_symbol_exposure"] is None
    assert ctx["current_total_exposure"] is None
    assert ctx["estimated_post_trade_total_exposure"] is None
    assert ctx["daily_pnl"] is None
    assert ctx["daily_loss"] is None


@pytest.mark.asyncio
async def test_dry_run_preflight_context_populated_from_request(client):
    """preflight_context echoes back caller-supplied portfolio values."""
    payload = _payload(
        cash_balance=50000.0,
        buying_power=80000.0,
        open_position_count=3,
        current_symbol_exposure=2000.0,
        current_total_exposure=12000.0,
        daily_pnl=250.0,
        daily_loss=0.0,
    )
    response = client.post("/broker/orders/dry-run", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    ctx = data["preflight_context"]
    assert ctx["cash_balance"] == 50000.0
    assert ctx["buying_power"] == 80000.0
    assert ctx["open_position_count"] == 3
    assert ctx["current_symbol_exposure"] == 2000.0
    assert ctx["current_total_exposure"] == 12000.0
    assert ctx["daily_pnl"] == 250.0
    assert ctx["daily_loss"] == 0.0


@pytest.mark.asyncio
async def test_dry_run_post_trade_exposure_computed_for_buy(client):
    """Post-trade symbol and total exposure are computed when BUY + context provided.

    payload: qty=10, limit_price=180.5 → estimated_notional=1805.0
    current_symbol_exposure=2000.0 → post-trade=3805.0
    current_total_exposure=12000.0 → post-trade=13805.0
    """
    payload = _payload(
        current_symbol_exposure=2000.0,
        current_total_exposure=12000.0,
    )
    response = client.post("/broker/orders/dry-run", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    ctx = data["preflight_context"]
    assert ctx["estimated_post_trade_symbol_exposure"] == pytest.approx(3805.0)
    assert ctx["estimated_post_trade_total_exposure"] == pytest.approx(13805.0)


@pytest.mark.asyncio
async def test_dry_run_post_trade_exposure_not_computed_for_sell(client):
    """Post-trade exposure is not computed for SELL orders (sells reduce exposure)."""
    payload = _payload(
        side="SELL",
        current_symbol_exposure=5000.0,
        current_total_exposure=20000.0,
    )
    response = client.post("/broker/orders/dry-run", json=payload)

    assert response.status_code == 200
    data = response.json()
    ctx = data["preflight_context"]
    assert ctx["estimated_post_trade_symbol_exposure"] is None
    assert ctx["estimated_post_trade_total_exposure"] is None


@pytest.mark.asyncio
async def test_dry_run_risk_limit_snapshot_populated_when_config_exists(client):
    """risk_limit_snapshot in preflight_context reflects active risk config."""
    client.post(
        "/risk/limits",
        json={
            "scope": "global",
            "trading_mode": "paper",
            "max_order_notional": 10000,
            "max_total_exposure": 50000,
        },
    )

    response = client.post("/broker/orders/dry-run", json=_payload())

    assert response.status_code == 200
    data = response.json()
    snap = data["preflight_context"]["risk_limit_snapshot"]
    assert snap is not None
    assert snap["max_order_notional"] == 10000.0
    assert snap["max_total_exposure"] == 50000.0


@pytest.mark.asyncio
async def test_dry_run_exposure_violation_when_context_exceeds_limit(client):
    """When context + estimated_notional exceeds max_total_exposure, violation appears in warnings."""
    client.post(
        "/risk/limits",
        json={
            "scope": "global",
            "trading_mode": "paper",
            "max_total_exposure": 13000,
        },
    )

    # current_total_exposure=12000 + notional=1805 = 13805 > 13000
    payload = _payload(current_total_exposure=12000.0)
    response = client.post("/broker/orders/dry-run", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"  # status never changes — advisory only
    codes = {w["code"] for w in data["warnings"]}
    assert "max_total_exposure_exceeded" in codes
    # placeholder should NOT fire when context is provided
    assert "max_exposure_placeholder" not in codes


@pytest.mark.asyncio
async def test_dry_run_status_unchanged_when_portfolio_context_supplied(client):
    """Supplying portfolio context that would violate limits does not change status."""
    client.post(
        "/risk/limits",
        json={
            "scope": "global",
            "trading_mode": "paper",
            "max_order_notional": 500,
            "max_total_exposure": 1000,
        },
    )

    # Both limits are exceeded by the payload
    payload = _payload(
        current_total_exposure=900.0,
        cash_balance=300.0,
    )
    response = client.post("/broker/orders/dry-run", json=payload)

    assert response.status_code == 200
    data = response.json()
    # status must remain ready — context violations are advisory only
    assert data["status"] == "ready"
    assert data["mode_guard_ok"] is True
    assert data["request_valid"] is True
    assert data["preflight_decision"]["submit_gate"] == "not_applied"
    assert data["preflight_decision"]["decision_status"] == "would_block"


@pytest.mark.asyncio
async def test_dry_run_reports_placeholder_status_warnings(client):
    risk_response = client.post(
        "/risk/limits",
        json={
            "scope": "global",
            "trading_mode": "paper",
            "daily_loss_limit_amount": 1000,
            "max_total_exposure": 25000,
        },
    )
    assert risk_response.status_code == 201

    response = client.post("/broker/orders/dry-run", json=_payload())

    assert response.status_code == 200
    data = response.json()
    codes = {warning["code"] for warning in data["warnings"]}
    assert "daily_loss_limit_placeholder" in codes
    assert "max_exposure_placeholder" in codes
