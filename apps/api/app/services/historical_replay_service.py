"""HistoricalReplayService — MH-07/MH-08 deterministic candle replay + simulation."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models.asset import Asset
from app.db.models.backtest_run import BacktestRun
from app.db.models.bar import Bar
from app.db.models.drawdown_period import DrawdownPeriod
from app.db.models.equity_curve_point import EquityCurvePoint
from app.db.models.market_data_quality_report import MarketDataQualityReport
from app.db.models.mock_trade import MockTrade
from app.db.models.strategy_config import StrategyConfig
from app.db.models.strategy_result import StrategyResult
from app.schemas.strategy_lab import BacktestReplayResponse, ReplayAssetSummary
from app.services.mock_trade_simulator_service import MockTradeSimulatorService, SimulationResult

_logger = logging.getLogger(__name__)

_COMPLETED_MESSAGE = "Replay completed. Mock trade simulator executed for MH-08."
_REPLAY_ONLY_MESSAGE = (
    "Replay completed (simulate_trades=false). "
    "Run with simulate_trades=true to generate mock trades."
)
_FAILED_MESSAGE = "Replay failed: no usable candle data found."


class ReplayError(Exception):
    """Raised for controlled replay failures."""


class HistoricalReplayService:
    """Execute a deterministic candle replay for one BacktestRun."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def replay(
        self,
        backtest_run_id: Any,
        *,
        allow_unapproved_data: bool = False,
        max_candles: int = 10000,
        simulate_trades: bool = True,
        clear_existing_results: bool = False,
    ) -> BacktestReplayResponse:
        run = self._session.get(BacktestRun, backtest_run_id)
        if run is None:
            raise ReplayError(f"Backtest run {backtest_run_id} not found.")

        if run.status == "running":
            raise ReplayError(
                "Backtest run is currently in status 'running'. "
                "Cannot replay while another replay is in progress."
            )

        if run.status not in ("queued",) and not clear_existing_results:
            raise ReplayError(
                f"Backtest run is in status '{run.status}'. "
                "Only 'queued' runs can be replayed. "
                "Pass clear_existing_results=true to re-run a completed or failed run."
            )

        if clear_existing_results:
            self._clear_outputs(run.id)

        run.status = "running"
        run.started_at = datetime.now(tz=timezone.utc)
        self._session.commit()

        try:
            result = self._execute_replay(run, allow_unapproved_data, max_candles, simulate_trades)
        except Exception as exc:
            run.status = "failed"
            run.error_message = str(exc)
            run.completed_at = datetime.now(tz=timezone.utc)
            self._session.commit()
            raise

        run.status = result.status
        run.completed_at = datetime.now(tz=timezone.utc)
        run.result_summary = result.model_dump(mode="json")
        if result.status == "failed":
            run.error_message = result.message
        self._session.commit()
        return result

    def _execute_replay(
        self,
        run: BacktestRun,
        allow_unapproved_data: bool,
        max_candles: int,
        simulate_trades: bool,
    ) -> BacktestReplayResponse:
        assets = _extract_list(run.requested_assets, "assets")
        timeframes = _extract_list(run.requested_timeframes, "timeframes")
        config_ids = _extract_list(run.strategy_config_ids, "config_ids")

        configs: list[StrategyConfig | None] = []
        if simulate_trades:
            if config_ids:
                for cid_str in config_ids:
                    try:
                        cid = uuid.UUID(cid_str)
                    except ValueError:
                        continue
                    cfg = self._session.get(StrategyConfig, cid)
                    if cfg:
                        configs.append(cfg)

                if not configs:
                    raise ReplayError(
                        "No valid strategy configs resolved from backtest_run.strategy_config_ids."
                    )
            else:
                # Legacy single-run path with no explicit strategy config IDs.
                configs = [None]

        warnings: list[str] = []
        asset_summaries: list[ReplayAssetSummary] = []
        total_candles = 0
        total_mock_trades = 0
        global_first: datetime | None = None
        global_last: datetime | None = None
        assets_replayed: list[str] = []
        timeframes_replayed: set[str] = set()
        skipped_assets: list[str] = []
        combined_sim: SimulationResult | None = None

        date_from = run.date_from
        date_to = run.date_to
        simulator = MockTradeSimulatorService(self._session) if simulate_trades else None

        for symbol in assets:
            asset_row = self._session.execute(
                select(Asset).where(Asset.symbol == symbol)
            ).scalar_one_or_none()

            for tf in timeframes:
                if asset_row is None:
                    key = f"{symbol}/{tf}"
                    skipped_assets.append(key)
                    warnings.append(f"Asset '{symbol}' not found in assets table.")
                    asset_summaries.append(ReplayAssetSummary(
                        asset=symbol, timeframe=tf, candles_loaded=0, approved=False,
                        first_timestamp=None, last_timestamp=None,
                        skipped=True, skip_reason=f"Asset '{symbol}' not in assets table.",
                    ))
                    continue

                approved, quality_warning = self._check_approval(symbol, tf, allow_unapproved_data)
                if quality_warning:
                    warnings.append(quality_warning)

                if not approved:
                    key = f"{symbol}/{tf}"
                    skipped_assets.append(key)
                    asset_summaries.append(ReplayAssetSummary(
                        asset=symbol, timeframe=tf, candles_loaded=0, approved=False,
                        first_timestamp=None, last_timestamp=None,
                        skipped=True, skip_reason=quality_warning or "Data not approved.",
                    ))
                    continue

                candles = self._load_candles(asset_row.id, tf, date_from, date_to, max_candles)

                if not candles:
                    warnings.append(f"No bars found for {symbol}/{tf} in requested date range.")
                    key = f"{symbol}/{tf}"
                    skipped_assets.append(key)
                    asset_summaries.append(ReplayAssetSummary(
                        asset=symbol, timeframe=tf, candles_loaded=0, approved=approved,
                        first_timestamp=None, last_timestamp=None,
                        skipped=True, skip_reason="No bars in requested date range.",
                    ))
                    continue

                first_ts, last_ts, count = candles[0].ts, candles[-1].ts, len(candles)

                if simulator is not None:
                    for cfg in configs:
                        sim = simulator.simulate(
                            backtest_run_id=run.id,
                            strategy_config=cfg,
                            candles=candles,
                            starting_capital=float(run.starting_capital),
                            asset=symbol,
                            timeframe=tf,
                        )
                        total_mock_trades += sim.total_trades
                        warnings.extend(sim.warnings)
                        combined_sim = _merge_sim(combined_sim, sim)

                total_candles += count
                assets_replayed.append(symbol)
                timeframes_replayed.add(tf)

                if global_first is None or first_ts < global_first:
                    global_first = first_ts
                if global_last is None or last_ts > global_last:
                    global_last = last_ts

                asset_summaries.append(ReplayAssetSummary(
                    asset=symbol, timeframe=tf, candles_loaded=count, approved=approved,
                    first_timestamp=first_ts, last_timestamp=last_ts,
                    skipped=False, skip_reason=None,
                ))

                _logger.info(
                    "Replayed %s candles for %s/%s (%s to %s). trades=%s",
                    count, symbol, tf, first_ts, last_ts, total_mock_trades,
                )

        if total_candles == 0:
            return BacktestReplayResponse(
                backtest_run_id=run.id,
                status="failed",
                total_candles_loaded=0,
                total_mock_trades=0,
                assets_replayed=[],
                timeframes_replayed=[],
                skipped_assets=skipped_assets,
                first_timestamp=None,
                last_timestamp=None,
                warnings=warnings,
                asset_summaries=asset_summaries,
                message=_FAILED_MESSAGE,
            )

        return BacktestReplayResponse(
            backtest_run_id=run.id,
            status="completed",
            total_candles_loaded=total_candles,
            total_mock_trades=total_mock_trades,
            assets_replayed=list(dict.fromkeys(assets_replayed)),
            timeframes_replayed=sorted(timeframes_replayed),
            skipped_assets=skipped_assets,
            first_timestamp=global_first,
            last_timestamp=global_last,
            warnings=warnings,
            asset_summaries=asset_summaries,
            win_rate=combined_sim.win_rate if combined_sim else None,
            profit_factor=combined_sim.profit_factor if combined_sim else None,
            max_drawdown_pct=combined_sim.max_drawdown_pct if combined_sim else None,
            total_return_pct=combined_sim.total_return_pct if combined_sim else None,
            message=_COMPLETED_MESSAGE if simulate_trades else _REPLAY_ONLY_MESSAGE,
        )

    def _check_approval(
        self,
        symbol: str,
        timeframe: str,
        allow_unapproved_data: bool,
    ) -> tuple[bool, str | None]:
        report = self._session.execute(
            select(MarketDataQualityReport)
            .where(MarketDataQualityReport.asset_symbol == symbol)
            .where(MarketDataQualityReport.timeframe == timeframe)
            .order_by(MarketDataQualityReport.evaluated_at.desc())
            .limit(1)
        ).scalar_one_or_none()

        if report is None:
            msg = f"No quality report for {symbol}/{timeframe}. Treating as unapproved."
            return (True, msg) if allow_unapproved_data else (False, msg)

        if report.approved_for_backtest:
            return True, None

        msg = (
            f"{symbol}/{timeframe} quality report exists but is not approved "
            f"(score={report.quality_score})."
        )
        return (True, msg) if allow_unapproved_data else (False, msg)

    def _load_candles(
        self,
        asset_id: Any,
        timeframe: str,
        date_from: datetime,
        date_to: datetime,
        max_candles: int,
    ) -> list[Bar]:
        return list(
            self._session.execute(
                select(Bar)
                .where(Bar.asset_id == asset_id)
                .where(Bar.timeframe == timeframe)
                .where(Bar.ts >= date_from)
                .where(Bar.ts <= date_to)
                .order_by(Bar.ts.asc())
                .limit(max_candles)
            ).scalars().all()
        )

    def _clear_outputs(self, run_id: uuid.UUID) -> None:
        for model in (MockTrade, StrategyResult, EquityCurvePoint, DrawdownPeriod):
            self._session.execute(
                delete(model).where(model.backtest_run_id == run_id)  # type: ignore[attr-defined]
            )
        self._session.commit()

    @staticmethod
    def _extract_list(jsonb_value: dict | list | None, key: str) -> list[str]:
        return _extract_list(jsonb_value, key)

    @staticmethod
    def _serialise_summary(result: BacktestReplayResponse) -> dict:
        return result.model_dump(mode="json")


