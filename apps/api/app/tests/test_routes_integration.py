"""Thin integration checks for core API routes mirrored by frontend smoke tests."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.routes import workflow as workflow_route
from app.api.routes import execution as execution_route
from app.db.base import Base
from app.db.enums import AssetClass
from app.db.models.approval_request import ApprovalRequest as ApprovalRequestModel
from app.db.models.asset import Asset
from app.db.models.paper_order import PaperOrder
from app.db.session import SessionLocal, engine, get_db_session
from app.main import app
from app.services.execution_journal_service import ExecutionJournalService
from app.services.signal_service import SignalOutput


def _signal_payload() -> dict:
    return {
        "asset": "EURUSD",
        "timeframe": "1h",
        "direction": "long",
        "regime": "trend",
        "setup_type": "trend_pullback",
        "entry_zone": [1.081, 1.082],
        "stop_price": 1.079,
        "target_price": 1.085,
        "confidence": 0.7,
        "horizon_label": "1_3_days",
        "catalyst_type": "macro",
        "catalyst_score": 0.6,
        "catalyst_summary": "Mock route integration signal",
        "thesis": "Thin route-level request payload",
        "invalidators": ["mock_invalidator"],
        "signal_score": 75.0,
        "should_trade": True,
    }


def _seed_asset(session: Session, symbol: str = "EURUSD") -> None:
    session.add(
        Asset(
            symbol=symbol,
            asset_class=AssetClass.FX,
            quote_currency="USD",
            is_active=True,
        )
    )
    session.commit()


@pytest.fixture()
def db_session() -> Session:
    schema_name = f"test_routes_{uuid4().hex}"

    admin_connection = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
    admin_connection.execute(text(f'CREATE SCHEMA "{schema_name}"'))
    admin_connection.close()

    connection = engine.connect()
    connection.execute(text(f'SET search_path TO "{schema_name}"'))
    connection.commit()
    Base.metadata.create_all(bind=connection)

    session = SessionLocal(bind=connection)
    _seed_asset(session)

    try:
        yield session
    finally:
        session.close()
        connection.close()
        admin_connection = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
        admin_connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))
        admin_connection.close()


@pytest.fixture()
def client(db_session: Session) -> TestClient:
    def _get_test_db_session():
        yield db_session

    app.dependency_overrides[get_db_session] = _get_test_db_session
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db_session, None)


def test_health_route(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json().get("status") == "ok"


def test_workflow_run_route_with_mock_signal(client: TestClient) -> None:
    response = client.post(
        "/workflow/run",
        json={
            "use_mock_signal": True,
            "signal_input": {
                "asset": "EURUSD",
                "timeframe": "1h",
                "latest_price": 1.0815,
                "feature_snapshot": {"source": "test"},
                "catalyst_context": {"mode": "mock"},
                "risk_notes": "Route integration test",
            },
            "risk_context": {
                "spread_bps": 10.0,
                "daily_drawdown_pct": 1.0,
                "consecutive_losses": 0,
                "minutes_since_last_loss": None,
                "correlated_exposure_count": 0,
                "open_positions_count": 0,
                "session_allowed": True,
                "kill_switch_active": False,
                "market_quality_flag": True,
                "account_equity": 50000.0,
                "requested_execution_mode": "paper",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert "selected_execution_mode" in payload
    assert "blocked_reasons" in payload
    assert isinstance(payload["blocked_reasons"], list)


def test_workflow_run_route_confirm_live_returns_approval_request_id(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _approved_mock_signal(
        self: workflow_route._MockSignalService,
        signal_input: workflow_route.SignalInput,
    ) -> SignalOutput:
        return SignalOutput(
            asset=signal_input.asset,
            timeframe=signal_input.timeframe,
            direction="long",
            regime="trend",
            setup_type="trend_pullback",
            entry_zone=(1.081, 1.082),
            stop_price=1.079,
            target_price=1.085,
            confidence=0.8,
            horizon_label="1_3_days",
            catalyst_type="macro",
            catalyst_score=0.6,
            catalyst_summary="Mock tradable signal for lifecycle route test.",
            thesis="Lifecycle routing validation",
            invalidators=["mock_invalidator"],
            signal_score=80.0,
            should_trade=True,
        )

    monkeypatch.setattr(
        workflow_route._MockSignalService,
        "generate_signal",
        _approved_mock_signal,
    )

    response = client.post(
        "/workflow/run",
        json={
            "use_mock_signal": True,
            "signal_input": {
                "asset": "EURUSD",
                "timeframe": "1h",
                "latest_price": 1.0815,
                "feature_snapshot": {"source": "test"},
                "catalyst_context": {"mode": "mock"},
                "risk_notes": "Route integration confirm-live lifecycle test",
            },
            "risk_context": {
                "spread_bps": 10.0,
                "daily_drawdown_pct": 1.0,
                "consecutive_losses": 0,
                "minutes_since_last_loss": None,
                "correlated_exposure_count": 0,
                "open_positions_count": 0,
                "session_allowed": True,
                "kill_switch_active": False,
                "market_quality_flag": True,
                "account_equity": 50000.0,
                "requested_execution_mode": "confirm_live",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["risk_approved"] is True
    assert payload["selected_execution_mode"] == "confirm_live"
    assert payload["approval_request_id"] is not None
    assert payload["paper_execution_id"] is None
    assert payload["live_execution_result"] is None


def test_workflow_run_route_auto_live_returns_disabled_live_result(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _approved_mock_signal(
        self: workflow_route._MockSignalService,
        signal_input: workflow_route.SignalInput,
    ) -> SignalOutput:
        return SignalOutput(
            asset=signal_input.asset,
            timeframe=signal_input.timeframe,
            direction="long",
            regime="trend",
            setup_type="trend_pullback",
            entry_zone=(1.081, 1.082),
            stop_price=1.079,
            target_price=1.085,
            confidence=0.8,
            horizon_label="1_3_days",
            catalyst_type="macro",
            catalyst_score=0.6,
            catalyst_summary="Mock tradable signal for lifecycle route test.",
            thesis="Lifecycle routing validation",
            invalidators=["mock_invalidator"],
            signal_score=80.0,
            should_trade=True,
        )

    monkeypatch.setattr(
        workflow_route._MockSignalService,
        "generate_signal",
        _approved_mock_signal,
    )

    response = client.post(
        "/workflow/run",
        json={
            "use_mock_signal": True,
            "signal_input": {
                "asset": "EURUSD",
                "timeframe": "1h",
                "latest_price": 1.0815,
                "feature_snapshot": {"source": "test"},
                "catalyst_context": {"mode": "mock"},
                "risk_notes": "Route integration auto-live lifecycle test",
            },
            "risk_context": {
                "spread_bps": 10.0,
                "daily_drawdown_pct": 1.0,
                "consecutive_losses": 0,
                "minutes_since_last_loss": None,
                "correlated_exposure_count": 0,
                "open_positions_count": 0,
                "session_allowed": True,
                "kill_switch_active": False,
                "market_quality_flag": True,
                "account_equity": 50000.0,
                "requested_execution_mode": "auto_live",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["risk_approved"] is True
    assert payload["selected_execution_mode"] == "auto_live"
    assert payload["approval_request_id"] is None
    assert payload["paper_execution_id"] is None
    assert payload["live_execution_result"] is not None
    assert payload["live_execution_result"]["status"] == "disabled"
    assert payload["live_execution_result"]["accepted"] is False
    assert payload["live_execution_result"]["reason"] == "live_execution_disabled_in_mvp"


def test_workflow_run_route_blocks_when_max_positions_exceeded(client: TestClient) -> None:
    response = client.post(
        "/workflow/run",
        json={
            "use_mock_signal": True,
            "signal_input": {
                "asset": "EURUSD",
                "timeframe": "1h",
                "latest_price": 1.0815,
                "feature_snapshot": {"source": "test"},
                "catalyst_context": {"mode": "mock"},
                "risk_notes": "Route integration test for open positions cap",
            },
            "risk_context": {
                "spread_bps": 10.0,
                "daily_drawdown_pct": 1.0,
                "consecutive_losses": 0,
                "minutes_since_last_loss": None,
                "correlated_exposure_count": 0,
                "open_positions_count": 6,
                "session_allowed": True,
                "kill_switch_active": False,
                "market_quality_flag": True,
                "account_equity": 50000.0,
                "requested_execution_mode": "paper",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["selected_execution_mode"] == "blocked"
    assert "max_open_positions_exceeded" in payload["blocked_reasons"]


def test_workflow_run_route_blocks_when_kill_switch_active(client: TestClient) -> None:
    response = client.post(
        "/workflow/run",
        json={
            "use_mock_signal": True,
            "signal_input": {
                "asset": "EURUSD",
                "timeframe": "1h",
                "latest_price": 1.0815,
                "feature_snapshot": {"source": "test"},
                "catalyst_context": {"mode": "mock"},
                "risk_notes": "Route integration test for kill switch gate",
            },
            "risk_context": {
                "spread_bps": 10.0,
                "daily_drawdown_pct": 1.0,
                "consecutive_losses": 0,
                "minutes_since_last_loss": None,
                "correlated_exposure_count": 0,
                "open_positions_count": 0,
                "session_allowed": True,
                "kill_switch_active": True,
                "market_quality_flag": True,
                "account_equity": 50000.0,
                "requested_execution_mode": "paper",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["selected_execution_mode"] == "blocked"
    assert "kill_switch_active" in payload["blocked_reasons"]


def test_workflow_run_route_stays_blocked_for_auto_live_when_risk_not_approved(
    client: TestClient,
) -> None:
    response = client.post(
        "/workflow/run",
        json={
            "use_mock_signal": True,
            "signal_input": {
                "asset": "EURUSD",
                "timeframe": "1h",
                "latest_price": 1.0815,
                "feature_snapshot": {"source": "test"},
                "catalyst_context": {"mode": "mock"},
                "risk_notes": "Route integration auto-live blocked invariance test",
            },
            "risk_context": {
                "spread_bps": 10.0,
                "daily_drawdown_pct": 1.0,
                "consecutive_losses": 0,
                "minutes_since_last_loss": None,
                "correlated_exposure_count": 0,
                "open_positions_count": 0,
                "session_allowed": True,
                "kill_switch_active": True,
                "market_quality_flag": True,
                "account_equity": 50000.0,
                "requested_execution_mode": "auto_live",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["risk_approved"] is False
    assert payload["selected_execution_mode"] == "blocked"
    assert "kill_switch_active" in payload["blocked_reasons"]
    assert payload["approval_request_id"] is None
    assert payload["paper_execution_id"] is None
    assert payload["live_execution_result"] is None


def test_workflow_run_route_blocks_when_session_not_allowed(client: TestClient) -> None:
    response = client.post(
        "/workflow/run",
        json={
            "use_mock_signal": True,
            "signal_input": {
                "asset": "EURUSD",
                "timeframe": "1h",
                "latest_price": 1.0815,
                "feature_snapshot": {"source": "test"},
                "catalyst_context": {"mode": "mock"},
                "risk_notes": "Route integration test for session gate",
            },
            "risk_context": {
                "spread_bps": 10.0,
                "daily_drawdown_pct": 1.0,
                "consecutive_losses": 0,
                "minutes_since_last_loss": None,
                "correlated_exposure_count": 0,
                "open_positions_count": 0,
                "session_allowed": False,
                "kill_switch_active": False,
                "market_quality_flag": True,
                "account_equity": 50000.0,
                "requested_execution_mode": "paper",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["selected_execution_mode"] == "blocked"
    assert "session_not_allowed" in payload["blocked_reasons"]


def test_signals_mock_generate_route(client: TestClient) -> None:
    response = client.post(
        "/signals/mock-generate",
        json={
            "asset": "EURUSD",
            "timeframe": "1h",
            "latest_price": 1.0815,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["asset"] == "EURUSD"
    assert payload["timeframe"] == "1h"


def test_signals_generate_route_with_mocked_llm(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """QA-013: POST /signals/generate returns SignalResponse shape when LLM is mocked."""
    from app.api.routes import signals as signals_route

    async def _mock_generate(self, signal_input):
        return SignalOutput(
            asset=signal_input.asset,
            timeframe=signal_input.timeframe,
            direction="long",
            regime="trend",
            setup_type="trend_pullback",
            entry_zone=(1.081, 1.082),
            stop_price=1.079,
            target_price=1.085,
            confidence=0.75,
            horizon_label="1_3_days",
            catalyst_type="macro",
            catalyst_score=0.6,
            catalyst_summary="Mocked LLM signal for route test.",
            thesis="Route-level test with mocked LLM provider.",
            invalidators=["mock_invalidator"],
            signal_score=77.0,
            should_trade=True,
        )

    monkeypatch.setattr(signals_route.SignalService, "generate_signal", _mock_generate)

    response = client.post(
        "/signals/generate",
        json={
            "asset": "EURUSD",
            "timeframe": "1h",
            "latest_price": 1.0815,
            "feature_snapshot": {"source": "test"},
            "catalyst_context": {"mode": "mock"},
            "risk_notes": "BP-05.03 route test",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["asset"] == "EURUSD"
    assert payload["direction"] == "long"
    assert payload["confidence"] == 0.75
    assert "signal_score" in payload
    assert "thesis" in payload


def test_risk_evaluate_route(client: TestClient) -> None:
    response = client.post(
        "/risk/evaluate",
        json={
            "signal": _signal_payload(),
            "risk_context": {
                "spread_bps": 10.0,
                "daily_drawdown_pct": 1.0,
                "consecutive_losses": 0,
                "minutes_since_last_loss": None,
                "correlated_exposure_count": 0,
                "open_positions_count": 0,
                "session_allowed": True,
                "kill_switch_active": False,
                "market_quality_flag": True,
                "account_equity": 50000.0,
                "requested_execution_mode": "paper",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload.get("approved"), bool)
    assert "selected_execution_mode" in payload


def test_risk_evaluate_route_blocks_when_session_not_allowed(client: TestClient) -> None:
    response = client.post(
        "/risk/evaluate",
        json={
            "signal": _signal_payload(),
            "risk_context": {
                "spread_bps": 10.0,
                "daily_drawdown_pct": 1.0,
                "consecutive_losses": 0,
                "minutes_since_last_loss": None,
                "correlated_exposure_count": 0,
                "open_positions_count": 0,
                "session_allowed": False,
                "kill_switch_active": False,
                "market_quality_flag": True,
                "account_equity": 50000.0,
                "requested_execution_mode": "paper",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["approved"] is False
    assert "session_not_allowed" in payload["blocked_reasons"]


def test_risk_evaluate_route_blocks_with_multiple_reasons_when_session_not_allowed_and_kill_switch_active(
    client: TestClient,
) -> None:
    response = client.post(
        "/risk/evaluate",
        json={
            "signal": _signal_payload(),
            "risk_context": {
                "spread_bps": 10.0,
                "daily_drawdown_pct": 1.0,
                "consecutive_losses": 0,
                "minutes_since_last_loss": None,
                "correlated_exposure_count": 0,
                "open_positions_count": 0,
                "session_allowed": False,
                "kill_switch_active": True,
                "market_quality_flag": True,
                "account_equity": 50000.0,
                "requested_execution_mode": "paper",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["approved"] is False
    assert "session_not_allowed" in payload["blocked_reasons"]
    assert "kill_switch_active" in payload["blocked_reasons"]
    assert payload["selected_execution_mode"] == "blocked"


def test_risk_evaluate_route_blocks_when_max_positions_exceeded(client: TestClient) -> None:
    response = client.post(
        "/risk/evaluate",
        json={
            "signal": _signal_payload(),
            "risk_context": {
                "spread_bps": 10.0,
                "daily_drawdown_pct": 1.0,
                "consecutive_losses": 0,
                "minutes_since_last_loss": None,
                "correlated_exposure_count": 0,
                "open_positions_count": 6,
                "session_allowed": True,
                "kill_switch_active": False,
                "market_quality_flag": True,
                "account_equity": 50000.0,
                "requested_execution_mode": "paper",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["approved"] is False
    assert "max_open_positions_exceeded" in payload["blocked_reasons"]
    assert payload["selected_execution_mode"] == "blocked"


def test_risk_evaluate_route_blocks_with_multiple_reasons_when_session_not_allowed_kill_switch_active_and_max_positions_exceeded(
    client: TestClient,
) -> None:
    response = client.post(
        "/risk/evaluate",
        json={
            "signal": _signal_payload(),
            "risk_context": {
                "spread_bps": 10.0,
                "daily_drawdown_pct": 1.0,
                "consecutive_losses": 0,
                "minutes_since_last_loss": None,
                "correlated_exposure_count": 0,
                "open_positions_count": 6,
                "session_allowed": False,
                "kill_switch_active": True,
                "market_quality_flag": True,
                "account_equity": 50000.0,
                "requested_execution_mode": "paper",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["approved"] is False
    assert "session_not_allowed" in payload["blocked_reasons"]
    assert "kill_switch_active" in payload["blocked_reasons"]
    assert "max_open_positions_exceeded" in payload["blocked_reasons"]
    assert payload["selected_execution_mode"] == "blocked"


def test_risk_evaluate_route_blocks_when_spread_above_cap(client: TestClient) -> None:
    response = client.post(
        "/risk/evaluate",
        json={
            "signal": _signal_payload(),
            "risk_context": {
                "spread_bps": 40.0,
                "daily_drawdown_pct": 1.0,
                "consecutive_losses": 0,
                "minutes_since_last_loss": None,
                "correlated_exposure_count": 0,
                "open_positions_count": 0,
                "session_allowed": True,
                "kill_switch_active": False,
                "market_quality_flag": True,
                "account_equity": 50000.0,
                "requested_execution_mode": "paper",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["approved"] is False
    assert "spread_above_cap" in payload["blocked_reasons"]
    assert payload["selected_execution_mode"] == "blocked"


def test_risk_evaluate_route_blocks_when_daily_drawdown_exceeded(client: TestClient) -> None:
    response = client.post(
        "/risk/evaluate",
        json={
            "signal": _signal_payload(),
            "risk_context": {
                "spread_bps": 10.0,
                "daily_drawdown_pct": 2.5,
                "consecutive_losses": 0,
                "minutes_since_last_loss": None,
                "correlated_exposure_count": 0,
                "open_positions_count": 0,
                "session_allowed": True,
                "kill_switch_active": False,
                "market_quality_flag": True,
                "account_equity": 50000.0,
                "requested_execution_mode": "paper",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["approved"] is False
    assert "daily_drawdown_exceeded" in payload["blocked_reasons"]
    assert payload["selected_execution_mode"] == "blocked"


def test_risk_evaluate_route_blocks_when_cooldown_active(client: TestClient) -> None:
    response = client.post(
        "/risk/evaluate",
        json={
            "signal": _signal_payload(),
            "risk_context": {
                "spread_bps": 10.0,
                "daily_drawdown_pct": 1.0,
                "consecutive_losses": 3,
                "minutes_since_last_loss": 60,
                "correlated_exposure_count": 0,
                "open_positions_count": 0,
                "session_allowed": True,
                "kill_switch_active": False,
                "market_quality_flag": True,
                "account_equity": 50000.0,
                "requested_execution_mode": "paper",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["approved"] is False
    assert "cooldown_active" in payload["blocked_reasons"]
    assert payload["selected_execution_mode"] == "blocked"


def test_risk_evaluate_route_blocks_with_multiple_reasons_when_daily_drawdown_exceeded_and_cooldown_active(
    client: TestClient,
) -> None:
    response = client.post(
        "/risk/evaluate",
        json={
            "signal": _signal_payload(),
            "risk_context": {
                "spread_bps": 10.0,
                "daily_drawdown_pct": 2.5,
                "consecutive_losses": 3,
                "minutes_since_last_loss": 60,
                "correlated_exposure_count": 0,
                "open_positions_count": 0,
                "session_allowed": True,
                "kill_switch_active": False,
                "market_quality_flag": True,
                "account_equity": 50000.0,
                "requested_execution_mode": "paper",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["approved"] is False
    assert "daily_drawdown_exceeded" in payload["blocked_reasons"]
    assert "cooldown_active" in payload["blocked_reasons"]
    assert payload["selected_execution_mode"] == "blocked"


def test_risk_evaluate_route_allows_when_cooldown_threshold_has_expired(client: TestClient) -> None:
    response = client.post(
        "/risk/evaluate",
        json={
            "signal": _signal_payload(),
            "risk_context": {
                "spread_bps": 10.0,
                "daily_drawdown_pct": 1.0,
                "consecutive_losses": 3,
                "minutes_since_last_loss": 180,
                "correlated_exposure_count": 0,
                "open_positions_count": 0,
                "session_allowed": True,
                "kill_switch_active": False,
                "market_quality_flag": True,
                "account_equity": 50000.0,
                "requested_execution_mode": "paper",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["approved"] is True
    assert "cooldown_active" not in payload["blocked_reasons"]
    assert payload["selected_execution_mode"] == "paper"


def test_risk_evaluate_route_blocks_when_cooldown_active_with_null_minutes(client: TestClient) -> None:
    response = client.post(
        "/risk/evaluate",
        json={
            "signal": _signal_payload(),
            "risk_context": {
                "spread_bps": 10.0,
                "daily_drawdown_pct": 1.0,
                "consecutive_losses": 3,
                "minutes_since_last_loss": None,
                "correlated_exposure_count": 0,
                "open_positions_count": 0,
                "session_allowed": True,
                "kill_switch_active": False,
                "market_quality_flag": True,
                "account_equity": 50000.0,
                "requested_execution_mode": "paper",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["approved"] is False
    assert "cooldown_active" in payload["blocked_reasons"]
    assert payload["selected_execution_mode"] == "blocked"


def test_risk_evaluate_route_allows_when_consecutive_losses_below_threshold_with_null_minutes(
    client: TestClient,
) -> None:
    response = client.post(
        "/risk/evaluate",
        json={
            "signal": _signal_payload(),
            "risk_context": {
                "spread_bps": 10.0,
                "daily_drawdown_pct": 1.0,
                "consecutive_losses": 2,
                "minutes_since_last_loss": None,
                "correlated_exposure_count": 0,
                "open_positions_count": 0,
                "session_allowed": True,
                "kill_switch_active": False,
                "market_quality_flag": True,
                "account_equity": 50000.0,
                "requested_execution_mode": "paper",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["approved"] is True
    assert "cooldown_active" not in payload["blocked_reasons"]
    assert payload["selected_execution_mode"] == "paper"


def test_risk_evaluate_route_blocks_when_kill_switch_active(client: TestClient) -> None:
    response = client.post(
        "/risk/evaluate",
        json={
            "signal": _signal_payload(),
            "risk_context": {
                "spread_bps": 10.0,
                "daily_drawdown_pct": 1.0,
                "consecutive_losses": 0,
                "minutes_since_last_loss": None,
                "correlated_exposure_count": 0,
                "open_positions_count": 0,
                "session_allowed": True,
                "kill_switch_active": True,
                "market_quality_flag": True,
                "account_equity": 50000.0,
                "requested_execution_mode": "paper",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["approved"] is False
    assert "kill_switch_active" in payload["blocked_reasons"]
    assert payload["selected_execution_mode"] == "blocked"


def test_risk_evaluate_route_blocks_when_market_quality_flag_is_false(client: TestClient) -> None:
    response = client.post(
        "/risk/evaluate",
        json={
            "signal": _signal_payload(),
            "risk_context": {
                "spread_bps": 10.0,
                "daily_drawdown_pct": 1.0,
                "consecutive_losses": 0,
                "minutes_since_last_loss": None,
                "correlated_exposure_count": 0,
                "open_positions_count": 0,
                "session_allowed": True,
                "kill_switch_active": False,
                "market_quality_flag": False,
                "account_equity": 50000.0,
                "requested_execution_mode": "paper",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["approved"] is False
    assert "market_quality_bad" in payload["blocked_reasons"]
    assert payload["selected_execution_mode"] == "blocked"


def test_risk_evaluate_route_blocks_when_correlated_exposure_exceeded(client: TestClient) -> None:
    response = client.post(
        "/risk/evaluate",
        json={
            "signal": _signal_payload(),
            "risk_context": {
                "spread_bps": 10.0,
                "daily_drawdown_pct": 1.0,
                "consecutive_losses": 0,
                "minutes_since_last_loss": None,
                "correlated_exposure_count": 2,
                "open_positions_count": 0,
                "session_allowed": True,
                "kill_switch_active": False,
                "market_quality_flag": True,
                "account_equity": 50000.0,
                "requested_execution_mode": "paper",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["approved"] is False
    assert "correlated_exposure_exceeded" in payload["blocked_reasons"]
    assert payload["selected_execution_mode"] == "blocked"


def test_risk_evaluate_route_blocks_with_multiple_reasons_when_max_positions_exceeded_and_correlated_exposure_exceeded(
    client: TestClient,
) -> None:
    response = client.post(
        "/risk/evaluate",
        json={
            "signal": _signal_payload(),
            "risk_context": {
                "spread_bps": 10.0,
                "daily_drawdown_pct": 1.0,
                "consecutive_losses": 0,
                "minutes_since_last_loss": None,
                "correlated_exposure_count": 2,
                "open_positions_count": 6,
                "session_allowed": True,
                "kill_switch_active": False,
                "market_quality_flag": True,
                "account_equity": 50000.0,
                "requested_execution_mode": "paper",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["approved"] is False
    assert "max_open_positions_exceeded" in payload["blocked_reasons"]
    assert "correlated_exposure_exceeded" in payload["blocked_reasons"]
    assert payload["selected_execution_mode"] == "blocked"


def test_risk_evaluate_route_blocks_when_confidence_below_threshold(client: TestClient) -> None:
    signal = _signal_payload()
    signal["confidence"] = 0.4

    response = client.post(
        "/risk/evaluate",
        json={
            "signal": signal,
            "risk_context": {
                "spread_bps": 10.0,
                "daily_drawdown_pct": 1.0,
                "consecutive_losses": 0,
                "minutes_since_last_loss": None,
                "correlated_exposure_count": 0,
                "open_positions_count": 0,
                "session_allowed": True,
                "kill_switch_active": False,
                "market_quality_flag": True,
                "account_equity": 50000.0,
                "requested_execution_mode": "paper",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["approved"] is False
    assert "confidence_below_threshold" in payload["blocked_reasons"]
    assert payload["selected_execution_mode"] == "blocked"


def test_risk_evaluate_route_blocks_when_signal_score_below_threshold(client: TestClient) -> None:
    signal = _signal_payload()
    signal["signal_score"] = 40.0

    response = client.post(
        "/risk/evaluate",
        json={
            "signal": signal,
            "risk_context": {
                "spread_bps": 10.0,
                "daily_drawdown_pct": 1.0,
                "consecutive_losses": 0,
                "minutes_since_last_loss": None,
                "correlated_exposure_count": 0,
                "open_positions_count": 0,
                "session_allowed": True,
                "kill_switch_active": False,
                "market_quality_flag": True,
                "account_equity": 50000.0,
                "requested_execution_mode": "paper",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["approved"] is False
    assert "signal_score_below_threshold" in payload["blocked_reasons"]
    assert payload["selected_execution_mode"] == "blocked"


def test_risk_evaluate_route_blocks_when_direction_is_flat(client: TestClient) -> None:
    signal = _signal_payload()
    signal["direction"] = "flat"

    response = client.post(
        "/risk/evaluate",
        json={
            "signal": signal,
            "risk_context": {
                "spread_bps": 10.0,
                "daily_drawdown_pct": 1.0,
                "consecutive_losses": 0,
                "minutes_since_last_loss": None,
                "correlated_exposure_count": 0,
                "open_positions_count": 0,
                "session_allowed": True,
                "kill_switch_active": False,
                "market_quality_flag": True,
                "account_equity": 50000.0,
                "requested_execution_mode": "paper",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["approved"] is False
    assert "signal_not_actionable" in payload["blocked_reasons"]
    assert payload["selected_execution_mode"] == "blocked"


def test_risk_evaluate_route_blocks_when_should_trade_is_false(client: TestClient) -> None:
    signal = _signal_payload()
    signal["should_trade"] = False

    response = client.post(
        "/risk/evaluate",
        json={
            "signal": signal,
            "risk_context": {
                "spread_bps": 10.0,
                "daily_drawdown_pct": 1.0,
                "consecutive_losses": 0,
                "minutes_since_last_loss": None,
                "correlated_exposure_count": 0,
                "open_positions_count": 0,
                "session_allowed": True,
                "kill_switch_active": False,
                "market_quality_flag": True,
                "account_equity": 50000.0,
                "requested_execution_mode": "paper",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["approved"] is False
    assert "signal_not_actionable" in payload["blocked_reasons"]
    assert payload["selected_execution_mode"] == "blocked"


def test_risk_evaluate_route_blocks_with_multiple_reasons_when_should_trade_is_false_and_spread_above_cap(
    client: TestClient,
) -> None:
    signal = _signal_payload()
    signal["should_trade"] = False

    response = client.post(
        "/risk/evaluate",
        json={
            "signal": signal,
            "risk_context": {
                "spread_bps": 40.0,
                "daily_drawdown_pct": 1.0,
                "consecutive_losses": 0,
                "minutes_since_last_loss": None,
                "correlated_exposure_count": 0,
                "open_positions_count": 0,
                "session_allowed": True,
                "kill_switch_active": False,
                "market_quality_flag": True,
                "account_equity": 50000.0,
                "requested_execution_mode": "paper",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["approved"] is False
    assert "signal_not_actionable" in payload["blocked_reasons"]
    assert "spread_above_cap" in payload["blocked_reasons"]
    assert payload["selected_execution_mode"] == "blocked"


def test_risk_evaluate_route_blocks_when_account_equity_is_zero(client: TestClient) -> None:
    response = client.post(
        "/risk/evaluate",
        json={
            "signal": _signal_payload(),
            "risk_context": {
                "spread_bps": 10.0,
                "daily_drawdown_pct": 1.0,
                "consecutive_losses": 0,
                "minutes_since_last_loss": None,
                "correlated_exposure_count": 0,
                "open_positions_count": 0,
                "session_allowed": True,
                "kill_switch_active": False,
                "market_quality_flag": True,
                "account_equity": 0.0,
                "requested_execution_mode": "paper",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["approved"] is False
    assert "capital_or_risk_limit_block" in payload["blocked_reasons"]
    assert payload["selected_execution_mode"] == "blocked"


def test_approvals_create_route(client: TestClient) -> None:
    response = client.post(
        "/approvals/create",
        json={
            "signal": _signal_payload(),
            "execution_mode": "confirm_live",
            "risk_approved": True,
            "ttl_minutes": 30,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert "request_id" in payload
    assert payload["status"] == "pending"


def test_approvals_approve_route_transitions_pending_to_approved(
    client: TestClient,
    db_session: Session,
) -> None:
    create_response = client.post(
        "/approvals/create",
        json={
            "signal": _signal_payload(),
            "execution_mode": "confirm_live",
            "risk_approved": True,
            "ttl_minutes": 30,
        },
    )
    assert create_response.status_code == 200

    request_id = create_response.json()["request_id"]

    response = client.post(f"/approvals/{request_id}/approve")

    assert response.status_code == 200
    payload = response.json()
    assert payload["request_id"] == request_id
    assert payload["status"] == "approved"

    persisted = db_session.get(ApprovalRequestModel, request_id)
    assert persisted is not None
    assert persisted.status.value == "approved"

    invalid_response = client.post(f"/approvals/{request_id}/approve")
    assert invalid_response.status_code == 400
    assert "Invalid transition" in invalid_response.json()["detail"]


def test_approvals_reject_route_transitions_pending_to_rejected(
    client: TestClient,
    db_session: Session,
) -> None:
    create_response = client.post(
        "/approvals/create",
        json={
            "signal": _signal_payload(),
            "execution_mode": "confirm_live",
            "risk_approved": True,
            "ttl_minutes": 30,
        },
    )
    assert create_response.status_code == 200

    request_id = create_response.json()["request_id"]

    response = client.post(f"/approvals/{request_id}/reject")

    assert response.status_code == 200
    payload = response.json()
    assert payload["request_id"] == request_id
    assert payload["status"] == "rejected"

    persisted = db_session.get(ApprovalRequestModel, request_id)
    assert persisted is not None
    assert persisted.status.value == "rejected"


def test_approvals_expire_route_transitions_pending_to_expired(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _approved_mock_signal(
        self: workflow_route._MockSignalService,
        signal_input: workflow_route.SignalInput,
    ) -> SignalOutput:
        return SignalOutput(
            asset=signal_input.asset,
            timeframe=signal_input.timeframe,
            direction="long",
            regime="trend",
            setup_type="trend_pullback",
            entry_zone=(1.081, 1.082),
            stop_price=1.079,
            target_price=1.085,
            confidence=0.8,
            horizon_label="1_3_days",
            catalyst_type="macro",
            catalyst_score=0.6,
            catalyst_summary="Mock tradable signal for approval action route test.",
            thesis="Approval action routing validation",
            invalidators=["mock_invalidator"],
            signal_score=80.0,
            should_trade=True,
        )

    monkeypatch.setattr(
        workflow_route._MockSignalService,
        "generate_signal",
        _approved_mock_signal,
    )

    create_response = client.post(
        "/workflow/run",
        json={
            "use_mock_signal": True,
            "signal_input": {
                "asset": "EURUSD",
                "timeframe": "1h",
                "latest_price": 1.0815,
                "feature_snapshot": {"source": "test"},
                "catalyst_context": {"mode": "mock"},
                "risk_notes": "Route integration approval expire lifecycle test",
            },
            "risk_context": {
                "spread_bps": 10.0,
                "daily_drawdown_pct": 1.0,
                "consecutive_losses": 0,
                "minutes_since_last_loss": None,
                "correlated_exposure_count": 0,
                "open_positions_count": 0,
                "session_allowed": True,
                "kill_switch_active": False,
                "market_quality_flag": True,
                "account_equity": 50000.0,
                "requested_execution_mode": "confirm_live",
            },
        },
    )

    request_id = create_response.json()["approval_request_id"]
    persisted = db_session.get(ApprovalRequestModel, request_id)
    assert persisted is not None
    persisted.expires_at = persisted.requested_at
    db_session.commit()

    response = client.post(f"/approvals/{request_id}/expire")

    assert response.status_code == 200
    payload = response.json()
    assert payload["request_id"] == request_id
    assert payload["status"] == "expired"

    refreshed = db_session.get(ApprovalRequestModel, request_id)
    assert refreshed is not None
    assert refreshed.status.value == "expired"


def test_approvals_execute_route_runs_paper_execution_for_approved_request(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _approved_mock_signal(
        self: workflow_route._MockSignalService,
        signal_input: workflow_route.SignalInput,
    ) -> SignalOutput:
        return SignalOutput(
            asset=signal_input.asset,
            timeframe=signal_input.timeframe,
            direction="long",
            regime="trend",
            setup_type="trend_pullback",
            entry_zone=(1.081, 1.082),
            stop_price=1.079,
            target_price=1.085,
            confidence=0.8,
            horizon_label="1_3_days",
            catalyst_type="macro",
            catalyst_score=0.6,
            catalyst_summary="Mock tradable signal for approval execute route test.",
            thesis="Approval execute routing validation",
            invalidators=["mock_invalidator"],
            signal_score=80.0,
            should_trade=True,
        )

    monkeypatch.setattr(
        workflow_route._MockSignalService,
        "generate_signal",
        _approved_mock_signal,
    )

    create_response = client.post(
        "/workflow/run",
        json={
            "use_mock_signal": True,
            "signal_input": {
                "asset": "EURUSD",
                "timeframe": "1h",
                "latest_price": 1.0815,
                "feature_snapshot": {"source": "test"},
                "catalyst_context": {"mode": "mock"},
                "risk_notes": "Route integration approval execute success test",
            },
            "risk_context": {
                "spread_bps": 10.0,
                "daily_drawdown_pct": 1.0,
                "consecutive_losses": 0,
                "minutes_since_last_loss": None,
                "correlated_exposure_count": 0,
                "open_positions_count": 0,
                "session_allowed": True,
                "kill_switch_active": False,
                "market_quality_flag": True,
                "account_equity": 50000.0,
                "requested_execution_mode": "confirm_live",
            },
        },
    )
    request_id = create_response.json()["approval_request_id"]
    approval_row = db_session.get(ApprovalRequestModel, request_id)
    assert approval_row is not None

    approve_response = client.post(f"/approvals/{request_id}/approve")
    assert approve_response.status_code == 200

    response = client.post(f"/approvals/{request_id}/execute")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "submitted"
    assert payload["qty"] > 0
    assert payload["notional"] > 0

    persisted_orders = (
        db_session.query(PaperOrder).filter(PaperOrder.signal_id == approval_row.signal_id).all()
    )
    assert len(persisted_orders) == 1


def test_approvals_execute_route_rejects_non_approved_request(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _approved_mock_signal(
        self: workflow_route._MockSignalService,
        signal_input: workflow_route.SignalInput,
    ) -> SignalOutput:
        return SignalOutput(
            asset=signal_input.asset,
            timeframe=signal_input.timeframe,
            direction="long",
            regime="trend",
            setup_type="trend_pullback",
            entry_zone=(1.081, 1.082),
            stop_price=1.079,
            target_price=1.085,
            confidence=0.8,
            horizon_label="1_3_days",
            catalyst_type="macro",
            catalyst_score=0.6,
            catalyst_summary="Mock tradable signal for approval execute route test.",
            thesis="Approval execute routing validation",
            invalidators=["mock_invalidator"],
            signal_score=80.0,
            should_trade=True,
        )

    monkeypatch.setattr(
        workflow_route._MockSignalService,
        "generate_signal",
        _approved_mock_signal,
    )

    create_response = client.post(
        "/workflow/run",
        json={
            "use_mock_signal": True,
            "signal_input": {
                "asset": "EURUSD",
                "timeframe": "1h",
                "latest_price": 1.0815,
                "feature_snapshot": {"source": "test"},
                "catalyst_context": {"mode": "mock"},
                "risk_notes": "Route integration approval execute invalid-status test",
            },
            "risk_context": {
                "spread_bps": 10.0,
                "daily_drawdown_pct": 1.0,
                "consecutive_losses": 0,
                "minutes_since_last_loss": None,
                "correlated_exposure_count": 0,
                "open_positions_count": 0,
                "session_allowed": True,
                "kill_switch_active": False,
                "market_quality_flag": True,
                "account_equity": 50000.0,
                "requested_execution_mode": "confirm_live",
            },
        },
    )
    request_id = create_response.json()["approval_request_id"]
    approval_row = db_session.get(ApprovalRequestModel, request_id)
    assert approval_row is not None

    response = client.post(f"/approvals/{request_id}/execute")

    assert response.status_code == 400
    assert "must be approved" in response.json()["detail"]

    persisted_orders = (
        db_session.query(PaperOrder).filter(PaperOrder.signal_id == approval_row.signal_id).all()
    )
    assert len(persisted_orders) == 0


def test_execution_paper_route(client: TestClient) -> None:
    response = client.post(
        "/execution/paper",
        json={
            "signal": _signal_payload(),
            "allowed_risk_amount": 250.0,
            "latest_price": 1.0815,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert "execution_id" in payload
    assert "status" in payload


def _create_submitted_paper_order(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> PaperOrder:
    async def _approved_mock_signal(
        self: workflow_route._MockSignalService,
        signal_input: workflow_route.SignalInput,
    ) -> SignalOutput:
        return SignalOutput(
            asset=signal_input.asset,
            timeframe=signal_input.timeframe,
            direction="long",
            regime="trend",
            setup_type="trend_pullback",
            entry_zone=(1.081, 1.082),
            stop_price=1.079,
            target_price=1.085,
            confidence=0.8,
            horizon_label="1_3_days",
            catalyst_type="macro",
            catalyst_score=0.6,
            catalyst_summary="Mock tradable signal for paper lifecycle route test.",
            thesis="Paper lifecycle routing validation",
            invalidators=["mock_invalidator"],
            signal_score=80.0,
            should_trade=True,
        )

    monkeypatch.setattr(
        workflow_route._MockSignalService,
        "generate_signal",
        _approved_mock_signal,
    )

    response = client.post(
        "/workflow/run",
        json={
            "use_mock_signal": True,
            "signal_input": {
                "asset": "EURUSD",
                "timeframe": "1h",
                "latest_price": 1.0815,
                "feature_snapshot": {"source": "test"},
                "catalyst_context": {"mode": "mock"},
                "risk_notes": "Route integration paper fill/close lifecycle test",
            },
            "risk_context": {
                "spread_bps": 10.0,
                "daily_drawdown_pct": 1.0,
                "consecutive_losses": 0,
                "minutes_since_last_loss": None,
                "correlated_exposure_count": 0,
                "open_positions_count": 0,
                "session_allowed": True,
                "kill_switch_active": False,
                "market_quality_flag": True,
                "account_equity": 50000.0,
                "requested_execution_mode": "paper",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["selected_execution_mode"] == "paper"
    assert payload["paper_execution_id"] is not None

    order = db_session.get(PaperOrder, payload["paper_execution_id"])
    assert order is not None
    return order


def test_execution_paper_fill_route_transitions_submitted_to_filled(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    submitted_order = _create_submitted_paper_order(client, db_session, monkeypatch)

    response = client.post(f"/execution/paper/{submitted_order.id}/fill")

    assert response.status_code == 200
    payload = response.json()
    assert payload["execution_id"] == str(submitted_order.id)
    assert payload["status"] == "filled"

    refreshed = db_session.get(PaperOrder, submitted_order.id)
    assert refreshed is not None
    assert refreshed.id == submitted_order.id
    assert refreshed.status.value == "filled"
    assert refreshed.submitted_at is not None

    invalid_response = client.post(f"/execution/paper/{submitted_order.id}/fill")
    assert invalid_response.status_code == 400
    assert "Only submitted paper orders can be filled" in invalid_response.json()["detail"]


def test_execution_paper_close_route_transitions_filled_to_closed(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    submitted_order = _create_submitted_paper_order(client, db_session, monkeypatch)

    fill_response = client.post(f"/execution/paper/{submitted_order.id}/fill")
    assert fill_response.status_code == 200

    response = client.post(f"/execution/paper/{submitted_order.id}/close?close_price=1.086")

    assert response.status_code == 200
    payload = response.json()
    assert payload["execution_id"] == str(submitted_order.id)
    assert payload["status"] == "closed"

    refreshed = db_session.get(PaperOrder, submitted_order.id)
    assert refreshed is not None
    assert refreshed.id == submitted_order.id
    assert refreshed.status.value == "closed"
    assert refreshed.submitted_at is not None


def test_execution_paper_get_route_returns_submitted_order(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    submitted_order = _create_submitted_paper_order(client, db_session, monkeypatch)

    response = client.get(f"/execution/paper/{submitted_order.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["execution_id"] == str(submitted_order.id)
    assert payload["status"] == "submitted"

    missing_response = client.get(f"/execution/paper/{uuid4()}")
    assert missing_response.status_code == 404


def test_execution_paper_get_route_returns_closed_order_after_progression(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    submitted_order = _create_submitted_paper_order(client, db_session, monkeypatch)

    fill_response = client.post(f"/execution/paper/{submitted_order.id}/fill")
    assert fill_response.status_code == 200

    close_response = client.post(f"/execution/paper/{submitted_order.id}/close?close_price=1.086")
    assert close_response.status_code == 200

    response = client.get(f"/execution/paper/{submitted_order.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["execution_id"] == str(submitted_order.id)
    assert payload["status"] == "closed"


def test_execution_paper_history_route_returns_submitted_event(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    submitted_order = _create_submitted_paper_order(client, db_session, monkeypatch)

    response = client.get(f"/execution/paper/{submitted_order.id}/history")

    assert response.status_code == 200
    payload = response.json()
    assert payload["execution_id"] == str(submitted_order.id)
    assert payload["events"] == ["submitted"]

    missing_response = client.get(f"/execution/paper/{uuid4()}/history")
    assert missing_response.status_code == 404


def test_execution_paper_history_route_returns_submitted_filled_closed_sequence(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    submitted_order = _create_submitted_paper_order(client, db_session, monkeypatch)

    fill_response = client.post(f"/execution/paper/{submitted_order.id}/fill")
    assert fill_response.status_code == 200

    close_response = client.post(f"/execution/paper/{submitted_order.id}/close?close_price=1.086")
    assert close_response.status_code == 200

    response = client.get(f"/execution/paper/{submitted_order.id}/history")

    assert response.status_code == 200
    payload = response.json()
    assert payload["execution_id"] == str(submitted_order.id)
    assert payload["events"] == ["submitted", "filled", "closed"]


def test_execution_paper_list_route_returns_orders_in_deterministic_order(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_order = _create_submitted_paper_order(client, db_session, monkeypatch)
    second_order = _create_submitted_paper_order(client, db_session, monkeypatch)

    response = client.get("/execution/paper?limit=10&offset=0")

    assert response.status_code == 200
    payload = response.json()
    expected_ids = sorted([str(first_order.id), str(second_order.id)])
    assert [item["execution_id"] for item in payload] == expected_ids

    paged = client.get("/execution/paper?limit=1&offset=1")
    assert paged.status_code == 200
    assert [item["execution_id"] for item in paged.json()] == [expected_ids[1]]


def test_execution_paper_list_route_filters_by_status(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    submitted_order = _create_submitted_paper_order(client, db_session, monkeypatch)
    closed_order = _create_submitted_paper_order(client, db_session, monkeypatch)

    fill_response = client.post(f"/execution/paper/{closed_order.id}/fill")
    assert fill_response.status_code == 200
    close_response = client.post(f"/execution/paper/{closed_order.id}/close?close_price=1.086")
    assert close_response.status_code == 200

    response = client.get("/execution/paper?status=accepted")

    assert response.status_code == 200
    payload = response.json()
    assert [item["execution_id"] for item in payload] == [str(submitted_order.id)]
    assert payload[0]["status"] == "submitted"


def test_execution_paper_list_route_returns_empty_list_when_no_orders(client: TestClient) -> None:
    response = client.get("/execution/paper")

    assert response.status_code == 200
    assert response.json() == []


def test_execution_paper_journal_put_then_get_round_trips_backend_data(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pytest.TempPathFactory,
) -> None:
    submitted_order = _create_submitted_paper_order(client, db_session, monkeypatch)
    store_path = tmp_path / "execution-journals.json"

    monkeypatch.setattr(
        execution_route,
        "_get_execution_journal_service",
        lambda: ExecutionJournalService(store_path=store_path),
    )

    put_response = client.put(
        f"/execution/paper/{submitted_order.id}/journal",
        json={
            "outcome_tag": "worked",
            "note": "  Clean continuation setup.  ",
            "tags": ["Breakout", "breakout", "Trend"],
        },
    )

    assert put_response.status_code == 200
    put_payload = put_response.json()
    assert put_payload["execution_id"] == str(submitted_order.id)
    assert put_payload["outcome_tag"] == "worked"
    assert put_payload["note"] == "Clean continuation setup."
    assert put_payload["tags"] == ["breakout", "trend"]
    assert put_payload["updated_at"]

    get_response = client.get(f"/execution/paper/{submitted_order.id}/journal")

    assert get_response.status_code == 200
    assert get_response.json() == put_payload


def test_execution_paper_journal_get_route_returns_404_when_entry_missing(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pytest.TempPathFactory,
) -> None:
    submitted_order = _create_submitted_paper_order(client, db_session, monkeypatch)
    store_path = tmp_path / "execution-journals.json"

    monkeypatch.setattr(
        execution_route,
        "_get_execution_journal_service",
        lambda: ExecutionJournalService(store_path=store_path),
    )

    response = client.get(f"/execution/paper/{submitted_order.id}/journal")

    assert response.status_code == 404
    assert "Journal for paper order" in response.json()["detail"]


def test_execution_live_route(client: TestClient) -> None:
    response = client.post(
        "/execution/live",
        json={
            "asset": "EURUSD",
            "side": "buy",
            "qty": 1000.0,
            "notional": 1081.5,
            "stop_price": 1.079,
            "target_price": 1.085,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted"] is False
    assert payload["status"] == "disabled"
    assert payload["reason"] == "live_execution_disabled_in_mvp"
    assert payload["reason"] == "live_execution_disabled_in_mvp"