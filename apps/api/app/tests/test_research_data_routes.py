"""Tests for MH-01 Data Centre Foundation — /research/data/* endpoints.

Tests:
- Route registration (all 5 endpoints reachable)
- Coverage response shape with no bars (empty state)
- Coverage response shape with existing bars
- Quality response shape with no bars (empty state)
- Quality response shape with existing bars
- Gaps response (always empty in MH-01; table exists but has no rows)
- Providers response (static catalogue, 6 entries)
- No duplicate candle table (bars table is the single OHLCV store)
"""

from __future__ import annotations

from datetime import datetime, UTC
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.enums import AssetClass
from app.db.models.asset import Asset
from app.db.models.bar import Bar
from app.db.session import SessionLocal, engine, get_db_session
from app.main import app


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


def _seed_bar(
    session: Session,
    asset_id: object,
    timeframe: str = "1d",
    ts: datetime | None = None,
    source: str = "polygon",
) -> Bar:
    bar = Bar(
        asset_id=asset_id,
        timeframe=timeframe,
        ts=ts or datetime(2025, 1, 2, tzinfo=UTC),
        open=100.0,
        high=105.0,
        low=99.0,
        close=103.0,
        volume=1_000_000.0,
        source=source,
    )
    session.add(bar)
    session.commit()
    return bar


@pytest.fixture()
def db_session() -> Session:  # type: ignore[misc]
    schema_name = f"test_research_{uuid4().hex}"

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


# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------


def test_research_data_assets_route_registered(client: TestClient) -> None:
    """GET /research/data/assets must be reachable (200)."""
    response = client.get("/research/data/assets")
    assert response.status_code == 200


def test_research_data_providers_route_registered(client: TestClient) -> None:
    """GET /research/data/providers must be reachable (200)."""
    response = client.get("/research/data/providers")
    assert response.status_code == 200


def test_research_data_coverage_route_registered(client: TestClient) -> None:
    """GET /research/data/coverage must be reachable (200)."""
    response = client.get("/research/data/coverage")
    assert response.status_code == 200


def test_research_data_quality_route_registered(client: TestClient) -> None:
    """GET /research/data/quality must be reachable (200)."""
    response = client.get("/research/data/quality")
    assert response.status_code == 200


def test_research_data_gaps_route_registered(client: TestClient) -> None:
    """GET /research/data/gaps must be reachable (200)."""
    response = client.get("/research/data/gaps")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Coverage response shape — empty state
# ---------------------------------------------------------------------------


def test_coverage_empty_state_no_assets(client: TestClient) -> None:
    """Coverage endpoint returns valid shape with zeros when no assets exist."""
    response = client.get("/research/data/coverage")
    assert response.status_code == 200
    body = response.json()
    assert "evaluated_at" in body
    assert body["total_assets"] == 0
    assert body["covered_assets"] == 0
    assert body["uncovered_assets"] == 0
    assert body["items"] == []


def test_coverage_empty_state_asset_no_bars(client: TestClient, db_session: Session) -> None:
    """Coverage endpoint correctly reports zero bars for an asset with no bars."""
    _seed_asset(db_session, "SPY")

    response = client.get("/research/data/coverage")
    assert response.status_code == 200
    body = response.json()
    assert body["total_assets"] == 1
    assert body["covered_assets"] == 0
    assert body["uncovered_assets"] == 1
    assert len(body["items"]) == 1

    item = body["items"][0]
    assert item["asset_symbol"] == "SPY"
    assert item["total_bars"] == 0
    assert item["timeframes"] == []
    assert item["providers"] == []
    assert item["earliest_bar_ts"] is None
    assert item["latest_bar_ts"] is None


# ---------------------------------------------------------------------------
# Coverage response shape — with bars
# ---------------------------------------------------------------------------


def test_coverage_with_bars(client: TestClient, db_session: Session) -> None:
    """Coverage endpoint reflects existing bar data correctly."""
    asset = _seed_asset(db_session, "TSLA", "Tesla Inc")
    _seed_bar(db_session, asset.id, timeframe="1d", source="polygon")
    _seed_bar(db_session, asset.id, timeframe="1h", ts=datetime(2025, 1, 3, 10, 0, tzinfo=UTC), source="tiingo")

    response = client.get("/research/data/coverage")
    assert response.status_code == 200
    body = response.json()
    assert body["total_assets"] == 1
    assert body["covered_assets"] == 1
    assert body["uncovered_assets"] == 0

    item = body["items"][0]
    assert item["asset_symbol"] == "TSLA"
    assert item["total_bars"] == 2
    assert set(item["timeframes"]) == {"1d", "1h"}
    assert set(item["providers"]) <= {"polygon", "tiingo"}
    assert item["earliest_bar_ts"] is not None
    assert item["latest_bar_ts"] is not None


# ---------------------------------------------------------------------------
# Quality response shape — empty state
# ---------------------------------------------------------------------------


