"""MH-03 tests for deterministic DataQualityEngine and quality endpoints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.enums import AssetClass
from app.db.models.asset import Asset
from app.db.models.bar import Bar
from app.db.models.market_data_gap import MarketDataGap
from app.db.models.market_data_quality_report import MarketDataQualityReport
from app.db.session import SessionLocal, engine, get_db_session
from app.main import app
from app.services.data_quality_engine import DataQualityEngine


@pytest.fixture()
def db_session() -> Session:  # type: ignore[misc]
    schema_name = f"test_quality_{uuid4().hex}"

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


def _seed_asset(session: Session, symbol: str, asset_class: AssetClass = AssetClass.EQUITY) -> Asset:
    asset = Asset(symbol=symbol, name=symbol, asset_class=asset_class, is_active=True)
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset


def _seed_bar(
    session: Session,
    asset_id: object,
    ts: datetime,
    timeframe: str = "1h",
    source: str = "mock",
    open_: float = 100.0,
    high: float = 102.0,
    low: float = 99.0,
    close: float = 101.0,
) -> None:
    session.add(
        Bar(
            asset_id=asset_id,
            timeframe=timeframe,
            ts=ts,
            open=open_,
            high=high,
            low=low,
            close=close,
            volume=1000.0,
            source=source,
        )
    )
    session.commit()


def test_duplicate_timestamp_detection_pure_function(db_session: Session) -> None:
    engine_svc = DataQualityEngine(db_session)
    t0 = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    t1 = t0 + timedelta(hours=1)
    bars = [
        SimpleNamespace(ts=t0, open=1, high=2, low=1, close=2),
        SimpleNamespace(ts=t0, open=1, high=2, low=1, close=2),
        SimpleNamespace(ts=t1, open=1, high=2, low=1, close=2),
    ]

    metrics = engine_svc._calculate_from_bars("AAPL", "1h", "mock", bars)  # noqa: SLF001
    assert metrics.duplicate_bars == 1


def test_missing_candle_gap_detection(db_session: Session) -> None:
    asset = _seed_asset(db_session, "AAPL")
    t0 = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    _seed_bar(db_session, asset.id, t0)
    _seed_bar(db_session, asset.id, t0 + timedelta(hours=3))

    engine_svc = DataQualityEngine(db_session)
    metrics = engine_svc.calculate("AAPL", "1h", "mock")

    assert metrics.missing_bars == 2
    assert len(metrics.gaps) == 1
    assert metrics.gaps[0].expected_candles_missing == 2
    assert metrics.gaps[0].severity == "low"


def test_bad_ohlc_and_non_positive_detection(db_session: Session) -> None:
    asset = _seed_asset(db_session, "MSFT")
    ts = datetime(2026, 1, 2, 0, 0, tzinfo=UTC)

    _seed_bar(db_session, asset.id, ts, open_=0.0, high=2.0, low=1.0, close=1.5)
    _seed_bar(db_session, asset.id, ts + timedelta(hours=1), open_=5.0, high=3.0, low=4.0, close=4.5)

    metrics = DataQualityEngine(db_session).calculate("MSFT", "1h", "mock")
    assert metrics.bad_price_bars == 2


def test_suspicious_spike_detection(db_session: Session) -> None:
    asset = _seed_asset(db_session, "TSLA")
    t0 = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    for i in range(25):
        _seed_bar(
            db_session,
            asset.id,
            t0 + timedelta(hours=i),
            open_=100.0,
            high=102.0,
            low=99.0,
            close=101.0,
        )

    _seed_bar(
        db_session,
        asset.id,
        t0 + timedelta(hours=25),
        open_=100.0,
        high=200.0,
        low=90.0,
        close=110.0,
    )

    metrics = DataQualityEngine(db_session).calculate("TSLA", "1h", "mock")
    assert metrics.suspicious_spike_bars >= 1


def test_quality_score_threshold_approval(db_session: Session) -> None:
    engine_svc = DataQualityEngine(db_session)
    score = engine_svc._quality_score(5.0, 0, 0, 0)  # noqa: SLF001
    assert score >= 90.0

    low_score = engine_svc._quality_score(90.0, 5, 5, 5)  # noqa: SLF001
    assert low_score < 75.0


def test_quality_recalculate_endpoint_and_gap_persistence(client: TestClient, db_session: Session) -> None:
    asset = _seed_asset(db_session, "QQQ")
    t0 = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    _seed_bar(db_session, asset.id, t0)
    _seed_bar(db_session, asset.id, t0 + timedelta(hours=2))

    response = client.post(
        "/research/data/quality/recalculate",
        json={
            "assets": ["QQQ"],
            "timeframes": ["1h"],
            "providers": ["mock"],
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 1
    assert body["succeeded"] == 1
    assert body["items"][0]["gap_count"] == 1

    gaps = db_session.execute(select(MarketDataGap)).scalars().all()
    assert len(gaps) == 1
    assert gaps[0].expected_candles_missing == 1


def test_quality_endpoint_returns_real_mh03_fields(client: TestClient, db_session: Session) -> None:
    asset = _seed_asset(db_session, "SPY")
    ts = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    _seed_bar(db_session, asset.id, ts)
    _seed_bar(db_session, asset.id, ts + timedelta(hours=1))

    resp = client.get("/research/data/quality?asset_symbol=SPY")
    assert resp.status_code == 200
    item = resp.json()["items"][0]
    assert item["quality_score"] is not None
    assert item["approved_for_backtest"] in (True, False)
    assert "bad_price_bars" in item
    assert "suspicious_spike_bars" in item


def test_gaps_endpoint_returns_detected_gaps(client: TestClient, db_session: Session) -> None:
    asset = _seed_asset(db_session, "IWM")
    t0 = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    _seed_bar(db_session, asset.id, t0)
    _seed_bar(db_session, asset.id, t0 + timedelta(hours=4))

    recalc = client.post(
        "/research/data/quality/recalculate",
        json={"assets": ["IWM"], "timeframes": ["1h"], "providers": ["mock"]},
    )
    assert recalc.status_code == 200

    resp = client.get("/research/data/gaps?asset_symbol=IWM&status=open")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    gap = body["items"][0]
    assert gap["severity"] in {"low", "medium", "high"}
    assert gap["expected_candles_missing"] >= 1


def test_quality_report_persisted_after_recalculate(client: TestClient, db_session: Session) -> None:
    asset = _seed_asset(db_session, "DIA")
    t0 = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    _seed_bar(db_session, asset.id, t0)
    _seed_bar(db_session, asset.id, t0 + timedelta(hours=1))

    recalc = client.post(
        "/research/data/quality/recalculate",
        json={"assets": ["DIA"], "timeframes": ["1h"], "providers": ["mock"]},
    )
    assert recalc.status_code == 200

    reports = db_session.execute(select(MarketDataQualityReport)).scalars().all()
    assert len(reports) == 1
    assert reports[0].quality_score is not None
    assert reports[0].actual_bars == 2


@pytest.mark.parametrize(
    ("symbol", "asset_class"),
    [
        ("AAPL", AssetClass.EQUITY),
        ("SPY", AssetClass.ETF),
        ("VIXIDX", AssetClass.INDEX_PROXY),
        ("EURUSD", AssetClass.FX),
    ],
)
def test_daily_weekend_not_missing_for_weekday_classes(
    db_session: Session,
    symbol: str,
    asset_class: AssetClass,
) -> None:
    asset = _seed_asset(db_session, symbol, asset_class=asset_class)
    # Mon..Fri only (2026-01-05 to 2026-01-09)
    t0 = datetime(2026, 1, 5, 0, 0, tzinfo=UTC)
    for i in range(5):
        _seed_bar(db_session, asset.id, t0 + timedelta(days=i), timeframe="1d")

    metrics = DataQualityEngine(db_session).calculate(symbol, "1d", "mock")
    assert metrics.expected_bars == 5
    assert metrics.actual_bars == 5
    assert metrics.missing_bars == 0
    assert metrics.gaps == []
    assert metrics.quality_score >= 99.0
    assert metrics.approved_for_backtest is True


def test_daily_crypto_counts_weekends_as_expected(db_session: Session) -> None:
    asset = _seed_asset(db_session, "BTC-USD", asset_class=AssetClass.CRYPTO)
    # Seed only weekdays within Mon..Sun span; weekend should be counted as missing.
    t0 = datetime(2026, 1, 5, 0, 0, tzinfo=UTC)
    for i in range(5):
        _seed_bar(db_session, asset.id, t0 + timedelta(days=i), timeframe="1d")

    metrics = DataQualityEngine(db_session).calculate("BTC-USD", "1d", "mock")
    assert metrics.expected_bars == 5
    assert metrics.missing_bars == 0

    # Add Monday after weekend to include Sat/Sun in expected range.
    _seed_bar(db_session, asset.id, datetime(2026, 1, 12, 0, 0, tzinfo=UTC), timeframe="1d")
    metrics2 = DataQualityEngine(db_session).calculate("BTC-USD", "1d", "mock")
    assert metrics2.expected_bars == 8
    assert metrics2.actual_bars == 6
    assert metrics2.missing_bars == 2
    assert len(metrics2.gaps) == 1
    assert metrics2.gaps[0].expected_candles_missing == 2


def test_daily_equity_weekend_gap_not_created(db_session: Session) -> None:
    asset = _seed_asset(db_session, "WEND", asset_class=AssetClass.EQUITY)
    # Friday then Monday only; weekend should not produce a gap.
    _seed_bar(db_session, asset.id, datetime(2026, 1, 9, 0, 0, tzinfo=UTC), timeframe="1d")
    _seed_bar(db_session, asset.id, datetime(2026, 1, 12, 0, 0, tzinfo=UTC), timeframe="1d")

    metrics = DataQualityEngine(db_session).calculate("WEND", "1d", "mock")
    assert metrics.expected_bars == 2
    assert metrics.actual_bars == 2
    assert metrics.missing_bars == 0
    assert metrics.gaps == []


def test_fx_daily_tiny_ohlc_outside_range_not_bad(db_session: Session) -> None:
    asset = _seed_asset(db_session, "EURUSD", asset_class=AssetClass.FX)
    ts = datetime(2026, 1, 5, 0, 0, tzinfo=UTC)

    # close is slightly below low; within FX daily tolerance envelope
    _seed_bar(
        db_session,
        asset.id,
        ts,
        timeframe="1d",
        open_=1.10000,
        high=1.10200,
        low=1.10000,
        close=1.09970,
    )
    metrics = DataQualityEngine(db_session).calculate("EURUSD", "1d", "mock")
    assert metrics.bad_price_bars == 0


def test_fx_daily_high_less_than_low_still_bad(db_session: Session) -> None:
    asset = _seed_asset(db_session, "GBPUSD", asset_class=AssetClass.FX)
    ts = datetime(2026, 1, 6, 0, 0, tzinfo=UTC)
    _seed_bar(
        db_session,
        asset.id,
        ts,
        timeframe="1d",
        open_=1.2500,
        high=1.2400,
        low=1.2450,
        close=1.2480,
    )

    metrics = DataQualityEngine(db_session).calculate("GBPUSD", "1d", "mock")
    assert metrics.bad_price_bars == 1


def test_fx_zero_or_negative_price_still_bad(db_session: Session) -> None:
    asset = _seed_asset(db_session, "USDJPY", asset_class=AssetClass.FX)
    ts = datetime(2026, 1, 7, 0, 0, tzinfo=UTC)
    _seed_bar(
        db_session,
        asset.id,
        ts,
        timeframe="1d",
        open_=0.0,
        high=130.0,
        low=129.0,
        close=129.5,
    )

    metrics = DataQualityEngine(db_session).calculate("USDJPY", "1d", "mock")
    assert metrics.bad_price_bars == 1


def test_crypto_bad_candle_still_bad(db_session: Session) -> None:
    asset = _seed_asset(db_session, "BTC-USD", asset_class=AssetClass.CRYPTO)
    ts = datetime(2026, 1, 8, 0, 0, tzinfo=UTC)
    _seed_bar(
        db_session,
        asset.id,
        ts,
        timeframe="1d",
        open_=42000.0,
        high=41900.0,
        low=42100.0,
        close=42050.0,
    )

    metrics = DataQualityEngine(db_session).calculate("BTC-USD", "1d", "mock")
    assert metrics.bad_price_bars == 1
