"""MH-08 tests for Mock Trade Simulator.

Covers:
- simulate_trades=False → no trade rows created
- simulate_trades=True + MA crossover data → trades persisted
- Long entry (fast crosses above slow) → target hit → win
- Short entry (fast crosses below slow) → target hit → win
- Stop hit → loss
- Hold-bars exit
- One-open-trade-at-a-time rule
- StrategyResult row created
- EquityCurvePoint rows created
- DrawdownPeriod created on equity dip
- result_summary has simulation metrics
- clear_existing_results=True → re-run without duplicates
- Not enough candles (< slow_window+1) → 0 trades, no crash
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.enums import AssetClass
from app.db.models.asset import Asset
from app.db.models.backtest_run import BacktestRun
from app.db.models.bar import Bar
from app.db.models.drawdown_period import DrawdownPeriod
from app.db.models.equity_curve_point import EquityCurvePoint
from app.db.models.market_data_quality_report import MarketDataQualityReport
from app.db.models.mock_trade import MockTrade
from app.db.models.strategy_result import StrategyResult
from app.db.session import SessionLocal, engine, get_db_session
from app.main import app
from app.services.mock_trade_simulator_service import MockTradeSimulatorService


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture()
def db_session():  # type: ignore[misc]
    schema_name = f"test_sim_{uuid4().hex}"

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


# ── Seed helpers ───────────────────────────────────────────────────────────

def _make_asset(session: Session, symbol: str = "AAPL") -> Asset:
    asset = Asset(symbol=symbol, name=symbol, asset_class=AssetClass.EQUITY, is_active=True)
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset


def _make_quality_report(
    session: Session,
    symbol: str,
    timeframe: str = "1d",
    approved: bool = True,
) -> MarketDataQualityReport:
    report = MarketDataQualityReport(
        asset_symbol=symbol,
        timeframe=timeframe,
        evaluated_at=datetime.now(tz=timezone.utc),
        actual_bars=30,
        total_bars=30,
        approved_for_backtest=approved,
        quality_score=0.95,
    )
    session.add(report)
    session.commit()
    session.refresh(report)
    return report


def _make_run(
    session: Session,
    assets: list[str] | None = None,
    timeframes: list[str] | None = None,
    starting_capital: float = 100_000.0,
) -> BacktestRun:
    run = BacktestRun(
        name="Sim Test Run",
        status="queued",
        date_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
        date_to=datetime(2024, 12, 31, tzinfo=timezone.utc),
        requested_assets={"assets": assets or ["AAPL"]},
        requested_timeframes={"timeframes": timeframes or ["1d"]},
        strategy_config_ids={"config_ids": []},
        starting_capital=Decimal(str(starting_capital)),
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


_T0 = datetime(2024, 1, 2, tzinfo=timezone.utc)


def _make_bars_with_prices(
    session: Session,
    asset: Asset,
    timeframe: str,
    prices: list[tuple[float, float, float]],  # (close, low, high)
) -> list[Bar]:
    """Create bars from (close, low, high) tuples."""
    bars = []
    for i, (close, low, high) in enumerate(prices):
        ts = _T0 + timedelta(days=i)
        bar = Bar(
            asset_id=asset.id,
            timeframe=timeframe,
            ts=ts,
            open=Decimal(str(close)),
            high=Decimal(str(high)),
            low=Decimal(str(low)),
            close=Decimal(str(close)),
            volume=Decimal("1000000"),
        )
        session.add(bar)
        bars.append(bar)
    session.commit()
    return bars


def _long_signal_prices() -> list[tuple[float, float, float]]:
    """Price data designed to produce one long entry with target hit.

    MA params: fast=3, slow=5.
    Bars 0-4: close=100 (flat). Bar 5: close=110 (spike up).
    At bar 5: fast_ma(3) = mean([100,100,110]) = 103.33
              slow_ma(5) = mean([100,100,100,100,110]) = 102
    prev_fast(bar4) = 100, prev_slow(bar4) = 100 → tie so prev_fast <= prev_slow
    curr_fast > curr_slow → LONG signal.
    Entry = 110. stop = min lows[0..4] = 99. risk_dist = 11. target = 110+22 = 132.
    Bar 6: high=135 → target hit → WIN.
    """
    return [
        (100, 99, 101),  # 0
        (100, 99, 101),  # 1
        (100, 99, 101),  # 2
        (100, 99, 101),  # 3
        (100, 99, 101),  # 4
        (110, 109, 111),  # 5  — signal bar, entry=110
        (130, 125, 135),  # 6  — high=135 >= target=132 → WIN
        (130, 125, 135),  # 7  (extra padding)
    ]


def _short_signal_prices() -> list[tuple[float, float, float]]:
    """Price data designed to produce one short entry with target hit.

    At bar 5: fast_ma(3) = mean([100,100,90]) = 96.67
              slow_ma(5) = mean([100,100,100,100,90]) = 98
    curr_fast < curr_slow → SHORT signal.
    Entry = 90. stop = max highs[0..4] = 101. risk_dist = 11. target = 90-22 = 68.
    Bar 6: low=65 → target hit → WIN.
    """
    return [
        (100, 99, 101),  # 0
        (100, 99, 101),  # 1
        (100, 99, 101),  # 2
        (100, 99, 101),  # 3
        (100, 99, 101),  # 4
        (90, 89, 91),   # 5  — signal bar, entry=90
        (70, 65, 75),   # 6  — low=65 <= target=68 → WIN
        (70, 65, 75),   # 7  (padding)
    ]


def _stop_hit_prices() -> list[tuple[float, float, float]]:
    """Long signal at bar 5, then stop hit at bar 6.

    Entry = 110. stop = 99. Bar 6: low=95 <= 99 → LOSS.
    """
    return [
        (100, 99, 101),  # 0
        (100, 99, 101),  # 1
        (100, 99, 101),  # 2
        (100, 99, 101),  # 3
        (100, 99, 101),  # 4
        (110, 109, 111),  # 5  — long signal, entry=110
        (96, 95, 100),   # 6  — low=95 <= stop=99 → LOSS
    ]


def _hold_exit_prices() -> list[tuple[float, float, float]]:
    """Long signal at bar 5, price barely moves — hold_bars=3 exit at bar 8.

    Entry=110, stop=99, target=132.
    Bars 6,7,8: close ~ 111 (neither stop nor target touched) → hold exit at bar 8.
    """
    return [
        (100, 99, 101),   # 0
        (100, 99, 101),   # 1
        (100, 99, 101),   # 2
        (100, 99, 101),   # 3
        (100, 99, 101),   # 4
        (110, 109, 111),  # 5  — long signal
        (111, 108, 112),  # 6  — held (bars_held=1)
        (111, 108, 112),  # 7  — held (bars_held=2)
        (111, 108, 112),  # 8  — bars_held=3 >= hold_bars → exit at close=111
    ]


def _insufficient_candles_prices() -> list[tuple[float, float, float]]:
    """Only 4 bars (< slow_window+1=6) — simulator should return early."""
    return [(100, 99, 101)] * 4


# ── Service-level tests ────────────────────────────────────────────────────

def test_simulator_service_not_enough_candles(db_session: Session) -> None:
    """Simulator returns 0 trades and a warning when candles < slow_window+1."""
    asset = _make_asset(db_session, "AAPL")
    bars = _make_bars_with_prices(db_session, asset, "1d", _insufficient_candles_prices())
    run = _make_run(db_session)

    svc = MockTradeSimulatorService(db_session)
    result = svc.simulate(
        backtest_run_id=run.id,
        strategy_config=None,
        candles=bars,
        starting_capital=10_000.0,
        asset="AAPL",
        timeframe="1d",
    )

    assert result.total_trades == 0
    assert len(result.warnings) > 0
    assert "enough candles" in result.warnings[0].lower()


def test_simulator_long_trade_target_win(db_session: Session) -> None:
    """Long MA crossover → target hit → win trade persisted."""
    asset = _make_asset(db_session, "AAPL")
    bars = _make_bars_with_prices(db_session, asset, "1d", _long_signal_prices())
    run = _make_run(db_session)

    svc = MockTradeSimulatorService(db_session)
    result = svc.simulate(
        backtest_run_id=run.id,
        strategy_config=None,
        candles=bars,
        starting_capital=10_000.0,
        asset="AAPL",
        timeframe="1d",
    )

    assert result.total_trades == 1
    assert result.wins == 1
    assert result.losses == 0

    trades = db_session.execute(
        select(MockTrade).where(MockTrade.backtest_run_id == run.id)
    ).scalars().all()
    assert len(trades) == 1
    trade = trades[0]
    assert trade.side == "long"
    assert trade.result == "win"
    assert trade.reason_for_exit == "target"
    assert float(trade.entry_price) == pytest.approx(110.0)
    assert float(trade.stop_price) == pytest.approx(99.0)
    assert float(trade.target_price) == pytest.approx(132.0)


def test_simulator_short_trade_target_win(db_session: Session) -> None:
    """Short MA crossover → target hit → win trade persisted."""
    asset = _make_asset(db_session, "AAPL")
    bars = _make_bars_with_prices(db_session, asset, "1d", _short_signal_prices())
    run = _make_run(db_session)

    svc = MockTradeSimulatorService(db_session)
    result = svc.simulate(
        backtest_run_id=run.id,
        strategy_config=None,
        candles=bars,
        starting_capital=10_000.0,
        asset="AAPL",
        timeframe="1d",
    )

    assert result.total_trades == 1
    assert result.wins == 1

    trades = db_session.execute(
        select(MockTrade).where(MockTrade.backtest_run_id == run.id)
    ).scalars().all()
    trade = trades[0]
    assert trade.side == "short"
    assert trade.result == "win"
    assert trade.reason_for_exit == "target"
    assert float(trade.entry_price) == pytest.approx(90.0)
    assert float(trade.stop_price) == pytest.approx(101.0)
    assert float(trade.target_price) == pytest.approx(68.0)


def test_simulator_stop_hit_creates_loss(db_session: Session) -> None:
    """Long trade stop hit → result=loss."""
    asset = _make_asset(db_session, "AAPL")
    bars = _make_bars_with_prices(db_session, asset, "1d", _stop_hit_prices())
    run = _make_run(db_session)

    svc = MockTradeSimulatorService(db_session)
    result = svc.simulate(
        backtest_run_id=run.id,
        strategy_config=None,
        candles=bars,
        starting_capital=10_000.0,
        asset="AAPL",
        timeframe="1d",
    )

    assert result.total_trades == 1
    assert result.losses == 1
    assert result.wins == 0

    trade = db_session.execute(
        select(MockTrade).where(MockTrade.backtest_run_id == run.id)
    ).scalars().first()
    assert trade is not None
    assert trade.result == "loss"
    assert trade.reason_for_exit == "stop"
    assert float(trade.pnl_amount) < 0


def test_simulator_hold_exit(db_session: Session) -> None:
    """Trade exits via hold_bars without stop/target hit."""
    asset = _make_asset(db_session, "AAPL")
    bars = _make_bars_with_prices(db_session, asset, "1d", _hold_exit_prices())
    run = _make_run(db_session)

    svc = MockTradeSimulatorService(db_session)
    svc.simulate(
        backtest_run_id=run.id,
        strategy_config=None,
        candles=bars,
        starting_capital=10_000.0,
        asset="AAPL",
        timeframe="1d",
    )

    trade = db_session.execute(
        select(MockTrade).where(MockTrade.backtest_run_id == run.id)
    ).scalars().first()
    assert trade is not None
    assert trade.reason_for_exit == "hold"
    # exit at close=111
    assert float(trade.exit_price) == pytest.approx(111.0)


def test_simulator_strategy_result_created(db_session: Session) -> None:
    """StrategyResult row is created after a successful simulation."""
    asset = _make_asset(db_session, "AAPL")
    bars = _make_bars_with_prices(db_session, asset, "1d", _long_signal_prices())
    run = _make_run(db_session)

    svc = MockTradeSimulatorService(db_session)
    svc.simulate(
        backtest_run_id=run.id,
        strategy_config=None,
        candles=bars,
        starting_capital=10_000.0,
        asset="AAPL",
        timeframe="1d",
    )

    sr = db_session.execute(
        select(StrategyResult).where(StrategyResult.backtest_run_id == run.id)
    ).scalars().first()
    assert sr is not None
    assert sr.total_trades == 1
    assert sr.wins == 1
    assert sr.asset == "AAPL"
    assert sr.timeframe == "1d"
    assert float(sr.win_rate) == pytest.approx(1.0, abs=0.01)


def test_simulator_trade_metadata_includes_cost_details(db_session: Session) -> None:
    """Closed trade metadata contains deterministic execution-cost fields."""
    asset = _make_asset(db_session, "AAPL")
    bars = _make_bars_with_prices(db_session, asset, "1d", _long_signal_prices())
    run = _make_run(db_session)

    svc = MockTradeSimulatorService(db_session)
    svc.simulate(
        backtest_run_id=run.id,
        strategy_config=None,
        candles=bars,
        starting_capital=10_000.0,
        asset="AAPL",
        timeframe="1d",
    )

    trade = db_session.execute(
        select(MockTrade).where(MockTrade.backtest_run_id == run.id)
    ).scalars().first()
    assert trade is not None
    metadata = trade.metadata_json or {}

    assert metadata.get("cost_model_version") == "mh15c_v1"
    assert metadata.get("cost_scenario_used") == "base"
    assert metadata.get("cost_profile_used") == "standard_research"
    assert metadata.get("stress_preset_used") == "normal_liquidity"
    assert metadata.get("broker_calibrated") is False
    assert float(metadata.get("estimated_total_cost", 0.0)) > 0.0
    assert float(metadata.get("gross_pnl_amount", 0.0)) > 0.0
    assert float(metadata.get("net_pnl_amount", 0.0)) < float(metadata.get("gross_pnl_amount", 0.0))
    assert "low_cost_estimate" in metadata
    assert "base_cost_estimate" in metadata
    assert "high_cost_estimate" in metadata
    assert float(metadata.get("low_net_pnl_amount", 0.0)) >= float(metadata.get("base_net_pnl_amount", 0.0))
    assert float(metadata.get("high_net_pnl_amount", 0.0)) <= float(metadata.get("base_net_pnl_amount", 0.0))
    assert metadata.get("cost_sensitivity_level") in {"low", "medium", "high", "loss_sensitive"}
    assert metadata.get("profile_sensitivity_summary", {}).get("broker_calibrated") is False


def test_strategy_result_metrics_include_gross_and_net_fields(db_session: Session) -> None:
    """StrategyResult.metrics stores gross/net returns and execution-cost metadata."""
    asset = _make_asset(db_session, "AAPL")
    bars = _make_bars_with_prices(db_session, asset, "1d", _long_signal_prices())
    run = _make_run(db_session)

    svc = MockTradeSimulatorService(db_session)
    svc.simulate(
        backtest_run_id=run.id,
        strategy_config=None,
        candles=bars,
        starting_capital=10_000.0,
        asset="AAPL",
        timeframe="1d",
    )

    result = db_session.execute(
        select(StrategyResult).where(StrategyResult.backtest_run_id == run.id)
    ).scalars().first()
    assert result is not None
    metrics = result.metrics or {}

    assert metrics.get("execution_costs_modelled") is True
    assert metrics.get("spread_modelled") is True
    assert metrics.get("slippage_modelled") is True
    assert metrics.get("fees_modelled") is True
    assert metrics.get("cost_model_version") == "mh15c_v1"
    assert metrics.get("cost_scenario_default") == "base"
    assert metrics.get("cost_profile_default") == "standard_research"
    assert metrics.get("stress_preset_default") == "normal_liquidity"
    assert metrics.get("broker_calibrated") is False

    assert "gross_total_return_pct" in metrics
    assert "low_net_total_return_pct" in metrics
    assert "base_net_total_return_pct" in metrics
    assert "high_net_total_return_pct" in metrics
    assert "net_total_return_pct" in metrics
    assert "gross_profit_factor" in metrics
    assert "low_net_profit_factor" in metrics
    assert "base_net_profit_factor" in metrics
    assert "high_net_profit_factor" in metrics
    assert "net_profit_factor" in metrics
    assert "gross_expectancy" in metrics
    assert "net_expectancy" in metrics
    assert "total_cost_amount" in metrics
    assert "low_total_cost_amount" in metrics
    assert "base_total_cost_amount" in metrics
    assert "high_total_cost_amount" in metrics
    assert "average_cost_per_trade" in metrics
    assert "cost_sensitivity_level" in metrics
    assert "profile_sensitivity_level" in metrics
    assert "stress_scenario_notes" in metrics
    assert metrics.get("result_quality_version") == "mh16_v1"
    assert metrics.get("quality_grade") in {"A", "B", "C", "D", "F"}
    assert "research_confidence_score" in metrics
    assert "sample_size_score" in metrics
    assert "profitability_score" in metrics
    assert "drawdown_score" in metrics
    assert "cost_sensitivity_score" in metrics
    assert "robustness_score" in metrics
    assert "overfitting_risk_score" in metrics
    assert metrics.get("paper_trade_ready") is False
    assert metrics.get("live_ready") is False
    assert "quality_warnings" in metrics

    assert float(metrics["total_cost_amount"]) > 0.0
    assert float(metrics["net_total_return_pct"]) <= float(metrics["gross_total_return_pct"])
    assert float(metrics["low_net_total_return_pct"]) >= float(metrics["base_net_total_return_pct"])
    assert float(metrics["high_net_total_return_pct"]) <= float(metrics["base_net_total_return_pct"])
    assert float(metrics["net_total_return_pct"]) == pytest.approx(float(metrics["base_net_total_return_pct"]))
    assert metrics["net_profit_factor"] == metrics["base_net_profit_factor"]
    assert float(metrics["total_cost_amount"]) == pytest.approx(float(metrics["base_total_cost_amount"]))


def test_simulator_equity_curve_points_created(db_session: Session) -> None:
    """EquityCurvePoint rows are created (start + exit points)."""
    asset = _make_asset(db_session, "AAPL")
    bars = _make_bars_with_prices(db_session, asset, "1d", _long_signal_prices())
    run = _make_run(db_session)

    svc = MockTradeSimulatorService(db_session)
    svc.simulate(
        backtest_run_id=run.id,
        strategy_config=None,
        candles=bars,
        starting_capital=10_000.0,
        asset="AAPL",
        timeframe="1d",
    )

    pts = db_session.execute(
        select(EquityCurvePoint).where(EquityCurvePoint.backtest_run_id == run.id)
    ).scalars().all()
    assert len(pts) >= 2  # at least start + exit


def test_simulator_drawdown_period_created_on_loss(db_session: Session) -> None:
    """DrawdownPeriod is created when equity drops below peak."""
    asset = _make_asset(db_session, "AAPL")
    bars = _make_bars_with_prices(db_session, asset, "1d", _stop_hit_prices())
    run = _make_run(db_session)

    svc = MockTradeSimulatorService(db_session)
    svc.simulate(
        backtest_run_id=run.id,
        strategy_config=None,
        candles=bars,
        starting_capital=10_000.0,
        asset="AAPL",
        timeframe="1d",
    )

    dds = db_session.execute(
        select(DrawdownPeriod).where(DrawdownPeriod.backtest_run_id == run.id)
    ).scalars().all()
    assert len(dds) == 1
    dd = dds[0]
    assert float(dd.max_drawdown_pct) > 0


def test_simulator_no_drawdown_when_only_win(db_session: Session) -> None:
    """No DrawdownPeriod when only wins and equity never dips below peak."""
    asset = _make_asset(db_session, "AAPL")
    bars = _make_bars_with_prices(db_session, asset, "1d", _long_signal_prices())
    run = _make_run(db_session)

    svc = MockTradeSimulatorService(db_session)
    svc.simulate(
        backtest_run_id=run.id,
        strategy_config=None,
        candles=bars,
        starting_capital=10_000.0,
        asset="AAPL",
        timeframe="1d",
    )

    dds = db_session.execute(
        select(DrawdownPeriod).where(DrawdownPeriod.backtest_run_id == run.id)
    ).scalars().all()
    # equity only goes up → no drawdown period
    assert len(dds) == 0


def test_simulator_zero_trades_no_db_writes(db_session: Session) -> None:
    """With insufficient candles, no MockTrade/StrategyResult/EquityCurve rows created."""
    asset = _make_asset(db_session, "AAPL")
    bars = _make_bars_with_prices(db_session, asset, "1d", _insufficient_candles_prices())
    run = _make_run(db_session)

    svc = MockTradeSimulatorService(db_session)
    svc.simulate(
        backtest_run_id=run.id,
        strategy_config=None,
        candles=bars,
        starting_capital=10_000.0,
        asset="AAPL",
        timeframe="1d",
    )

    assert db_session.execute(
        select(MockTrade).where(MockTrade.backtest_run_id == run.id)
    ).scalars().first() is None

    assert db_session.execute(
        select(StrategyResult).where(StrategyResult.backtest_run_id == run.id)
    ).scalars().first() is None

    assert db_session.execute(
        select(EquityCurvePoint).where(EquityCurvePoint.backtest_run_id == run.id)
    ).scalars().first() is None


# ── Route-level tests ──────────────────────────────────────────────────────

def test_replay_with_simulate_false_no_trades(
    db_session: Session, client: TestClient
) -> None:
    """simulate_trades=False → no MockTrade rows created."""
    asset = _make_asset(db_session, "AAPL")
    _make_bars_with_prices(db_session, asset, "1d", _long_signal_prices())
    _make_quality_report(db_session, "AAPL", "1d", approved=True)
    run = _make_run(db_session)

    resp = client.post(
        f"/strategy-lab/backtests/{run.id}/replay",
        json={"simulate_trades": False, "allow_unapproved_data": False},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["total_mock_trades"] == 0

    assert db_session.execute(
        select(MockTrade).where(MockTrade.backtest_run_id == run.id)
    ).scalars().first() is None


def test_replay_with_simulate_true_creates_trades(
    db_session: Session, client: TestClient
) -> None:
    """simulate_trades=True + long signal data → trades exist in DB."""
    asset = _make_asset(db_session, "AAPL")
    _make_bars_with_prices(db_session, asset, "1d", _long_signal_prices())
    _make_quality_report(db_session, "AAPL", "1d", approved=True)
    run = _make_run(db_session)

    resp = client.post(
        f"/strategy-lab/backtests/{run.id}/replay",
        json={"simulate_trades": True, "allow_unapproved_data": False},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["total_mock_trades"] == 1

    trades = db_session.execute(
        select(MockTrade).where(MockTrade.backtest_run_id == run.id)
    ).scalars().all()
    assert len(trades) == 1


def test_replay_response_has_simulation_stats(
    db_session: Session, client: TestClient
) -> None:
    """BacktestReplayResponse contains win_rate, profit_factor etc after simulation."""
    asset = _make_asset(db_session, "AAPL")
    _make_bars_with_prices(db_session, asset, "1d", _long_signal_prices())
    _make_quality_report(db_session, "AAPL", "1d", approved=True)
    run = _make_run(db_session)

    resp = client.post(
        f"/strategy-lab/backtests/{run.id}/replay",
        json={"simulate_trades": True, "allow_unapproved_data": False},
    )
    data = resp.json()
    assert data["win_rate"] is not None
    assert data["win_rate"] == pytest.approx(1.0, abs=0.01)
    assert data["profit_factor"] is None  # profit_factor is None when no losses
    assert data["total_return_pct"] is not None
    assert data["total_return_pct"] > 0


def test_replay_result_summary_persisted(
    db_session: Session, client: TestClient
) -> None:
    """BacktestRun.result_summary is saved to DB with simulation fields."""
    asset = _make_asset(db_session, "AAPL")
    _make_bars_with_prices(db_session, asset, "1d", _long_signal_prices())
    _make_quality_report(db_session, "AAPL", "1d", approved=True)
    run = _make_run(db_session)

    client.post(
        f"/strategy-lab/backtests/{run.id}/replay",
        json={"simulate_trades": True, "allow_unapproved_data": False},
    )

    db_session.refresh(run)
    assert run.result_summary is not None
    assert run.result_summary["total_mock_trades"] == 1
    assert run.result_summary["status"] == "completed"


def test_replay_clear_existing_results_no_duplicates(
    db_session: Session, client: TestClient
) -> None:
    """Re-running with clear_existing_results=True removes old outputs and re-creates them."""
    asset = _make_asset(db_session, "AAPL")
    _make_bars_with_prices(db_session, asset, "1d", _long_signal_prices())
    _make_quality_report(db_session, "AAPL", "1d", approved=True)
    run = _make_run(db_session)

    # First run
    r1 = client.post(
        f"/strategy-lab/backtests/{run.id}/replay",
        json={"simulate_trades": True, "allow_unapproved_data": False},
    )
    assert r1.status_code == 200

    # Re-run with clear
    r2 = client.post(
        f"/strategy-lab/backtests/{run.id}/replay",
        json={
            "simulate_trades": True,
            "allow_unapproved_data": False,
            "clear_existing_results": True,
        },
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "completed"

    # Should have exactly same count, not doubled
    trades = db_session.execute(
        select(MockTrade).where(MockTrade.backtest_run_id == run.id)
    ).scalars().all()
    assert len(trades) == 1  # not 2


def test_replay_rejects_completed_run_without_clear_flag(
    db_session: Session, client: TestClient
) -> None:
    """Replaying a completed run without clear_existing_results=True returns 400."""
    asset = _make_asset(db_session, "AAPL")
    _make_bars_with_prices(db_session, asset, "1d", _long_signal_prices())
    _make_quality_report(db_session, "AAPL", "1d", approved=True)
    run = _make_run(db_session)

    # First run
    client.post(
        f"/strategy-lab/backtests/{run.id}/replay",
        json={"simulate_trades": True, "allow_unapproved_data": False},
    )

    # Attempt re-run without clear flag
    resp = client.post(
        f"/strategy-lab/backtests/{run.id}/replay",
        json={"simulate_trades": True, "allow_unapproved_data": False},
    )
    assert resp.status_code == 400
    assert "clear_existing_results" in resp.json()["detail"].lower()


def test_replay_one_trade_at_a_time(db_session: Session) -> None:
    """Simulator never opens a second trade while one is open."""
    # Build price data with two crossover signals close together.
    # After first long signal, price rises then drops back for a potential short signal.
    # But there should still be only 1 open trade at any moment.
    prices: list[tuple[float, float, float]] = [
        (100, 99, 101),  # 0
        (100, 99, 101),  # 1
        (100, 99, 101),  # 2
        (100, 99, 101),  # 3
        (100, 99, 101),  # 4
        (110, 109, 111),  # 5 — long crossover
        (111, 108, 112),  # 6 held
        (111, 108, 112),  # 7 held
        (111, 108, 112),  # 8 hold exit
        # Now possibility of short signal
        (90, 89, 91),   # 9
        (80, 79, 81),   # 10 potential short after hold exit
        (70, 65, 75),   # 11
        (70, 65, 75),   # 12
    ]
    asset = _make_asset(db_session, "AAPL")
    bars = _make_bars_with_prices(db_session, asset, "1d", prices)
    run = _make_run(db_session)

    svc = MockTradeSimulatorService(db_session)
    result = svc.simulate(
        backtest_run_id=run.id,
        strategy_config=None,
        candles=bars,
        starting_capital=10_000.0,
        asset="AAPL",
        timeframe="1d",
    )

    trades = db_session.execute(
        select(MockTrade).where(MockTrade.backtest_run_id == run.id)
        .order_by(MockTrade.entry_time)
    ).scalars().all()

    # Verify no two trades overlap in time
    for i in range(len(trades) - 1):
        assert trades[i].exit_time is not None
        assert trades[i].exit_time <= trades[i + 1].entry_time, (
            f"Trade {i} exit {trades[i].exit_time} overlaps trade {i+1} entry "
            f"{trades[i+1].entry_time}"
        )
    assert result.total_trades >= 1
