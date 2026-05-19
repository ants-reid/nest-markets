"""MH-17 tests for walk-forward and out-of-sample validation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models.backtest_run import BacktestRun
from app.db.models.mock_trade import MockTrade
from app.db.models.strategy_result import StrategyResult
from app.db.session import SessionLocal, engine, get_db_session
from app.main import app
from app.services.walk_forward_validation_service import (
    build_rolling_fold_splits,
    build_date_splits,
    calculate_multi_fold_summary,
    calculate_walk_forward_summary,
)


@pytest.fixture()
def db_session() -> Session:  # type: ignore[misc]
    schema_name = f"test_wf_{uuid4().hex}"

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


def test_default_60_20_20_split_generation() -> None:
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = datetime(2024, 1, 11, tzinfo=timezone.utc)
    splits = build_date_splits(date_from=start, date_to=end)

    assert [s.label for s in splits] == ["in_sample", "validation", "out_of_sample"]
    assert [s.percentage for s in splits] == [60, 20, 20]
    assert all(s.end > s.start for s in splits)


def test_custom_split_validation() -> None:
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = datetime(2024, 2, 1, tzinfo=timezone.utc)
    splits = build_date_splits(
        date_from=start,
        date_to=end,
        in_sample_pct=50,
        validation_pct=30,
        out_of_sample_pct=20,
    )
    assert [s.percentage for s in splits] == [50, 30, 20]


def test_build_rolling_fold_splits_generates_requested_fold_count() -> None:
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = datetime(2024, 3, 1, tzinfo=timezone.utc)
    folds = build_rolling_fold_splits(
        date_from=start,
        date_to=end,
        fold_count=3,
    )

    assert len(folds) == 3
    assert [fold.fold_index for fold in folds] == [1, 2, 3]
    assert all(len(fold.splits) == 3 for fold in folds)
    assert folds[1].splits[0].start > folds[0].splits[0].start


def test_multi_fold_summary_aggregates_dispersion_and_grade() -> None:
    summary = calculate_multi_fold_summary(
        [
            {
                "validation_stability_score": 88,
                "validation_stability_grade": "stable",
                "out_of_sample_pass": True,
                "return_degradation_pct": 18,
                "confidence_degradation_pct": 12,
            },
            {
                "validation_stability_score": 74,
                "validation_stability_grade": "mixed",
                "out_of_sample_pass": True,
                "return_degradation_pct": 28,
                "confidence_degradation_pct": 20,
            },
            {
                "validation_stability_score": 42,
                "validation_stability_grade": "unstable",
                "out_of_sample_pass": False,
                "return_degradation_pct": 66,
                "confidence_degradation_pct": 38,
            },
        ]
    )

    assert summary["fold_count"] == 3
    assert summary["stability_dispersion"] > 0
    assert summary["rolling_validation_grade"] in {"mixed", "unstable"}
    assert summary["rolling_out_of_sample_pass"] is False


def test_invalid_split_percentages_rejected() -> None:
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = datetime(2024, 2, 1, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="total 100"):
        build_date_splits(
            date_from=start,
            date_to=end,
            in_sample_pct=70,
            validation_pct=20,
            out_of_sample_pct=20,
        )


def test_out_of_sample_degradation_calculation() -> None:
    summary = calculate_walk_forward_summary(
        in_sample_metrics={
            "net_total_return_pct": 20,
            "net_profit_factor": 1.5,
            "research_confidence_score": 80,
            "max_drawdown_pct": 8,
            "total_trades": 100,
        },
        validation_metrics={"net_total_return_pct": 10},
        out_of_sample_metrics={
            "net_total_return_pct": 5,
            "net_profit_factor": 1.1,
            "research_confidence_score": 60,
            "max_drawdown_pct": 9,
            "total_trades": 60,
        },
    )
    assert summary["return_degradation_pct"] == pytest.approx(75.0)
    assert summary["profit_factor_degradation_pct"] > 0
    assert summary["confidence_degradation_pct"] > 0


def test_stability_score_bands_stable_mixed_unstable() -> None:
    stable = calculate_walk_forward_summary(
        in_sample_metrics={"net_total_return_pct": 12, "net_profit_factor": 1.3, "research_confidence_score": 70, "max_drawdown_pct": 8, "total_trades": 100},
        validation_metrics={"net_total_return_pct": 10},
        out_of_sample_metrics={"net_total_return_pct": 9, "net_profit_factor": 1.2, "research_confidence_score": 68, "max_drawdown_pct": 8, "total_trades": 80},
    )
    mixed = calculate_walk_forward_summary(
        in_sample_metrics={"net_total_return_pct": 20, "net_profit_factor": 1.4, "research_confidence_score": 85, "max_drawdown_pct": 7, "total_trades": 120},
        validation_metrics={"net_total_return_pct": 8},
        out_of_sample_metrics={"net_total_return_pct": 2, "net_profit_factor": 0.98, "research_confidence_score": 50, "max_drawdown_pct": 10, "total_trades": 40},
    )
    unstable = calculate_walk_forward_summary(
        in_sample_metrics={"net_total_return_pct": 35, "net_profit_factor": 2.1, "research_confidence_score": 90, "max_drawdown_pct": 6, "total_trades": 80},
        validation_metrics={"net_total_return_pct": 5},
        out_of_sample_metrics={"net_total_return_pct": -6, "net_profit_factor": 0.7, "research_confidence_score": 35, "max_drawdown_pct": 20, "total_trades": 12},
    )

    assert stable["validation_stability_grade"] == "stable"
    assert mixed["validation_stability_grade"] in {"mixed", "unstable"}
    assert unstable["validation_stability_grade"] == "unstable"


def test_low_out_of_sample_trade_count_warning() -> None:
    summary = calculate_walk_forward_summary(
        in_sample_metrics={"net_total_return_pct": 15, "net_profit_factor": 1.4, "research_confidence_score": 80, "max_drawdown_pct": 10, "total_trades": 100},
        validation_metrics={"net_total_return_pct": 7},
        out_of_sample_metrics={"net_total_return_pct": 3, "net_profit_factor": 1.1, "research_confidence_score": 70, "max_drawdown_pct": 11, "total_trades": 10},
    )
    assert "Out-of-sample trade count too low" in summary["warnings"]


def test_negative_out_of_sample_return_warning() -> None:
    summary = calculate_walk_forward_summary(
        in_sample_metrics={"net_total_return_pct": 10, "net_profit_factor": 1.2, "research_confidence_score": 70, "max_drawdown_pct": 8, "total_trades": 90},
        validation_metrics={"net_total_return_pct": 6},
        out_of_sample_metrics={"net_total_return_pct": -1, "net_profit_factor": 1.05, "research_confidence_score": 60, "max_drawdown_pct": 9, "total_trades": 35},
    )
    assert "Out-of-sample performance degraded materially" in summary["warnings"]


def test_walk_forward_endpoint_returns_research_only_response(
    client: TestClient,
    db_session: Session,
) -> None:
    run = BacktestRun(
        name="Walk Forward Run",
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

    result = StrategyResult(
        backtest_run_id=run.id,
        strategy_config_id=None,
        asset="AAPL",
        timeframe="1d",
        total_trades=3,
        wins=2,
        losses=1,
        breakeven=0,
        win_rate=Decimal("0.66"),
        metrics={},
    )
    db_session.add(result)

    t0 = run.date_from + timedelta(days=2)
    for i, pnl in enumerate([20.0, -10.0, 5.0]):
        db_session.add(
            MockTrade(
                backtest_run_id=run.id,
                strategy_config_id=None,
                asset="AAPL",
                timeframe="1d",
                side="long",
                entry_time=t0 + timedelta(days=i),
                entry_price=Decimal("100"),
                stop_price=Decimal("99"),
                target_price=Decimal("102"),
                exit_time=t0 + timedelta(days=i),
                exit_price=Decimal("101"),
                status="closed",
                result="win" if pnl > 0 else "loss",
                pnl_amount=Decimal(str(pnl)),
                metadata_json={
                    "base_net_pnl_amount": pnl,
                    "cost_sensitivity_level": "low",
                },
            )
        )
    db_session.commit()

    response = client.post(f"/strategy-lab/backtests/{run.id}/walk-forward", json={})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["paper_trade_ready"] is False
    assert data["live_ready"] is False
    assert len(data["splits"]) == 3
    assert len(data["strategies"]) >= 1
    assert data["rolling_window_summary"] is not None


def test_walk_forward_endpoint_rejects_invalid_custom_split(
    client: TestClient,
    db_session: Session,
) -> None:
    run = BacktestRun(
        name="Walk Forward Bad Split",
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

    response = client.post(
        f"/strategy-lab/backtests/{run.id}/walk-forward",
        json={"in_sample_pct": 70, "validation_pct": 20, "out_of_sample_pct": 20},
    )
    assert response.status_code == 400


def test_get_walk_forward_endpoint_returns_latest_or_computed(
    client: TestClient,
    db_session: Session,
) -> None:
    run = BacktestRun(
        name="Walk Forward GET",
        status="completed",
        date_from=datetime(2024, 2, 1, tzinfo=timezone.utc),
        date_to=datetime(2024, 2, 20, tzinfo=timezone.utc),
        requested_assets={"assets": ["AAPL"]},
        requested_timeframes={"timeframes": ["1d"]},
        strategy_config_ids={"config_ids": []},
        starting_capital=Decimal("10000"),
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)

    response = client.get(f"/strategy-lab/backtests/{run.id}/walk-forward")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["paper_trade_ready"] is False
    assert data["live_ready"] is False


def test_walk_forward_endpoint_supports_multi_fold_validation(
    client: TestClient,
    db_session: Session,
) -> None:
    run = BacktestRun(
        name="Walk Forward Multi Fold",
        status="completed",
        date_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
        date_to=datetime(2024, 4, 30, tzinfo=timezone.utc),
        requested_assets={"assets": ["AAPL"]},
        requested_timeframes={"timeframes": ["1d"]},
        strategy_config_ids={"config_ids": []},
        starting_capital=Decimal("10000"),
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)

    result = StrategyResult(
        backtest_run_id=run.id,
        strategy_config_id=None,
        asset="AAPL",
        timeframe="1d",
        total_trades=12,
        wins=8,
        losses=4,
        breakeven=0,
        win_rate=Decimal("0.66"),
        metrics={},
    )
    db_session.add(result)

    t0 = run.date_from + timedelta(days=3)
    pnls = [35.0, 20.0, -12.0, 24.0, 18.0, -8.0, 30.0, 14.0, -10.0, 12.0, 8.0, -6.0]
    for i, pnl in enumerate(pnls):
        trade_time = t0 + timedelta(days=i * 8)
        db_session.add(
            MockTrade(
                backtest_run_id=run.id,
                strategy_config_id=None,
                asset="AAPL",
                timeframe="1d",
                side="long",
                entry_time=trade_time,
                entry_price=Decimal("100"),
                stop_price=Decimal("99"),
                target_price=Decimal("103"),
                exit_time=trade_time,
                exit_price=Decimal("101"),
                status="closed",
                result="win" if pnl > 0 else "loss",
                pnl_amount=Decimal(str(pnl)),
                metadata_json={
                    "base_net_pnl_amount": pnl,
                    "cost_sensitivity_level": "low" if pnl > 0 else "medium",
                },
            )
        )
    db_session.commit()

    response = client.post(
        f"/strategy-lab/backtests/{run.id}/walk-forward",
        json={"fold_count": 3},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["paper_trade_ready"] is False
    assert data["live_ready"] is False
    assert data["rolling_window_summary"]["fold_count"] >= 1
    assert len(data["strategies"]) == 1
    assert len(data["strategies"][0]["folds"]) == 3

    db_session.refresh(result)
    metrics = result.metrics or {}
    assert metrics["walk_forward_validation_version"] == "mh18_v1"
    assert metrics["walk_forward_fold_count"] == 3
    assert len(metrics["walk_forward_folds"]) == 3
