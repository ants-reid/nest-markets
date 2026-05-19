"""Tests for MH-02 Historical Import Manager — POST /research/data/import and GET /research/data/import-runs.

Tests:
- POST /research/data/import dry_run returns plan with no bars written
- POST /research/data/import dry_run unknown provider records as dry_run
- POST /research/data/import live creates import run records per combo
- POST /research/data/import live writes bars for a known asset
- POST /research/data/import live partial success (asset not in DB) continues
- POST /research/data/import live creates provider_asset_coverage rows
- POST /research/data/import live creates quality report placeholder rows
- GET /research/data/import-runs returns created run records
- MH-01 endpoints still work (regression guard)
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.enums import AssetClass
from app.db.models.asset import Asset
from app.db.models.bar import Bar
from app.db.models.market_data_import_run import MarketDataImportRun
from app.db.models.market_data_quality_report import MarketDataQualityReport
from app.db.models.provider_asset_coverage import ProviderAssetCoverage
from app.db.session import SessionLocal, engine, get_db_session
from app.main import app
from app.clients.market_data.polygon_client import BarData
from app.services.historical_import_service import HistoricalImportService


# ---------------------------------------------------------------------------
# Helpers — synthetic bar factory
# ---------------------------------------------------------------------------

def _make_bars(
    ticker: str,
    from_date: date,
    to_date: date,
    timeframe: str,
    count: int = 5,
) -> list[BarData]:
    """Return a list of synthetic BarData for testing."""

    bars: list[BarData] = []
    start_ms = int(datetime(from_date.year, from_date.month, from_date.day, tzinfo=UTC).timestamp() * 1000)
    step_ms = 86_400_000  # 1 day in ms
    for i in range(count):
        bars.append(
            BarData(
                ticker=ticker,
                timestamp_ms=start_ms + i * step_ms,
                open=100.0 + i,
                high=105.0 + i,
                low=99.0 + i,
                close=103.0 + i,
                volume=1_000_000.0,
                timeframe=timeframe,
            )
        )
    return bars


def _mock_provider_fn(ticker: str, from_date: date, to_date: date, timeframe: str) -> list[BarData]:
    """Synchronous mock provider function — returns 5 bars for any request."""
    return _make_bars(ticker, from_date, to_date, timeframe, count=5)


async def _async_mock_provider_fn(ticker: str, from_date: date, to_date: date, timeframe: str) -> list[BarData]:
    return _mock_provider_fn(ticker, from_date, to_date, timeframe)


async def _empty_provider_fn(ticker: str, from_date: date, to_date: date, timeframe: str) -> list[BarData]:
    return []


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _seed_asset(session: Session, symbol: str = "AAPL", name: str = "Apple Inc") -> Asset:
    asset = Asset(
        symbol=symbol,
        name=name,
        asset_class=AssetClass.EQUITY,
        is_active=True,
    )
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset


@pytest.fixture()
def db_session():  # type: ignore[misc]
    schema_name = f"test_import_{uuid4().hex}"

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
def client(db_session: Session):  # type: ignore[misc]
    def _override():
        yield db_session

    app.dependency_overrides[get_db_session] = _override
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_db_session, None)


# ---------------------------------------------------------------------------
# POST /research/data/import — dry_run
# ---------------------------------------------------------------------------


def test_import_dry_run_returns_plan(client: TestClient, db_session: Session) -> None:
    """dry_run=True returns plan with no bars written, runs recorded as dry_run."""
    _seed_asset(db_session, "AAPL")

    payload = {
        "assets": ["AAPL"],
        "timeframes": ["1d"],
        "requested_years": 2,
        "providers": ["yfinance"],
        "dry_run": True,
    }
    response = client.post("/research/data/import", json=payload)
    assert response.status_code == 202, response.text

    body = response.json()
    assert body["dry_run"] is True
    assert body["status"] == "dry_run"
    assert "batch_id" in body
    assert len(body["results"]) == 1

    result = body["results"][0]
    assert result["asset_symbol"] == "AAPL"
    assert result["timeframe"] == "1d"
    assert result["status"] == "dry_run"
    assert result["candles_imported"] > 0  # estimated count, not 0

    # No real bars should have been written
    bars = db_session.execute(select(Bar)).scalars().all()
    assert bars == []

    # Import run record should exist with status dry_run
    runs = db_session.execute(select(MarketDataImportRun)).scalars().all()
    assert len(runs) == 1
    assert runs[0].status == "dry_run"
    assert runs[0].rows_upserted == 0


def test_import_dry_run_multi_provider(client: TestClient, db_session: Session) -> None:
    """dry_run with multiple providers returns one result per (asset,tf,provider) combo."""
    _seed_asset(db_session, "SPY")

    payload = {
        "assets": ["SPY"],
        "timeframes": ["1d"],
        "requested_years": 1,
        "providers": ["yfinance", "polygon"],
        "dry_run": True,
    }
    response = client.post("/research/data/import", json=payload)
    assert response.status_code == 202

    body = response.json()
    assert len(body["results"]) == 2
    assert all(r["status"] == "dry_run" for r in body["results"])


def test_import_dry_run_records_coverage_rows(client: TestClient, db_session: Session) -> None:
    """dry_run creates provider_asset_coverage rows (upserted with 0 candles)."""
    _seed_asset(db_session, "TSLA")

    payload = {
        "assets": ["TSLA"],
        "timeframes": ["1d"],
        "requested_years": 1,
        "providers": ["yfinance"],
        "dry_run": True,
    }
    response = client.post("/research/data/import", json=payload)
    assert response.status_code == 202

    rows = db_session.execute(select(ProviderAssetCoverage)).scalars().all()
    assert len(rows) == 1
    assert rows[0].provider == "yfinance"
    assert rows[0].asset_symbol == "TSLA"


# ---------------------------------------------------------------------------
# POST /research/data/import — live import with mock provider
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_import_creates_run_records_per_combo(db_session: Session) -> None:
    """Live import creates one MarketDataImportRun per (asset, tf, provider) combo."""
    _seed_asset(db_session, "AAPL")

    svc = HistoricalImportService(
        session=db_session,
        provider_overrides={"mock": _async_mock_provider_fn},
    )
    result = await svc.run_import(
        assets=["AAPL"],
        timeframes=["1d"],
        providers=["mock"],
        requested_years=1,
        dry_run=False,
    )

    assert result.status == "completed"
    assert len(result.results) == 1
    assert result.results[0].candles_imported == 5

    runs = db_session.execute(select(MarketDataImportRun)).scalars().all()
    assert len(runs) == 1
    assert runs[0].status == "completed"
    assert runs[0].rows_upserted == 5
    assert runs[0].batch_id == result.batch_id


@pytest.mark.asyncio
async def test_import_writes_bars_for_known_asset(db_session: Session) -> None:
    """Live import writes the expected bar rows into the bars table."""
    asset = _seed_asset(db_session, "MSFT")

    svc = HistoricalImportService(
        session=db_session,
        provider_overrides={"mock": _async_mock_provider_fn},
    )
    result = await svc.run_import(
        assets=["MSFT"],
        timeframes=["1d"],
        providers=["mock"],
        requested_years=1,
        dry_run=False,
    )

    assert result.results[0].candles_imported == 5

    bars = db_session.execute(
        select(Bar).where(Bar.asset_id == asset.id)
    ).scalars().all()
    assert len(bars) == 5
    assert all(b.timeframe == "1d" for b in bars)
    assert all(b.source == "mock" for b in bars)


@pytest.mark.asyncio
async def test_import_partial_success_continues_on_missing_asset(db_session: Session) -> None:
    """If one asset is missing from DB, it's skipped; others succeed."""
    _seed_asset(db_session, "AAPL")
    # UNKNOWN is intentionally NOT seeded

    svc = HistoricalImportService(
        session=db_session,
        provider_overrides={"mock": _async_mock_provider_fn},
    )
    result = await svc.run_import(
        assets=["AAPL", "UNKNOWN"],
        timeframes=["1d"],
        providers=["mock"],
        requested_years=1,
        dry_run=False,
    )

    statuses = {r.asset_symbol: r.status for r in result.results}
    # AAPL should succeed, UNKNOWN should be skipped (no Asset row)
    assert statuses["AAPL"] == "completed"
    assert statuses["UNKNOWN"] == "skipped"
    # Batch-level should be partial since one was skipped
    assert result.status in ("completed", "partial")


