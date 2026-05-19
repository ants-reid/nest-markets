"""MH-11 tests for Strategy Lab comparison history and dashboard detail endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models.backtest_run import BacktestRun
from app.db.models.drawdown_period import DrawdownPeriod
from app.db.models.equity_curve_point import EquityCurvePoint
from app.db.models.mock_trade import MockTrade
from app.db.models.strategy_config import StrategyConfig
from app.db.models.strategy_result import StrategyResult
from app.db.session import SessionLocal, engine, get_db_session
from app.main import app


@pytest.fixture()
def db_session() -> Session:  # type: ignore[misc]
    schema_name = f"test_strategy_lab_hist_{uuid4().hex}"

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


def _seed_comparison_run(db: Session, name: str = "AAPL Compare") -> BacktestRun:
    cfg1 = StrategyConfig(
        name=f"{name} cfg1",
        strategy_type="ma_momentum",
        asset="AAPL",
        timeframe="1d",
        parameters={"fast_window": 3, "slow_window": 20, "risk_reward": 1.5, "hold_bars": 5},
        risk_settings={},
        enabled=True,
    )
    cfg2 = StrategyConfig(
        name=f"{name} cfg2",
        strategy_type="ma_momentum",
        asset="AAPL",
        timeframe="1d",
        parameters={"fast_window": 5, "slow_window": 20, "risk_reward": 2.0, "hold_bars": 10},
        risk_settings={},
        enabled=True,
    )
    db.add_all([cfg1, cfg2])
    db.flush()

    run = BacktestRun(
        name=name,
        status="completed",
        date_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
        date_to=datetime(2024, 12, 31, tzinfo=timezone.utc),
        requested_assets={"assets": ["AAPL"]},
        requested_timeframes={"timeframes": ["1d"]},
        strategy_config_ids={"config_ids": [str(cfg1.id), str(cfg2.id)]},
        starting_capital=Decimal("100000"),
        result_summary={
            "comparison_summary": {
                "total_configs_tested": 2,
                "warnings": ["sample warning"],
            }
        },
        started_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        completed_at=datetime(2024, 1, 2, tzinfo=timezone.utc),
    )
    db.add(run)
    db.flush()

    result_low = StrategyResult(
        backtest_run_id=run.id,
        strategy_config_id=cfg1.id,
        asset="AAPL",
        timeframe="1d",
        total_trades=80,
        wins=45,
        losses=35,
        breakeven=0,
        win_rate=Decimal("0.5625"),
        profit_factor=Decimal("1.23"),
        total_return_pct=Decimal("4.11"),
        max_drawdown_pct=Decimal("3.40"),
        score=Decimal("55.0"),
    )
    result_high = StrategyResult(
        backtest_run_id=run.id,
        strategy_config_id=cfg2.id,
        asset="AAPL",
        timeframe="1d",
        total_trades=95,
        wins=57,
        losses=38,
        breakeven=0,
        win_rate=Decimal("0.6000"),
        profit_factor=Decimal("1.55"),
        total_return_pct=Decimal("7.75"),
        max_drawdown_pct=Decimal("2.10"),
        score=Decimal("78.0"),
    )
    db.add_all([result_low, result_high])

    trade = MockTrade(
        backtest_run_id=run.id,
        strategy_config_id=cfg2.id,
        asset="AAPL",
        timeframe="1d",
        side="long",
        entry_time=datetime(2024, 2, 1, tzinfo=timezone.utc),
        entry_price=Decimal("100.0"),
        stop_price=Decimal("97.0"),
        target_price=Decimal("106.0"),
        exit_time=datetime(2024, 2, 5, tzinfo=timezone.utc),
        exit_price=Decimal("106.0"),
        status="closed",
        result="win",
        pnl_amount=Decimal("500.0"),
        pnl_pct=Decimal("0.5"),
        r_multiple=Decimal("2.0"),
    )
    db.add(trade)

    eq1 = EquityCurvePoint(
        backtest_run_id=run.id,
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        equity=Decimal("100000.0"),
        cash=Decimal("100000.0"),
        open_pnl=Decimal("0.0"),
        drawdown_pct=Decimal("0.0"),
    )
    eq2 = EquityCurvePoint(
        backtest_run_id=run.id,
        timestamp=datetime(2024, 6, 1, tzinfo=timezone.utc),
        equity=Decimal("108500.0"),
        cash=Decimal("108500.0"),
        open_pnl=Decimal("0.0"),
        drawdown_pct=Decimal("1.2"),
    )
    db.add_all([eq1, eq2])

    dd = DrawdownPeriod(
        backtest_run_id=run.id,
        start_time=datetime(2024, 3, 1, tzinfo=timezone.utc),
        trough_time=datetime(2024, 3, 7, tzinfo=timezone.utc),
        end_time=datetime(2024, 3, 10, tzinfo=timezone.utc),
        max_drawdown_pct=Decimal("2.1"),
        duration_candles=7,
        recovered=True,
    )
    db.add(dd)

    db.commit()
    db.refresh(run)
    return run


def test_comparison_history_empty(client: TestClient) -> None:
    resp = client.get("/strategy-lab/comparisons")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["total"] == 0
    assert payload["items"] == []


def test_comparison_history_returns_recent_runs_and_best_row(
    client: TestClient,
    db_session: Session,
) -> None:
    _seed_comparison_run(db_session, "Run One")
    _seed_comparison_run(db_session, "Run Two")

    resp = client.get("/strategy-lab/comparisons")
    assert resp.status_code == 200
    payload = resp.json()

    assert payload["total"] == 2
    first = payload["items"][0]
    assert first["total_configs_tested"] == 2
    assert first["best_score"] == 78.0
    assert first["best_strategy_name"].endswith("cfg2")
    assert first["best_parameters"]["fast_window"] == 5
    assert first["best_profit_factor"] == 1.55


def test_comparison_detail_returns_ranked_rows_and_summaries(
    client: TestClient,
    db_session: Session,
) -> None:
    run = _seed_comparison_run(db_session)

    resp = client.get(f"/strategy-lab/comparisons/{run.id}")
    assert resp.status_code == 200
    payload = resp.json()

    assert payload["backtest_run"]["id"] == str(run.id)
    assert payload["mock_trade_count"] == 1
    assert payload["equity_curve_summary"]["total_points"] == 2
    assert payload["drawdown_summary"]["total_periods"] == 1
    assert payload["warnings"] == ["sample warning"]

    rows = payload["ranked_rows"]
    assert len(rows) == 2
    assert rows[0]["rank"] == 1
    assert rows[0]["score"] == 78.0
    assert rows[0]["strategy_name"].endswith("cfg2")


def test_comparison_label_updates_result_summary(
    client: TestClient,
    db_session: Session,
) -> None:
    run = _seed_comparison_run(db_session)

    resp = client.post(
        f"/strategy-lab/comparisons/{run.id}/label",
        json={
            "research_label": "watchlist_candidate",
            "research_notes": "Strong PF with controlled drawdown.",
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["research_label"] == "watchlist_candidate"
    assert payload["updated"] is True

    detail = client.get(f"/strategy-lab/comparisons/{run.id}")
    assert detail.status_code == 200
    detail_payload = detail.json()
    assert detail_payload["research_label"] == "watchlist_candidate"
    assert detail_payload["research_notes"] == "Strong PF with controlled drawdown."
