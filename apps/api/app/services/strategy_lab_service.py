"""Strategy Lab service — data contract operations for MH-06.

Responsibilities for this phase (MH-06):
- CRUD for StrategyConfig
- Create/list/get BacktestRun stubs (no replay)
- List sub-resources for a run (trades, results, equity curve, drawdowns)

Historical replay and mock trade generation are deferred to MH-07.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from datetime import datetime
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.db.models.backtest_run import BacktestRun
from app.db.models.drawdown_period import DrawdownPeriod
from app.db.models.equity_curve_point import EquityCurvePoint
from app.db.models.mock_trade import MockTrade
from app.db.models.strategy_config import StrategyConfig
from app.db.models.strategy_result import StrategyResult
from app.services.walk_forward_validation_service import (
    build_rolling_fold_splits,
    build_date_splits,
    calculate_multi_fold_summary,
    calculate_period_metrics,
    calculate_walk_forward_summary,
)

_STUB_MESSAGE = (
    "Backtest record created. Historical replay engine is scheduled for MH-07."
)


class StrategyLabService:
    """Read/write operations for Strategy Lab data contracts."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # ── Strategy Configs ───────────────────────────────────────────────

    def create_config(
        self,
        name: str,
        strategy_type: str,
        asset: str,
        timeframe: str,
        parameters: dict[str, Any] | None = None,
        risk_settings: dict[str, Any] | None = None,
        enabled: bool = True,
    ) -> StrategyConfig:
        config = StrategyConfig(
            name=name,
            strategy_type=strategy_type,
            asset=asset,
            timeframe=timeframe,
            parameters=parameters or {},
            risk_settings=risk_settings or {},
            enabled=enabled,
        )
        self._session.add(config)
        self._session.commit()
        self._session.refresh(config)
        return config

    def list_configs(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[int, list[StrategyConfig]]:
        total = self._session.execute(
            select(func.count()).select_from(StrategyConfig)
        ).scalar_one()
        items = self._session.execute(
            select(StrategyConfig)
            .order_by(StrategyConfig.created_at.desc())
            .limit(limit)
            .offset(offset)
        ).scalars().all()
        return total, list(items)

    def get_config(self, config_id: uuid.UUID) -> StrategyConfig | None:
        return self._session.get(StrategyConfig, config_id)

    # ── Backtest Runs ──────────────────────────────────────────────────

    def create_backtest_run(
        self,
        name: str,
        date_from: datetime,
        date_to: datetime,
        requested_assets: list[str],
        requested_timeframes: list[str],
        strategy_config_ids: list[str],
        starting_capital: float = 10000.0,
    ) -> tuple[BacktestRun, str]:
        """Create a queued backtest run stub. Returns (run, message).

        The replay engine is not invoked here; that is MH-07 scope.
        """
        run = BacktestRun(
            name=name,
            status="queued",
            date_from=date_from,
            date_to=date_to,
            requested_assets={"assets": requested_assets},
            requested_timeframes={"timeframes": requested_timeframes},
            strategy_config_ids={"config_ids": strategy_config_ids},
            starting_capital=starting_capital,
        )
        self._session.add(run)
        self._session.commit()
        self._session.refresh(run)
        return run, _STUB_MESSAGE

    def list_backtest_runs(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[int, list[BacktestRun]]:
        total = self._session.execute(
            select(func.count()).select_from(BacktestRun)
        ).scalar_one()
        items = self._session.execute(
            select(BacktestRun)
            .order_by(BacktestRun.created_at.desc())
            .limit(limit)
            .offset(offset)
        ).scalars().all()
        return total, list(items)

    def get_backtest_run(self, run_id: uuid.UUID) -> BacktestRun | None:
        return self._session.get(BacktestRun, run_id)

    # ── Sub-resource queries (all return empty lists in MH-06) ─────────

    def list_trades(
        self,
        run_id: uuid.UUID,
        limit: int = 200,
        offset: int = 0,
    ) -> tuple[int, list[MockTrade]]:
        total = self._session.execute(
            select(func.count())
            .select_from(MockTrade)
            .where(MockTrade.backtest_run_id == run_id)
        ).scalar_one()
        items = self._session.execute(
            select(MockTrade)
            .where(MockTrade.backtest_run_id == run_id)
            .order_by(MockTrade.entry_time.asc())
            .limit(limit)
            .offset(offset)
        ).scalars().all()
        return total, list(items)

    def list_results(
        self,
        run_id: uuid.UUID,
    ) -> tuple[int, list[StrategyResult]]:
        total = self._session.execute(
            select(func.count())
            .select_from(StrategyResult)
            .where(StrategyResult.backtest_run_id == run_id)
        ).scalar_one()
        items = self._session.execute(
            select(StrategyResult)
            .where(StrategyResult.backtest_run_id == run_id)
        ).scalars().all()
        return total, list(items)

    def list_equity_curve(
        self,
        run_id: uuid.UUID,
        limit: int = 5000,
        offset: int = 0,
    ) -> tuple[int, list[EquityCurvePoint]]:
        total = self._session.execute(
            select(func.count())
            .select_from(EquityCurvePoint)
            .where(EquityCurvePoint.backtest_run_id == run_id)
        ).scalar_one()
        items = self._session.execute(
            select(EquityCurvePoint)
            .where(EquityCurvePoint.backtest_run_id == run_id)
            .order_by(EquityCurvePoint.timestamp.asc())
            .limit(limit)
            .offset(offset)
        ).scalars().all()
        return total, list(items)

    def list_drawdowns(
        self,
        run_id: uuid.UUID,
    ) -> tuple[int, list[DrawdownPeriod]]:
        total = self._session.execute(
            select(func.count())
            .select_from(DrawdownPeriod)
            .where(DrawdownPeriod.backtest_run_id == run_id)
        ).scalar_one()
        items = self._session.execute(
            select(DrawdownPeriod)
            .where(DrawdownPeriod.backtest_run_id == run_id)
            .order_by(DrawdownPeriod.start_time.asc())
        ).scalars().all()
        return total, list(items)

    def clear_backtest_outputs(self, run_id: uuid.UUID) -> None:
        """Delete all simulation outputs (mock trades, results, equity curve, drawdowns)."""
        from sqlalchemy import delete as sa_delete

        from app.db.models.drawdown_period import DrawdownPeriod as DD
        from app.db.models.equity_curve_point import EquityCurvePoint as ECP
        from app.db.models.mock_trade import MockTrade as MT
        from app.db.models.strategy_result import StrategyResult as SR

        for model in (MT, SR, ECP, DD):
            self._session.execute(
                sa_delete(model).where(model.backtest_run_id == run_id)  # type: ignore[attr-defined]
            )
        self._session.commit()

    # ── Comparison history/detail (MH-11) ─────────────────────────────

    def list_comparison_runs(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[int, list[dict[str, Any]]]:
        runs = self._session.execute(
            select(BacktestRun).order_by(BacktestRun.created_at.desc())
        ).scalars().all()

        run_ids = [r.id for r in runs]
        if not run_ids:
            return 0, []

        results = self._session.execute(
            select(StrategyResult).where(StrategyResult.backtest_run_id.in_(run_ids))
        ).scalars().all()
        results_by_run: dict[uuid.UUID, list[StrategyResult]] = {}
        for row in results:
            results_by_run.setdefault(row.backtest_run_id, []).append(row)

        config_ids: set[uuid.UUID] = {
            r.strategy_config_id
            for r in results
            if r.strategy_config_id is not None
        }
        configs = self._session.execute(
            select(StrategyConfig).where(StrategyConfig.id.in_(config_ids))
        ).scalars().all() if config_ids else []
        config_by_id = {cfg.id: cfg for cfg in configs}

        history_rows: list[dict[str, Any]] = []
        for run in runs:
            strategy_config_ids = _extract_string_list(run.strategy_config_ids, "config_ids")
            has_multi_configs = len(strategy_config_ids) > 1
            summary = run.result_summary if isinstance(run.result_summary, dict) else {}
            has_comparison_summary = isinstance(summary.get("comparison_summary"), dict)
            run_results = results_by_run.get(run.id, [])
            has_strategy_results = len(run_results) > 0

            if not (has_comparison_summary or has_multi_configs or has_strategy_results):
                continue

            best_result = _best_result_row(run_results)
            best_config = (
                config_by_id.get(best_result.strategy_config_id)
                if best_result and best_result.strategy_config_id is not None
                else None
            )
            comparison_summary = summary.get("comparison_summary")
            total_configs_tested = (
                int(comparison_summary.get("total_configs_tested"))
                if isinstance(comparison_summary, dict)
                and comparison_summary.get("total_configs_tested") is not None
                else len(run_results) if run_results else len(strategy_config_ids)
            )

            history_rows.append(
                {
                    "backtest_run_id": run.id,
                    "name": run.name,
                    "status": run.status,
                    "date_from": run.date_from,
                    "date_to": run.date_to,
                    "requested_assets": _extract_string_list(run.requested_assets, "assets"),
                    "requested_timeframes": _extract_string_list(run.requested_timeframes, "timeframes"),
                    "starting_capital": _to_float(run.starting_capital),
                    "created_at": run.created_at,
                    "completed_at": run.completed_at,
                    "total_configs_tested": total_configs_tested,
                    "best_score": _to_float(best_result.score) if best_result else None,
                    "best_asset": best_result.asset if best_result else None,
                    "best_timeframe": best_result.timeframe if best_result else None,
                    "best_strategy_config_id": best_result.strategy_config_id if best_result else None,
                    "best_strategy_name": best_config.name if best_config else None,
                    "best_parameters": best_config.parameters if best_config else None,
                    "best_total_trades": best_result.total_trades if best_result else None,
                    "best_win_rate": _to_float(best_result.win_rate) if best_result else None,
                    "best_profit_factor": _to_float(best_result.profit_factor) if best_result else None,
                    "best_total_return_pct": _to_float(best_result.total_return_pct) if best_result else None,
                    "best_max_drawdown_pct": _to_float(best_result.max_drawdown_pct) if best_result else None,
                }
            )

        total = len(history_rows)
        return total, history_rows[offset : offset + limit]

    def get_comparison_detail(self, run_id: uuid.UUID) -> dict[str, Any] | None:
        run = self._session.get(BacktestRun, run_id)
        if not run:
            return None

        results = self._session.execute(
            select(StrategyResult).where(StrategyResult.backtest_run_id == run_id)
        ).scalars().all()
        config_ids = [r.strategy_config_id for r in results if r.strategy_config_id is not None]
        configs = self._session.execute(
            select(StrategyConfig).where(StrategyConfig.id.in_(config_ids))
        ).scalars().all() if config_ids else []
        config_by_id = {cfg.id: cfg for cfg in configs}

        sorted_results = sorted(
            results,
            key=lambda r: _to_float(r.score) if r.score is not None else -1.0,
            reverse=True,
        )
        ranked_rows: list[dict[str, Any]] = []
        for idx, row in enumerate(sorted_results, start=1):
            cfg = config_by_id.get(row.strategy_config_id) if row.strategy_config_id else None
            metrics = row.metrics if isinstance(row.metrics, dict) else {}
            raw_quality_warnings = metrics.get("quality_warnings")
            raw_walk_forward_warnings = metrics.get("walk_forward_warnings")
            ranked_rows.append(
                {
                    "strategy_config_id": row.strategy_config_id,
                    "strategy_name": cfg.name if cfg else "unknown",
                    "backtest_run_id": run.id,
                    "asset": row.asset or (cfg.asset if cfg else ""),
                    "timeframe": row.timeframe or (cfg.timeframe if cfg else ""),
                    "parameters": cfg.parameters if cfg else {},
                    "total_trades": row.total_trades,
                    "wins": row.wins,
                    "losses": row.losses,
                    "win_rate": _to_float(row.win_rate),
                    "profit_factor": _to_float(row.profit_factor),
                    "expectancy": _to_float(row.expectancy),
                    "total_return_pct": _to_float(row.total_return_pct),
                    "max_drawdown_pct": _to_float(row.max_drawdown_pct),
                    "quality_grade": str(metrics.get("quality_grade")) if metrics.get("quality_grade") is not None else None,
                    "research_confidence_score": _to_float(metrics.get("research_confidence_score")),
                    "overfitting_risk_score": _to_float(metrics.get("overfitting_risk_score")),
                    "quality_warnings": (
                        [str(w) for w in raw_quality_warnings]
                        if isinstance(raw_quality_warnings, list)
                        else []
                    ),
                    "validation_stability_score": _to_float(metrics.get("validation_stability_score")),
                    "validation_stability_grade": (
                        str(metrics.get("validation_stability_grade"))
                        if metrics.get("validation_stability_grade") is not None
                        else None
                    ),
                    "out_of_sample_pass": (
                        bool(metrics.get("out_of_sample_pass"))
                        if isinstance(metrics.get("out_of_sample_pass"), bool)
                        else None
                    ),
                    "walk_forward_warnings": (
                        [str(w) for w in raw_walk_forward_warnings]
                        if isinstance(raw_walk_forward_warnings, list)
                        else []
                    ),
                    "score": _to_float(row.score) or 0.0,
                    "rank": idx,
                }
            )

        mock_trade_count = self._session.execute(
            select(func.count()).select_from(MockTrade).where(MockTrade.backtest_run_id == run_id)
        ).scalar_one()

        equity_points = self._session.execute(
            select(EquityCurvePoint)
            .where(EquityCurvePoint.backtest_run_id == run_id)
            .order_by(EquityCurvePoint.timestamp.asc())
        ).scalars().all()

        if equity_points:
            start_equity = _to_float(equity_points[0].equity)
            end_equity = _to_float(equity_points[-1].equity)
            peak_equity = max(_to_float(p.equity) for p in equity_points)
            latest_drawdown_pct = _to_float(equity_points[-1].drawdown_pct)
            total_return_pct = (
                ((end_equity - start_equity) / start_equity) * 100.0
                if start_equity not in (None, 0)
                and end_equity is not None
                else None
            )
            preview_points = _sample_preview_points([_to_float(p.equity) for p in equity_points])
        else:
            start_equity = None
            end_equity = None
            peak_equity = None
            latest_drawdown_pct = None
            total_return_pct = None
            preview_points = []

        drawdowns = self._session.execute(
            select(DrawdownPeriod).where(DrawdownPeriod.backtest_run_id == run_id)
        ).scalars().all()
        worst_drawdown_pct = (
            max((_to_float(d.max_drawdown_pct) or 0.0) for d in drawdowns)
            if drawdowns
            else None
        )
        recovered_periods = sum(1 for d in drawdowns if d.recovered)

        result_summary = run.result_summary if isinstance(run.result_summary, dict) else {}
        warnings = result_summary.get("warnings", [])
        comparison_summary = result_summary.get("comparison_summary", {})
        if isinstance(comparison_summary, dict):
            summary_warnings = comparison_summary.get("warnings", [])
            if isinstance(summary_warnings, list):
                warnings = [*warnings, *summary_warnings] if isinstance(warnings, list) else summary_warnings

        return {
            "backtest_run": run,
            "ranked_rows": ranked_rows,
            "mock_trade_count": int(mock_trade_count),
            "equity_curve_summary": {
                "total_points": len(equity_points),
                "start_equity": start_equity,
                "end_equity": end_equity,
                "peak_equity": peak_equity,
                "latest_drawdown_pct": latest_drawdown_pct,
                "total_return_pct": total_return_pct,
                "preview_points": preview_points,
            },
            "drawdown_summary": {
                "total_periods": len(drawdowns),
                "worst_drawdown_pct": worst_drawdown_pct,
                "recovered_periods": recovered_periods,
                "open_periods": len(drawdowns) - recovered_periods,
            },
            "warnings": warnings if isinstance(warnings, list) else [],
            "research_label": result_summary.get("research_label"),
            "research_notes": result_summary.get("research_notes"),
        }

    def get_quality_summary(self, run_id: uuid.UUID) -> dict[str, Any] | None:
        run = self._session.get(BacktestRun, run_id)
        if not run:
            return None

        results = self._session.execute(
            select(StrategyResult).where(StrategyResult.backtest_run_id == run_id)
        ).scalars().all()

        grade_distribution: dict[str, int] = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0, "unknown": 0}
        confidences: list[float] = []
        overfitting_scores: list[float] = []

        for row in results:
            metrics = row.metrics if isinstance(row.metrics, dict) else {}
            grade_raw = metrics.get("quality_grade")
            grade = str(grade_raw) if grade_raw is not None else "unknown"
            if grade not in grade_distribution:
                grade = "unknown"
            grade_distribution[grade] += 1

            confidence = _to_float(metrics.get("research_confidence_score"))
            if confidence is not None:
                confidences.append(confidence)

            overfitting = _to_float(metrics.get("overfitting_risk_score"))
            if overfitting is not None:
                overfitting_scores.append(overfitting)

        avg_conf = round(sum(confidences) / len(confidences), 2) if confidences else 0.0
        highest_overfitting = round(max(overfitting_scores), 2) if overfitting_scores else 0.0

        warnings: list[str] = []
        if grade_distribution["F"] > 0:
            warnings.append("At least one strategy has quality grade F.")
        if avg_conf < 55 and len(results) > 0:
            warnings.append("Average research confidence is below preferred research threshold.")
        if highest_overfitting >= 70:
            warnings.append("High overfitting risk detected in one or more strategies.")
        unstable_walk_forward_rows = sum(
            1
            for row in results
            if isinstance(row.metrics, dict)
            and str(row.metrics.get("validation_stability_grade") or "") == "unstable"
        )
        if unstable_walk_forward_rows > 0:
            warnings.append("Some strategies are unstable under out-of-sample validation.")
        warnings.append("Research only, not approved for paper or live trading")

        return {
            "backtest_run_id": run.id,
            "total_strategies": len(results),
            "average_confidence": avg_conf,
            "grade_distribution": grade_distribution,
            "highest_overfitting_risk": highest_overfitting,
            "warnings": warnings,
            "paper_trade_ready": False,
            "live_ready": False,
        }

    def run_walk_forward_validation(
        self,
        run_id: uuid.UUID,
        *,
        in_sample_pct: int = 60,
        validation_pct: int = 20,
        out_of_sample_pct: int = 20,
        fold_count: int = 1,
        persist: bool = True,
    ) -> dict[str, Any] | None:
        run = self._session.get(BacktestRun, run_id)
        if not run:
            return None

        if fold_count == 1:
            rolling_folds = [
                {
                    "fold_index": 1,
                    "splits": build_date_splits(
                        date_from=run.date_from,
                        date_to=run.date_to,
                        in_sample_pct=in_sample_pct,
                        validation_pct=validation_pct,
                        out_of_sample_pct=out_of_sample_pct,
                    ),
                }
            ]
        else:
            rolling_folds = [
                {
                    "fold_index": fold.fold_index,
                    "splits": fold.splits,
                }
                for fold in build_rolling_fold_splits(
                    date_from=run.date_from,
                    date_to=run.date_to,
                    fold_count=fold_count,
                    in_sample_pct=in_sample_pct,
                    validation_pct=validation_pct,
                    out_of_sample_pct=out_of_sample_pct,
                )
            ]
        splits = list(rolling_folds[0]["splits"])

        results = self._session.execute(
            select(StrategyResult).where(StrategyResult.backtest_run_id == run_id)
        ).scalars().all()
        result_by_config = {row.strategy_config_id: row for row in results}

        trades = self._session.execute(
            select(MockTrade)
            .where(MockTrade.backtest_run_id == run_id)
            .where(MockTrade.status == "closed")
            .order_by(MockTrade.exit_time.asc(), MockTrade.entry_time.asc())
        ).scalars().all()

        grouped: dict[uuid.UUID | None, list[MockTrade]] = {}
        for trade in trades:
            grouped.setdefault(trade.strategy_config_id, []).append(trade)

        config_ids = {
            cfg_id
            for cfg_id in list(grouped.keys()) + [row.strategy_config_id for row in results]
        }
        clean_config_ids = [cid for cid in config_ids if cid is not None]
        configs = self._session.execute(
            select(StrategyConfig).where(StrategyConfig.id.in_(clean_config_ids))
        ).scalars().all() if clean_config_ids else []
        config_by_id = {cfg.id: cfg for cfg in configs}

        strategies_payload: list[dict[str, Any]] = []
        global_warning_messages: list[str] = []
        starting_capital = _to_float(run.starting_capital) or 0.0

        for config_id in sorted(config_ids, key=lambda v: str(v)):
            config_trades = grouped.get(config_id, [])

            fold_payloads: list[dict[str, Any]] = []
            fold_summaries: list[dict[str, Any]] = []
            for fold in rolling_folds:
                fold_splits = list(fold["splits"])
                split_trade_dicts: dict[str, list[dict[str, Any]]] = {
                    s.label: [] for s in fold_splits
                }
                for t in config_trades:
                    ts = t.exit_time or t.entry_time
                    if ts is None:
                        continue
                    bucket = _split_label_for_timestamp(ts, fold_splits)
                    if bucket is None:
                        continue
                    metadata = t.metadata_json if isinstance(t.metadata_json, dict) else {}
                    split_trade_dicts[bucket].append(
                        {
                            "net_pnl": _to_float(metadata.get("base_net_pnl_amount"))
                            if metadata.get("base_net_pnl_amount") is not None
                            else _to_float(t.pnl_amount)
                            or 0.0,
                            "cost_sensitivity_level": str(metadata.get("cost_sensitivity_level") or ""),
                        }
                    )

                in_sample = calculate_period_metrics(
                    period_label="in_sample",
                    trades=split_trade_dicts["in_sample"],
                    starting_capital=starting_capital,
                )
                validation = calculate_period_metrics(
                    period_label="validation",
                    trades=split_trade_dicts["validation"],
                    starting_capital=starting_capital,
                )
                out_of_sample = calculate_period_metrics(
                    period_label="out_of_sample",
                    trades=split_trade_dicts["out_of_sample"],
                    starting_capital=starting_capital,
                )

                summary = calculate_walk_forward_summary(
                    in_sample_metrics=in_sample,
                    validation_metrics=validation,
                    out_of_sample_metrics=out_of_sample,
                )
                fold_summaries.append(summary)
                fold_payloads.append(
                    {
                        "fold_index": fold["fold_index"],
                        "splits": [
                            {
                                "period": s.label,
                                "start": s.start,
                                "end": s.end,
                                "percentage": s.percentage,
                            }
                            for s in fold_splits
                        ],
                        "in_sample": in_sample,
                        "validation": validation,
                        "out_of_sample": out_of_sample,
                        **summary,
                        "warnings": [{"message": w} for w in summary.get("warnings", [])],
                    }
                )

            primary_fold = fold_payloads[0]
            rolling_summary = calculate_multi_fold_summary(fold_summaries)

            strategy_payload = {
                "strategy_config_id": config_id,
                "strategy_name": config_by_id.get(config_id).name if config_id in config_by_id else None,
                "in_sample": primary_fold["in_sample"],
                "validation": primary_fold["validation"],
                "out_of_sample": primary_fold["out_of_sample"],
                "folds": fold_payloads,
                "in_sample_return": primary_fold["in_sample_return"],
                "validation_return": primary_fold["validation_return"],
                "out_of_sample_return": primary_fold["out_of_sample_return"],
                "out_of_sample_profit_factor": primary_fold["out_of_sample_profit_factor"],
                "return_degradation_pct": rolling_summary["average_return_degradation_pct"],
                "profit_factor_degradation_pct": round(
                    sum(_to_float(item.get("profit_factor_degradation_pct")) or 0.0 for item in fold_summaries)
                    / len(fold_summaries),
                    6,
                ),
                "confidence_degradation_pct": rolling_summary["average_confidence_degradation_pct"],
                "validation_stability_score": rolling_summary["average_validation_stability_score"],
                "validation_stability_grade": rolling_summary["rolling_validation_grade"],
                "out_of_sample_pass": rolling_summary["rolling_out_of_sample_pass"],
                "warnings": [{"message": w} for w in rolling_summary.get("warnings", [])],
                "paper_trade_ready": False,
                "live_ready": False,
            }
            strategies_payload.append(strategy_payload)

            for warning in rolling_summary.get("warnings", []):
                if warning not in global_warning_messages:
                    global_warning_messages.append(warning)

            result_row = result_by_config.get(config_id)
            if persist and result_row is not None:
                metrics = dict(result_row.metrics or {})
                metrics.update(
                    {
                        "walk_forward_validation_version": "mh18_v1" if fold_count > 1 else "mh17_v1",
                        "walk_forward_splits": [
                            {
                                "period": s.label,
                                "start": s.start.isoformat(),
                                "end": s.end.isoformat(),
                                "percentage": s.percentage,
                            }
                            for s in splits
                        ],
                        "walk_forward_fold_count": fold_count,
                        "walk_forward_folds": [
                            {
                                "fold_index": fold["fold_index"],
                                "splits": [
                                    {
                                        "period": s.label,
                                        "start": s.start.isoformat(),
                                        "end": s.end.isoformat(),
                                        "percentage": s.percentage,
                                    }
                                    for s in fold["splits"]
                                ],
                                "in_sample": payload["in_sample"],
                                "validation": payload["validation"],
                                "out_of_sample": payload["out_of_sample"],
                                "validation_stability_score": payload["validation_stability_score"],
                                "validation_stability_grade": payload["validation_stability_grade"],
                                "out_of_sample_pass": payload["out_of_sample_pass"],
                                "return_degradation_pct": payload["return_degradation_pct"],
                                "profit_factor_degradation_pct": payload["profit_factor_degradation_pct"],
                                "confidence_degradation_pct": payload["confidence_degradation_pct"],
                                "warnings": [w["message"] for w in payload["warnings"]],
                            }
                            for fold, payload in zip(rolling_folds, fold_payloads, strict=False)
                        ],
                        "walk_forward_in_sample": primary_fold["in_sample"],
                        "walk_forward_validation": primary_fold["validation"],
                        "walk_forward_out_of_sample": primary_fold["out_of_sample"],
                        "validation_stability_score": rolling_summary["average_validation_stability_score"],
                        "validation_stability_grade": rolling_summary["rolling_validation_grade"],
                        "out_of_sample_pass": rolling_summary["rolling_out_of_sample_pass"],
                        "return_degradation_pct": rolling_summary["average_return_degradation_pct"],
                        "profit_factor_degradation_pct": round(
                            sum(_to_float(item.get("profit_factor_degradation_pct")) or 0.0 for item in fold_summaries)
                            / len(fold_summaries),
                            6,
                        ),
                        "confidence_degradation_pct": rolling_summary["average_confidence_degradation_pct"],
                        "rolling_window_summary": rolling_summary,
                        "walk_forward_warnings": rolling_summary["warnings"],
                        "paper_trade_ready": False,
                        "live_ready": False,
                    }
                )
                result_row.metrics = metrics

        strategy_rollups = [
            {
                "validation_stability_score": row["validation_stability_score"],
                "validation_stability_grade": row["validation_stability_grade"],
                "out_of_sample_pass": row["out_of_sample_pass"],
                "return_degradation_pct": row["return_degradation_pct"],
                "confidence_degradation_pct": row["confidence_degradation_pct"],
            }
            for row in strategies_payload
        ]
        run_level_rolling_summary = calculate_multi_fold_summary(strategy_rollups)
        response_rolling_window_summary = {
            **run_level_rolling_summary,
            "warnings": [
                {"message": warning}
                for warning in run_level_rolling_summary.get("warnings", [])
            ],
        }

        payload = {
            "backtest_run_id": run.id,
            "splits": [
                {
                    "period": s.label,
                    "start": s.start,
                    "end": s.end,
                    "percentage": s.percentage,
                }
                for s in splits
            ],
            "strategies": strategies_payload,
            "rolling_window_summary": response_rolling_window_summary,
            "warnings": [{"message": w} for w in global_warning_messages],
            "paper_trade_ready": False,
            "live_ready": False,
        }

        if persist:
            summary = run.result_summary if isinstance(run.result_summary, dict) else {}
            summary["walk_forward_validation"] = {
                **payload,
                "backtest_run_id": str(run.id),
                "strategies": [
                    {
                        **row,
                        "strategy_config_id": (
                            str(row.get("strategy_config_id"))
                            if row.get("strategy_config_id") is not None
                            else None
                        ),
                        "folds": [
                            {
                                **fold,
                                "splits": [
                                    {
                                        **split,
                                        "start": split["start"].isoformat(),
                                        "end": split["end"].isoformat(),
                                    }
                                    for split in fold.get("splits", [])
                                ],
                            }
                            for fold in row.get("folds", [])
                        ],
                    }
                    for row in strategies_payload
                ],
                "splits": [
                    {
                        "period": s.label,
                        "start": s.start.isoformat(),
                        "end": s.end.isoformat(),
                        "percentage": s.percentage,
                    }
                    for s in splits
                ],
                "rolling_window_summary": response_rolling_window_summary,
            }
            run.result_summary = summary
            self._session.commit()

        return payload

    def get_walk_forward_validation(self, run_id: uuid.UUID) -> dict[str, Any] | None:
        run = self._session.get(BacktestRun, run_id)
        if not run:
            return None

        summary = run.result_summary if isinstance(run.result_summary, dict) else {}
        stored = summary.get("walk_forward_validation")
        if isinstance(stored, dict):
            return stored
        return None

    def set_comparison_research_label(
        self,
        run_id: uuid.UUID,
        research_label: str,
        research_notes: str,
    ) -> dict[str, Any] | None:
        run = self._session.get(BacktestRun, run_id)
        if not run:
            return None

        summary = run.result_summary if isinstance(run.result_summary, dict) else {}
        summary = {
            **summary,
            "research_label": research_label,
            "research_notes": research_notes,
        }
        run.result_summary = summary
        self._session.commit()

        return {
            "backtest_run_id": run.id,
            "research_label": research_label,
            "research_notes": research_notes,
            "updated": True,
        }


def _extract_string_list(value: Any, key: str) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, dict):
        nested = value.get(key)
        if isinstance(nested, list):
            return [str(v) for v in nested]
    return []


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _best_result_row(rows: list[StrategyResult]) -> StrategyResult | None:
    if not rows:
        return None
    return max(rows, key=lambda r: _to_float(r.score) if r.score is not None else -1.0)


def _sample_preview_points(points: list[float | None], max_points: int = 32) -> list[float]:
    clean = [p for p in points if p is not None]
    if len(clean) <= max_points:
        return [float(p) for p in clean]
    step = max(1, len(clean) // max_points)
    sampled = [clean[i] for i in range(0, len(clean), step)]
    return [float(p) for p in sampled[:max_points]]


def _split_label_for_timestamp(ts: datetime, splits: list[Any]) -> str | None:
    for idx, split in enumerate(splits):
        if idx < len(splits) - 1:
            if split.start <= ts < split.end:
                return str(split.label)
        else:
            if split.start <= ts <= split.end:
                return str(split.label)
    return None
