"""StrategyComparisonService — MH-10 multi-config ma_momentum comparison runner."""

from __future__ import annotations

import itertools
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.models.backtest_run import BacktestRun
from app.db.models.strategy_config import StrategyConfig
from app.db.models.strategy_result import StrategyResult
from app.schemas.strategy_lab import (
    StrategyComparisonRequest,
    StrategyComparisonResponse,
    StrategyComparisonRow,
)
from app.services.historical_replay_service import HistoricalReplayService, ReplayError
from app.services.execution_cost_model import DEFAULT_COST_PROFILE, DEFAULT_STRESS_PRESET

_HARD_MAX_CONFIGS = 100


class ComparisonError(Exception):
    """Raised for controlled comparison failures."""


def _compute_score(
    profit_factor: float | None,
    total_return_pct: float | None,
    win_rate: float | None,
    max_drawdown_pct: float | None,
    total_trades: int,
) -> float:
    """Deterministic risk-aware score in range [0, 100]."""
    score = 0.0

    pf = float(profit_factor) if profit_factor is not None else 0.0
    ret = float(total_return_pct) if total_return_pct is not None else 0.0
    wr = float(win_rate) if win_rate is not None else 0.0
    dd = float(max_drawdown_pct) if max_drawdown_pct is not None else 0.0

    score += min(pf, 5.0) * 30      # cap PF contribution at 5.0 * 30 = 150 before clamp
    score += ret * 2
    score += wr * 20
    score -= dd * 3

    if total_trades < 5:
        score -= 25
    elif total_trades < 10:
        score -= 10

    return float(max(0.0, min(100.0, score)))


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _resolve_scoring_inputs(result: StrategyResult) -> tuple[float | None, float | None, bool]:
    """Prefer net metrics when available; fall back to gross fields."""
    metrics = result.metrics if isinstance(result.metrics, dict) else {}

    net_profit_factor = _safe_float(metrics.get("base_net_profit_factor"))
    net_total_return_pct = _safe_float(metrics.get("base_net_total_return_pct"))
    if net_profit_factor is None:
        net_profit_factor = _safe_float(metrics.get("net_profit_factor"))
    if net_total_return_pct is None:
        net_total_return_pct = _safe_float(metrics.get("net_total_return_pct"))
    gross_profit_factor = _safe_float(result.profit_factor)
    gross_total_return_pct = _safe_float(result.total_return_pct)

    used_gross_fallback = False
    if net_profit_factor is None:
        net_profit_factor = gross_profit_factor
        used_gross_fallback = True
    if net_total_return_pct is None:
        net_total_return_pct = gross_total_return_pct
        used_gross_fallback = True

    return net_profit_factor, net_total_return_pct, used_gross_fallback


