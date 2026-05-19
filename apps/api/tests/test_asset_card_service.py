"""MH-COCKPIT-02-A — Tests for asset_card_service."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.db.enums import AssetClass
from app.db.models.asset import Asset
from app.db.models.bar import Bar
from app.db.session import SessionLocal
from app.services.asset_card_service import get_asset_card_snapshot


_TEST_PREFIX = "TEST_COCKPIT02_"


def _cleanup(session) -> None:
    rows = session.query(Asset).filter(Asset.symbol.like(f"{_TEST_PREFIX}%")).all()
    for row in rows:
        session.query(Bar).filter(Bar.asset_id == row.id).delete(
            synchronize_session=False
        )
        session.delete(row)
    session.commit()


@pytest.fixture(autouse=True)
def _isolate_test_assets():
    s = SessionLocal()
    try:
        _cleanup(s)
    finally:
        s.close()
    yield
    s = SessionLocal()
    try:
        _cleanup(s)
    finally:
        s.close()


def _make_asset(session, *, symbol_suffix: str, **overrides) -> Asset:
    defaults = dict(
        symbol=f"{_TEST_PREFIX}{symbol_suffix}",
        name=f"Test {symbol_suffix}",
        asset_class=AssetClass.FX,
        is_active=True,
    )
    defaults.update(overrides)
    asset = Asset(**defaults)
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset


def _make_bar(session, *, asset, ts, close=1.0, volume=1000.0, timeframe="1m") -> Bar:
    bar = Bar(
        asset_id=asset.id,
        timeframe=timeframe,
        ts=ts,
        open=Decimal(str(close)),
        high=Decimal(str(close)),
        low=Decimal(str(close)),
        close=Decimal(str(close)),
        volume=Decimal(str(volume)),
        source="test",
    )
    session.add(bar)
    session.commit()
    return bar


def test_no_data_quality_when_asset_has_no_bars():
    s = SessionLocal()
    try:
        asset = _make_asset(s, symbol_suffix="NODATA")
        snap = get_asset_card_snapshot(s, limit=200)
    finally:
        s.close()

    card = next(c for c in snap["items"] if c["symbol"] == asset.symbol)
    assert card["market_quality"]["quality"] == "no_data"
    assert card["market_quality"]["last_close"] is None
    assert card["market_quality"]["bar_count"] == 0


def test_fresh_quality_when_recent_bars_present():
    now = datetime.now(timezone.utc)
    s = SessionLocal()
    try:
        asset = _make_asset(s, symbol_suffix="FRESH")
        for i in range(5):
            _make_bar(
                s,
                asset=asset,
                ts=now - timedelta(minutes=i),
                close=1.0 + 0.001 * i,
                volume=1000.0,
            )
        snap = get_asset_card_snapshot(s, limit=200, now_utc=now)
    finally:
        s.close()

    card = next(c for c in snap["items"] if c["symbol"] == asset.symbol)
    mq = card["market_quality"]
    assert mq["quality"] == "fresh"
    assert mq["bar_count"] == 5
    assert mq["last_close"] is not None
    assert mq["recent_avg_volume"] == 1000.0
    assert mq["recent_volatility"] is not None
    assert mq["bars_age_seconds"] is not None
    assert mq["bars_age_seconds"] < 60


def test_stale_quality_when_bars_are_hours_old():
    now = datetime.now(timezone.utc)
    s = SessionLocal()
    try:
        asset = _make_asset(s, symbol_suffix="STALE")
        _make_bar(s, asset=asset, ts=now - timedelta(hours=5), close=1.0)
        snap = get_asset_card_snapshot(s, limit=200, now_utc=now)
    finally:
        s.close()

    card = next(c for c in snap["items"] if c["symbol"] == asset.symbol)
    assert card["market_quality"]["quality"] == "stale"


def test_very_stale_quality_when_bars_are_days_old():
    now = datetime.now(timezone.utc)
    s = SessionLocal()
    try:
        asset = _make_asset(s, symbol_suffix="VERYSTALE")
        _make_bar(s, asset=asset, ts=now - timedelta(days=5), close=1.0)
        snap = get_asset_card_snapshot(s, limit=200, now_utc=now)
    finally:
        s.close()

    card = next(c for c in snap["items"] if c["symbol"] == asset.symbol)
    assert card["market_quality"]["quality"] == "very_stale"


def test_filter_by_asset_class():
    s = SessionLocal()
    try:
        _make_asset(s, symbol_suffix="FX1", asset_class=AssetClass.FX)
        _make_asset(s, symbol_suffix="EQ1", asset_class=AssetClass.EQUITY)
        snap = get_asset_card_snapshot(s, asset_class=AssetClass.EQUITY, limit=200)
    finally:
        s.close()

    test_symbols = [c["symbol"] for c in snap["items"] if c["symbol"].startswith(_TEST_PREFIX)]
    assert f"{_TEST_PREFIX}EQ1" in test_symbols
    assert f"{_TEST_PREFIX}FX1" not in test_symbols


def test_inactive_excluded_by_default():
    s = SessionLocal()
    try:
        _make_asset(s, symbol_suffix="INACTIVE", is_active=False)
        snap = get_asset_card_snapshot(s, limit=200)
        symbols = [c["symbol"] for c in snap["items"]]
        assert f"{_TEST_PREFIX}INACTIVE" not in symbols

        snap_all = get_asset_card_snapshot(s, limit=200, active_only=False)
        symbols_all = [c["symbol"] for c in snap_all["items"]]
        assert f"{_TEST_PREFIX}INACTIVE" in symbols_all
    finally:
        s.close()


def test_advisory_present_in_response():
    s = SessionLocal()
    try:
        snap = get_asset_card_snapshot(s, limit=10)
    finally:
        s.close()
    assert "advisory" in snap
    assert "operator hint" in snap["advisory"].lower()


def test_limit_clamped_to_max():
    s = SessionLocal()
    try:
        snap = get_asset_card_snapshot(s, limit=10_000)
    finally:
        s.close()
    assert snap["limit"] == 200
