"""Deterministic Data Quality Engine for MH-03.

This engine computes quality metrics from bars and can persist:
- market_data_quality_reports
- market_data_gaps
- provider_asset_coverage
- provider_coverage_reports
"""

from __future__ import annotations

import statistics
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.db.models.asset import Asset
from app.db.models.bar import Bar
from app.db.models.market_data_gap import MarketDataGap
from app.db.models.market_data_quality_report import MarketDataQualityReport
from app.db.models.provider_asset_coverage import ProviderAssetCoverage
from app.db.models.provider_coverage_report import ProviderCoverageReport
from app.db.enums import AssetClass


TIMEFRAME_SECONDS: dict[str, int] = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
}

SPIKE_MULTIPLIER = 8.0
SPIKE_LOOKBACK = 20


@dataclass(frozen=True)
class QualityGap:
    gap_start: datetime
    gap_end: datetime
    expected_candles_missing: int
    severity: str


@dataclass(frozen=True)
class QualityMetrics:
    asset_symbol: str
    timeframe: str
    provider: str | None
    evaluated_at: datetime
    expected_bars: int | None
    actual_bars: int
    total_bars: int
    completeness_pct: float | None
    missing_bars: int
    missing_pct: float | None
    duplicate_bars: int
    bad_price_bars: int
    suspicious_spike_bars: int
    earliest_bar_ts: datetime | None
    latest_bar_ts: datetime | None
    quality_score: float
    approved_for_backtest: bool
    notes: str | None
    gaps: list[QualityGap]


