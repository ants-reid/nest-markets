"""Safely clean temporary market data and optional Strategy Lab outputs.

Default mode is dry-run (no deletions). Actual deletion requires BOTH:
  - --execute
  - --confirm-cleanup

Safety principles:
  - Never touches assets table.
  - Refuses execute mode unless provider is set and at least one of
    assets/timeframes filters is provided.
  - Counts targets before deletion.
  - Commits once at the end; rolls back on any error.

Usage example (dry-run):
    PYTHONPATH=$PWD .venv/bin/python scripts/cleanup_temp_market_data.py \
      --provider polygon \
      --assets AAPL,AMD,MSFT,NVDA,SPY,QQQ,GLD,EURUSD,GBPUSD,USDJPY,TSLA \
      --timeframes 1d \
      --include-strategy-lab-outputs true \
      --dry-run
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from pathlib import Path

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

# Ensure the app package is importable when run from CLI
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.models.asset import Asset
from app.db.models.backtest_run import BacktestRun
from app.db.models.bar import Bar
from app.db.models.drawdown_period import DrawdownPeriod
from app.db.models.equity_curve_point import EquityCurvePoint
from app.db.models.market_data_gap import MarketDataGap
from app.db.models.market_data_import_run import MarketDataImportRun
from app.db.models.market_data_quality_report import MarketDataQualityReport
from app.db.models.mock_trade import MockTrade
from app.db.models.provider_asset_coverage import ProviderAssetCoverage
from app.db.models.provider_coverage_report import ProviderCoverageReport
from app.db.models.strategy_result import StrategyResult
from app.db.session import SessionLocal


@dataclass
class CleanupCounts:
    bars: int = 0
    market_data_import_runs: int = 0
    market_data_quality_reports: int = 0
    market_data_gaps: int = 0
    provider_coverage_reports: int = 0
    provider_asset_coverage: int = 0
    backtest_runs: int = 0
    mock_trades: int = 0
    strategy_results: int = 0
    equity_curve_points: int = 0
    drawdown_periods: int = 0

    @property
    def market_data_total(self) -> int:
        return (
            self.bars
            + self.market_data_import_runs
            + self.market_data_quality_reports
            + self.market_data_gaps
            + self.provider_coverage_reports
            + self.provider_asset_coverage
        )

    @property
    def strategy_lab_total(self) -> int:
        return (
            self.backtest_runs
            + self.mock_trades
            + self.strategy_results
            + self.equity_curve_points
            + self.drawdown_periods
        )


def _parse_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _parse_bool(value: str) -> bool:
    val = value.strip().lower()
    if val in {"true", "1", "yes", "y"}:
        return True
    if val in {"false", "0", "no", "n"}:
        return False
    raise argparse.ArgumentTypeError("Expected true/false")


def _parse_date_start(value: str | None) -> datetime | None:
    if value is None:
        return None
    d = date.fromisoformat(value)
    return datetime.combine(d, time.min, tzinfo=UTC)


def _parse_date_end(value: str | None) -> datetime | None:
    if value is None:
        return None
    d = date.fromisoformat(value)
    return datetime.combine(d, time.max, tzinfo=UTC)


def _validate_execute_safety(
    execute: bool,
    confirm_cleanup: bool,
    provider: str | None,
    assets: list[str],
    timeframes: list[str],
) -> None:
    if not execute:
        return

    if not confirm_cleanup:
        raise ValueError("Refusing execute mode: --confirm-cleanup is required.")

    if not provider:
        raise ValueError("Refusing execute mode: --provider is required.")

    if not assets and not timeframes:
        raise ValueError(
            "Refusing execute mode: provide at least one filter in --assets or --timeframes."
        )


def _asset_id_lookup(session: Session, symbols: list[str]) -> dict[str, str]:
    if not symbols:
        return {}
    rows = session.execute(
        select(Asset.id, Asset.symbol).where(Asset.symbol.in_(symbols))
    ).all()
    return {symbol: str(asset_id) for asset_id, symbol in rows}


def _resolve_strategy_run_ids(
    session: Session,
    assets: list[str],
    timeframes: list[str],
    date_from: datetime | None,
    date_to: datetime | None,
) -> list[str]:
    run_ids: set[str] = set()

    mt_query = select(MockTrade.backtest_run_id)
    if assets:
        mt_query = mt_query.where(MockTrade.asset.in_(assets))
    if timeframes:
        mt_query = mt_query.where(MockTrade.timeframe.in_(timeframes))
    if date_from is not None:
        mt_query = mt_query.where(MockTrade.entry_time >= date_from)
    if date_to is not None:
        mt_query = mt_query.where(MockTrade.entry_time <= date_to)

    for (run_id,) in session.execute(mt_query).all():
        run_ids.add(str(run_id))

    sr_query = select(StrategyResult.backtest_run_id)
    if assets:
        sr_query = sr_query.where(StrategyResult.asset.in_(assets))
    if timeframes:
        sr_query = sr_query.where(StrategyResult.timeframe.in_(timeframes))
    for (run_id,) in session.execute(sr_query).all():
        run_ids.add(str(run_id))

    return sorted(run_ids)


def _count_targets(
    session: Session,
    provider: str,
    assets: list[str],
    timeframes: list[str],
    date_from: datetime | None,
    date_to: datetime | None,
    include_strategy_lab_outputs: bool,
) -> tuple[CleanupCounts, list[str], list[str]]:
    counts = CleanupCounts()
    notes: list[str] = []
    strategy_run_ids: list[str] = []

    asset_ids = _asset_id_lookup(session, assets)
    missing_assets = [sym for sym in assets if sym not in asset_ids]
    if missing_assets:
        notes.append(f"Missing asset symbols (not in assets table): {', '.join(missing_assets)}")

    # bars (provider/source + optional asset/timeframe/date filters)
    bars_query = select(func.count()).select_from(Bar).where(Bar.source == provider)
    if asset_ids:
        bars_query = bars_query.where(Bar.asset_id.in_(list(asset_ids.values())))
    if timeframes:
        bars_query = bars_query.where(Bar.timeframe.in_(timeframes))
    if date_from is not None:
        bars_query = bars_query.where(Bar.ts >= date_from)
    if date_to is not None:
        bars_query = bars_query.where(Bar.ts <= date_to)
    counts.bars = int(session.execute(bars_query).scalar_one())

    # market_data_import_runs
    mir_query = (
        select(func.count())
        .select_from(MarketDataImportRun)
        .where(MarketDataImportRun.provider == provider)
    )
    if assets:
        mir_query = mir_query.where(MarketDataImportRun.asset_symbol.in_(assets))
    if timeframes:
        mir_query = mir_query.where(MarketDataImportRun.timeframe.in_(timeframes))
    if date_from is not None:
        mir_query = mir_query.where(MarketDataImportRun.from_date >= date_from)
    if date_to is not None:
        mir_query = mir_query.where(MarketDataImportRun.to_date <= date_to)
    counts.market_data_import_runs = int(session.execute(mir_query).scalar_one())

    # market_data_quality_reports
    mqr_query = (
        select(func.count())
        .select_from(MarketDataQualityReport)
        .where(MarketDataQualityReport.provider == provider)
    )
    if assets:
        mqr_query = mqr_query.where(MarketDataQualityReport.asset_symbol.in_(assets))
    if timeframes:
        mqr_query = mqr_query.where(MarketDataQualityReport.timeframe.in_(timeframes))
    counts.market_data_quality_reports = int(session.execute(mqr_query).scalar_one())

    # market_data_gaps
    mdg_query = (
        select(func.count())
        .select_from(MarketDataGap)
        .where(MarketDataGap.provider == provider)
    )
    if assets:
        mdg_query = mdg_query.where(MarketDataGap.asset_symbol.in_(assets))
    if timeframes:
        mdg_query = mdg_query.where(MarketDataGap.timeframe.in_(timeframes))
    if date_from is not None:
        mdg_query = mdg_query.where(MarketDataGap.gap_start >= date_from)
    if date_to is not None:
        mdg_query = mdg_query.where(MarketDataGap.gap_end <= date_to)
    counts.market_data_gaps = int(session.execute(mdg_query).scalar_one())

    # provider_coverage_reports (aggregate table; safely filterable by provider/date only)
    pcr_query = (
        select(func.count())
        .select_from(ProviderCoverageReport)
        .where(ProviderCoverageReport.provider == provider)
    )
    if date_from is not None:
        pcr_query = pcr_query.where(ProviderCoverageReport.evaluated_at >= date_from)
    if date_to is not None:
        pcr_query = pcr_query.where(ProviderCoverageReport.evaluated_at <= date_to)
    counts.provider_coverage_reports = int(session.execute(pcr_query).scalar_one())

    # provider_asset_coverage
    pac_query = (
        select(func.count())
        .select_from(ProviderAssetCoverage)
        .where(ProviderAssetCoverage.provider == provider)
    )
    if assets:
        pac_query = pac_query.where(ProviderAssetCoverage.asset_symbol.in_(assets))
    if timeframes:
        pac_query = pac_query.where(ProviderAssetCoverage.timeframe.in_(timeframes))
    counts.provider_asset_coverage = int(session.execute(pac_query).scalar_one())

    if include_strategy_lab_outputs:
        strategy_run_ids = _resolve_strategy_run_ids(session, assets, timeframes, date_from, date_to)
        if strategy_run_ids:
            counts.backtest_runs = int(
                session.execute(
                    select(func.count()).select_from(BacktestRun).where(BacktestRun.id.in_(strategy_run_ids))
                ).scalar_one()
            )
            counts.mock_trades = int(
                session.execute(
                    select(func.count()).select_from(MockTrade).where(MockTrade.backtest_run_id.in_(strategy_run_ids))
                ).scalar_one()
            )
            counts.strategy_results = int(
                session.execute(
                    select(func.count()).select_from(StrategyResult).where(StrategyResult.backtest_run_id.in_(strategy_run_ids))
                ).scalar_one()
            )
            counts.equity_curve_points = int(
                session.execute(
                    select(func.count()).select_from(EquityCurvePoint).where(EquityCurvePoint.backtest_run_id.in_(strategy_run_ids))
                ).scalar_one()
            )
            counts.drawdown_periods = int(
                session.execute(
                    select(func.count()).select_from(DrawdownPeriod).where(DrawdownPeriod.backtest_run_id.in_(strategy_run_ids))
                ).scalar_one()
            )
        else:
            notes.append("No Strategy Lab run IDs matched the provided asset/timeframe/date filters.")

    return counts, notes, strategy_run_ids


def _delete_targets(
    session: Session,
    provider: str,
    assets: list[str],
    timeframes: list[str],
    date_from: datetime | None,
    date_to: datetime | None,
    include_strategy_lab_outputs: bool,
    strategy_run_ids: list[str],
) -> CleanupCounts:
    deleted = CleanupCounts()

    asset_ids = _asset_id_lookup(session, assets)

    bars_stmt = delete(Bar).where(Bar.source == provider)
    if asset_ids:
        bars_stmt = bars_stmt.where(Bar.asset_id.in_(list(asset_ids.values())))
    if timeframes:
        bars_stmt = bars_stmt.where(Bar.timeframe.in_(timeframes))
    if date_from is not None:
        bars_stmt = bars_stmt.where(Bar.ts >= date_from)
    if date_to is not None:
        bars_stmt = bars_stmt.where(Bar.ts <= date_to)
    deleted.bars = int(session.execute(bars_stmt).rowcount or 0)

    mir_stmt = delete(MarketDataImportRun).where(MarketDataImportRun.provider == provider)
    if assets:
        mir_stmt = mir_stmt.where(MarketDataImportRun.asset_symbol.in_(assets))
    if timeframes:
        mir_stmt = mir_stmt.where(MarketDataImportRun.timeframe.in_(timeframes))
    if date_from is not None:
        mir_stmt = mir_stmt.where(MarketDataImportRun.from_date >= date_from)
    if date_to is not None:
        mir_stmt = mir_stmt.where(MarketDataImportRun.to_date <= date_to)
    deleted.market_data_import_runs = int(session.execute(mir_stmt).rowcount or 0)

    mqr_stmt = delete(MarketDataQualityReport).where(MarketDataQualityReport.provider == provider)
    if assets:
        mqr_stmt = mqr_stmt.where(MarketDataQualityReport.asset_symbol.in_(assets))
    if timeframes:
        mqr_stmt = mqr_stmt.where(MarketDataQualityReport.timeframe.in_(timeframes))
    deleted.market_data_quality_reports = int(session.execute(mqr_stmt).rowcount or 0)

    mdg_stmt = delete(MarketDataGap).where(MarketDataGap.provider == provider)
    if assets:
        mdg_stmt = mdg_stmt.where(MarketDataGap.asset_symbol.in_(assets))
    if timeframes:
        mdg_stmt = mdg_stmt.where(MarketDataGap.timeframe.in_(timeframes))
    if date_from is not None:
        mdg_stmt = mdg_stmt.where(MarketDataGap.gap_start >= date_from)
    if date_to is not None:
        mdg_stmt = mdg_stmt.where(MarketDataGap.gap_end <= date_to)
    deleted.market_data_gaps = int(session.execute(mdg_stmt).rowcount or 0)

    pcr_stmt = delete(ProviderCoverageReport).where(ProviderCoverageReport.provider == provider)
    if date_from is not None:
        pcr_stmt = pcr_stmt.where(ProviderCoverageReport.evaluated_at >= date_from)
    if date_to is not None:
        pcr_stmt = pcr_stmt.where(ProviderCoverageReport.evaluated_at <= date_to)
    deleted.provider_coverage_reports = int(session.execute(pcr_stmt).rowcount or 0)

    pac_stmt = delete(ProviderAssetCoverage).where(ProviderAssetCoverage.provider == provider)
    if assets:
        pac_stmt = pac_stmt.where(ProviderAssetCoverage.asset_symbol.in_(assets))
    if timeframes:
        pac_stmt = pac_stmt.where(ProviderAssetCoverage.timeframe.in_(timeframes))
    deleted.provider_asset_coverage = int(session.execute(pac_stmt).rowcount or 0)

    if include_strategy_lab_outputs and strategy_run_ids:
        deleted.drawdown_periods = int(
            session.execute(
                delete(DrawdownPeriod).where(DrawdownPeriod.backtest_run_id.in_(strategy_run_ids))
            ).rowcount
            or 0
        )
        deleted.equity_curve_points = int(
            session.execute(
                delete(EquityCurvePoint).where(EquityCurvePoint.backtest_run_id.in_(strategy_run_ids))
            ).rowcount
            or 0
        )
        deleted.strategy_results = int(
            session.execute(
                delete(StrategyResult).where(StrategyResult.backtest_run_id.in_(strategy_run_ids))
            ).rowcount
            or 0
        )
        deleted.mock_trades = int(
            session.execute(
                delete(MockTrade).where(MockTrade.backtest_run_id.in_(strategy_run_ids))
            ).rowcount
            or 0
        )
        deleted.backtest_runs = int(
            session.execute(
                delete(BacktestRun).where(BacktestRun.id.in_(strategy_run_ids))
            ).rowcount
            or 0
        )

    return deleted


def _print_counts(counts: CleanupCounts) -> None:
    print("\nTargeted row counts:")
    print("  Market data")
    print(f"    bars: {counts.bars}")
    print(f"    market_data_import_runs: {counts.market_data_import_runs}")
    print(f"    market_data_quality_reports: {counts.market_data_quality_reports}")
    print(f"    market_data_gaps: {counts.market_data_gaps}")
    print(f"    provider_coverage_reports: {counts.provider_coverage_reports}")
    print(f"    provider_asset_coverage: {counts.provider_asset_coverage}")
    print(f"    market_data_total: {counts.market_data_total}")

    print("  Strategy Lab (optional)")
    print(f"    backtest_runs: {counts.backtest_runs}")
    print(f"    mock_trades: {counts.mock_trades}")
    print(f"    strategy_results: {counts.strategy_results}")
    print(f"    equity_curve_points: {counts.equity_curve_points}")
    print(f"    drawdown_periods: {counts.drawdown_periods}")
    print(f"    strategy_lab_total: {counts.strategy_lab_total}")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Safely clean temporary market/test data.")
    parser.add_argument("--provider", default="polygon", help="Data provider name (default: polygon)")
    parser.add_argument("--assets", default="", help="Comma-separated symbols (e.g. AAPL,MSFT,EURUSD)")
    parser.add_argument("--timeframes", default="", help="Comma-separated timeframes (e.g. 1d,1h)")
    parser.add_argument("--date-from", default=None, help="Optional start date (YYYY-MM-DD)")
    parser.add_argument("--date-to", default=None, help="Optional end date (YYYY-MM-DD)")
    parser.add_argument(
        "--include-strategy-lab-outputs",
        type=_parse_bool,
        default=False,
        help="true/false. Include backtest output tables (default: false)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Preview only (default: true)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually perform deletion (requires --confirm-cleanup)",
    )
    parser.add_argument(
        "--confirm-cleanup",
        action="store_true",
        help="Second required safety flag for execute mode",
    )
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()

    # Execute mode always overrides dry-run intent.
    dry_run = True if not args.execute else False

    assets = [symbol.upper() for symbol in _parse_csv(args.assets)]
    timeframes = [tf.lower() for tf in _parse_csv(args.timeframes)]

    try:
        date_from = _parse_date_start(args.date_from)
        date_to = _parse_date_end(args.date_to)
        _validate_execute_safety(
            execute=args.execute,
            confirm_cleanup=args.confirm_cleanup,
            provider=args.provider,
            assets=assets,
            timeframes=timeframes,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}")
        return 2

    print("Cleanup plan")
    print(f"  provider: {args.provider}")
    print(f"  assets: {', '.join(assets) if assets else '(all for provider)'}")
    print(f"  timeframes: {', '.join(timeframes) if timeframes else '(all for provider)'}")
    print(f"  date_from: {args.date_from or '(none)'}")
    print(f"  date_to: {args.date_to or '(none)'}")
    print(f"  include_strategy_lab_outputs: {args.include_strategy_lab_outputs}")
    print(f"  mode: {'DRY-RUN' if dry_run else 'EXECUTE'}")

    session = SessionLocal()
    try:
        counts, notes, strategy_run_ids = _count_targets(
            session=session,
            provider=args.provider,
            assets=assets,
            timeframes=timeframes,
            date_from=date_from,
            date_to=date_to,
            include_strategy_lab_outputs=args.include_strategy_lab_outputs,
        )

        if notes:
            print("\nNotes:")
            for note in notes:
                print(f"  - {note}")

        if args.include_strategy_lab_outputs:
            print(f"\nStrategy Lab matched backtest_run_ids: {len(strategy_run_ids)}")

        _print_counts(counts)

        if dry_run:
            session.rollback()
            print("\nDry-run complete. No rows deleted.")
            return 0

        deleted = _delete_targets(
            session=session,
            provider=args.provider,
            assets=assets,
            timeframes=timeframes,
            date_from=date_from,
            date_to=date_to,
            include_strategy_lab_outputs=args.include_strategy_lab_outputs,
            strategy_run_ids=strategy_run_ids,
        )
        session.commit()

        print("\nDeletion complete.")
        _print_counts(deleted)
        return 0
    except Exception as exc:  # noqa: BLE001
        session.rollback()
        print(f"\nERROR: cleanup failed, rolled back transaction: {exc}")
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
