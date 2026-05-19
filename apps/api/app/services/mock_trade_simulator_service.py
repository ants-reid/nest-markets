"""MockTradeSimulatorService — MH-08 deterministic mock trade generation.

Only one strategy type is supported in this phase: `ma_momentum`.

MA Momentum rules:
    Parameters (all overridable via StrategyConfig.parameters):
        fast_window        = 3   (bars in fast MA)
        slow_window        = 5   (bars in slow MA)
        risk_reward        = 2.0 (target distance = stop distance × risk_reward)
        risk_per_trade_pct = 0.5 (% of current equity risked per trade)
        hold_bars          = 3   (max bars to hold if stop/target not hit)

    Long entry : fast MA crosses above slow MA
    Short entry: fast MA crosses below slow MA
    Entry price: close of signal candle
    Stop        : recent swing low (long) / swing high (short) over last slow_window candles
    Target      : entry ± stop_distance × risk_reward
    Exit order  : stop hit → loss, target hit → win, hold_bars elapsed → hold exit
    One open trade at a time per (asset, timeframe, strategy_config).
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.asset import Asset
from app.db.models.backtest_run import BacktestRun  # noqa: F401 (kept for future)
from app.db.models.bar import Bar
from app.db.models.drawdown_period import DrawdownPeriod
from app.db.models.equity_curve_point import EquityCurvePoint
from app.db.models.mock_trade import MockTrade
from app.db.models.strategy_config import StrategyConfig
from app.db.models.strategy_result import StrategyResult
from app.services.execution_cost_model import (
    COST_MODEL_VERSION,
    DEFAULT_COST_PROFILE,
    DEFAULT_STRESS_PRESET,
    build_profile_sensitivity_summary,
    calculate_cost_for_profile_and_scenario,
)
from app.services.strategy_result_quality_service import compute_result_quality

_logger = logging.getLogger(__name__)

_SUPPORTED_STRATEGIES: frozenset[str] = frozenset({"ma_momentum"})

_DEFAULT_MA_MOMENTUM_PARAMS: dict[str, Any] = {
    "fast_window": 3,
    "slow_window": 5,
    "risk_reward": 2.0,
    "risk_per_trade_pct": 0.5,
    "hold_bars": 3,
}


class SimulatorError(Exception):
    """Raised for controlled simulation failures."""


@dataclass
class _OpenTrade:
    entry_bar_index: int
    entry_time: datetime
    entry_price: float
    stop_price: float
    target_price: float
    side: str  # "long" | "short"
    risk_distance: float
    quantity: float
    strategy_config_id: uuid.UUID | None
    asset: str
    timeframe: str


@dataclass
class SimulationResult:
    """Aggregate metrics returned after one simulation pass."""

    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    breakeven: int = 0
    win_rate: float | None = None
    average_win: float | None = None
    average_loss: float | None = None
    profit_factor: float | None = None
    expectancy: float | None = None
    total_return_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    final_equity: float = 0.0
    warnings: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)


class MockTradeSimulatorService:
    """Run a deterministic ma_momentum simulation on a set of OHLCV bars."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def simulate(
        self,
        backtest_run_id: uuid.UUID,
        strategy_config: StrategyConfig | None,
        candles: list[Bar],
        starting_capital: float,
        asset: str,
        timeframe: str,
        cost_profile: str = DEFAULT_COST_PROFILE,
        stress_preset: str = DEFAULT_STRESS_PRESET,
    ) -> SimulationResult:
        """Simulate trades and persist all outputs.

        Returns a SimulationResult with aggregate metrics.
        Raises SimulatorError for unsupported strategy types.
        """
        strategy_type = "ma_momentum"
        params: dict[str, Any] = dict(_DEFAULT_MA_MOMENTUM_PARAMS)

        if strategy_config is not None:
            strategy_type = strategy_config.strategy_type
            if strategy_type not in _SUPPORTED_STRATEGIES:
                raise SimulatorError(
                    f"Strategy type '{strategy_type}' is not supported in MH-08. "
                    "Supported types: ma_momentum."
                )
            if strategy_config.parameters:
                params.update(strategy_config.parameters)

        config_id = strategy_config.id if strategy_config else None
        asset_row = self._session.execute(
            select(Asset).where(Asset.symbol == asset)
        ).scalar_one_or_none()
        asset_class = asset_row.asset_class.value if asset_row is not None else None

        fast_window = int(params.get("fast_window", 3))
        slow_window = int(params.get("slow_window", 5))
        risk_reward = float(params.get("risk_reward", 2.0))
        risk_per_trade_pct = float(params.get("risk_per_trade_pct", 0.5))
        hold_bars = int(params.get("hold_bars", 3))

        min_candles = slow_window + 1
        if len(candles) < min_candles:
            return SimulationResult(
                final_equity=starting_capital,
                warnings=[
                    f"Not enough candles ({len(candles)}) for "
                    f"slow_window={slow_window}. Minimum {min_candles} required."
                ],
            )

        return self._run_ma_momentum(
            backtest_run_id=backtest_run_id,
            config_id=config_id,
            candles=candles,
            starting_capital=starting_capital,
            asset=asset,
            timeframe=timeframe,
            asset_class=asset_class,
            cost_profile=cost_profile,
            stress_preset=stress_preset,
            fast_window=fast_window,
            slow_window=slow_window,
            risk_reward=risk_reward,
            risk_per_trade_pct=risk_per_trade_pct,
            hold_bars=hold_bars,
        )

    # ── Core simulation loop ────────────────────────────────────────────

    def _run_ma_momentum(
        self,
        backtest_run_id: uuid.UUID,
        config_id: uuid.UUID | None,
        candles: list[Bar],
        starting_capital: float,
        asset: str,
        timeframe: str,
        asset_class: str | None,
        cost_profile: str,
        stress_preset: str,
        fast_window: int,
        slow_window: int,
        risk_reward: float,
        risk_per_trade_pct: float,
        hold_bars: int,
    ) -> SimulationResult:
        closes = [float(c.close) for c in candles]
        highs = [float(c.high) for c in candles]
        lows = [float(c.low) for c in candles]

        equity = float(starting_capital)
        peak_equity = equity
        open_trade: _OpenTrade | None = None
        trades: list[MockTrade] = []
        equity_points: list[EquityCurvePoint] = []
        warnings: list[str] = []

        for i in range(slow_window, len(candles)):
            bar = candles[i]

            # ── Exit check ──────────────────────────────────────────────
            if open_trade is not None:
                bars_held = i - open_trade.entry_bar_index
                exit_price: float | None = None
                exit_reason = ""

                if open_trade.side == "long":
                    if lows[i] <= open_trade.stop_price:
                        exit_price, exit_reason = open_trade.stop_price, "stop"
                    elif highs[i] >= open_trade.target_price:
                        exit_price, exit_reason = open_trade.target_price, "target"
                    elif bars_held >= hold_bars:
                        exit_price, exit_reason = closes[i], "hold"
                else:  # short
                    if highs[i] >= open_trade.stop_price:
                        exit_price, exit_reason = open_trade.stop_price, "stop"
                    elif lows[i] <= open_trade.target_price:
                        exit_price, exit_reason = open_trade.target_price, "target"
                    elif bars_held >= hold_bars:
                        exit_price, exit_reason = closes[i], "hold"

                if exit_price is not None:
                    trade, pnl = self._close_trade(
                        open_trade, exit_price, exit_reason, bar.ts,
                        backtest_run_id, config_id,
                        asset_class=asset_class,
                        cost_profile=cost_profile,
                        stress_preset=stress_preset,
                    )
                    self._session.add(trade)
                    trades.append(trade)
                    equity += pnl
                    peak_equity = max(peak_equity, equity)
                    dd_pct = _drawdown_pct(peak_equity, equity)

                    eq_pt = _eq_point(backtest_run_id, bar.ts, equity, dd_pct)
                    self._session.add(eq_pt)
                    equity_points.append(eq_pt)
                    open_trade = None

            # ── Entry check (only one open trade at a time) ─────────────
            if open_trade is None:
                curr_fast = _sma(closes, i, fast_window)
                curr_slow = _sma(closes, i, slow_window)
                prev_fast = _sma(closes, i - 1, fast_window)
                prev_slow = _sma(closes, i - 1, slow_window)

                signal: str | None = None
                if prev_fast <= prev_slow and curr_fast > curr_slow:
                    signal = "long"
                elif prev_fast >= prev_slow and curr_fast < curr_slow:
                    signal = "short"

                if signal:
                    entry_price = closes[i]
                    if signal == "long":
                        stop_price = min(lows[max(0, i - slow_window): i])
                    else:
                        stop_price = max(highs[max(0, i - slow_window): i])

                    risk_dist = abs(entry_price - stop_price)
                    if risk_dist <= 0.0:
                        warnings.append(
                            f"Zero risk distance at bar {i} for {asset}/{timeframe}. "
                            "Skipping trade entry."
                        )
                        continue

                    risk_amount = equity * risk_per_trade_pct / 100.0
                    quantity = risk_amount / risk_dist

                    if signal == "long":
                        target_price = entry_price + risk_dist * risk_reward
                    else:
                        target_price = entry_price - risk_dist * risk_reward

                    open_trade = _OpenTrade(
                        entry_bar_index=i,
                        entry_time=bar.ts,
                        entry_price=entry_price,
                        stop_price=stop_price,
                        target_price=target_price,
                        side=signal,
                        risk_distance=risk_dist,
                        quantity=quantity,
                        strategy_config_id=config_id,
                        asset=asset,
                        timeframe=timeframe,
                    )

        # ── Close any trade still open at end of data ───────────────────
        if open_trade is not None:
            last_bar = candles[-1]
            trade, pnl = self._close_trade(
                open_trade, float(last_bar.close), "end_of_data", last_bar.ts,
                backtest_run_id, config_id,
                asset_class=asset_class,
                cost_profile=cost_profile,
                stress_preset=stress_preset,
            )
            self._session.add(trade)
            trades.append(trade)
            equity += pnl
            peak_equity = max(peak_equity, equity)
            dd_pct = _drawdown_pct(peak_equity, equity)
            eq_pt = _eq_point(backtest_run_id, last_bar.ts, equity, dd_pct)
            self._session.add(eq_pt)
            equity_points.append(eq_pt)

        # Nothing to persist if no trades were generated
        if not trades:
            return SimulationResult(
                final_equity=equity,
                total_return_pct=(equity - starting_capital) / starting_capital * 100,
                warnings=warnings,
            )

        # Add equity curve starting point (before first trade) and flush
        eq_start = _eq_point(backtest_run_id, candles[0].ts, starting_capital, 0.0)
        self._session.add(eq_start)
        # Put it at the front for drawdown detection ordering
        equity_points_ordered = [eq_start] + equity_points

        self._session.flush()

        # Detect and persist drawdown periods
        drawdown_periods = self._detect_drawdown_periods(backtest_run_id, equity_points_ordered)
        for ddp in drawdown_periods:
            self._session.add(ddp)

        # Compute aggregate metrics
        sim_result = self._compute_metrics(
            trades=trades,
            starting_capital=starting_capital,
            final_equity=equity,
            equity_points=equity_points_ordered,
            warnings=warnings,
        )

        # Persist StrategyResult
        sr = StrategyResult(
            backtest_run_id=backtest_run_id,
            strategy_config_id=config_id,
            asset=asset,
            timeframe=timeframe,
            total_trades=sim_result.total_trades,
            wins=sim_result.wins,
            losses=sim_result.losses,
            breakeven=sim_result.breakeven,
            win_rate=_dec(sim_result.win_rate, 6),
            average_win=_dec(sim_result.average_win, 4),
            average_loss=_dec(sim_result.average_loss, 4),
            profit_factor=_dec(sim_result.profit_factor, 4),
            expectancy=_dec(sim_result.expectancy, 4),
            total_return_pct=Decimal(str(round(sim_result.total_return_pct, 4))),
            max_drawdown_pct=Decimal(str(round(sim_result.max_drawdown_pct, 4))),
            metrics={
                **sim_result.metrics,
                "final_equity": round(sim_result.final_equity, 4),
                "strategy_type": "ma_momentum",
            },
        )
        self._session.add(sr)
        self._session.commit()

        return sim_result

    # ── Helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _close_trade(
        ot: _OpenTrade,
        exit_price: float,
        exit_reason: str,
        exit_time: datetime,
        backtest_run_id: uuid.UUID,
        config_id: uuid.UUID | None,
        asset_class: str | None = None,
        cost_profile: str = DEFAULT_COST_PROFILE,
        stress_preset: str = DEFAULT_STRESS_PRESET,
    ) -> tuple[MockTrade, float]:
        if ot.side == "long":
            pnl = (exit_price - ot.entry_price) * ot.quantity
            pnl_pct = (exit_price - ot.entry_price) / ot.entry_price * 100.0
            r_mult = (exit_price - ot.entry_price) / ot.risk_distance
        else:
            pnl = (ot.entry_price - exit_price) * ot.quantity
            pnl_pct = (ot.entry_price - exit_price) / ot.entry_price * 100.0
            r_mult = (ot.entry_price - exit_price) / ot.risk_distance

        low_cost_estimate = calculate_cost_for_profile_and_scenario(
            symbol=ot.asset,
            quantity=ot.quantity,
            entry_price=ot.entry_price,
            exit_price=exit_price,
            asset_class=asset_class,
            scenario="low",
            profile_name=cost_profile,
            stress_preset=stress_preset,
        )
        base_cost_estimate = calculate_cost_for_profile_and_scenario(
            symbol=ot.asset,
            quantity=ot.quantity,
            entry_price=ot.entry_price,
            exit_price=exit_price,
            asset_class=asset_class,
            scenario="base",
            profile_name=cost_profile,
            stress_preset=stress_preset,
        )
        high_cost_estimate = calculate_cost_for_profile_and_scenario(
            symbol=ot.asset,
            quantity=ot.quantity,
            entry_price=ot.entry_price,
            exit_price=exit_price,
            asset_class=asset_class,
            scenario="high",
            profile_name=cost_profile,
            stress_preset=stress_preset,
        )

        sensitivity_summary = build_profile_sensitivity_summary(
            symbol=ot.asset,
            quantity=ot.quantity,
            entry_price=ot.entry_price,
            exit_price=exit_price,
            gross_pnl_amount=pnl,
            profile_name=cost_profile,
            stress_preset=stress_preset,
            asset_class=asset_class,
        )

        net_pnl = float(sensitivity_summary["base_net_pnl_amount"])
        base_notional = max(abs(ot.entry_price * ot.quantity), 1e-9)
        net_pnl_pct = net_pnl / base_notional * 100.0
        gross_risk_amount = max(abs(ot.risk_distance * ot.quantity), 1e-9)
        net_r_mult = net_pnl / gross_risk_amount

        if pnl > 0.0001:
            result = "win"
        elif pnl < -0.0001:
            result = "loss"
        else:
            result = "breakeven"

        trade = MockTrade(
            backtest_run_id=backtest_run_id,
            strategy_config_id=config_id,
            asset=ot.asset,
            timeframe=ot.timeframe,
            side=ot.side,
            entry_time=ot.entry_time,
            entry_price=Decimal(str(round(ot.entry_price, 8))),
            stop_price=Decimal(str(round(ot.stop_price, 8))),
            target_price=Decimal(str(round(ot.target_price, 8))),
            exit_time=exit_time,
            exit_price=Decimal(str(round(exit_price, 8))),
            status="closed",
            result=result,
            pnl_amount=Decimal(str(round(pnl, 4))),
            pnl_pct=Decimal(str(round(pnl_pct, 6))),
            r_multiple=Decimal(str(round(r_mult, 4))),
            reason_for_entry="ma_momentum cross",
            reason_for_exit=exit_reason,
            metadata_json={
                "quantity": round(ot.quantity, 6),
                "cost_model_version": base_cost_estimate.cost_model_version,
                "asset_class": base_cost_estimate.asset_class,
                "cost_scenario_used": "base",
                "cost_profile_used": cost_profile,
                "stress_preset_used": stress_preset,
                "broker_calibrated": False,
                "spread_bps": base_cost_estimate.spread_bps,
                "slippage_bps": base_cost_estimate.slippage_bps,
                "commission_bps": base_cost_estimate.commission_bps,
                "fixed_fee_per_trade": base_cost_estimate.fixed_fee_per_trade,
                "round_trip_cost_bps": base_cost_estimate.round_trip_cost_bps,
                "estimated_entry_cost": base_cost_estimate.estimated_entry_cost,
                "estimated_exit_cost": base_cost_estimate.estimated_exit_cost,
                "estimated_total_cost": base_cost_estimate.estimated_total_cost,
                "low_cost_estimate": {
                    "cost_scenario": low_cost_estimate.cost_scenario,
                    "estimated_entry_cost": low_cost_estimate.estimated_entry_cost,
                    "estimated_exit_cost": low_cost_estimate.estimated_exit_cost,
                    "estimated_total_cost": low_cost_estimate.estimated_total_cost,
                    "round_trip_cost_bps": low_cost_estimate.round_trip_cost_bps,
                },
                "base_cost_estimate": {
                    "cost_scenario": base_cost_estimate.cost_scenario,
                    "estimated_entry_cost": base_cost_estimate.estimated_entry_cost,
                    "estimated_exit_cost": base_cost_estimate.estimated_exit_cost,
                    "estimated_total_cost": base_cost_estimate.estimated_total_cost,
                    "round_trip_cost_bps": base_cost_estimate.round_trip_cost_bps,
                },
                "high_cost_estimate": {
                    "cost_scenario": high_cost_estimate.cost_scenario,
                    "estimated_entry_cost": high_cost_estimate.estimated_entry_cost,
                    "estimated_exit_cost": high_cost_estimate.estimated_exit_cost,
                    "estimated_total_cost": high_cost_estimate.estimated_total_cost,
                    "round_trip_cost_bps": high_cost_estimate.round_trip_cost_bps,
                },
                "gross_pnl_amount": round(pnl, 4),
                "gross_pnl_pct": round(pnl_pct, 6),
                "gross_r_multiple": round(r_mult, 4),
                "net_pnl_amount": round(net_pnl, 4),
                "net_pnl_pct": round(net_pnl_pct, 6),
                "net_r_multiple": round(net_r_mult, 4),
                "low_net_pnl_amount": round(float(sensitivity_summary["low_net_pnl_amount"]), 4),
                "base_net_pnl_amount": round(float(sensitivity_summary["base_net_pnl_amount"]), 4),
                "high_net_pnl_amount": round(float(sensitivity_summary["high_net_pnl_amount"]), 4),
                "low_total_cost_amount": round(float(sensitivity_summary["low_total_cost_amount"]), 6),
                "base_total_cost_amount": round(float(sensitivity_summary["base_total_cost_amount"]), 6),
                "high_total_cost_amount": round(float(sensitivity_summary["high_total_cost_amount"]), 6),
                "cost_drag_low_pct": sensitivity_summary["cost_drag_low_pct"],
                "cost_drag_base_pct": sensitivity_summary["cost_drag_base_pct"],
                "cost_drag_high_pct": sensitivity_summary["cost_drag_high_pct"],
                "cost_sensitivity_level": sensitivity_summary["cost_sensitivity_level"],
                "profile_sensitivity_summary": sensitivity_summary,
            },
        )
        return trade, pnl

    def _detect_drawdown_periods(
        self,
        backtest_run_id: uuid.UUID,
        equity_points: list[EquityCurvePoint],
    ) -> list[DrawdownPeriod]:
        if len(equity_points) < 2:
            return []

        periods: list[DrawdownPeriod] = []
        peak_eq = float(equity_points[0].equity)
        peak_ts = equity_points[0].timestamp
        in_dd = False
        dd_start_ts = peak_ts
        trough_eq = peak_eq
        trough_ts = peak_ts

        for pt in equity_points[1:]:
            eq = float(pt.equity)
            if eq > peak_eq:
                if in_dd:
                    max_dd = (peak_eq - trough_eq) / peak_eq * 100.0 if peak_eq > 0 else 0.0
                    periods.append(DrawdownPeriod(
                        backtest_run_id=backtest_run_id,
                        start_time=dd_start_ts,
                        trough_time=trough_ts,
                        end_time=pt.timestamp,
                        max_drawdown_pct=Decimal(str(round(max_dd, 4))),
                        recovered=True,
                    ))
                    in_dd = False
                peak_eq = eq
                peak_ts = pt.timestamp
            elif eq < peak_eq:
                if not in_dd:
                    in_dd = True
                    dd_start_ts = peak_ts
                    trough_eq = eq
                    trough_ts = pt.timestamp
                elif eq < trough_eq:
                    trough_eq = eq
                    trough_ts = pt.timestamp

        if in_dd:
            max_dd = (peak_eq - trough_eq) / peak_eq * 100.0 if peak_eq > 0 else 0.0
            periods.append(DrawdownPeriod(
                backtest_run_id=backtest_run_id,
                start_time=dd_start_ts,
                trough_time=trough_ts,
                end_time=None,
                max_drawdown_pct=Decimal(str(round(max_dd, 4))),
                recovered=False,
            ))

        return periods

    @staticmethod
    def _compute_metrics(
        trades: list[MockTrade],
        starting_capital: float,
        final_equity: float,
        equity_points: list[EquityCurvePoint],
        warnings: list[str],
    ) -> SimulationResult:
        total = len(trades)
        wins = sum(1 for t in trades if t.result == "win")
        losses = sum(1 for t in trades if t.result == "loss")
        breakeven = total - wins - losses

        if total == 0:
            return SimulationResult(
                final_equity=final_equity,
                total_return_pct=(final_equity - starting_capital) / starting_capital * 100,
                warnings=warnings,
            )

        win_rate = wins / total
        win_pnls = [float(t.pnl_amount) for t in trades if t.result == "win" and t.pnl_amount is not None]
        loss_pnls = [abs(float(t.pnl_amount)) for t in trades if t.result == "loss" and t.pnl_amount is not None]

        avg_win = sum(win_pnls) / len(win_pnls) if win_pnls else None
        avg_loss = sum(loss_pnls) / len(loss_pnls) if loss_pnls else None
        gross_profit = sum(win_pnls)
        gross_loss = sum(loss_pnls)
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else None

        total_cost_amount = sum(
            _meta_float(t.metadata_json, "estimated_total_cost")
            for t in trades
        )
        low_total_cost_amount = sum(_meta_float(t.metadata_json, "low_total_cost_amount") for t in trades)
        base_total_cost_amount = sum(_meta_float(t.metadata_json, "base_total_cost_amount") for t in trades)
        high_total_cost_amount = sum(_meta_float(t.metadata_json, "high_total_cost_amount") for t in trades)

        low_net_pnls = [_meta_float(t.metadata_json, "low_net_pnl_amount") for t in trades]
        base_net_pnls = [_meta_float(t.metadata_json, "base_net_pnl_amount") for t in trades]
        high_net_pnls = [_meta_float(t.metadata_json, "high_net_pnl_amount") for t in trades]

        net_profit = sum(v for v in base_net_pnls if v > 0)
        net_loss = abs(sum(v for v in base_net_pnls if v < 0))
        net_profit_factor = net_profit / net_loss if net_loss > 0 else None
        net_expectancy = (sum(base_net_pnls) / len(base_net_pnls)) if base_net_pnls else None
        net_final_equity = starting_capital + sum(base_net_pnls)
        net_total_return_pct = (
            (net_final_equity - starting_capital) / starting_capital * 100
            if starting_capital > 0
            else 0.0
        )

        low_net_profit = sum(v for v in low_net_pnls if v > 0)
        low_net_loss = abs(sum(v for v in low_net_pnls if v < 0))
        low_net_profit_factor = low_net_profit / low_net_loss if low_net_loss > 0 else None
        low_net_final_equity = starting_capital + sum(low_net_pnls)
        low_net_total_return_pct = (
            (low_net_final_equity - starting_capital) / starting_capital * 100
            if starting_capital > 0
            else 0.0
        )

        high_net_profit = sum(v for v in high_net_pnls if v > 0)
        high_net_loss = abs(sum(v for v in high_net_pnls if v < 0))
        high_net_profit_factor = high_net_profit / high_net_loss if high_net_loss > 0 else None
        high_net_final_equity = starting_capital + sum(high_net_pnls)
        high_net_total_return_pct = (
            (high_net_final_equity - starting_capital) / starting_capital * 100
            if starting_capital > 0
            else 0.0
        )

        levels = [
            _meta_str(t.metadata_json, "cost_sensitivity_level")
            for t in trades
        ]
        sensitivity_rank = {"low": 0, "medium": 1, "high": 2, "loss_sensitive": 3}
        max_level = "low"
        max_rank = -1
        for level in levels:
            rank = sensitivity_rank.get(level, -1)
            if rank > max_rank:
                max_rank = rank
                max_level = level if level else "low"

        if avg_win is not None and avg_loss is not None:
            expectancy = win_rate * avg_win - (1 - win_rate) * avg_loss
        else:
            expectancy = None

        total_return_pct = (final_equity - starting_capital) / starting_capital * 100

        max_dd = max(
            (float(pt.drawdown_pct) for pt in equity_points if pt.drawdown_pct is not None),
            default=0.0,
        )

        return SimulationResult(
            total_trades=total,
            wins=wins,
            losses=losses,
            breakeven=breakeven,
            win_rate=win_rate,
            average_win=avg_win,
            average_loss=avg_loss,
            profit_factor=profit_factor,
            expectancy=expectancy,
            total_return_pct=total_return_pct,
            max_drawdown_pct=max_dd,
            final_equity=final_equity,
            warnings=warnings,
            metrics={
                "cost_model_version": COST_MODEL_VERSION,
                "cost_scenario_default": "base",
                "cost_profile_default": DEFAULT_COST_PROFILE,
                "stress_preset_default": DEFAULT_STRESS_PRESET,
                "broker_calibrated": False,
                "execution_costs_modelled": True,
                "spread_modelled": True,
                "slippage_modelled": True,
                "fees_modelled": True,
                "gross_total_return_pct": round(total_return_pct, 6),
                "low_net_total_return_pct": round(low_net_total_return_pct, 6),
                "base_net_total_return_pct": round(net_total_return_pct, 6),
                "high_net_total_return_pct": round(high_net_total_return_pct, 6),
                "net_total_return_pct": round(net_total_return_pct, 6),
                "gross_profit_factor": round(profit_factor, 6) if profit_factor is not None else None,
                "low_net_profit_factor": round(low_net_profit_factor, 6) if low_net_profit_factor is not None else None,
                "base_net_profit_factor": round(net_profit_factor, 6) if net_profit_factor is not None else None,
                "high_net_profit_factor": round(high_net_profit_factor, 6) if high_net_profit_factor is not None else None,
                "net_profit_factor": round(net_profit_factor, 6) if net_profit_factor is not None else None,
                "gross_expectancy": round(expectancy, 6) if expectancy is not None else None,
                "net_expectancy": round(net_expectancy, 6) if net_expectancy is not None else None,
                "low_total_cost_amount": round(low_total_cost_amount, 6),
                "base_total_cost_amount": round(base_total_cost_amount, 6),
                "high_total_cost_amount": round(high_total_cost_amount, 6),
                "total_cost_amount": round(total_cost_amount, 6),
                "average_cost_per_trade": round(total_cost_amount / total, 6) if total > 0 else 0.0,
                "gross_final_equity": round(final_equity, 6),
                "net_final_equity": round(net_final_equity, 6),
                "cost_sensitivity_level": max_level,
                "profile_sensitivity_level": max_level,
                "stress_scenario_notes": (
                    "Profiles and stress presets are deterministic research "
                    "assumptions and are not broker-calibrated."
                ),
                **compute_result_quality(
                    total_trades=total,
                    net_profit_factor=net_profit_factor,
                    net_total_return_pct=net_total_return_pct,
                    max_drawdown_pct=max_dd,
                    cost_sensitivity_level=max_level,
                    high_cost_net_total_return_pct=high_net_total_return_pct,
                    high_cost_net_profit_factor=high_net_profit_factor,
                    monthly_returns=None,
                    asset_count=1,
                    timeframe_count=1,
                ),
            },
        )