@pytest.mark.asyncio
async def test_import_creates_provider_asset_coverage(db_session: Session) -> None:
    """Live import creates a ProviderAssetCoverage row for the combo."""
    _seed_asset(db_session, "QQQ")

    svc = HistoricalImportService(
        session=db_session,
        provider_overrides={"mock": _async_mock_provider_fn},
    )
    await svc.run_import(
        assets=["QQQ"],
        timeframes=["1d"],
        providers=["mock"],
        requested_years=1,
        dry_run=False,
    )

    rows = db_session.execute(select(ProviderAssetCoverage)).scalars().all()
    assert len(rows) == 1
    row = rows[0]
    assert row.provider == "mock"
    assert row.asset_symbol == "QQQ"
    assert row.timeframe == "1d"
    assert row.candle_count == 5


@pytest.mark.asyncio
async def test_import_creates_quality_report_with_mh03_metrics(db_session: Session) -> None:
    """Live import triggers MH-03 quality calculation and persists metrics."""
    _seed_asset(db_session, "GLD")

    svc = HistoricalImportService(
        session=db_session,
        provider_overrides={"mock": _async_mock_provider_fn},
    )
    await svc.run_import(
        assets=["GLD"],
        timeframes=["1d"],
        providers=["mock"],
        requested_years=1,
        dry_run=False,
    )

    reports = db_session.execute(select(MarketDataQualityReport)).scalars().all()
    assert len(reports) == 1
    assert reports[0].asset_symbol == "GLD"
    assert reports[0].timeframe == "1d"
    assert reports[0].provider == "mock"
    assert reports[0].total_bars == 5
    assert reports[0].quality_score is not None
    assert reports[0].approved_for_backtest is not None


