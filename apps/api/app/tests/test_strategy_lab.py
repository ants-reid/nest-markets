"""MH-06 tests for Strategy Lab data contract routes and service behavior."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import SessionLocal, engine, get_db_session
from app.main import app
from app.services.strategy_lab_service import StrategyLabService


@pytest.fixture()
def db_session() -> Session:  # type: ignore[misc]
    schema_name = f"test_strategy_lab_{uuid4().hex}"

    admin_conn = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
    admin_conn.execute(text(f'CREATE SCHEMA "{schema_name}"'))
    admin_conn.close()

    conn = engine.connect()
    conn.execute(text(f'SET search_path TO "{schema_name}"'))
    conn.commit()
    Base.metadata.create_all(bind=conn)

    session = SessionLocal(bind=conn)
    try:
        yield session
    finally:
        session.close()
        conn.close()
        cleanup = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
        cleanup.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))
        cleanup.close()


@pytest.fixture()
def client(db_session: Session) -> TestClient:  # type: ignore[misc]
    def _override():
        yield db_session

    app.dependency_overrides[get_db_session] = _override
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_db_session, None)


# ── Strategy Config tests ──────────────────────────────────────────────────

def test_create_strategy_config(client: TestClient) -> None:
    response = client.post(
        "/strategy-lab/configs",
        json={
            "name": "RSI Reversal",
            "strategy_type": "mean_reversion",
            "asset": "AAPL",
            "timeframe": "1d",
            "parameters": {"rsi_period": 14, "rsi_oversold": 30},
            "risk_settings": {"stop_pct": 0.02},
        },
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["name"] == "RSI Reversal"
    assert data["asset"] == "AAPL"
    assert data["enabled"] is True
    assert "id" in data


def test_list_strategy_configs_empty(client: TestClient) -> None:
    response = client.get("/strategy-lab/configs")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


def test_list_strategy_configs_after_create(client: TestClient) -> None:
    client.post(
        "/strategy-lab/configs",
        json={
            "name": "Breakout",
            "strategy_type": "momentum",
            "asset": "SPY",
            "timeframe": "1h",
        },
    )
    response = client.get("/strategy-lab/configs")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1


def test_get_strategy_config(client: TestClient) -> None:
    create_resp = client.post(
        "/strategy-lab/configs",
        json={
            "name": "MACD Cross",
            "strategy_type": "trend",
            "asset": "TSLA",
            "timeframe": "4h",
        },
    )
    config_id = create_resp.json()["id"]
    response = client.get(f"/strategy-lab/configs/{config_id}")
    assert response.status_code == 200
    assert response.json()["id"] == config_id


def test_get_strategy_config_not_found(client: TestClient) -> None:
    response = client.get(f"/strategy-lab/configs/{uuid4()}")
    assert response.status_code == 404


# ── Backtest Run tests ─────────────────────────────────────────────────────

_BACKTEST_PAYLOAD = {
    "name": "Q1 2024 Backtest",
    "date_from": "2024-01-01T00:00:00Z",
    "date_to": "2024-03-31T23:59:59Z",
    "requested_assets": ["AAPL", "MSFT"],
    "requested_timeframes": ["1d"],
    "strategy_config_ids": [],
    "starting_capital": 50000,
}


def test_create_backtest_run_returns_202(client: TestClient) -> None:
    response = client.post("/strategy-lab/backtests", json=_BACKTEST_PAYLOAD)
    assert response.status_code == 202, response.text
    data = response.json()
    assert data["status"] == "queued"
    assert "id" in data
    assert "MH-07" in data["message"]


def test_create_backtest_run_no_mock_trades_generated(
    client: TestClient, db_session: Session
) -> None:
    """Creating a backtest stub must NOT produce any mock trades (MH-07 scope)."""
    response = client.post("/strategy-lab/backtests", json=_BACKTEST_PAYLOAD)
    run_id = response.json()["id"]

    trades_resp = client.get(f"/strategy-lab/backtests/{run_id}/trades")
    assert trades_resp.status_code == 200
    assert trades_resp.json()["total"] == 0
    assert trades_resp.json()["items"] == []


def test_list_backtests_empty(client: TestClient) -> None:
    response = client.get("/strategy-lab/backtests")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


def test_list_backtests_after_create(client: TestClient) -> None:
    client.post("/strategy-lab/backtests", json=_BACKTEST_PAYLOAD)
    response = client.get("/strategy-lab/backtests")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1


def test_get_backtest_run(client: TestClient) -> None:
    create_resp = client.post("/strategy-lab/backtests", json=_BACKTEST_PAYLOAD)
    run_id = create_resp.json()["id"]
    response = client.get(f"/strategy-lab/backtests/{run_id}")
    assert response.status_code == 200
    assert response.json()["id"] == run_id


def test_get_backtest_not_found(client: TestClient) -> None:
    response = client.get(f"/strategy-lab/backtests/{uuid4()}")
    assert response.status_code == 404


# ── Sub-resource empty list tests ──────────────────────────────────────────

def test_backtest_results_empty(client: TestClient) -> None:
    create_resp = client.post("/strategy-lab/backtests", json=_BACKTEST_PAYLOAD)
    run_id = create_resp.json()["id"]
    response = client.get(f"/strategy-lab/backtests/{run_id}/results")
    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_backtest_equity_curve_empty(client: TestClient) -> None:
    create_resp = client.post("/strategy-lab/backtests", json=_BACKTEST_PAYLOAD)
    run_id = create_resp.json()["id"]
    response = client.get(f"/strategy-lab/backtests/{run_id}/equity-curve")
    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_backtest_drawdowns_empty(client: TestClient) -> None:
    create_resp = client.post("/strategy-lab/backtests", json=_BACKTEST_PAYLOAD)
    run_id = create_resp.json()["id"]
    response = client.get(f"/strategy-lab/backtests/{run_id}/drawdowns")
    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_sub_resource_404_on_unknown_run(client: TestClient) -> None:
    unknown = str(uuid4())
    for path in ["trades", "results", "equity-curve", "drawdowns"]:
        resp = client.get(f"/strategy-lab/backtests/{unknown}/{path}")
        assert resp.status_code == 404, f"{path} should 404"


def test_cost_model_profiles_endpoint(client: TestClient) -> None:
    response = client.get("/strategy-lab/cost-model/profiles")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["total"] >= 4
    names = {item["profile_name"] for item in data["items"]}
    assert "standard_research" in names
    assert "stress_research" in names


def test_cost_model_stress_presets_endpoint(client: TestClient) -> None:
    response = client.get("/strategy-lab/cost-model/stress-presets")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["total"] >= 5
    names = {item["preset_name"] for item in data["items"]}
    assert "normal_liquidity" in names
    assert "news_event_stress" in names


# ── Route registration test ────────────────────────────────────────────────

def test_strategy_lab_routes_registered() -> None:
    """Smoke test: all expected routes are mounted in the app."""
    paths = {r.path for r in app.routes}
    expected = {
        "/strategy-lab/cost-model/profiles",
        "/strategy-lab/cost-model/stress-presets",
        "/strategy-lab/configs",
        "/strategy-lab/configs/{config_id}",
        "/strategy-lab/backtests",
        "/strategy-lab/backtests/{backtest_id}",
        "/strategy-lab/backtests/{backtest_id}/trades",
        "/strategy-lab/backtests/{backtest_id}/results",
        "/strategy-lab/backtests/{backtest_id}/quality-summary",
        "/strategy-lab/backtests/{backtest_id}/walk-forward",
        "/strategy-lab/backtests/{backtest_id}/equity-curve",
        "/strategy-lab/backtests/{backtest_id}/drawdowns",
    }
    for path in expected:
        assert path in paths, f"Route not found: {path}"


# ── Service unit tests ─────────────────────────────────────────────────────

def test_service_create_and_list_configs(db_session: Session) -> None:
    svc = StrategyLabService(db_session)
    svc.create_config(
        name="SMA Cross",
        strategy_type="trend",
        asset="QQQ",
        timeframe="1d",
    )
    total, items = svc.list_configs()
    assert total == 1
    assert items[0].name == "SMA Cross"


def test_service_create_backtest_returns_queued(db_session: Session) -> None:
    from datetime import datetime, timezone

    svc = StrategyLabService(db_session)
    run, msg = svc.create_backtest_run(
        name="Test Run",
        date_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
        date_to=datetime(2024, 6, 30, tzinfo=timezone.utc),
        requested_assets=["AAPL"],
        requested_timeframes=["1d"],
        strategy_config_ids=[],
    )
    assert run.status == "queued"
    assert "MH-07" in msg
