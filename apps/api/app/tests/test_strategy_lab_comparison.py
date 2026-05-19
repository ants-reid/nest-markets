"""MH-10 tests for Strategy Comparison / Multi-Config Runner.

Covers:
- parameter grid creates valid configs only (fast_window < slow_window)
- fast_window >= slow_window combinations are skipped
- max_configs cap is enforced
- comparison run creates exactly one backtest run
- comparison run creates multiple strategy configs
- comparison run returns ranked rows (rank 1 = best score)
- score penalises low trade counts (< 5 trades)
- endpoint rejects request where no valid grid exists
- endpoint POST /strategy-lab/comparisons/run returns 200
- existing candles produce StrategyResult rows
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
from app.db.models.market_data_quality_report import MarketDataQualityReport
from app.db.models.mock_trade import MockTrade
from app.db.models.strategy_config import StrategyConfig
from app.db.models.strategy_result import StrategyResult
from app.db.session import SessionLocal, engine, get_db_session
from app.main import app
from app.schemas.strategy_lab import StrategyComparisonRequest
from app.services.strategy_comparison_service import (
    ComparisonError,
    StrategyComparisonService,
    _compute_score,
    _resolve_scoring_inputs,
)


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture()
def db_session():  # type: ignore[misc]
    schema_name = f"test_cmp_{uuid4().hex}"

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

_T0 = datetime(2024, 1, 2, tzinfo=timezone.utc)


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


def _make_bars(
    session: Session,
    asset: Asset,
    timeframe: str = "1d",
    n: int = 30,
) -> None:
    """Create a minimal set of candle bars with a clear MA crossover pattern."""
    # Prices: first half low, second half higher to trigger crossover signals
    prices = []
    for i in range(n):
        if i < n // 2:
            close = 100.0 + i * 0.1
        else:
            close = 110.0 + (i - n // 2) * 0.5
        prices.append(close)

    bars = []
    for i, close in enumerate(prices):
        low = close * 0.99
        high = close * 1.01
        bar = Bar(
            asset_id=asset.id,
            timeframe=timeframe,
            ts=_T0 + timedelta(days=i),
            open=Decimal(str(close)),
            high=Decimal(str(high)),
            low=Decimal(str(low)),
            close=Decimal(str(close)),
            volume=Decimal("10000"),
        )
        bars.append(bar)
    session.add_all(bars)
    session.commit()


def _long_signal_prices() -> list[tuple[float, float, float]]:
    """Deterministic bars that produce a long signal for fast=3, slow=5."""
    return [
        (100, 99, 101),
        (100, 99, 101),
        (100, 99, 101),
        (100, 99, 101),
        (100, 99, 101),
        (110, 109, 111),
        (130, 125, 135),
        (130, 125, 135),
    ]


def _make_bars_with_prices(
    session: Session,
    asset: Asset,
    timeframe: str,
    prices: list[tuple[float, float, float]],
) -> None:
    bars = []
    for i, (close, low, high) in enumerate(prices):
        bars.append(
            Bar(
                asset_id=asset.id,
                timeframe=timeframe,
                ts=_T0 + timedelta(days=i),
                open=Decimal(str(close)),
                high=Decimal(str(high)),
                low=Decimal(str(low)),
                close=Decimal(str(close)),
                volume=Decimal("10000"),
            )
        )
    session.add_all(bars)
    session.commit()


def _base_request(**overrides) -> StrategyComparisonRequest:  # type: ignore[misc]
    defaults: dict = {
        "name": "Test Comparison",
        "asset": "AAPL",
        "timeframe": "1d",
        "date_from": _T0,
        "date_to": _T0 + timedelta(days=30),
        "starting_capital": 10000.0,
        "allow_unapproved_data": True,
        "max_candles": 1000,
        "fast_windows": [3, 5],
        "slow_windows": [10],
        "risk_rewards": [2.0],
        "hold_bars_options": [3],
        "risk_per_trade_pct_options": [0.5],
        "max_configs": 30,
    }
    defaults.update(overrides)
    return StrategyComparisonRequest(**defaults)


# ── Unit tests: _compute_score ─────────────────────────────────────────────

def test_score_penalises_very_low_trade_count() -> None:
    # With fewer than 5 trades, a 25-point penalty is applied
    # Use modest inputs that won't hit the 100 clamp (win_rate is 0-1 fraction)
    score_low = _compute_score(
        profit_factor=1.5,
        total_return_pct=5.0,
        win_rate=0.5,
        max_drawdown_pct=5.0,
        total_trades=3,
    )
    score_normal = _compute_score(
        profit_factor=1.5,
        total_return_pct=5.0,
        win_rate=0.5,
        max_drawdown_pct=5.0,
        total_trades=15,
    )
    assert score_low < score_normal


def test_score_penalises_low_trade_count() -> None:
    # Between 5 and 9 trades, a 10-point penalty is applied
    score_mid = _compute_score(
        profit_factor=1.5,
        total_return_pct=5.0,
        win_rate=0.5,
        max_drawdown_pct=5.0,
        total_trades=7,
    )
    score_normal = _compute_score(
        profit_factor=1.5,
        total_return_pct=5.0,
        win_rate=0.5,
        max_drawdown_pct=5.0,
        total_trades=15,
    )
    assert score_mid < score_normal


def test_score_clamped_to_zero_minimum() -> None:
    score = _compute_score(
        profit_factor=0.0,
        total_return_pct=-100.0,
        win_rate=0.0,
        max_drawdown_pct=100.0,
        total_trades=1,
    )
    assert score == 0.0


def test_score_clamped_to_100_maximum() -> None:
    score = _compute_score(
        profit_factor=5.0,
        total_return_pct=50.0,
        win_rate=100.0,
        max_drawdown_pct=0.0,
        total_trades=20,
    )
    assert score == 100.0


def test_resolve_scoring_inputs_prefers_net_metrics() -> None:
    """Scoring should prefer net metrics in StrategyResult.metrics when present."""
    result = StrategyResult(
        backtest_run_id=uuid4(),
        strategy_config_id=uuid4(),
        total_trades=10,
        wins=6,
        losses=4,
        breakeven=0,
        profit_factor=Decimal("0.8"),
        total_return_pct=Decimal("-3.0"),
        metrics={
            "base_net_profit_factor": 1.9,
            "base_net_total_return_pct": 7.5,
        },
    )

    pf, ret, used_gross = _resolve_scoring_inputs(result)
    assert pf == pytest.approx(1.9)
    assert ret == pytest.approx(7.5)
    assert used_gross is False


def test_resolve_scoring_inputs_falls_back_to_gross_when_missing_net() -> None:
    """Scoring falls back to gross fields and marks fallback when net fields are missing."""
    result = StrategyResult(
        backtest_run_id=uuid4(),
        strategy_config_id=uuid4(),
        total_trades=10,
        wins=6,
        losses=4,
        breakeven=0,
        profit_factor=Decimal("1.2"),
        total_return_pct=Decimal("5.0"),
        metrics={},
    )

    pf, ret, used_gross = _resolve_scoring_inputs(result)
    assert pf == pytest.approx(1.2)
    assert ret == pytest.approx(5.0)
    assert used_gross is True


def test_comparison_rows_include_cost_scenario_metadata(db_session: Session) -> None:
    """Comparison rows expose base-scenario scoring and high-cost metadata fields."""
    asset = _make_asset(db_session, "AAPL")
    _make_bars_with_prices(db_session, asset, "1d", _long_signal_prices())
    _make_quality_report(db_session, "AAPL")

    req = _base_request(
        date_to=_T0 + timedelta(days=8),
        fast_windows=[3],
        slow_windows=[5],
        risk_rewards=[2.0],
        hold_bars_options=[3],
        risk_per_trade_pct_options=[0.5],
        max_configs=1,
    )
    result = StrategyComparisonService(db_session).run_comparison(req)

    assert len(result.rows) == 1
    row = result.rows[0]
    assert row.scoring_cost_scenario == "base"
    assert row.cost_sensitivity_level in {"low", "medium", "high", "loss_sensitive"}
    assert row.quality_grade in {"A", "B", "C", "D", "F"}
    assert row.research_confidence_score is not None
    assert row.overfitting_risk_score is not None
    assert isinstance(row.quality_warnings, list)
    assert row.validation_stability_score is None or isinstance(row.validation_stability_score, float)
    assert row.validation_stability_grade is None or row.validation_stability_grade in {"stable", "mixed", "unstable"}
    assert row.out_of_sample_pass is None or isinstance(row.out_of_sample_pass, bool)
    assert isinstance(row.walk_forward_warnings, list)
    assert result.cost_profile_used == "standard_research"
    assert result.stress_preset_used == "normal_liquidity"
    assert result.broker_calibrated is False


def test_high_cost_warning_when_scenario_turns_unprofitable(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Adds warning when high-cost scenario makes strategy unprofitable."""
    _make_asset(db_session)
    _make_quality_report(db_session, "AAPL")

    def _fake_replay(self, backtest_run_id, **kwargs):  # type: ignore[no-untyped-def]
        run = db_session.get(BacktestRun, backtest_run_id)
        assert run is not None
        config_ids = run.strategy_config_ids.get("config_ids", []) if isinstance(run.strategy_config_ids, dict) else []
        cfg_id = uuid4() if not config_ids else config_ids[0]
        if isinstance(cfg_id, str):
            from uuid import UUID

            cfg_id = UUID(cfg_id)

        row = StrategyResult(
            backtest_run_id=run.id,
            strategy_config_id=cfg_id,
            asset="AAPL",
            timeframe="1d",
            total_trades=20,
            wins=12,
            losses=8,
            breakeven=0,
            win_rate=Decimal("0.6"),
            profit_factor=Decimal("1.2"),
            total_return_pct=Decimal("2.0"),
            max_drawdown_pct=Decimal("5.0"),
            metrics={
                "base_net_profit_factor": 1.2,
                "base_net_total_return_pct": 2.0,
                "high_net_total_return_pct": -1.0,
                "high_net_profit_factor": 0.8,
                "cost_sensitivity_level": "high",
            },
        )
        db_session.add(row)
        db_session.commit()
        return None

    monkeypatch.setattr(
        "app.services.strategy_comparison_service.HistoricalReplayService.replay",
        _fake_replay,
    )

    req = _base_request(
        fast_windows=[3],
        slow_windows=[10],
        max_configs=1,
    )
    result = StrategyComparisonService(db_session).run_comparison(req)

    combined = " ".join(result.warnings).lower()
    assert "sensitive to execution costs under high-cost assumptions" in combined
    assert "deterministic research assumptions" in combined
    assert result.rows[0].scoring_cost_scenario == "base"
    assert result.rows[0].high_cost_scenario_net_return_pct == pytest.approx(-1.0)


