"""HistoricalImportService — batch historical bar import for the Data Centre.

MH-02: Historical Import Manager.

Responsibilities:
- Accept (assets, timeframes, providers, requested_years, dry_run) batch request.
- Calculate requested_start = now − requested_years.
- For each (asset, timeframe, provider) combination:
  - In dry_run mode: record the plan without fetching or writing bars.
  - In live mode: fetch bars from the provider, upsert into the existing bars
    table, record the actual available date range and candle count.
- Continue processing even when one combination fails (partial success).
- Write MarketDataImportRun records per combination (batch_id groups them).
- Upsert ProviderAssetCoverage rows.
- Upsert MarketDataQualityReport placeholder rows.
- Return a structured BatchImportResult.

Provider support matrix (MH-02):
  yfinance  — functional, no API key required
  polygon   — functional, requires POLYGON_API_KEY; returns [] without key
  mock      — functional, deterministic synthetic bars for testing
  tiingo    — stub, raises NotImplementedError → records as skipped
  twelvedata — stub, raises NotImplementedError → records as skipped
  ibkr      — stub, raises NotImplementedError → records as skipped

The service accepts an optional ``provider_overrides`` dict for testing
so the real network clients can be replaced with mocks.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Callable, Sequence

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.clients.market_data.polygon_client import BarData, PolygonClient
from app.clients.market_data.yfinance_client import YFinanceClient
from app.config import get_settings
from app.db.models.asset import Asset
from app.db.models.bar import Bar
from app.db.models.market_data_import_run import MarketDataImportRun
from app.db.models.provider_asset_coverage import ProviderAssetCoverage
from app.services.data_quality_engine import DataQualityEngine

_logger = logging.getLogger(__name__)

# Type alias: any callable with the same signature as YFinanceClient.get_bars
ProviderFn = Callable[[str, date, date, str], list[BarData]]


# ---------------------------------------------------------------------------
# Result dataclasses (internal; converted to Pydantic in the route layer)
# ---------------------------------------------------------------------------

@dataclass
class AssetImportResult:
    asset_symbol: str
    timeframe: str
    provider: str
    requested_start: datetime
    requested_end: datetime
    available_from: datetime | None
    available_to: datetime | None
    candles_imported: int
    status: str  # completed | partial | failed | skipped | dry_run
    message: str | None


@dataclass
class BatchImportResult:
    batch_id: uuid.UUID
    status: str  # completed | partial | failed | dry_run
    requested_years: int
    dry_run: bool
    started_at: datetime
    completed_at: datetime
    results: list[AssetImportResult] = field(default_factory=list)

    @property
    def total_candles_imported(self) -> int:
        return sum(r.candles_imported for r in self.results)


# ---------------------------------------------------------------------------
# Main service
# ---------------------------------------------------------------------------

class HistoricalImportService:
    """Batch historical bar import manager."""

    # Timeframes known to yfinance; intraday is limited by the library
    _YFINANCE_INTRADAY_LIMIT_DAYS = 730  # ~2 years for 1h; shorter for finer TFs

    def __init__(
        self,
        session: Session,
        provider_overrides: dict[str, ProviderFn] | None = None,
    ) -> None:
        self._session = session
        self._provider_fns = self._build_provider_registry(provider_overrides)
        self._quality_engine = DataQualityEngine(session)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run_import(
        self,
        assets: list[str],
        timeframes: list[str],
        providers: list[str],
        requested_years: int,
        dry_run: bool = False,
    ) -> BatchImportResult:
        """Execute a batch import and return structured results.

        Never raises — individual combination failures are captured in results.
        """
        batch_id = uuid.uuid4()
        started_at = datetime.now(UTC)
        now: date = datetime.now(UTC).date()
        requested_start_date = date(now.year - requested_years, now.month, now.day)
        requested_end_date = now

        requested_start_dt = datetime(
            requested_start_date.year, requested_start_date.month, requested_start_date.day, tzinfo=UTC
        )
        requested_end_dt = datetime(
            requested_end_date.year, requested_end_date.month, requested_end_date.day, tzinfo=UTC
        )

        results: list[AssetImportResult] = []

        for asset_symbol in assets:
            for timeframe in timeframes:
                for provider_name in providers:
                    result = await self._import_one(
                        batch_id=batch_id,
                        asset_symbol=asset_symbol.upper(),
                        timeframe=timeframe,
                        provider_name=provider_name,
                        requested_start=requested_start_dt,
                        requested_end=requested_end_dt,
                        requested_start_date=requested_start_date,
                        requested_end_date=requested_end_date,
                        dry_run=dry_run,
                    )
                    results.append(result)

        completed_at = datetime.now(UTC)

        # Determine batch-level status
        statuses = {r.status for r in results}
        if dry_run:
            batch_status = "dry_run"
        elif "failed" in statuses and all(r.status == "failed" for r in results):
            batch_status = "failed"
        elif "failed" in statuses or "skipped" in statuses:
            batch_status = "partial"
        else:
            batch_status = "completed"

        return BatchImportResult(
            batch_id=batch_id,
            status=batch_status,
            requested_years=requested_years,
            dry_run=dry_run,
            started_at=started_at,
            completed_at=completed_at,
            results=results,
        )

    # ------------------------------------------------------------------
    # Per-combination import
    # ------------------------------------------------------------------

    async def _import_one(
        self,
        batch_id: uuid.UUID,
        asset_symbol: str,
        timeframe: str,
        provider_name: str,
        requested_start: datetime,
        requested_end: datetime,
        requested_start_date: date,
        requested_end_date: date,
        dry_run: bool,
    ) -> AssetImportResult:
        """Import bars for one (asset, timeframe, provider) and record the run."""
        started = datetime.now(UTC)

        if dry_run:
            result = self._dry_run_result(
                batch_id=batch_id,
                asset_symbol=asset_symbol,
                timeframe=timeframe,
                provider_name=provider_name,
                requested_start=requested_start,
                requested_end=requested_end,
                requested_start_date=requested_start_date,
                requested_end_date=requested_end_date,
            )
            # Still record the import run as dry_run
            self._record_import_run(
                batch_id=batch_id,
                asset_symbol=asset_symbol,
                timeframe=timeframe,
                provider_name=provider_name,
                from_date=requested_start,
                to_date=requested_end,
                rows_requested=result.candles_imported,
                rows_upserted=0,
                status="dry_run",
                error_message=None,
                started_at=started,
                finished_at=datetime.now(UTC),
            )
            self._upsert_provider_asset_coverage(
                provider=provider_name,
                asset_symbol=asset_symbol,
                timeframe=timeframe,
                requested_start=requested_start,
                requested_end=requested_end,
                available_from=result.available_from,
                available_to=result.available_to,
                candle_count=0,
                limitations=result.message,
            )
            self._session.commit()
            return result

        # ── Live import ────────────────────────────────────────────────
        provider_fn = self._provider_fns.get(provider_name)

        # ── Check asset exists before calling provider ─────────────────
        asset_exists = self._session.execute(
            select(Asset).where(Asset.symbol == asset_symbol)
        ).scalar_one_or_none()
        if asset_exists is None:
            msg = f"Asset '{asset_symbol}' not found in database — import skipped"
            _logger.warning("Import skipped %s/%s/%s: asset not found", provider_name, asset_symbol, timeframe)
            self._record_import_run(
                batch_id=batch_id,
                asset_symbol=asset_symbol,
                timeframe=timeframe,
                provider_name=provider_name,
                from_date=requested_start,
                to_date=requested_end,
                rows_requested=None,
                rows_upserted=0,
                status="skipped",
                error_message=msg,
                started_at=started,
                finished_at=datetime.now(UTC),
            )
            self._session.commit()
            return AssetImportResult(
                asset_symbol=asset_symbol,
                timeframe=timeframe,
                provider=provider_name,
                requested_start=requested_start,
                requested_end=requested_end,
                available_from=None,
                available_to=None,
                candles_imported=0,
                status="skipped",
                message=msg,
            )

        if provider_fn is None:
            msg = f"Provider '{provider_name}' is not supported in MH-02"
            self._record_import_run(
                batch_id=batch_id,
                asset_symbol=asset_symbol,
                timeframe=timeframe,
                provider_name=provider_name,
                from_date=requested_start,
                to_date=requested_end,
                rows_requested=None,
                rows_upserted=0,
                status="skipped",
                error_message=msg,
                started_at=started,
                finished_at=datetime.now(UTC),
            )
            self._session.commit()
            return AssetImportResult(
                asset_symbol=asset_symbol,
                timeframe=timeframe,
                provider=provider_name,
                requested_start=requested_start,
                requested_end=requested_end,
                available_from=None,
                available_to=None,
                candles_imported=0,
                status="skipped",
                message=msg,
            )

        # Fetch bars from provider (tolerates failure)
        try:
            bars = await provider_fn(
                asset_symbol,
                requested_start_date,
                requested_end_date,
                timeframe,
            )
        except Exception as exc:  # noqa: BLE001
            msg = f"Provider fetch failed: {exc}"
            _logger.warning("Import failed %s/%s/%s: %s", provider_name, asset_symbol, timeframe, exc)
            self._record_import_run(
                batch_id=batch_id,
                asset_symbol=asset_symbol,
                timeframe=timeframe,
                provider_name=provider_name,
                from_date=requested_start,
                to_date=requested_end,
                rows_requested=None,
                rows_upserted=0,
                status="failed",
                error_message=msg,
                started_at=started,
                finished_at=datetime.now(UTC),
            )
            self._session.commit()
            return AssetImportResult(
                asset_symbol=asset_symbol,
                timeframe=timeframe,
                provider=provider_name,
                requested_start=requested_start,
                requested_end=requested_end,
                available_from=None,
                available_to=None,
                candles_imported=0,
                status="failed",
                message=msg,
            )

        if not bars:
            msg = f"No bars returned by {provider_name} for {asset_symbol}/{timeframe}"
            self._record_import_run(
                batch_id=batch_id,
                asset_symbol=asset_symbol,
                timeframe=timeframe,
                provider_name=provider_name,
                from_date=requested_start,
                to_date=requested_end,
                rows_requested=0,
                rows_upserted=0,
                status="skipped",
                error_message=msg,
                started_at=started,
                finished_at=datetime.now(UTC),
            )
            self._upsert_provider_asset_coverage(
                provider=provider_name,
                asset_symbol=asset_symbol,
                timeframe=timeframe,
                requested_start=requested_start,
                requested_end=requested_end,
                available_from=None,
                available_to=None,
                candle_count=0,
                limitations=msg,
            )
            self._session.commit()
            return AssetImportResult(
                asset_symbol=asset_symbol,
                timeframe=timeframe,
                provider=provider_name,
                requested_start=requested_start,
                requested_end=requested_end,
                available_from=None,
                available_to=None,
                candles_imported=0,
                status="skipped",
                message=msg,
            )

        # Upsert bars into the existing bars table
        upserted = self._upsert_bars(
            asset_symbol=asset_symbol,
            timeframe=timeframe,
            bars=bars,
            provider_name=provider_name,
        )

        available_from, available_to = self._date_range(bars)
        finished = datetime.now(UTC)
        # Determine limitation message if provider returned less than requested
        limitation: str | None = None
        if available_from and available_from > requested_start:
            limitation = (
                f"{provider_name} oldest available bar: {available_from.date().isoformat()}; "
                f"requested from {requested_start.date().isoformat()}"
            )

        status = "completed" if upserted > 0 else "partial"

        import_run = self._record_import_run(
            batch_id=batch_id,
            asset_symbol=asset_symbol,
            timeframe=timeframe,
            provider_name=provider_name,
            from_date=requested_start,
            to_date=requested_end,
            rows_requested=len(bars),
            rows_upserted=upserted,
            status=status,
            error_message=limitation,
            started_at=started,
            finished_at=finished,
        )
        self._upsert_provider_asset_coverage(
            provider=provider_name,
            asset_symbol=asset_symbol,
            timeframe=timeframe,
            requested_start=requested_start,
            requested_end=requested_end,
            available_from=available_from,
            available_to=available_to,
            candle_count=upserted,
            limitations=limitation,
        )
        self._quality_engine.recalculate_and_persist(
            assets=[asset_symbol],
            timeframes=[timeframe],
            providers=[provider_name],
            import_run_id=import_run.id,
        )
        self._session.commit()

        return AssetImportResult(
            asset_symbol=asset_symbol,
            timeframe=timeframe,
            provider=provider_name,
            requested_start=requested_start,
            requested_end=requested_end,
            available_from=available_from,
            available_to=available_to,
            candles_imported=upserted,
            status=status,
            message=limitation,
        )

    # ------------------------------------------------------------------
    # Dry-run
    # ------------------------------------------------------------------

    def _dry_run_result(
        self,
        batch_id: uuid.UUID,
        asset_symbol: str,
        timeframe: str,
        provider_name: str,
        requested_start: datetime,
        requested_end: datetime,
        requested_start_date: date,
        requested_end_date: date,
    ) -> AssetImportResult:
        """Estimate the import plan without calling the provider or writing bars."""
        days = (requested_end_date - requested_start_date).days
        estimated = self._estimate_bar_count(timeframe, days)

        # yfinance intraday limitation note
        limitation: str | None = None
        if timeframe in ("1h", "4h", "30m", "15m", "5m", "1m") and days > self._YFINANCE_INTRADAY_LIMIT_DAYS:
            available_start = requested_end_date - timedelta(days=self._YFINANCE_INTRADAY_LIMIT_DAYS)
            limitation = (
                f"yfinance intraday ({timeframe}) limited to ~{self._YFINANCE_INTRADAY_LIMIT_DAYS} days; "
                f"estimated available from {available_start.isoformat()}"
            )
            estimated = self._estimate_bar_count(timeframe, self._YFINANCE_INTRADAY_LIMIT_DAYS)

        return AssetImportResult(
            asset_symbol=asset_symbol,
            timeframe=timeframe,
            provider=provider_name,
            requested_start=requested_start,
            requested_end=requested_end,
            available_from=requested_start,
            available_to=requested_end,
            candles_imported=estimated,
            status="dry_run",
            message=limitation,
        )

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    def _upsert_bars(
        self,
        asset_symbol: str,
        timeframe: str,
        bars: Sequence[BarData],
        provider_name: str,
    ) -> int:
        """Upsert BarData list into the existing bars table. Returns upserted count."""
        asset = self._session.execute(
            select(Asset).where(Asset.symbol == asset_symbol)
        ).scalar_one_or_none()

        if asset is None:
            _logger.warning("Asset %s not found in database — skipping bar upsert", asset_symbol)
            return 0

        rows = [
            {
                "asset_id": asset.id,
                "timeframe": timeframe,
                "ts": datetime.fromtimestamp(bar.timestamp_ms / 1000, tz=UTC),
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
                "volume": bar.volume,
                "source": provider_name,
            }
            for bar in bars
        ]

        if not rows:
            return 0

        stmt = (
            pg_insert(Bar)
            .values(rows)
            .on_conflict_do_update(
                constraint="uq_bars_asset_timeframe_ts",
                set_={
                    "open": pg_insert(Bar).excluded.open,
                    "high": pg_insert(Bar).excluded.high,
                    "low": pg_insert(Bar).excluded.low,
                    "close": pg_insert(Bar).excluded.close,
                    "volume": pg_insert(Bar).excluded.volume,
                    "source": pg_insert(Bar).excluded.source,
                },
            )
        )
        self._session.execute(stmt)
        return len(rows)

    def _record_import_run(
        self,
        batch_id: uuid.UUID,
        asset_symbol: str,
        timeframe: str,
        provider_name: str,
        from_date: datetime,
        to_date: datetime,
        rows_requested: int | None,
        rows_upserted: int,
        status: str,
        error_message: str | None,
        started_at: datetime,
        finished_at: datetime,
    ) -> MarketDataImportRun:
        duration = (finished_at - started_at).total_seconds()
        run = MarketDataImportRun(
            batch_id=batch_id,
            provider=provider_name,
            asset_symbol=asset_symbol,
            timeframe=timeframe,
            from_date=from_date,
            to_date=to_date,
            rows_requested=rows_requested,
            rows_upserted=rows_upserted,
            rows_skipped=None,
            status=status,
            error_message=error_message,
            duration_seconds=duration,
            started_at=started_at,
            finished_at=finished_at,
        )
        self._session.add(run)
        return run

    def _upsert_provider_asset_coverage(
        self,
        provider: str,
        asset_symbol: str,
        timeframe: str,
        requested_start: datetime,
        requested_end: datetime,
        available_from: datetime | None,
        available_to: datetime | None,
        candle_count: int,
        limitations: str | None,
    ) -> None:
        """Insert or update the ProviderAssetCoverage row."""
        now = datetime.now(UTC)
        stmt = (
            pg_insert(ProviderAssetCoverage)
            .values(
                id=uuid.uuid4(),
                provider=provider,
                asset_symbol=asset_symbol,
                timeframe=timeframe,
                requested_start=requested_start,
                requested_end=requested_end,
                available_from=available_from,
                available_to=available_to,
                candle_count=candle_count,
                limitations=limitations,
                evaluated_at=now,
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_update(
                constraint="uq_pac_provider_asset_tf",
                set_={
                    "requested_start": pg_insert(ProviderAssetCoverage).excluded.requested_start,
                    "requested_end": pg_insert(ProviderAssetCoverage).excluded.requested_end,
                    "available_from": pg_insert(ProviderAssetCoverage).excluded.available_from,
                    "available_to": pg_insert(ProviderAssetCoverage).excluded.available_to,
                    "candle_count": pg_insert(ProviderAssetCoverage).excluded.candle_count,
                    "limitations": pg_insert(ProviderAssetCoverage).excluded.limitations,
                    "evaluated_at": pg_insert(ProviderAssetCoverage).excluded.evaluated_at,
                    "updated_at": pg_insert(ProviderAssetCoverage).excluded.updated_at,
                },
            )
        )
        self._session.execute(stmt)

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _date_range(bars: Sequence[BarData]) -> tuple[datetime | None, datetime | None]:
        """Return (earliest, latest) datetimes from a bar list."""
        if not bars:
            return None, None
        ts_values = [datetime.fromtimestamp(b.timestamp_ms / 1000, tz=UTC) for b in bars]
        return min(ts_values), max(ts_values)

    @staticmethod
    def _estimate_bar_count(timeframe: str, days: int) -> int:
        """Rough estimate of bar count for a date range and timeframe."""
        # Approximate trading days = 70% of calendar days
        trading_days = max(1, int(days * 0.7))
        multipliers = {
            "1d": 1,
            "day": 1,
            "4h": 2,
            "1h": 7,
            "30m": 14,
            "15m": 26,
            "5m": 78,
            "1m": 390,
        }
        return trading_days * multipliers.get(timeframe, 1)

    def _build_provider_registry(
        self,
        overrides: dict[str, ProviderFn] | None,
    ) -> dict[str, ProviderFn]:
        """Build the provider function registry.

        Uses injected overrides first (for testing), then builds real clients.
        Unsupported providers are simply absent from the registry; the caller
        handles the missing-key case as a "skipped" result.
        """
        if overrides is not None:
            return dict(overrides)

        registry: dict[str, ProviderFn] = {}

        # yfinance — always available (no key required)
        yf_client = YFinanceClient()
        registry["yfinance"] = yf_client.get_bars

        # polygon — available only when key is configured
        settings = get_settings()
        if settings.polygon_api_key:
            polygon_client = PolygonClient(api_key=settings.polygon_api_key)
            registry["polygon"] = polygon_client.get_bars

        # tiingo, twelvedata, ibkr are stubs — not registered (handled as skipped)

        return registry
