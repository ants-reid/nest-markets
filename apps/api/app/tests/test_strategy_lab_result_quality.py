"""MH-16 tests for deterministic Strategy Lab result quality scoring."""

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
from app.db.models.strategy_result import StrategyResult
from app.db.session import SessionLocal, engine, get_db_session
from app.main import app
from app.services.strategy_result_quality_service import (
    compute_result_quality,
    grade_from_confidence,
    score_cost_sensitivity,
    score_drawdown,
    score_profitability,
    score_sample_size,
)


@pytest.fixture()
def db_session() -> Session:  # type: ignore[misc]
    schema_name = f"test_quality_{uuid4().hex}"

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


def test_sample_size_scoring_buckets() -> None:
    assert score_sample_size(600) == 100
    assert score_sample_size(300) == 80
    assert score_sample_size(150) == 60
    assert score_sample_size(75) == 40
    assert score_sample_size(10) == 20


def test_profitability_scoring_buckets() -> None:
    assert score_profitability(1.6, 25.0) == 100
    assert score_profitability(1.3, 12.0) == 80
    assert score_profitability(1.12, 2.0) == 60
    assert score_profitability(1.0, -5.0) == 40
    assert score_profitability(0.9, -2.0) == 20


def test_drawdown_scoring_buckets() -> None:
    assert score_drawdown(4.0) == 100
    assert score_drawdown(8.0) == 80
    assert score_drawdown(12.0) == 60
    assert score_drawdown(20.0) == 40
    assert score_drawdown(30.0) == 20


def test_cost_sensitivity_scoring_buckets() -> None:
    assert score_cost_sensitivity("low") == 100
    assert score_cost_sensitivity("medium") == 70
    assert score_cost_sensitivity("high") == 30
    assert score_cost_sensitivity("unknown") == 50


def test_grade_mapping() -> None:
    assert grade_from_confidence(90) == "A"
    assert grade_from_confidence(75) == "B"
    assert grade_from_confidence(60) == "C"
    assert grade_from_confidence(45) == "D"
    assert grade_from_confidence(20) == "F"


def test_overfitting_warning_low_trade_high_return() -> None:
    result = compute_result_quality(
        total_trades=40,
        net_profit_factor=2.2,
        net_total_return_pct=45.0,
        max_drawdown_pct=8.0,
        cost_sensitivity_level="medium",
        high_cost_net_total_return_pct=-5.0,
    )
    assert result["overfitting_risk_score"] >= 70
    assert "High overfitting risk" in result["quality_warnings"]


def test_high_drawdown_warning() -> None:
    result = compute_result_quality(
        total_trades=220,
        net_profit_factor=1.3,
        net_total_return_pct=15.0,
        max_drawdown_pct=30.0,
        cost_sensitivity_level="low",
    )
    assert "High drawdown" in result["quality_warnings"]


def test_weak_net_profitability_warning() -> None:
    result = compute_result_quality(
        total_trades=220,
        net_profit_factor=0.95,
        net_total_return_pct=-1.0,
        max_drawdown_pct=10.0,
        cost_sensitivity_level="low",
    )
    assert "Net profitability weak after costs" in result["quality_warnings"]


def test_quality_flags_are_always_false() -> None:
    result = compute_result_quality(
        total_trades=500,
        net_profit_factor=1.8,
        net_total_return_pct=30.0,
        max_drawdown_pct=4.0,
        cost_sensitivity_level="low",
    )
    assert result["paper_trade_ready"] is False
    assert result["live_ready"] is False


def test_quality_summary_endpoint_returns_aggregate(client: TestClient, db_session: Session) -> None:
    run = BacktestRun(
        name="Quality Summary Run",
        status="completed",
        date_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
        date_to=datetime(2024, 1, 31, tzinfo=timezone.utc),
        requested_assets={"assets": ["AAPL"]},
        requested_timeframes={"timeframes": ["1d"]},
        strategy_config_ids={"config_ids": []},
        starting_capital=Decimal("10000"),
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)

    quality_a = compute_result_quality(
        total_trades=520,
        net_profit_factor=1.7,
        net_total_return_pct=26.0,
        max_drawdown_pct=4.0,
        cost_sensitivity_level="low",
    )
    quality_f = compute_result_quality(
        total_trades=20,
        net_profit_factor=0.8,
        net_total_return_pct=-5.0,
        max_drawdown_pct=28.0,
        cost_sensitivity_level="high",
    )

    db_session.add(
        StrategyResult(
            backtest_run_id=run.id,
            strategy_config_id=None,
            asset="AAPL",
            timeframe="1d",
            total_trades=520,
            wins=300,
            losses=220,
            breakeven=0,
            win_rate=Decimal("0.57"),
            metrics=quality_a,
        )
    )
    db_session.add(
        StrategyResult(
            backtest_run_id=run.id,
            strategy_config_id=None,
            asset="AAPL",
            timeframe="1d",
            total_trades=20,
            wins=5,
            losses=15,
            breakeven=0,
            win_rate=Decimal("0.25"),
            metrics=quality_f,
        )
    )
    db_session.commit()

    response = client.get(f"/strategy-lab/backtests/{run.id}/quality-summary")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["total_strategies"] == 2
    assert data["grade_distribution"]["A"] >= 1
    assert data["grade_distribution"]["F"] >= 1
    assert data["paper_trade_ready"] is False
    assert data["live_ready"] is False