# ── Module-level helpers ────────────────────────────────────────────────────

def _sma(closes: list[float], end_idx: int, window: int) -> float:
    """Simple moving average ending at end_idx (inclusive)."""
    start = max(0, end_idx - window + 1)
    segment = closes[start: end_idx + 1]
    return sum(segment) / len(segment) if segment else 0.0


def _drawdown_pct(peak: float, current: float) -> float:
    return (peak - current) / peak * 100.0 if peak > 0 else 0.0


def _eq_point(
    backtest_run_id: uuid.UUID,
    ts: datetime,
    equity: float,
    drawdown_pct: float,
) -> EquityCurvePoint:
    return EquityCurvePoint(
        backtest_run_id=backtest_run_id,
        timestamp=ts,
        equity=Decimal(str(round(equity, 4))),
        cash=Decimal(str(round(equity, 4))),
        open_pnl=Decimal("0"),
        drawdown_pct=Decimal(str(round(drawdown_pct, 6))),
    )


def _dec(value: float | None, places: int) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(round(value, places)))


def _meta_float(metadata: dict[str, Any] | None, key: str) -> float:
    if not isinstance(metadata, dict):
        return 0.0
    value = metadata.get(key)
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _meta_str(metadata: dict[str, Any] | None, key: str) -> str:
    if not isinstance(metadata, dict):
        return ""
    value = metadata.get(key)
    return str(value) if value is not None else ""
