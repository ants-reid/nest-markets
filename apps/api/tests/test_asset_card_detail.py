"""Tests for MH-COCKPIT-11-A asset-card detail endpoint + service."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.db.enums import AssetClass
from app.db.models.asset import Asset
from app.db.models.bar import Bar
from app.db.session import SessionLocal
from app.main import app
from app.services.asset_card_service import (
    AssetCardNotFoundError,
    get_asset_card_detail,
)


@pytest.fixture()
def asset_with_bars():
    session = SessionLocal()
    asset = Asset(
        symbol=f"TST{uuid.uuid4().hex[:6].upper()}",
        name="Test Asset",
        asset_class=AssetClass.EQUITY,
        exchange="TEST",
        is_active=True,
    )
    session.add(asset)
    session.flush()
    now = datetime.now(timezone.utc)
    for i in range(5):
        session.add(
            Bar(
                asset_id=asset.id,
                timeframe="1d",
                ts=now - timedelta(days=i),
                open=100 + i,
                high=101 + i,
                low=99 + i,
                close=100.5 + i,
                volume=1000 + i,
                source="test",
            )
        )
    session.commit()
    asset_id = asset.id
    session.close()
    yield asset_id
    cleanup = SessionLocal()
    cleanup.query(Bar).filter(Bar.asset_id == asset_id).delete()
    cleanup.query(Asset).filter(Asset.id == asset_id).delete()
    cleanup.commit()
    cleanup.close()


def test_detail_returns_card_with_recent_bars(asset_with_bars):
    session = SessionLocal()
    try:
        result = get_asset_card_detail(session, asset_with_bars, recent_bars_limit=10)
    finally:
        session.close()
    assert result["asset"]["id"] == str(asset_with_bars)
    assert result["asset"]["asset_class"] == "equity"
    assert result["recent_bars_limit"] == 10
    assert len(result["recent_bars"]) == 5
    # newest-first
    ts_values = [b["ts"] for b in result["recent_bars"]]
    assert ts_values == sorted(ts_values, reverse=True)
    mq = result["market_quality"]
    assert mq["bar_count"] == 5
    assert mq["quality"] in {"fresh", "stale", "very_stale"}


def test_detail_raises_for_unknown_asset_id():
    session = SessionLocal()
    try:
        with pytest.raises(AssetCardNotFoundError):
            get_asset_card_detail(session, uuid.uuid4())
    finally:
        session.close()


def test_detail_route_404_for_unknown_id():
    client = TestClient(app)
    resp = client.get(f"/asset-cards/{uuid.uuid4()}")
    assert resp.status_code == 404


def test_detail_route_returns_payload(asset_with_bars):
    client = TestClient(app)
    resp = client.get(f"/asset-cards/{asset_with_bars}?recent_bars_limit=3")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    for key in ("as_of_utc", "advisory", "recent_bars_limit", "asset", "market_quality", "recent_bars"):
        assert key in body
    assert body["recent_bars_limit"] == 3
    assert len(body["recent_bars"]) == 3
    assert body["asset"]["id"] == str(asset_with_bars)


def test_detail_route_invalid_limit_rejected():
    client = TestClient(app)
    resp = client.get(f"/asset-cards/{uuid.uuid4()}?recent_bars_limit=0")
    assert resp.status_code == 422