# ── Service unit tests ─────────────────────────────────────────────────────

def test_grid_skips_fast_gte_slow(db_session: Session) -> None:
    """Configs where fast_window >= slow_window must be excluded."""
    _make_asset(db_session)
    req = _base_request(fast_windows=[10, 20], slow_windows=[5, 10])
    # All combos: (10,5) skip, (10,10) skip, (20,5) skip, (20,10) skip
    with pytest.raises(ComparisonError, match="No valid parameter combinations"):
        StrategyComparisonService(db_session).run_comparison(req)


def test_grid_creates_valid_configs_only(db_session: Session) -> None:
    """Only combos where fast_window < slow_window produce StrategyConfig rows."""
    _make_asset(db_session)
    _make_quality_report(db_session, "AAPL")
    req = _base_request(fast_windows=[3, 10], slow_windows=[10, 5])
    # Valid combos: (3,10), (3,5) — wait (3,5)? 3<5 yes. (3,10) yes. (10,10) skip. (10,5) skip
    # So 2 valid: fw=3,sw=10 and fw=3,sw=5
    result = StrategyComparisonService(db_session).run_comparison(req)
    assert result.total_configs_tested == 2
    configs = db_session.execute(select(StrategyConfig)).scalars().all()
    for cfg in configs:
        params = cfg.parameters
        assert params["fast_window"] < params["slow_window"]