@pytest.mark.asyncio
async def test_import_upsert_idempotent(db_session: Session) -> None:
    """Running the same import twice doesn't duplicate bars or coverage rows."""
    _seed_asset(db_session, "SPY")

    svc = HistoricalImportService(
        session=db_session,
        provider_overrides={"mock": _async_mock_provider_fn},
    )
    await svc.run_import(
        assets=["SPY"],
        timeframes=["1d"],
        providers=["mock"],
        requested_years=1,
        dry_run=False,
    )
    await svc.run_import(
        assets=["SPY"],
        timeframes=["1d"],
        providers=["mock"],
        requested_years=1,
        dry_run=False,
    )

    # Bars should be upserted, not doubled (unique constraint)
    bars = db_session.execute(select(Bar)).scalars().all()
    assert len(bars) == 5  # not 10

    # Coverage row should be single, updated in-place
    coverage = db_session.execute(select(ProviderAssetCoverage)).scalars().all()
    assert len(coverage) == 1


@pytest.mark.asyncio
async def test_import_skips_unknown_provider(db_session: Session) -> None:
    """Provider not in the registry records as skipped, not failed."""
    _seed_asset(db_session, "AAPL")

    svc = HistoricalImportService(
        session=db_session,
        provider_overrides={},  # empty registry
    )
    result = await svc.run_import(
        assets=["AAPL"],
        timeframes=["1d"],
        providers=["nonexistent"],
        requested_years=1,
        dry_run=False,
    )

    assert result.results[0].status == "skipped"
    runs = db_session.execute(select(MarketDataImportRun)).scalars().all()
    assert runs[0].status == "skipped"


# ---------------------------------------------------------------------------
# GET /research/data/import-runs
# ---------------------------------------------------------------------------


def test_list_import_runs_empty(client: TestClient) -> None:
    """Import runs endpoint returns empty list when no runs exist."""
    response = client.get("/research/data/import-runs")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 0
    assert body["items"] == []


def test_list_import_runs_returns_created_runs(client: TestClient, db_session: Session) -> None:
    """Import runs endpoint returns runs after a dry_run import."""
    _seed_asset(db_session, "AAPL")

    payload = {
        "assets": ["AAPL"],
        "timeframes": ["1d"],
        "requested_years": 1,
        "providers": ["yfinance"],
        "dry_run": True,
    }
    post_resp = client.post("/research/data/import", json=payload)
    assert post_resp.status_code == 202

    get_resp = client.get("/research/data/import-runs")
    assert get_resp.status_code == 200
    body = get_resp.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["dry_run"] is True
    assert "batch_id" in item


def test_list_import_runs_filter_by_batch_id(client: TestClient, db_session: Session) -> None:
    """Import runs can be filtered by batch_id."""
    _seed_asset(db_session, "AAPL")

    # Create two separate batches
    for _ in range(2):
        client.post("/research/data/import", json={
            "assets": ["AAPL"],
            "timeframes": ["1d"],
            "requested_years": 1,
            "providers": ["yfinance"],
            "dry_run": True,
        })

    # Get runs and pick first batch_id
    all_runs = client.get("/research/data/import-runs").json()
    assert all_runs["total"] >= 2

    first_bid = all_runs["items"][0]["batch_id"]
    filtered = client.get(f"/research/data/import-runs?batch_id={first_bid}")
    assert filtered.status_code == 200
    items = filtered.json()["items"]
    assert all(item["batch_id"] == first_bid for item in items)


# ---------------------------------------------------------------------------
# MH-01 regression guard
# ---------------------------------------------------------------------------


def test_mh01_endpoints_unaffected(client: TestClient) -> None:
    """All MH-01 endpoints are still reachable and return 200 after MH-02 changes."""
    for path in ["/research/data/assets", "/research/data/providers",
                 "/research/data/coverage", "/research/data/quality", "/research/data/gaps"]:
        resp = client.get(path)
        assert resp.status_code == 200, f"{path} returned {resp.status_code}: {resp.text}"
