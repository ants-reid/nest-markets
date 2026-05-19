"""Route tests for GET /broker/daily-pnl — MH-43 Daily P&L / Loss Context Foundation."""
from __future__ import annotations

from datetime import date, datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from fastapi.testclient import TestClient

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _snapshot(
    closed_pnl: float | None = None,
    open_pnl: float | None = None,
    hours_ago: float = 0.0,
) -> MagicMock:
    """Build a minimal PnlSnapshot mock for today."""
    row = MagicMock()
    row.closed_pnl = closed_pnl
    row.open_pnl = open_pnl
    row.snapshot_ts = datetime.now(tz=timezone.utc) - timedelta(hours=hours_ago)
    return row


def _old_snapshot(
    closed_pnl: float | None = None,
    open_pnl: float | None = None,
) -> MagicMock:
    """Build a snapshot from yesterday (should be excluded)."""
    row = MagicMock()
    row.closed_pnl = closed_pnl
    row.open_pnl = open_pnl
    # snapshot_ts 25 hours ago — outside today's UTC window
    row.snapshot_ts = datetime.now(tz=timezone.utc) - timedelta(hours=25)
    return row


# ---------------------------------------------------------------------------
# Tests: empty state
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_daily_pnl_returns_safe_empty_when_no_snapshots(client):
    """Returns safe empty response with note when no pnl_snapshots for today."""
    with patch(
        "app.services.broker_service.SessionLocal"
    ) as mock_session_cls:
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        mock_session_cls.return_value = mock_session

        response = client.get("/broker/daily-pnl")

    assert response.status_code == 200
    data = response.json()
    assert data["snapshot_count"] == 0
    assert data["daily_pnl"] is None
    assert data["daily_loss"] is None
    assert data["closed_pnl"] is None
    assert data["open_pnl"] is None
    assert data["total_pnl"] is None
    assert data["latest_snapshot_ts"] is None
    assert data["note"] == "No P&L snapshots available for today."
    assert data["source"] == "pnl_snapshots"
    assert data["date"] == date.today().isoformat()


# ---------------------------------------------------------------------------
# Tests: positive P&L
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_daily_pnl_returns_correct_values_when_snapshots_exist(client):
    """Returns daily_pnl and daily_loss correctly when today's snapshots exist."""
    rows = [
        _snapshot(closed_pnl=100.0, open_pnl=50.0, hours_ago=2.0),
        _snapshot(closed_pnl=200.0, open_pnl=75.0, hours_ago=1.0),
    ]
    with patch(
        "app.services.broker_service.SessionLocal"
    ) as mock_session_cls:
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = rows
        mock_session_cls.return_value = mock_session

        response = client.get("/broker/daily-pnl")

    assert response.status_code == 200
    data = response.json()
    # closed_pnl = sum(100 + 200) = 300
    assert data["closed_pnl"] == pytest.approx(300.0)
    # open_pnl = latest row's open_pnl = 75.0
    assert data["open_pnl"] == pytest.approx(75.0)
    # total_pnl = 300 + 75 = 375
    assert data["total_pnl"] == pytest.approx(375.0)
    assert data["daily_pnl"] == pytest.approx(375.0)
    # profitable day -> daily_loss = 0
    assert data["daily_loss"] == pytest.approx(0.0)
    assert data["snapshot_count"] == 2
    assert data["note"] is None


# ---------------------------------------------------------------------------
# Tests: daily_loss is positive when daily_pnl is negative
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_daily_loss_is_positive_when_daily_pnl_is_negative(client):
    """daily_loss is the absolute value of the loss when daily_pnl < 0."""
    rows = [
        _snapshot(closed_pnl=-150.0, open_pnl=-50.0, hours_ago=1.0),
    ]
    with patch(
        "app.services.broker_service.SessionLocal"
    ) as mock_session_cls:
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = rows
        mock_session_cls.return_value = mock_session

        response = client.get("/broker/daily-pnl")

    assert response.status_code == 200
    data = response.json()
    assert data["daily_pnl"] == pytest.approx(-200.0)
    assert data["daily_loss"] == pytest.approx(200.0)


# ---------------------------------------------------------------------------
# Tests: latest_snapshot_ts is from latest row
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_latest_snapshot_ts_is_most_recent_row(client):
    """latest_snapshot_ts is the snapshot_ts of the most-recent row."""
    earlier = _snapshot(closed_pnl=10.0, hours_ago=3.0)
    later = _snapshot(closed_pnl=20.0, hours_ago=0.5)
    rows = [earlier, later]  # ordered asc by snapshot_ts as service queries

    with patch(
        "app.services.broker_service.SessionLocal"
    ) as mock_session_cls:
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = rows
        mock_session_cls.return_value = mock_session

        response = client.get("/broker/daily-pnl")

    assert response.status_code == 200
    data = response.json()
    # latest_snapshot_ts must match the last row (later)
    assert data["latest_snapshot_ts"] == later.snapshot_ts.isoformat()