def test_max_configs_cap_enforced(db_session: Session) -> None:
    """max_configs limits the number of generated configs."""
    _make_asset(db_session)
    _make_quality_report(db_session, "AAPL")
    req = _base_request(
        fast_windows=[3, 5],
        slow_windows=[10, 20],
        risk_rewards=[1.5, 2.0, 2.5],
        hold_bars_options=[3, 5],
        max_configs=3,
    )
    result = StrategyComparisonService(db_session).run_comparison(req)
    assert result.total_configs_tested == 3
    assert len(result.warnings) >= 1
    assert any("truncated" in w for w in result.warnings)


def test_comparison_creates_one_backtest_run(db_session: Session) -> None:
    """Exactly one BacktestRun should be created per comparison call."""
    _make_asset(db_session)
    _make_quality_report(db_session, "AAPL")
    req = _base_request()
    StrategyComparisonService(db_session).run_comparison(req)
    runs = db_session.execute(select(BacktestRun)).scalars().all()
    assert len(runs) == 1


def test_comparison_creates_multiple_configs(db_session: Session) -> None:
    """Each valid grid combination should produce a StrategyConfig row."""
    _make_asset(db_session)
    _make_quality_report(db_session, "AAPL")
    req = _base_request(fast_windows=[3, 5], slow_windows=[10])  # 2 valid combos
    result = StrategyComparisonService(db_session).run_comparison(req)
    assert result.total_configs_tested == 2
    assert len(result.rows) == 2


