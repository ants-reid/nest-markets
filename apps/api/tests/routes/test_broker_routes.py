"""Integration tests for /broker endpoints."""
import pytest
import httpx
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.main import create_app
from app.clients.broker.broker_interface import (
    AccountInfo,
    OrderResult,
    PositionInfo,
)
from app.config import get_settings
from app.db.models import TradingHalt
from app.db.models.broker_submit_decision import BrokerSubmitDecision
from app.db.session import SessionLocal
from app.services.broker_service import BrokerService
from app.services.broker_mode_guard import LiveExecutionBlockedError  # noqa: F401 — import confirms symbol is importable


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def mock_service():
    """Create a mock broker service."""
    return AsyncMock()


@pytest.mark.asyncio
async def test_get_account_info(client, mock_service):
    """Test GET /broker/account endpoint."""
    expected_info = AccountInfo(
        net_liquidation=Decimal("100000"),
        cash_balance=Decimal("50000"),
        buying_power=Decimal("100000"),
        excess_liquidity=Decimal("15000"),
        margin=Decimal("5000"),
        unrealized_pnl=Decimal("2500"),
    )
    
    with patch("app.api.routes.broker.get_broker_service") as mock_get_service:
        mock_service.get_account_info = AsyncMock(return_value=expected_info)
        mock_get_service.return_value = mock_service
        
        response = client.get("/broker/account")
        
        assert response.status_code == 200
        data = response.json()
        assert data["net_liquidation"] == 100000.0
        assert data["cash_balance"] == 50000.0
        assert data["buying_power"] == 100000.0


@pytest.mark.asyncio
async def test_get_positions(client, mock_service):
    """Test GET /broker/positions endpoint."""
    positions = [
        PositionInfo(
            conid=265598,
            ticker="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            avg_cost=Decimal("150.00"),
            market_price=Decimal("175.25"),
        ),
    ]
    
    with patch("app.api.routes.broker.get_broker_service") as mock_get_service:
        mock_service.get_positions = AsyncMock(return_value=positions)
        mock_get_service.return_value = mock_service
        
        response = client.get("/broker/positions")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["ticker"] == "AAPL"
        assert data[0]["quantity"] == 100.0


@pytest.mark.asyncio
async def test_get_account_returns_empty_snapshot_when_gateway_unreachable_in_paper_mode(client, mock_service):
    """GET /broker/account must degrade safely when paper gateway is unreachable."""
    with patch("app.api.routes.broker.get_broker_service") as mock_get_service:
        mock_service.get_account_info = AsyncMock(side_effect=httpx.ConnectError("All connection attempts failed"))
        mock_get_service.return_value = mock_service

        response = client.get("/broker/account")

    assert response.status_code == 200
    data = response.json()
    assert data["net_liquidation"] == 0.0
    assert data["cash_balance"] == 0.0
    assert data["buying_power"] == 0.0
    assert data["broker_mode"]["mode"] == "paper"


@pytest.mark.asyncio
async def test_get_positions_returns_empty_list_when_gateway_unreachable_in_paper_mode(client, mock_service):
    """GET /broker/positions must degrade safely when paper gateway is unreachable."""
    with patch("app.api.routes.broker.get_broker_service") as mock_get_service:
        mock_service.get_positions = AsyncMock(side_effect=httpx.ConnectError("All connection attempts failed"))
        mock_get_service.return_value = mock_service

        response = client.get("/broker/positions")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_account_returns_503_on_tws_client_id_contention(client, mock_service):
    with patch("app.api.routes.broker.get_broker_service") as mock_get_service:
        mock_service.get_account_info = AsyncMock(
            side_effect=RuntimeError("client id is already in use")
        )
        mock_get_service.return_value = mock_service

        response = client.get("/broker/account")

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["code"] == "tws_unavailable"
    assert "client id" in detail["message"].lower()


@pytest.mark.asyncio
async def test_get_positions_returns_503_on_tws_timeout(client, mock_service):
    with patch("app.api.routes.broker.get_broker_service") as mock_get_service:
        mock_service.get_positions = AsyncMock(
            side_effect=RuntimeError("API connection failed: TimeoutError()")
        )
        mock_get_service.return_value = mock_service

        response = client.get("/broker/positions")

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["code"] == "tws_unavailable"
    assert "timeout" in detail["message"].lower()