def _extract_list(jsonb_value: dict | list | None, key: str) -> list[str]:
    if jsonb_value is None:
        return []
    if isinstance(jsonb_value, list):
        return [str(v) for v in jsonb_value]
    if isinstance(jsonb_value, dict):
        return [str(v) for v in jsonb_value.get(key, [])]
    return []


def _merge_sim(
    existing: SimulationResult | None,
    new: SimulationResult,
) -> SimulationResult:
    if existing is None:
        return new

    total = existing.total_trades + new.total_trades
    wins = existing.wins + new.wins
    losses = existing.losses + new.losses
    breakeven = existing.breakeven + new.breakeven
    win_rate = wins / total if total > 0 else None

    def _avg(a: float | None, b: float | None) -> float | None:
        vals = [v for v in (a, b) if v is not None]
        return sum(vals) / len(vals) if vals else None

    return SimulationResult(
        total_trades=total,
        wins=wins,
        losses=losses,
        breakeven=breakeven,
        win_rate=win_rate,
        average_win=_avg(existing.average_win, new.average_win),
        average_loss=_avg(existing.average_loss, new.average_loss),
        profit_factor=_avg(existing.profit_factor, new.profit_factor),
        expectancy=_avg(existing.expectancy, new.expectancy),
        total_return_pct=existing.total_return_pct + new.total_return_pct,
        max_drawdown_pct=max(existing.max_drawdown_pct, new.max_drawdown_pct),
        final_equity=new.final_equity,
        warnings=existing.warnings + new.warnings,
    )