def test_comparison_returns_ranked_rows(db_session: Session) -> None:
    """Rows should be ranked 1..N, rank 1 having the highest score."""
    _make_asset(db_session)
    _make_bars(db_session, db_session.execute(
        select(Asset).where(Asset.symbol == "AAPL")
    ).scalar_one())
    _make_quality_report(db_session, "AAPL")
    req = _base_request(fast_windows=[3, 5], slow_windows=[10])
    result = StrategyComparisonService(db_session).run_comparison(req)
    ranks = [r.rank for r in result.rows]
    assert ranks == list(range(1, len(ranks) + 1))
    scores = [r.score for r in result.rows]
    assert scores == sorted(scores, reverse=True)


def test_no_valid_grid_raises_comparison_error(db_session: Session) -> None:
    """Raise ComparisonError with 400 if no valid combinations exist."""
    _make_asset(db_session)
    req = _base_request(fast_windows=[20], slow_windows=[5])
    with pytest.raises(ComparisonError):
        StrategyComparisonService(db_session).run_comparison(req)


# ── Endpoint tests ─────────────────────────────────────────────────────────

def test_endpoint_run_comparison_200(
    client: TestClient, db_session: Session,
) -> None:
    """POST /strategy-lab/comparisons/run returns 200 with valid payload."""
    _make_asset(db_session)
    _make_quality_report(db_session, "AAPL")
    payload = {
        "name": "Endpoint Test",
        "asset": "AAPL",
        "timeframe": "1d",
        "date_from": "2024-01-02T00:00:00Z",
        "date_to": "2024-02-01T00:00:00Z",
        "starting_capital": 10000.0,
        "allow_unapproved_data": True,
        "max_candles": 1000,
        "fast_windows": [3],
        "slow_windows": [10],
        "risk_rewards": [2.0],
        "hold_bars_options": [3],
        "risk_per_trade_pct_options": [0.5],
        "max_configs": 10,
    }
    resp = client.post("/strategy-lab/comparisons/run", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "backtest_run_id" in data
    assert data["total_configs_tested"] >= 1
    assert isinstance(data["rows"], list)


def test_endpoint_rejects_invalid_grid(
    client: TestClient, db_session: Session,
) -> None:
    """POST returns 400 when no valid grid combinations can be built."""
    _make_asset(db_session)
    payload = {
        "name": "Bad Grid",
        "asset": "AAPL",
        "timeframe": "1d",
        "date_from": "2024-01-02T00:00:00Z",
        "date_to": "2024-02-01T00:00:00Z",
        "starting_capital": 10000.0,
        "allow_unapproved_data": True,
        "max_candles": 1000,
        "fast_windows": [20],
        "slow_windows": [5],
        "risk_rewards": [2.0],
        "hold_bars_options": [3],
        "risk_per_trade_pct_options": [0.5],
        "max_configs": 10,
    }
    resp = client.post("/strategy-lab/comparisons/run", json=payload)
    assert resp.status_code == 400
    assert "No valid parameter" in resp.json()["detail"]


def test_comparison_result_summary_stored(db_session: Session) -> None:
    """result_summary on the BacktestRun should contain comparison_summary."""
    _make_asset(db_session)
    _make_quality_report(db_session, "AAPL")
    req = _base_request(fast_windows=[3], slow_windows=[10])
    result = StrategyComparisonService(db_session).run_comparison(req)
    run = db_session.get(BacktestRun, result.backtest_run_id)
    assert run is not None
    assert run.result_summary is not None
    assert "comparison_summary" in run.result_summary


def test_comparison_seeded_data_generates_non_zero_trades(db_session: Session) -> None:
    """At least one generated config should produce trades on deterministic seeded data."""
    asset = _make_asset(db_session, "AAPL")
    _make_bars_with_prices(db_session, asset, "1d", _long_signal_prices())
    _make_quality_report(db_session, "AAPL")

    req = _base_request(
        date_to=_T0 + timedelta(days=8),
        fast_windows=[3, 4],
        slow_windows=[5, 6],
        risk_rewards=[2.0],
        hold_bars_options=[3],
        risk_per_trade_pct_options=[0.5],
        max_configs=2,
    )
    result = StrategyComparisonService(db_session).run_comparison(req)

    assert result.total_configs_tested == 2
    assert any(row.total_trades > 0 for row in result.rows)

    strategy_results = db_session.execute(
        select(StrategyResult).where(StrategyResult.backtest_run_id == result.backtest_run_id)
    ).scalars().all()
    assert any(r.total_trades > 0 for r in strategy_results)
    assert any(r.strategy_config_id is not None for r in strategy_results)

    trades = db_session.execute(
        select(MockTrade).where(MockTrade.backtest_run_id == result.backtest_run_id)
    ).scalars().all()
    assert len(trades) > 0
    assert all(t.strategy_config_id is not None for t in trades)


def test_comparison_rows_include_config_ids_and_parameters(db_session: Session) -> None:
    """Comparison rows expose per-config identifiers and parameter payloads."""
    asset = _make_asset(db_session, "AAPL")
    _make_bars_with_prices(db_session, asset, "1d", _long_signal_prices())
    _make_quality_report(db_session, "AAPL")

    req = _base_request(
        date_to=_T0 + timedelta(days=8),
        fast_windows=[3],
        slow_windows=[5],
        risk_rewards=[2.0],
        hold_bars_options=[3],
        risk_per_trade_pct_options=[0.5],
        max_configs=1,
    )
    result = StrategyComparisonService(db_session).run_comparison(req)

    assert len(result.rows) == 1
    row = result.rows[0]
    assert row.strategy_config_id is not None
    assert isinstance(row.parameters, dict)
    assert row.parameters.get("fast_window") == 3
    assert row.parameters.get("slow_window") == 5


def test_comparison_clear_existing_results_does_not_wipe_new_outputs(db_session: Session) -> None:
    """Replay clear step should run before simulation and preserve newly created outputs."""
    asset = _make_asset(db_session, "AAPL")
    _make_bars_with_prices(db_session, asset, "1d", _long_signal_prices())
    _make_quality_report(db_session, "AAPL")

    req = _base_request(
        date_to=_T0 + timedelta(days=8),
        fast_windows=[3],
        slow_windows=[5],
        risk_rewards=[2.0],
        hold_bars_options=[3],
        risk_per_trade_pct_options=[0.5],
        max_configs=1,
    )
    result = StrategyComparisonService(db_session).run_comparison(req)

    trades = db_session.execute(
        select(MockTrade).where(MockTrade.backtest_run_id == result.backtest_run_id)
    ).scalars().all()
    strategy_results = db_session.execute(
        select(StrategyResult).where(StrategyResult.backtest_run_id == result.backtest_run_id)
    ).scalars().all()

    assert len(trades) > 0
    assert len(strategy_results) > 0
    assert any(r.total_trades > 0 for r in strategy_results)