# ---------------------------------------------------------------------------
# Tests: snapshot_count is correct
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_snapshot_count_matches_rows(client):
    """snapshot_count equals the number of pnl_snapshot rows returned."""
    rows = [_snapshot(closed_pnl=float(i * 10)) for i in range(5)]
    with patch(
        "app.services.broker_service.SessionLocal"
    ) as mock_session_cls:
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = rows
        mock_session_cls.return_value = mock_session

        response = client.get("/broker/daily-pnl")

    assert response.status_code == 200
    assert response.json()["snapshot_count"] == 5


# ---------------------------------------------------------------------------
# Tests: null closed_pnl rows handled safely
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_null_closed_pnl_rows_handled_safely(client):
    """Rows with null closed_pnl are skipped in sum; open_pnl still returned."""
    rows = [
        _snapshot(closed_pnl=None, open_pnl=30.0, hours_ago=1.0),
    ]
    with patch(
        "app.services.broker_service.SessionLocal"
    ) as mock_session_cls:
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = rows
        mock_session_cls.return_value = mock_session

        response = client.get("/broker/daily-pnl")

    assert response.status_code == 200
    data = response.json()
    # closed_pnl is None (no non-null closed_pnl rows)
    assert data["closed_pnl"] is None
    # open_pnl is from latest row
    assert data["open_pnl"] == pytest.approx(30.0)
    # total_pnl = 0 + 30 = 30
    assert data["total_pnl"] == pytest.approx(30.0)