class StrategyComparisonService:
    """Run a parameter grid over ma_momentum and return ranked results."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def run_comparison(
        self,
        request: StrategyComparisonRequest,
    ) -> StrategyComparisonResponse:
        warnings: list[str] = [
            "Comparison runs currently create new StrategyConfig rows and do not "
            "deduplicate equivalent parameter sets. This is acceptable for research "
            "but may grow storage over time.",
            "Cost profiles and stress presets are deterministic research assumptions "
            "and are not broker-calibrated.",
        ]

        # Build parameter grid
        grid: list[dict[str, Any]] = []
        for fw, sw, rr, hb, rp in itertools.product(
            request.fast_windows,
            request.slow_windows,
            request.risk_rewards,
            request.hold_bars_options,
            request.risk_per_trade_pct_options,
        ):
            if fw >= sw:
                continue
            grid.append(
                {
                    "fast_window": fw,
                    "slow_window": sw,
                    "risk_reward": rr,
                    "hold_bars": hb,
                    "risk_per_trade_pct": rp,
                }
            )

        if not grid:
            raise ComparisonError(
                "No valid parameter combinations generated. "
                "Ensure at least one fast_window < slow_window combination exists."
            )

        effective_max = min(request.max_configs, _HARD_MAX_CONFIGS)
        if len(grid) > effective_max:
            warnings.append(
                f"Grid had {len(grid)} combinations; truncated to {effective_max} "
                f"(max_configs={request.max_configs}, hard_max={_HARD_MAX_CONFIGS})."
            )
            grid = grid[:effective_max]

        # Create StrategyConfig rows
        configs: list[StrategyConfig] = []
        for idx, params in enumerate(grid):
            fw = params["fast_window"]
            sw = params["slow_window"]
            rr = params["risk_reward"]
            hb = params["hold_bars"]
            rp = params["risk_per_trade_pct"]
            cfg_name = (
                f"{request.name} | fw={fw} sw={sw} rr={rr} hb={hb} rp={rp}"
            )
            cfg = StrategyConfig(
                name=cfg_name,
                strategy_type="ma_momentum",
                asset=request.asset,
                timeframe=request.timeframe,
                parameters=params,
                risk_settings={},
                enabled=True,
            )
            self._session.add(cfg)
            configs.append(cfg)

        self._session.flush()  # assign IDs without committing yet

        config_ids = [str(cfg.id) for cfg in configs]

        # Create one BacktestRun for all configs
        run = BacktestRun(
            name=request.name,
            status="queued",
            date_from=request.date_from,
            date_to=request.date_to,
            requested_assets={"assets": [request.asset]},
            requested_timeframes={"timeframes": [request.timeframe]},
            strategy_config_ids={"config_ids": config_ids},
            starting_capital=Decimal(str(request.starting_capital)),
        )
        self._session.add(run)
        self._session.commit()
        self._session.refresh(run)
        for cfg in configs:
            self._session.refresh(cfg)

        # Run replay/simulation using existing pipeline
        replay_svc = HistoricalReplayService(self._session)
        try:
            replay_svc.replay(
                run.id,
                allow_unapproved_data=request.allow_unapproved_data,
                max_candles=request.max_candles,
                simulate_trades=True,
                clear_existing_results=True,
            )
        except ReplayError as exc:
            raise ComparisonError(f"Comparison replay failed: {exc}") from exc

        # Fetch StrategyResult rows produced for this run
        results = self._session.execute(
            select(StrategyResult).where(StrategyResult.backtest_run_id == run.id)
        ).scalars().all()

        # Build a lookup by strategy_config_id
        result_by_config: dict[uuid.UUID, StrategyResult] = {}
        for res in results:
            if res.strategy_config_id is not None:
                result_by_config[res.strategy_config_id] = res

        # Build comparison rows for every config
        rows: list[StrategyComparisonRow] = []
        gross_fallback_rows = 0
        high_cost_sensitive_rows = 0
        low_quality_rows = 0
        for cfg in configs:
            res = result_by_config.get(cfg.id)
            total_trades = res.total_trades if res else 0
            wins = res.wins if res else 0
            losses = res.losses if res else 0
            win_rate = float(res.win_rate) if res and res.win_rate is not None else None
            profit_factor = float(res.profit_factor) if res and res.profit_factor is not None else None
            expectancy = float(res.expectancy) if res and res.expectancy is not None else None
            total_return_pct = float(res.total_return_pct) if res and res.total_return_pct is not None else None
            max_drawdown_pct = float(res.max_drawdown_pct) if res and res.max_drawdown_pct is not None else None
            high_cost_scenario_net_return_pct = None
            high_cost_scenario_profit_factor = None
            cost_sensitivity_level = None
            quality_grade = None
            research_confidence_score = None
            overfitting_risk_score = None
            quality_warnings: list[str] = []
            validation_stability_score = None
            validation_stability_grade = None
            out_of_sample_pass = None
            walk_forward_warnings: list[str] = []

            scoring_profit_factor = profit_factor
            scoring_total_return_pct = total_return_pct
            if res is not None:
                scoring_profit_factor, scoring_total_return_pct, used_gross_fallback = _resolve_scoring_inputs(res)
                if used_gross_fallback:
                    gross_fallback_rows += 1
                metrics = res.metrics if isinstance(res.metrics, dict) else {}
                high_cost_scenario_net_return_pct = _safe_float(metrics.get("high_net_total_return_pct"))
                high_cost_scenario_profit_factor = _safe_float(metrics.get("high_net_profit_factor"))
                raw_level = metrics.get("cost_sensitivity_level")
                cost_sensitivity_level = str(raw_level) if raw_level is not None else None
                raw_grade = metrics.get("quality_grade")
                quality_grade = str(raw_grade) if raw_grade is not None else None
                research_confidence_score = _safe_float(metrics.get("research_confidence_score"))
                overfitting_risk_score = _safe_float(metrics.get("overfitting_risk_score"))
                raw_quality_warnings = metrics.get("quality_warnings")
                if isinstance(raw_quality_warnings, list):
                    quality_warnings = [str(w) for w in raw_quality_warnings]
                validation_stability_score = _safe_float(metrics.get("validation_stability_score"))
                raw_stability_grade = metrics.get("validation_stability_grade")
                validation_stability_grade = (
                    str(raw_stability_grade) if raw_stability_grade is not None else None
                )
                raw_oos_pass = metrics.get("out_of_sample_pass")
                if isinstance(raw_oos_pass, bool):
                    out_of_sample_pass = raw_oos_pass
                raw_walk_warnings = metrics.get("walk_forward_warnings")
                if isinstance(raw_walk_warnings, list):
                    walk_forward_warnings = [str(w) for w in raw_walk_warnings]
                if quality_grade in {"D", "F"}:
                    low_quality_rows += 1
                if (
                    high_cost_scenario_net_return_pct is not None
                    and high_cost_scenario_net_return_pct < 0
                ) or (
                    high_cost_scenario_profit_factor is not None
                    and high_cost_scenario_profit_factor < 1.0
                ):
                    high_cost_sensitive_rows += 1

            score = _compute_score(
                profit_factor=scoring_profit_factor,
                total_return_pct=scoring_total_return_pct,
                win_rate=win_rate,
                max_drawdown_pct=max_drawdown_pct,
                total_trades=total_trades,
            )

            rows.append(
                StrategyComparisonRow(
                    strategy_config_id=cfg.id,
                    strategy_name=cfg.name,
                    backtest_run_id=run.id,
                    asset=cfg.asset,
                    timeframe=cfg.timeframe,
                    parameters=cfg.parameters or {},
                    total_trades=total_trades,
                    wins=wins,
                    losses=losses,
                    win_rate=win_rate,
                    profit_factor=profit_factor,
                    expectancy=expectancy,
                    total_return_pct=total_return_pct,
                    max_drawdown_pct=max_drawdown_pct,
                    scoring_cost_scenario="base",
                    high_cost_scenario_net_return_pct=high_cost_scenario_net_return_pct,
                    high_cost_scenario_profit_factor=high_cost_scenario_profit_factor,
                    cost_sensitivity_level=cost_sensitivity_level,
                    quality_grade=quality_grade,
                    research_confidence_score=research_confidence_score,
                    overfitting_risk_score=overfitting_risk_score,
                    quality_warnings=quality_warnings,
                    validation_stability_score=validation_stability_score,
                    validation_stability_grade=validation_stability_grade,
                    out_of_sample_pass=out_of_sample_pass,
                    walk_forward_warnings=walk_forward_warnings,
                    score=score,
                    rank=0,  # assigned below
                )
            )

        # Sort by score descending and assign ranks
        rows.sort(key=lambda r: r.score, reverse=True)
        for i, row in enumerate(rows):
            row.rank = i + 1

        if gross_fallback_rows > 0:
            warnings.append(
                "Some comparison rows were scored using gross metrics because net "
                "metrics were missing in strategy_results.metrics."
            )
        if high_cost_sensitive_rows > 0:
            warnings.append(
                "Strategy is sensitive to execution costs under high-cost assumptions."
            )
        if low_quality_rows > 0:
            warnings.append(
                "Some strategies received low research quality grades (D/F); "
                "review sample size, drawdown, and overfitting risk before any promotion."
            )

        # Persist comparison summary in result_summary
        run_row = self._session.get(BacktestRun, run.id)
        if run_row is not None:
            run_row.result_summary = {
                **(run_row.result_summary or {}),
                "comparison_summary": {
                    "total_configs_tested": len(rows),
                    "asset": request.asset,
                    "timeframe": request.timeframe,
                    "scoring_cost_scenario": "base",
                    "cost_profile_used": DEFAULT_COST_PROFILE,
                    "stress_preset_used": DEFAULT_STRESS_PRESET,
                    "broker_calibrated": False,
                    "high_cost_sensitive_rows": high_cost_sensitive_rows,
                    "low_quality_rows": low_quality_rows,
                    "generated_at": datetime.now(tz=timezone.utc).isoformat(),
                },
            }
            self._session.commit()

        return StrategyComparisonResponse(
            backtest_run_id=run.id,
            total_configs_tested=len(rows),
            asset=request.asset,
            timeframe=request.timeframe,
            cost_profile_used=DEFAULT_COST_PROFILE,
            stress_preset_used=DEFAULT_STRESS_PRESET,
            broker_calibrated=False,
            rows=rows,
            warnings=warnings,
            message=(
                f"Comparison complete. {len(rows)} config(s) tested on "
                f"{request.asset}/{request.timeframe}."
            ),
        )
