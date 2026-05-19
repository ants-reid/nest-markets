"""Tests for GET/POST/DELETE /assets — QA-201."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.db.enums import AssetClass
from app.db.models.asset import Asset
from app.db.session import get_db_session
from app.main import app


def _make_asset(**kwargs) -> MagicMock:
    defaults = dict(
        id=uuid.uuid4(),
        symbol="EURUSD",
        name="Euro / US Dollar",
        asset_class=AssetClass.FX,
        base_currency="EUR",
        quote_currency="USD",
        exchange=None,
        sector=None,
        industry=None,
        is_active=True,
    )
    defaults.update(kwargs)
    obj = MagicMock(spec=Asset)
    for key, value in defaults.items():
        setattr(obj, key, value)
    # Support model_validate
    obj.model_dump = lambda: defaults
    return obj


@pytest.fixture()
def client():
    mock_session = MagicMock()
    app.dependency_overrides[get_db_session] = lambda: (yield mock_session)
    try:
        with TestClient(app) as c:
            yield c, mock_session
    finally:
        app.dependency_overrides.pop(get_db_session, None)


# ---------------------------------------------------------------------------
# GET /assets
# ---------------------------------------------------------------------------


def test_list_assets_returns_items(client):
    c, session = client
    rows = [
        _make_asset(symbol="EURUSD", asset_class=AssetClass.FX),
        _make_asset(symbol="AAPL", asset_class=AssetClass.EQUITY),
    ]
    mock_query = MagicMock()
    mock_query.filter.return_value = mock_query
    mock_query.filter.return_value.filter.return_value = mock_query
    mock_query.order_by.return_value.all.return_value = rows
    session.query.return_value = mock_query

    resp = c.get("/assets")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


def test_list_assets_empty(client):
    c, session = client
    mock_query = MagicMock()
    mock_query.filter.return_value = mock_query
    mock_query.order_by.return_value.all.return_value = []
    session.query.return_value = mock_query

    resp = c.get("/assets")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


# ---------------------------------------------------------------------------
# POST /assets
# ---------------------------------------------------------------------------


def test_create_asset_returns_201(client):
    c, session = client
    # No existing asset
    session.query.return_value.filter_by.return_value.first.return_value = None

    new_asset = _make_asset(symbol="GBPUSD", asset_class=AssetClass.FX)
    session.refresh.side_effect = lambda obj: None
    # simulate ORM object returned after commit
    session.add.return_value = None

    # patch session.refresh to set attributes on the added object
    def _refresh(obj):
        obj.id = new_asset.id
        obj.symbol = "GBPUSD"
        obj.name = "British Pound"
        obj.asset_class = AssetClass.FX
        obj.base_currency = "GBP"
        obj.quote_currency = "USD"
        obj.exchange = None
        obj.sector = None
        obj.industry = None
        obj.is_active = True

    session.refresh.side_effect = _refresh

    resp = c.post(
        "/assets",
        json={
            "symbol": "GBPUSD",
            "name": "British Pound",
            "asset_class": "fx",
            "base_currency": "GBP",
            "quote_currency": "USD",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["symbol"] == "GBPUSD"


def test_create_asset_409_when_duplicate(client):
    c, session = client
    session.query.return_value.filter_by.return_value.first.return_value = _make_asset(symbol="EURUSD")

    resp = c.post(
        "/assets",
        json={"symbol": "EURUSD", "asset_class": "fx"},
    )
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# DELETE /assets/{id}
# ---------------------------------------------------------------------------


def test_deactivate_asset_returns_204(client):
    c, session = client
    asset_id = uuid.uuid4()
    asset = _make_asset(id=asset_id, is_active=True)
    session.get.return_value = asset

    resp = c.delete(f"/assets/{asset_id}")
    assert resp.status_code == 204
    assert asset.is_active is False


def test_deactivate_asset_404_when_not_found(client):
    c, session = client
    session.get.return_value = None

    resp = c.delete(f"/assets/{uuid.uuid4()}")
    assert resp.status_code == 404