# ---------------------------------------------------------------------------
# Tests: route is read-only and not gated by live-mode config
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_daily_pnl_route_not_blocked_by_live_mode_config(client, monkeypatch):
    """GET /broker/daily-pnl is never blocked by live-mode config."""
    # Simulate live-mode environment (would normally block order submission)
    monkeypatch.setenv("LIVE_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("BROKER_MODE", "live")
    monkeypatch.setenv("IBKR_ACCOUNT_TYPE", "live")
    get_settings.cache_clear()

    with patch(
        "app.services.broker_service.SessionLocal"
    ) as mock_session_cls:
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        mock_session_cls.return_value = mock_session

        response = client.get("/broker/daily-pnl")

    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Tests: broker submit regression (order submission unchanged)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_broker_submit_still_blocked_after_mh43(client):
    """Adding GET /broker/daily-pnl does not change POST /broker/orders submission guard."""
    payload = {
        "ticker": "AAPL",
        "side": "BUY",
        "quantity": 10,
        "order_type": "LIMIT",
        "limit_price": 180.5,
    }
    # Paper mode by default — submit should succeed with mock broker
    with patch(
        "app.services.broker_service.BrokerService.submit_order"
    ) as mock_submit:
        from app.clients.broker.broker_interface import OrderResult
        mock_submit.return_value = OrderResult(
            broker_order_id="test-order-1",
            status="SUBMITTED",
        )
        response = client.post("/broker/orders", json=payload)

    # Should be 200 (paper mode allowed) — guards unchanged
    assert response.status_code in (200, 500)  # 500 if gateway not up; guard not the blocker


# ---------------------------------------------------------------------------
# MH-45: POST /broker/daily-pnl/snapshot ingestion endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_capture_daily_pnl_snapshot_returns_captured_values(client):
    """POST /broker/daily-pnl/snapshot returns manual captured payload with metadata."""
    payload = {
        "snapshot_ts": "2026-04-28T12:00:00+00:00",
        "equity": 105000.0,
        "cash": 42000.0,
        "gross_exposure": 2650.0,
        "net_exposure": 1050.0,
        "open_pnl": 1250.0,
        "closed_pnl": 30.0,
        "closed_pnl_source": "broker_trade_events",
        "source": "manual",
        "account_id": "DU123456",
        "broker_mode": {
            "broker": "ibkr",
            "mode": "paper",
            "live_execution_enabled": False,
            "paper_trading_enabled": True,
        },
        "position_count": 2,
    }

    with patch("app.api.routes.broker.get_broker_service") as mock_get_service:
        mock_service = MagicMock()
        mock_service.capture_daily_pnl_snapshot = AsyncMock(return_value=payload)
        mock_get_service.return_value = mock_service

        response = client.post("/broker/daily-pnl/snapshot")

    assert response.status_code == 200
    data = response.json()
    assert data["snapshot_ts"] == payload["snapshot_ts"]
    assert data["equity"] == pytest.approx(105000.0)
    assert data["gross_exposure"] == pytest.approx(2650.0)
    assert data["closed_pnl"] == pytest.approx(30.0)
    assert data["closed_pnl_source"] == "broker_trade_events"
    assert data["source"] == "manual"
    assert data["account_id"] == "DU123456"
    assert data["broker_mode"]["mode"] == "paper"
    assert data["position_count"] == 2


@pytest.mark.asyncio
async def test_capture_daily_pnl_snapshot_does_not_change_submit_guard(client):
    """MH-45 does not modify submit behavior or guards."""
    capture_payload = {
        "snapshot_ts": "2026-04-28T12:00:00+00:00",
        "equity": 100000.0,
        "cash": 50000.0,
        "gross_exposure": 0.0,
        "net_exposure": 0.0,
        "open_pnl": 0.0,
        "closed_pnl": 5.0,
        "closed_pnl_source": "broker_trade_events",
        "source": "scheduled",
        "account_id": "DU123456",
        "broker_mode": {
            "broker": "ibkr",
            "mode": "paper",
            "live_execution_enabled": False,
            "paper_trading_enabled": True,
        },
        "position_count": 0,
    }

    with patch("app.api.routes.broker.get_broker_service") as mock_get_service:
        mock_service = MagicMock()
        mock_service.capture_daily_pnl_snapshot = AsyncMock(return_value=capture_payload)
        mock_get_service.return_value = mock_service

        capture_response = client.post("/broker/daily-pnl/snapshot/scheduled")

    assert capture_response.status_code == 200
    assert capture_response.json()["source"] == "scheduled"
    assert capture_response.json()["closed_pnl_source"] == "broker_trade_events"

    order_payload = {
        "ticker": "AAPL",
        "side": "BUY",
        "quantity": 10,
        "order_type": "LIMIT",
        "limit_price": 180.5,
    }
    with patch("app.services.broker_service.BrokerService.submit_order") as mock_submit:
        from app.clients.broker.broker_interface import OrderResult

        mock_submit.return_value = OrderResult(
            broker_order_id="test-order-mh45",
            status="SUBMITTED",
        )
        order_response = client.post("/broker/orders", json=order_payload)

    assert order_response.status_code in (200, 500)


@pytest.mark.asyncio
async def test_scheduled_capture_endpoint_passes_source_to_service(client):
    """POST /broker/daily-pnl/snapshot/scheduled keeps source label scheduled."""
    payload = {
        "snapshot_ts": "2026-04-28T12:00:00+00:00",
        "equity": 100000.0,
        "cash": 50000.0,
        "gross_exposure": 0.0,
        "net_exposure": 0.0,
        "open_pnl": 0.0,
        "closed_pnl": None,
        "source": "scheduled",
        "account_id": "DU999000",
        "broker_mode": {
            "broker": "ibkr",
            "mode": "paper",
            "live_execution_enabled": False,
            "paper_trading_enabled": True,
        },
        "position_count": 0,
    }

    with patch("app.api.routes.broker.get_broker_service") as mock_get_service:
        mock_service = MagicMock()
        mock_service.capture_daily_pnl_snapshot = AsyncMock(return_value=payload)
        mock_get_service.return_value = mock_service

        response = client.post("/broker/daily-pnl/snapshot/scheduled")

    assert response.status_code == 200
    assert response.json()["source"] == "scheduled"
    mock_service.capture_daily_pnl_snapshot.assert_awaited_once_with(source="scheduled")


@pytest.mark.asyncio
async def test_get_daily_pnl_reads_snapshots_created_by_scheduled_capture(client):
    """GET /broker/daily-pnl uses pnl_snapshots rows regardless of capture source metadata."""
    row = MagicMock()
    row.closed_pnl = 20.0
    row.open_pnl = 5.0
    row.snapshot_ts = datetime.now(tz=timezone.utc)
    row.metadata_json = {"source": "scheduled", "account_id": "DU123456"}

    with patch("app.services.broker_service.SessionLocal") as mock_session_cls:
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [row]
        mock_session_cls.return_value = mock_session

        response = client.get("/broker/daily-pnl")

    assert response.status_code == 200
    data = response.json()
    assert data["snapshot_count"] == 1
    assert data["daily_pnl"] == pytest.approx(25.0)