class DataQualityEngine:
    """Calculate and persist deterministic bar quality metrics."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def calculate(
        self,
        asset_symbol: str,
        timeframe: str,
        provider: str | None = None,
        from_ts: datetime | None = None,
        to_ts: datetime | None = None,
    ) -> QualityMetrics:
        asset = self._session.execute(
            select(Asset).where(Asset.symbol == asset_symbol)
        ).scalar_one_or_none()
        now = datetime.now(UTC)
        if asset is None:
            return QualityMetrics(
                asset_symbol=asset_symbol,
                timeframe=timeframe,
                provider=provider,
                evaluated_at=now,
                expected_bars=None,
                actual_bars=0,
                total_bars=0,
                completeness_pct=0.0,
                missing_bars=0,
                missing_pct=0.0,
                duplicate_bars=0,
                bad_price_bars=0,
                suspicious_spike_bars=0,
                earliest_bar_ts=None,
                latest_bar_ts=None,
                quality_score=0.0,
                approved_for_backtest=False,
                notes=f"Asset {asset_symbol} not found",
                gaps=[],
            )

        bars = self._load_bars(asset.id, timeframe, provider, from_ts, to_ts)
        return self._calculate_from_bars(
            asset_symbol,
            timeframe,
            provider,
            bars,
            asset_class=asset.asset_class,
        )

    def recalculate_and_persist(
        self,
        assets: list[str],
        timeframes: list[str],
        providers: list[str] | None = None,
        import_run_id: uuid.UUID | None = None,
    ) -> list[QualityMetrics]:
        results: list[QualityMetrics] = []
        provider_values = providers or [None]
        for asset_symbol in assets:
            for timeframe in timeframes:
                for provider in provider_values:
                    normalized_provider = provider if provider not in {"*", "all"} else None
                    metrics = self.calculate(
                        asset_symbol=asset_symbol,
                        timeframe=timeframe,
                        provider=normalized_provider,
                    )
                    self._persist_metrics(metrics, import_run_id=import_run_id)
                    results.append(metrics)
        self._session.commit()
        return results

    def _load_bars(
        self,
        asset_id: uuid.UUID,
        timeframe: str,
        provider: str | None,
        from_ts: datetime | None,
        to_ts: datetime | None,
    ) -> list[Bar]:
        query = select(Bar).where(
            Bar.asset_id == asset_id,
            Bar.timeframe == timeframe,
        )
        if provider:
            query = query.where(Bar.source == provider)
        if from_ts:
            query = query.where(Bar.ts >= from_ts)
        if to_ts:
            query = query.where(Bar.ts <= to_ts)
        query = query.order_by(Bar.ts.asc())
        return list(self._session.execute(query).scalars().all())

    def _calculate_from_bars(
        self,
        asset_symbol: str,
        timeframe: str,
        provider: str | None,
        bars: list[Bar],
        asset_class: AssetClass | None = None,
    ) -> QualityMetrics:
        now = datetime.now(UTC)
        if not bars:
            return QualityMetrics(
                asset_symbol=asset_symbol,
                timeframe=timeframe,
                provider=provider,
                evaluated_at=now,
                expected_bars=0,
                actual_bars=0,
                total_bars=0,
                completeness_pct=0.0,
                missing_bars=0,
                missing_pct=0.0,
                duplicate_bars=0,
                bad_price_bars=0,
                suspicious_spike_bars=0,
                earliest_bar_ts=None,
                latest_bar_ts=None,
                quality_score=0.0,
                approved_for_backtest=False,
                notes="No bars found for this selection",
                gaps=[],
            )

        interval = TIMEFRAME_SECONDS.get(timeframe)
        timestamps = [bar.ts for bar in bars]
        counts = Counter(timestamps)
        duplicate_count = sum(c - 1 for c in counts.values() if c > 1)
        unique_ts = sorted(counts.keys())

        bad_price_count = self._count_bad_prices(
            bars,
            asset_class=asset_class,
            timeframe=timeframe,
        )
        suspicious_spikes = self._count_suspicious_spikes(bars)

        missing_bars = 0
        expected_bars: int | None = None
        gaps: list[QualityGap] = []
        notes: list[str] = []

        if interval is None:
            notes.append(f"Unsupported timeframe '{timeframe}'. Missing-bar detection skipped.")
            completeness_pct = None
            missing_pct = None
        elif timeframe == "1d" and asset_class is not None:
            expected_dates = self._expected_daily_dates(unique_ts[0].date(), unique_ts[-1].date(), asset_class)
            actual_dates = {ts.date() for ts in unique_ts}
            missing_dates = sorted(expected_dates - actual_dates)

            expected_bars = len(expected_dates)
            missing_bars = len(missing_dates)
            gaps = self._daily_gaps_from_missing_dates(missing_dates)

            if expected_bars > 0:
                completeness_pct = max(0.0, min(100.0, (len(actual_dates) / expected_bars) * 100.0))
                missing_pct = max(0.0, min(100.0, (missing_bars / expected_bars) * 100.0))
            else:
                completeness_pct = 0.0
                missing_pct = 0.0

            if asset_class in {
                AssetClass.EQUITY,
                AssetClass.ETF,
                AssetClass.INDEX_PROXY,
                AssetClass.COMMODITY_PROXY,
            }:
                notes.append(
                    "Daily completeness uses weekday trading-day expectations for equity/ETF/index classes."
                )
            elif asset_class == AssetClass.FX:
                notes.append("Daily completeness uses weekday expectations for forex.")
            elif asset_class == AssetClass.CRYPTO:
                notes.append("Daily completeness uses calendar-day expectations for crypto (24/7).")
            else:
                notes.append(
                    "Daily completeness uses simple interval counting; session-aware market calendars are deferred."
                )
        else:
            expected_bars = int((unique_ts[-1] - unique_ts[0]).total_seconds() // interval) + 1
            for prev, curr in zip(unique_ts, unique_ts[1:], strict=False):
                delta_steps = int((curr - prev).total_seconds() // interval)
                if delta_steps > 1:
                    gap_missing = delta_steps - 1
                    missing_bars += gap_missing
                    gap_start = prev + timedelta(seconds=interval)
                    gap_end = curr - timedelta(seconds=interval)
                    gaps.append(
                        QualityGap(
                            gap_start=gap_start,
                            gap_end=gap_end,
                            expected_candles_missing=gap_missing,
                            severity=self._severity_for_missing(gap_missing),
                        )
                    )

            actual_unique = len(unique_ts)
            if expected_bars > 0:
                completeness_pct = max(0.0, min(100.0, (actual_unique / expected_bars) * 100.0))
                missing_pct = max(0.0, min(100.0, (missing_bars / expected_bars) * 100.0))
            else:
                completeness_pct = 0.0
                missing_pct = 0.0

            notes.append(
                "Completeness uses simple interval counting; session-aware market calendars are deferred."
            )

        quality_score = self._quality_score(
            missing_pct=missing_pct or 0.0,
            duplicate_count=duplicate_count,
            bad_price_count=bad_price_count,
            suspicious_spikes=suspicious_spikes,
        )

        return QualityMetrics(
            asset_symbol=asset_symbol,
            timeframe=timeframe,
            provider=provider,
            evaluated_at=now,
            expected_bars=expected_bars,
            actual_bars=len(unique_ts),
            total_bars=len(bars),
            completeness_pct=completeness_pct,
            missing_bars=missing_bars,
            missing_pct=missing_pct,
            duplicate_bars=duplicate_count,
            bad_price_bars=bad_price_count,
            suspicious_spike_bars=suspicious_spikes,
            earliest_bar_ts=min(unique_ts),
            latest_bar_ts=max(unique_ts),
            quality_score=quality_score,
            approved_for_backtest=quality_score >= 90.0,
            notes=" ".join(notes),
            gaps=gaps,
        )

    @staticmethod
    def _expected_daily_dates(start_date: date, end_date: date, asset_class: AssetClass) -> set[date]:
        current = start_date
        dates: set[date] = set()
        while current <= end_date:
            if asset_class == AssetClass.CRYPTO:
                dates.add(current)
            elif asset_class in {
                AssetClass.EQUITY,
                AssetClass.ETF,
                AssetClass.INDEX_PROXY,
                AssetClass.COMMODITY_PROXY,
                AssetClass.FX,
            }:
                if current.weekday() < 5:
                    dates.add(current)
            else:
                dates.add(current)
            current += timedelta(days=1)
        return dates

    def _daily_gaps_from_missing_dates(self, missing_dates: list[date]) -> list[QualityGap]:
        if not missing_dates:
            return []

        gaps: list[QualityGap] = []
        run_start = missing_dates[0]
        run_end = missing_dates[0]

        for missing_date in missing_dates[1:]:
            if missing_date == run_end + timedelta(days=1):
                run_end = missing_date
                continue

            gap_missing = (run_end - run_start).days + 1
            gaps.append(
                QualityGap(
                    gap_start=datetime.combine(run_start, datetime.min.time(), tzinfo=UTC),
                    gap_end=datetime.combine(run_end, datetime.min.time(), tzinfo=UTC),
                    expected_candles_missing=gap_missing,
                    severity=self._severity_for_missing(gap_missing),
                )
            )
            run_start = run_end = missing_date

        final_missing = (run_end - run_start).days + 1
        gaps.append(
            QualityGap(
                gap_start=datetime.combine(run_start, datetime.min.time(), tzinfo=UTC),
                gap_end=datetime.combine(run_end, datetime.min.time(), tzinfo=UTC),
                expected_candles_missing=final_missing,
                severity=self._severity_for_missing(final_missing),
            )
        )
        return gaps

    @staticmethod
    def _count_bad_prices(
        bars: list[Bar],
        asset_class: AssetClass | None = None,
        timeframe: str | None = None,
    ) -> int:
        bad = 0
        for bar in bars:
            o = float(bar.open)
            h = float(bar.high)
            low = float(bar.low)
            c = float(bar.close)

            # Keep strict impossible-candle checks globally.
            high_low_tol = max(abs(c) * 1e-12, 1e-12)

            # yfinance FX daily bars can have open/close outside high/low by small-to-moderate
            # amounts due to quote construction differences. Use controlled tolerance only there.
            if asset_class == AssetClass.FX and timeframe == "1d":
                range_tol = max(abs(c) * 5e-3, 1e-8)  # ~0.5% max-relative envelope
            else:
                range_tol = max(abs(c) * 1e-10, 1e-10)

            invalid = (
                o <= 0
                or h <= 0
                or low <= 0
                or c <= 0
                or h + high_low_tol < low
                or o < (low - range_tol)
                or o > (h + range_tol)
                or c < (low - range_tol)
                or c > (h + range_tol)
            )
            if invalid:
                bad += 1
        return bad

    @staticmethod
    def _count_suspicious_spikes(bars: list[Bar]) -> int:
        ranges = [max(0.0, float(bar.high) - float(bar.low)) for bar in bars]
        spikes = 0
        for idx in range(1, len(ranges)):
            history = ranges[max(0, idx - SPIKE_LOOKBACK):idx]
            if not history:
                continue
            baseline = statistics.median(history)
            if baseline <= 0:
                continue
            if ranges[idx] > baseline * SPIKE_MULTIPLIER:
                spikes += 1
        return spikes

    @staticmethod
    def _quality_score(
        missing_pct: float,
        duplicate_count: int,
        bad_price_count: int,
        suspicious_spikes: int,
    ) -> float:
        score = 100.0
        score -= missing_pct * 0.5
        score -= duplicate_count * 2.0
        score -= bad_price_count * 3.0
        score -= suspicious_spikes * 2.0
        return round(max(0.0, min(100.0, score)), 2)

    @staticmethod
    def _severity_for_missing(missing: int) -> str:
        if missing <= 3:
            return "low"
        if missing <= 24:
            return "medium"
        return "high"

    def _persist_metrics(self, metrics: QualityMetrics, import_run_id: uuid.UUID | None) -> None:
        existing = self._session.execute(
            select(MarketDataQualityReport).where(
                MarketDataQualityReport.asset_symbol == metrics.asset_symbol,
                MarketDataQualityReport.timeframe == metrics.timeframe,
                MarketDataQualityReport.provider == metrics.provider,
            )
        ).scalar_one_or_none()

        if existing:
            existing.evaluated_at = metrics.evaluated_at
            existing.expected_bars = metrics.expected_bars
            existing.actual_bars = metrics.actual_bars
            existing.total_bars = metrics.total_bars
            existing.completeness_pct = metrics.completeness_pct
            existing.missing_bars = metrics.missing_bars
            existing.duplicate_bars = metrics.duplicate_bars
            existing.bad_price_bars = metrics.bad_price_bars
            existing.suspicious_spike_bars = metrics.suspicious_spike_bars
            existing.earliest_bar_ts = metrics.earliest_bar_ts
            existing.latest_bar_ts = metrics.latest_bar_ts
            existing.quality_score = metrics.quality_score
            existing.approved_for_backtest = metrics.approved_for_backtest
            existing.notes = metrics.notes
            existing.metadata_json = {
                "missing_pct": metrics.missing_pct,
            }
        else:
            self._session.add(
                MarketDataQualityReport(
                    asset_symbol=metrics.asset_symbol,
                    timeframe=metrics.timeframe,
                    provider=metrics.provider,
                    evaluated_at=metrics.evaluated_at,
                    expected_bars=metrics.expected_bars,
                    actual_bars=metrics.actual_bars,
                    total_bars=metrics.total_bars,
                    completeness_pct=metrics.completeness_pct,
                    missing_bars=metrics.missing_bars,
                    duplicate_bars=metrics.duplicate_bars,
                    bad_price_bars=metrics.bad_price_bars,
                    suspicious_spike_bars=metrics.suspicious_spike_bars,
                    stale_bars=0,
                    earliest_bar_ts=metrics.earliest_bar_ts,
                    latest_bar_ts=metrics.latest_bar_ts,
                    quality_score=metrics.quality_score,
                    approved_for_backtest=metrics.approved_for_backtest,
                    notes=metrics.notes,
                    metadata_json={"missing_pct": metrics.missing_pct},
                )
            )

        self._session.execute(
            delete(MarketDataGap).where(
                MarketDataGap.asset_symbol == metrics.asset_symbol,
                MarketDataGap.timeframe == metrics.timeframe,
                MarketDataGap.provider == metrics.provider,
                MarketDataGap.status == "open",
            )
        )
        for gap in metrics.gaps:
            self._session.add(
                MarketDataGap(
                    asset_symbol=metrics.asset_symbol,
                    timeframe=metrics.timeframe,
                    provider=metrics.provider,
                    gap_start=gap.gap_start,
                    gap_end=gap.gap_end,
                    expected_candles_missing=gap.expected_candles_missing,
                    severity=gap.severity,
                    status="open",
                    import_run_id=import_run_id,
                    notes="Detected by MH-03 DataQualityEngine",
                )
            )

        if metrics.provider:
            now = datetime.now(UTC)
            pac_stmt = (
                pg_insert(ProviderAssetCoverage)
                .values(
                    id=uuid.uuid4(),
                    provider=metrics.provider,
                    asset_symbol=metrics.asset_symbol,
                    timeframe=metrics.timeframe,
                    available_from=metrics.earliest_bar_ts,
                    available_to=metrics.latest_bar_ts,
                    candle_count=metrics.total_bars,
                    missing_pct=metrics.missing_pct,
                    quality_score=metrics.quality_score,
                    approved_for_backtest=metrics.approved_for_backtest,
                    limitations=metrics.notes,
                    last_import_run_id=import_run_id,
                    evaluated_at=metrics.evaluated_at,
                    created_at=now,
                    updated_at=now,
                )
                .on_conflict_do_update(
                    constraint="uq_pac_provider_asset_tf",
                    set_={
                        "available_from": pg_insert(ProviderAssetCoverage).excluded.available_from,
                        "available_to": pg_insert(ProviderAssetCoverage).excluded.available_to,
                        "candle_count": pg_insert(ProviderAssetCoverage).excluded.candle_count,
                        "missing_pct": pg_insert(ProviderAssetCoverage).excluded.missing_pct,
                        "quality_score": pg_insert(ProviderAssetCoverage).excluded.quality_score,
                        "approved_for_backtest": pg_insert(ProviderAssetCoverage).excluded.approved_for_backtest,
                        "limitations": pg_insert(ProviderAssetCoverage).excluded.limitations,
                        "last_import_run_id": pg_insert(ProviderAssetCoverage).excluded.last_import_run_id,
                        "evaluated_at": pg_insert(ProviderAssetCoverage).excluded.evaluated_at,
                        "updated_at": pg_insert(ProviderAssetCoverage).excluded.updated_at,
                    },
                )
            )
            self._session.execute(pac_stmt)
            self._refresh_provider_coverage_snapshot(metrics.provider)

    def _refresh_provider_coverage_snapshot(self, provider: str) -> None:
        now = datetime.now(UTC)
        total_assets = int(self._session.execute(select(func.count(Asset.id))).scalar_one() or 0)

        pac_rows = self._session.execute(
            select(ProviderAssetCoverage).where(ProviderAssetCoverage.provider == provider)
        ).scalars().all()
        covered_assets = len({row.asset_symbol for row in pac_rows if row.candle_count > 0})
        total_bars = int(sum(row.candle_count for row in pac_rows))
        earliest = min((row.available_from for row in pac_rows if row.available_from), default=None)
        latest = max((row.available_to for row in pac_rows if row.available_to), default=None)
        coverage_pct = (covered_assets / total_assets * 100.0) if total_assets else 0.0

        self._session.add(
            ProviderCoverageReport(
                provider=provider,
                evaluated_at=now,
                total_assets=total_assets,
                covered_assets=covered_assets,
                coverage_pct=coverage_pct,
                earliest_bar_ts=earliest,
                latest_bar_ts=latest,
                total_bars=total_bars,
                notes="MH-03 quality-engine snapshot",
                metadata_json=None,
            )
        )