def test_quality_empty_state_no_bars(client: TestClient) -> None:
    """Quality endpoint returns valid shape with no items when no bars exist."""
    response = client.get("/research/data/quality")
    assert response.status_code == 200
    body = response.json()
    assert "evaluated_at" in body
    assert body["total_items"] == 0
    assert body["items"] == []


def test_quality_empty_state_with_asset_but_no_bars(client: TestClient, db_session: Session) -> None:
    """Quality endpoint returns empty items even when assets exist but have no bars."""
    _seed_asset(db_session, "NVDA")

    response = client.get("/research/data/quality")
    assert response.status_code == 200
    body = response.json()
    assert body["total_items"] == 0
    assert body["items"] == []


# ---------------------------------------------------------------------------
# Quality response shape — with bars
# ---------------------------------------------------------------------------


def test_quality_with_bars_response_shape(client: TestClient, db_session: Session) -> None:
    """Quality endpoint returns correct shape for existing bars."""
    asset = _seed_asset(db_session, "MSFT", "Microsoft")
    _seed_bar(db_session, asset.id, timeframe="1d", source="polygon")

    response = client.get("/research/data/quality")
    assert response.status_code == 200
    body = response.json()
    assert body["total_items"] == 1

    item = body["items"][0]
    assert item["asset_symbol"] == "MSFT"
    assert item["timeframe"] == "1d"
    assert item["total_bars"] == 1
    assert item["duplicate_bars"] == 0
    assert item["earliest_bar_ts"] is not None
    assert item["latest_bar_ts"] is not None


def test_quality_filter_by_asset_symbol(client: TestClient, db_session: Session) -> None:
    """Quality endpoint ?asset_symbol= filter returns only matching asset rows."""
    asset1 = _seed_asset(db_session, "AMZN")
    asset2 = _seed_asset(db_session, "GOOG")
    _seed_bar(db_session, asset1.id, timeframe="1d", source="polygon")
    _seed_bar(db_session, asset2.id, timeframe="1d", source="polygon")

    response = client.get("/research/data/quality?asset_symbol=AMZN")
    assert response.status_code == 200
    body = response.json()
    assert body["total_items"] == 1
    assert body["items"][0]["asset_symbol"] == "AMZN"


# ---------------------------------------------------------------------------
# Gaps — empty state in MH-01 (table exists, no rows yet)
# ---------------------------------------------------------------------------


def test_gaps_empty_state(client: TestClient) -> None:
    """Gaps endpoint returns zero items in MH-01 (no gap records written yet)."""
    response = client.get("/research/data/gaps")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 0
    assert body["items"] == []


def test_gaps_filter_params_accepted(client: TestClient) -> None:
    """Gaps endpoint accepts asset_symbol and status query params without error."""
    response = client.get("/research/data/gaps?asset_symbol=AAPL&status=open")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 0


# ---------------------------------------------------------------------------
# Provider catalogue
# ---------------------------------------------------------------------------


def test_providers_returns_known_providers(client: TestClient) -> None:
    """Providers endpoint returns at least the 6 known providers."""
    response = client.get("/research/data/providers")
    assert response.status_code == 200
    body = response.json()
    assert "providers" in body
    names = {p["name"] for p in body["providers"]}
    assert {"polygon", "tiingo", "twelve_data", "yfinance", "ibkr", "mock"} <= names


def test_providers_schema_shape(client: TestClient) -> None:
    """Each provider entry has required fields."""
    response = client.get("/research/data/providers")
    body = response.json()
    for provider in body["providers"]:
        assert "name" in provider
        assert "label" in provider
        assert "supported_asset_classes" in provider
        assert "supported_timeframes" in provider


# ---------------------------------------------------------------------------
# No duplicate candle table (drift guard)
# ---------------------------------------------------------------------------


def test_no_duplicate_candle_table(db_session: Session) -> None:
    """The bars table is the single OHLCV store — no 'candles' or 'ohlcv' table exists."""
    inspector = inspect(db_session.bind)
    table_names = inspector.get_table_names()
    # bars table must exist
    assert "bars" in table_names, "bars table is missing"
    # No alternate candle tables should exist
    forbidden_names = {"candles", "ohlcv", "ohlcv_bars", "historical_bars", "price_bars"}
    duplicates = forbidden_names & set(table_names)
    assert not duplicates, f"Duplicate candle tables found: {duplicates}"


def test_data_centre_tables_exist(db_session: Session) -> None:
    """All four MH-01 data centre tables must be created by the migration."""
    inspector = inspect(db_session.bind)
    table_names = set(inspector.get_table_names())
    required = {
        "market_data_import_runs",
        "market_data_quality_reports",
        "market_data_gaps",
        "provider_coverage_reports",
    }
    missing = required - table_names
    assert not missing, f"Missing MH-01 tables: {missing}"