@pytest.mark.asyncio
async def test_submit_order(client, mock_service):
    """Test POST /broker/orders endpoint."""
    order_result = OrderResult(
        broker_order_id="123456",
        status="SUBMITTED",
    )
    
    with patch("app.api.routes.broker.get_broker_service") as mock_get_service:
        mock_service.submit_order = AsyncMock(return_value=order_result)
        mock_get_service.return_value = mock_service
        
        payload = {
            "ticker": "AAPL",
            "side": "BUY",
            "quantity": 100,
            "order_type": "MARKET",
        }
        
        response = client.post("/broker/orders", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["broker_order_id"] == "123456"
        assert data["status"] == "SUBMITTED"


@pytest.mark.asyncio
async def test_submit_order_returns_structured_403_when_paper_preflight_blocks(client):
    """POST /broker/orders must block paper submit when MH-77 would-block findings exist."""
    client.post(
        "/risk/limits",
        json={
            "scope": "global",
            "trading_mode": "paper",
            "max_order_notional": 500,
        },
    )

    broker = AsyncMock()
    broker.get_account_info = AsyncMock(
        return_value=AccountInfo(
            net_liquidation=Decimal("100000"),
            cash_balance=Decimal("50000"),
            buying_power=Decimal("100000"),
        )
    )
    broker.get_positions = AsyncMock(return_value=[])
    broker.submit_order = AsyncMock(
        return_value=OrderResult(
            broker_order_id="SHOULD-NOT-SUBMIT",
            status="SUBMITTED",
        )
    )
    service = BrokerService(broker=broker)

    with patch("app.api.routes.broker.get_broker_service", return_value=service), patch.object(
        service,
        "get_daily_pnl",
        return_value={"daily_pnl": 0.0, "daily_loss": 0.0},
    ):
        response = client.post(
            "/broker/orders",
            json={
                "ticker": "AAPL",
                "side": "BUY",
                "quantity": 10,
                "order_type": "LIMIT",
                "limit_price": 180.5,
                "recommendation_id": "fddb0edb-4f0c-43fe-95df-b3d2e66f11ab",
                "route_check_reference": "recommendation_route_check:eligible",
                "dry_run_reference": "broker_dry_run:would_block",
                "submit_decision_correlation_id": "manual_paper_submit_corr_1",
            },
        )

    assert response.status_code == 403
    data = response.json()["detail"]
    assert data["code"] == "paper_preflight_blocked"
    assert data["submit_gate"] == "blocked"
    assert data["decision_status"] == "would_block"
    assert any(item["code"] == "max_order_notional_exceeded" for item in data["blocking_reasons"])
    broker.submit_order.assert_not_called()

    with SessionLocal() as session:
        rows = (
            session.query(BrokerSubmitDecision)
            .order_by(BrokerSubmitDecision.created_at.asc())
            .all()
        )

    assert len(rows) == 2
    assert rows[0].preflight_json["source"] == "submit_preflight"
    assert rows[0].preflight_json["decision_status"] == "would_block"
    assert rows[0].preflight_json["allowed_to_submit"] is False
    assert rows[0].preflight_json["correlation_id"] == "manual_paper_submit_corr_1"
    assert rows[0].preflight_json["recommendation_id"] == "fddb0edb-4f0c-43fe-95df-b3d2e66f11ab"
    assert rows[0].preflight_json["route_check_reference"] == "recommendation_route_check:eligible"
    assert rows[0].preflight_json["dry_run_reference"] == "broker_dry_run:would_block"
    assert rows[0].preflight_json["request_summary"] == {
        "ticker": "AAPL",
        "side": "BUY",
        "quantity": 10.0,
        "order_type": "LIMIT",
        "limit_price": 180.5,
        "stop_price": None,
    }
    assert rows[1].preflight_json["source"] == "submit_attempt"
    assert rows[1].preflight_json["submit_gate"] == "blocked"
    assert rows[1].preflight_json["allowed_to_submit"] is False
    assert rows[1].preflight_json["correlation_id"] == "manual_paper_submit_corr_1"
    assert rows[1].preflight_json["recommendation_id"] == "fddb0edb-4f0c-43fe-95df-b3d2e66f11ab"
    assert rows[1].would_block is True


@pytest.mark.asyncio
async def test_submit_order_returns_halt_block_when_active_halt_exists(client):
    """POST /broker/orders must return a structured halt-related block when an active halt exists."""
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

    broker = AsyncMock()
    broker.get_account_info = AsyncMock(
        return_value=AccountInfo(
            net_liquidation=Decimal("100000"),
            cash_balance=Decimal("50000"),
            buying_power=Decimal("100000"),
        )
    )
    broker.get_positions = AsyncMock(return_value=[])
    broker.submit_order = AsyncMock(
        return_value=OrderResult(
            broker_order_id="SHOULD-NOT-SUBMIT",
            status="SUBMITTED",
        )
    )
    service = BrokerService(broker=broker)

    with patch("app.api.routes.broker.get_broker_service", return_value=service), patch.object(
        service,
        "get_daily_pnl",
        return_value={"daily_pnl": 0.0, "daily_loss": 0.0},
    ):
        response = client.post(
            "/broker/orders",
            json={
                "ticker": "AAPL",
                "side": "BUY",
                "quantity": 10,
                "order_type": "LIMIT",
                "limit_price": 180.5,
            },
        )

    assert response.status_code == 403
    data = response.json()["detail"]
    assert data["code"] == "paper_preflight_blocked"
    assert data["submit_gate"] == "blocked"
    assert data["decision_status"] == "blocked"
    assert any(item["code"] == "emergency_stop_active" for item in data["blocking_reasons"])
    broker.submit_order.assert_not_called()


@pytest.mark.asyncio
async def test_submit_order_live_mode_remains_blocked_even_with_active_halt(client, monkeypatch):
    """Live submit must remain blocked by trading control even if a halt is also active."""
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

    monkeypatch.setenv("LIVE_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("BROKER_MODE", "live")
    monkeypatch.setenv("IBKR_ACCOUNT_TYPE", "live")
    get_settings.cache_clear()

    response = client.post(
        "/broker/orders",
        json={"ticker": "AAPL", "side": "BUY", "quantity": 10, "order_type": "MARKET"},
    )

    assert response.status_code == 403
    assert "Live order submission" in response.json()["detail"]


@pytest.mark.asyncio
async def test_resolved_halt_restores_existing_paper_submit_path(client):
    """Resolved halt must allow the existing paper submit path again."""
    created = client.post(
        "/trading/halt",
        json={
            "halt_type": "manual",
            "scope": "global",
            "trading_mode": "paper",
            "reason": "temporary operator pause",
        },
    ).json()
    resolved = client.post(
        f"/trading/halt/{created['id']}/resolve",
        json={"resolved_by": "ops", "resolution_notes": "cleared"},
    )
    assert resolved.status_code == 200

    broker = AsyncMock()
    broker.get_account_info = AsyncMock(
        return_value=AccountInfo(
            net_liquidation=Decimal("100000"),
            cash_balance=Decimal("50000"),
            buying_power=Decimal("100000"),
        )
    )
    broker.get_positions = AsyncMock(return_value=[])
    broker.submit_order = AsyncMock(
        return_value=OrderResult(
            broker_order_id="PAPER-HALT-CLEARED",
            status="SUBMITTED",
        )
    )
    service = BrokerService(broker=broker)

    with patch("app.api.routes.broker.get_broker_service", return_value=service), patch.object(
        service,
        "get_daily_pnl",
        return_value={"daily_pnl": 0.0, "daily_loss": 0.0},
    ):
        response = client.post(
            "/broker/orders",
            json={
                "ticker": "AAPL",
                "side": "BUY",
                "quantity": 10,
                "order_type": "MARKET",
            },
        )

    assert response.status_code == 200
    assert response.json()["status"] == "SUBMITTED"
    broker.submit_order.assert_called_once()

    with SessionLocal() as session:
        rows = (
            session.query(BrokerSubmitDecision)
            .order_by(BrokerSubmitDecision.created_at.asc())
            .all()
        )

    assert len(rows) == 2
    assert rows[0].preflight_json["source"] == "submit_preflight"
    assert rows[0].preflight_json["decision_status"] == "advisory"
    assert rows[1].preflight_json["source"] == "submit_attempt"
    assert rows[1].preflight_json["decision_status"] == "allowed"
    assert rows[1].preflight_json["submit_gate"] == "allowed"
    assert rows[1].preflight_json["broker_order_id"] == "PAPER-HALT-CLEARED"


@pytest.mark.asyncio
async def test_submit_order_invalid_request(client):
    """Test POST /broker/orders with invalid request."""
    payload = {
        "ticker": "AAPL",
        "side": "BUY",
        "quantity": 0,  # Invalid
        "order_type": "MARKET",
    }
    
    response = client.post("/broker/orders", json=payload)
    
    # Should fail validation or service logic
    assert response.status_code in (400, 422, 500)


@pytest.mark.asyncio
async def test_cancel_order(client, mock_service):
    """Test DELETE /broker/orders/{order_id} endpoint."""
    with patch("app.api.routes.broker.get_broker_service") as mock_get_service:
        mock_service.cancel_order = AsyncMock(return_value=True)
        mock_get_service.return_value = mock_service
        
        response = client.delete("/broker/orders/123456")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


@pytest.mark.asyncio
async def test_cancel_order_not_found(client, mock_service):
    """Test DELETE for non-existent order."""
    with patch("app.api.routes.broker.get_broker_service") as mock_get_service:
        mock_service.cancel_order = AsyncMock(return_value=False)
        mock_get_service.return_value = mock_service
        
        response = client.delete("/broker/orders/999999")
        
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_order_status(client, mock_service):
    """Test GET /broker/orders/{order_id}/status endpoint."""
    status_dict = {
        "order_id": "123456",
        "order_status": "Filled",
        "avgPrice": 175.25,
    }
    
    with patch("app.api.routes.broker.get_broker_service") as mock_get_service:
        mock_service.get_order_status = AsyncMock(return_value=status_dict)
        mock_get_service.return_value = mock_service
        
        response = client.get("/broker/orders/123456/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["order_status"] == "Filled"


@pytest.mark.asyncio
async def test_reconcile_positions(client, mock_service):
    """Test POST /broker/reconcile endpoint."""
    positions = [
        PositionInfo(
            conid=265598,
            ticker="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            avg_cost=Decimal("150.00"),
        ),
    ]
    
    reconciliation_report = {
        "matched_count": 1,
        "mismatch_count": 0,
        "mismatches": {},
        "actual_positions": positions,
    }
    
    with patch("app.api.routes.broker.get_broker_service") as mock_get_service:
        mock_service.reconcile_positions = AsyncMock(
            return_value=reconciliation_report
        )
        mock_get_service.return_value = mock_service
        
        payload = {"AAPL": 100.0}
        response = client.post("/broker/reconcile", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["matched_count"] == 1
        assert data["mismatch_count"] == 0


@pytest.mark.asyncio
async def test_normalize_broker_trades_endpoint(client, mock_service):
    """Test POST /broker/trades/normalize endpoint."""
    with patch("app.api.routes.broker.get_broker_service") as mock_get_service:
        mock_service.normalize_and_stage_trade_events = AsyncMock(
            return_value={
                "received": 2,
                "inserted": 2,
                "skipped": 0,
                "source": "broker_account_trades",
                "account_id": "DU123456",
                "broker_mode": {
                    "broker": "ibkr",
                    "mode": "paper",
                    "live_execution_enabled": False,
                    "paper_trading_enabled": True,
                },
                "note": None,
            }
        )
        mock_get_service.return_value = mock_service

        response = client.post("/broker/trades/normalize")

        assert response.status_code == 200
        data = response.json()
        assert data["received"] == 2
        assert data["inserted"] == 2
        assert data["source"] == "broker_account_trades"


@pytest.mark.asyncio
async def test_get_normalized_broker_trades_audit_endpoint(client, mock_service):
    """Test GET /broker/trades/normalized readback endpoint."""
    with patch("app.api.routes.broker.get_broker_service") as mock_get_service:
        mock_service.get_normalized_trade_events = MagicMock(
            return_value={
            "entries": [
                {
                    "event_fingerprint": "abc123",
                    "external_trade_id": "T-1001",
                    "broker_order_id": "1001",
                    "symbol": "AAPL",
                    "side": "BUY",
                    "quantity": 10.0,
                    "fill_price": 185.1,
                    "commission": 1.0,
                    "net_amount": 1850.0,
                    "realized_pnl": 5.0,
                    "trade_ts": "2026-04-28T12:00:00+00:00",
                    "source": "broker_account_trades",
                    "account_id": "DU123456",
                    "broker_provider": "ibkr",
                    "created_at": "2026-04-28T12:00:01+00:00",
                }
            ],
            "returned": 1,
            "account_id": "DU123456",
            "broker_mode": {
                "broker": "ibkr",
                "mode": "paper",
                "live_execution_enabled": False,
                "paper_trading_enabled": True,
            },
        }
        )
        mock_get_service.return_value = mock_service

        response = client.get("/broker/trades/normalized?limit=25")

        assert response.status_code == 200
        data = response.json()
        assert data["returned"] == 1
        assert data["entries"][0]["event_fingerprint"] == "abc123"
        mock_service.get_normalized_trade_events.assert_called_once_with(limit=25)


# ---------------------------------------------------------------------------
# MH-26 Operational Verification — mode endpoint, metadata, guard trips
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clear_settings_cache():
    """Re-read env for every test so monkeypatch env changes take effect."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _clear_active_global_halts():
    with SessionLocal() as session:
        session.query(TradingHalt).filter(
            TradingHalt.scope == "global",
            TradingHalt.status == "active",
        ).delete(synchronize_session=False)
        session.commit()
    yield
    with SessionLocal() as session:
        session.query(TradingHalt).filter(
            TradingHalt.scope == "global",
            TradingHalt.status == "active",
        ).delete(synchronize_session=False)
        session.commit()


@pytest.fixture(autouse=True)
def _clear_submit_decisions():
    with SessionLocal() as session:
        session.query(BrokerSubmitDecision).delete(synchronize_session=False)
        session.commit()
    yield
    with SessionLocal() as session:
        session.query(BrokerSubmitDecision).delete(synchronize_session=False)
        session.commit()


@pytest.mark.asyncio
async def test_get_broker_mode_endpoint(client):
    """GET /broker/mode must return paper-mode metadata with correct shape."""
    response = client.get("/broker/mode")
    assert response.status_code == 200
    data = response.json()
    assert data["broker"] == "ibkr"
    assert data["mode"] == "paper"
    assert data["live_execution_enabled"] is False
    assert data["paper_trading_enabled"] is True


@pytest.mark.asyncio
async def test_get_broker_control_endpoint(client):
    """GET /broker/control must expose MH-36B trading control state."""
    response = client.get("/broker/control")
    assert response.status_code == 200
    data = response.json()
    assert data["trading_mode"] == "paper"
    assert data["execution_control"] == "manual"
    assert data["arming_state"] == "armed"
    assert data["paper_order_submission_allowed"] is True
    assert data["live_order_submission_allowed"] is False
    assert data["auto_trading_allowed"] is False


@pytest.mark.asyncio
async def test_get_broker_control_endpoint_live_visible_but_blocked(client, monkeypatch):
    """Fully configured live mode should be visible in control state but still blocked for submit."""
    monkeypatch.setenv("LIVE_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("BROKER_MODE", "live")
    monkeypatch.setenv("IBKR_ACCOUNT_TYPE", "live")
    get_settings.cache_clear()

    response = client.get("/broker/control")
    assert response.status_code == 200
    data = response.json()
    assert data["trading_mode"] == "live"
    assert data["execution_control"] == "manual"
    assert data["arming_state"] == "disarmed"
    assert data["live_order_submission_allowed"] is False
    assert data["auto_trading_allowed"] is False
    assert data["reasons"]


@pytest.mark.asyncio
async def test_get_canonical_paper_route_resolves_to_broker_orders_in_paper_mode(client):
    """Serious-paper route-check must resolve only to /broker/orders in coherent paper mode."""
    response = client.get("/broker/paper/canonical-route")

    assert response.status_code == 200
    data = response.json()
    assert data["requested_mode"] == "serious_paper"
    assert data["resolved_execution_source"] == "ibkr_paper"
    assert data["resolved_route"] == "/broker/orders"
    assert data["simulator_route"] == "/execution/paper"
    assert data["simulator_allowed_for_serious_paper"] is False
    assert data["current_broker_account_mode"] == "paper"
    assert data["can_route_to_broker_paper"] is True
    assert data["would_block"] is False
    assert data["is_submit"] is False


@pytest.mark.asyncio
async def test_get_canonical_paper_route_blocks_in_live_mode(monkeypatch):
    """Serious-paper route-check must fail closed when broker mode is live."""
    monkeypatch.setenv("LIVE_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("BROKER_MODE", "live")
    monkeypatch.setenv("IBKR_ACCOUNT_TYPE", "live")
    get_settings.cache_clear()

    client = TestClient(create_app())
    response = client.get("/broker/paper/canonical-route")

    assert response.status_code == 200
    data = response.json()
    assert data["resolved_execution_source"] is None
    assert data["resolved_route"] is None
    assert data["current_broker_account_mode"] == "live"
    assert data["can_route_to_broker_paper"] is False
    assert data["would_block"] is True
    assert "live" in data["blocked_reason"].lower()
    assert data["canonical_paper_route"] == "/broker/orders"
    assert data["simulator_route"] == "/execution/paper"


@pytest.mark.asyncio
async def test_get_canonical_paper_route_blocks_in_unknown_mode(monkeypatch):
    """Serious-paper route-check must fail closed when broker mode is not coherently paper."""
    monkeypatch.setenv("LIVE_EXECUTION_ENABLED", "false")
    monkeypatch.setenv("BROKER_MODE", "paper")
    monkeypatch.setenv("IBKR_ACCOUNT_TYPE", "live")
    get_settings.cache_clear()

    client = TestClient(create_app())
    response = client.get("/broker/paper/canonical-route")

    assert response.status_code == 200
    data = response.json()
    assert data["resolved_execution_source"] is None
    assert data["resolved_route"] is None
    assert data["current_broker_account_mode"] == "unknown"
    assert data["can_route_to_broker_paper"] is False
    assert data["would_block"] is True
    assert "coherently paper" in data["blocked_reason"].lower()
    assert data["simulator_allowed_for_serious_paper"] is False


@pytest.mark.asyncio
async def test_submit_order_returns_403_when_live_mode_fully_configured(client, monkeypatch):
    """POST /broker/orders stays blocked in fully configured live mode for MH-36B."""
    monkeypatch.setenv("LIVE_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("BROKER_MODE", "live")
    monkeypatch.setenv("IBKR_ACCOUNT_TYPE", "live")
    get_settings.cache_clear()

    response = client.post(
        "/broker/orders",
        json={"ticker": "AAPL", "side": "BUY", "quantity": 10, "order_type": "MARKET"},
    )

    assert response.status_code == 403
    assert "Live order submission" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_account_includes_broker_mode(client, mock_service):
    """GET /broker/account response must include broker_mode metadata."""
    expected_info = AccountInfo(
        net_liquidation=Decimal("100000"),
        cash_balance=Decimal("50000"),
        buying_power=Decimal("100000"),
    )
    with patch("app.api.routes.broker.get_broker_service") as mock_get_service:
        mock_service.get_account_info = AsyncMock(return_value=expected_info)
        mock_get_service.return_value = mock_service

        response = client.get("/broker/account")

    assert response.status_code == 200
    data = response.json()
    assert "broker_mode" in data
    bm = data["broker_mode"]
    assert bm["mode"] == "paper"
    assert bm["live_execution_enabled"] is False
    assert bm["paper_trading_enabled"] is True
    assert data["execution_source"] == "ibkr_paper"
    assert data["balance_source"] == "ibkr_paper"
    assert data["fees_source"] == "ibkr_reported"
    assert data["fills_source"] == "ibkr_paper"
    assert data["positions_source"] == "ibkr_paper"
    assert data["serious_paper_source"] == "ibkr_paper"
    assert data["is_canonical_paper"] is True


@pytest.mark.asyncio
async def test_submit_order_includes_broker_mode(client, mock_service):
    """POST /broker/orders success response must include broker_mode metadata."""
    order_result = OrderResult(broker_order_id="PAPER-001", status="SUBMITTED")
    with patch("app.api.routes.broker.get_broker_service") as mock_get_service:
        mock_service.submit_order = AsyncMock(return_value=order_result)
        mock_get_service.return_value = mock_service

        response = client.post(
            "/broker/orders",
            json={"ticker": "AAPL", "side": "BUY", "quantity": 10, "order_type": "MARKET"},
        )

    assert response.status_code == 200
    data = response.json()
    assert "broker_mode" in data
    assert data["broker_mode"]["mode"] == "paper"
    assert data["broker_mode"]["paper_trading_enabled"] is True
    assert data["execution_source"] == "ibkr_paper"
    assert data["balance_source"] == "ibkr_paper"
    assert data["fees_source"] == "ibkr_reported"
    assert data["fills_source"] == "ibkr_paper"
    assert data["positions_source"] == "ibkr_paper"
    assert data["serious_paper_source"] == "ibkr_paper"
    assert data["is_canonical_paper"] is True


@pytest.mark.asyncio
async def test_submit_order_returns_403_when_live_execution_enabled(client, monkeypatch):
    """POST /broker/orders must return HTTP 403 when LIVE_EXECUTION_ENABLED=true."""
    monkeypatch.setenv("LIVE_EXECUTION_ENABLED", "true")
    get_settings.cache_clear()

    response = client.post(
        "/broker/orders",
        json={"ticker": "AAPL", "side": "BUY", "quantity": 10, "order_type": "MARKET"},
    )

    assert response.status_code == 403
    assert "LIVE_EXECUTION_ENABLED" in response.json()["detail"]


@pytest.mark.asyncio
async def test_submit_order_returns_403_when_broker_mode_live(client, monkeypatch):
    """POST /broker/orders must return HTTP 403 when BROKER_MODE=live."""
    monkeypatch.setenv("BROKER_MODE", "live")
    get_settings.cache_clear()

    response = client.post(
        "/broker/orders",
        json={"ticker": "AAPL", "side": "BUY", "quantity": 10, "order_type": "MARKET"},
    )

    assert response.status_code == 403
    assert "BROKER_MODE" in response.json()["detail"]


@pytest.mark.asyncio
async def test_submit_order_returns_403_when_ibkr_account_type_live(client, monkeypatch):
    """POST /broker/orders must return HTTP 403 when IBKR_ACCOUNT_TYPE=live."""
    monkeypatch.setenv("IBKR_ACCOUNT_TYPE", "live")
    get_settings.cache_clear()

    response = client.post(
        "/broker/orders",
        json={"ticker": "AAPL", "side": "BUY", "quantity": 10, "order_type": "MARKET"},
    )

    assert response.status_code == 403
    assert "IBKR_ACCOUNT_TYPE" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_account_not_blocked_when_live_execution_enabled(client, mock_service, monkeypatch):
    """GET /broker/account must NOT be blocked even when live guard would trip for orders.

    Read-only paths are always allowed — only order submission is gated.
    """
    monkeypatch.setenv("LIVE_EXECUTION_ENABLED", "true")
    get_settings.cache_clear()

    expected_info = AccountInfo(
        net_liquidation=Decimal("100000"),
        cash_balance=Decimal("50000"),
        buying_power=Decimal("100000"),
    )
    with patch("app.api.routes.broker.get_broker_service") as mock_get_service:
        mock_service.get_account_info = AsyncMock(return_value=expected_info)
        mock_get_service.return_value = mock_service

        response = client.get("/broker/account")

    assert response.status_code == 200
    data = response.json()
    assert data["execution_source"] == "ibkr_paper"
    assert data["balance_source"] == "ibkr_paper"
    assert data["fees_source"] == "ibkr_reported"
    assert data["fills_source"] == "ibkr_paper"
    assert data["positions_source"] == "ibkr_paper"
    assert data["serious_paper_source"] == "ibkr_paper"
    assert data["is_canonical_paper"] is True


@pytest.mark.asyncio
async def test_get_positions_not_blocked_when_live_execution_enabled(client, mock_service, monkeypatch):
    """GET /broker/positions must NOT be blocked by live execution guard."""
    monkeypatch.setenv("LIVE_EXECUTION_ENABLED", "true")
    get_settings.cache_clear()

    with patch("app.api.routes.broker.get_broker_service") as mock_get_service:
        mock_service.get_positions = AsyncMock(return_value=[])
        mock_get_service.return_value = mock_service

        response = client.get("/broker/positions")

    assert response.status_code == 200

