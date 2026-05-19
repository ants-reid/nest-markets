"""QA-104 — FeatureSnapshot persistence tests."""

from __future__ import annotations

from datetime import datetime, UTC
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.db.enums import RegimeType
from app.db.models.feature_snapshot import FeatureSnapshot
from app.services.feature_service import FeatureSnapshotPayload
from app.services.persistence_signal_service import PersistenceSignalService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_session() -> MagicMock:
    session = MagicMock(spec=Session)

    def _refresh(obj):
        if getattr(obj, "id", None) is None:
            obj.id = uuid4()

    session.refresh.side_effect = _refresh
    return session


def _make_payload(**overrides) -> FeatureSnapshotPayload:
    defaults = dict(
        ema_fast=1.0820,
        ema_slow=1.0750,
        rsi=58.4,
        atr=0.0012,
        adx=28.5,
        volatility_score=55.0,
        liquidity_score=75.0,
        trend_score=62.0,
        momentum_score=48.0,
        regime_preclassification="trend",
        market_quality_flag=True,
    )
    defaults.update(overrides)
    return FeatureSnapshotPayload(**defaults)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPersistFeatureSnapshot:
    """QA-104 — persist_feature_snapshot method on PersistenceSignalService."""

    def test_creates_feature_snapshot_row(self):
        session = _make_session()
        service = PersistenceSignalService(session)
        payload = _make_payload()
        asset_id = uuid4()

        row = service.persist_feature_snapshot(
            payload,
            asset_id=asset_id,
            timeframe="1h",
        )

        session.add.assert_called_once()
        assert row.asset_id == asset_id
        assert row.timeframe == "1h"

    def test_maps_scores_from_payload(self):
        session = _make_session()
        service = PersistenceSignalService(session)
        payload = _make_payload(trend_score=72.0, momentum_score=55.0, volatility_score=40.0)
        row = service.persist_feature_snapshot(payload, asset_id=uuid4(), timeframe="4h")

        assert row.trend_score == pytest.approx(72.0)
        assert row.momentum_score == pytest.approx(55.0)
        assert row.volatility_score == pytest.approx(40.0)

    def test_maps_regime_from_payload(self):
        session = _make_session()
        service = PersistenceSignalService(session)
        payload = _make_payload(regime_preclassification="trend")
        row = service.persist_feature_snapshot(payload, asset_id=uuid4(), timeframe="1h")

        assert row.regime == RegimeType.TREND

    def test_stores_signal_id_when_provided(self):
        session = _make_session()
        service = PersistenceSignalService(session)
        payload = _make_payload()
        signal_id = uuid4()

        row = service.persist_feature_snapshot(
            payload,
            asset_id=uuid4(),
            timeframe="1h",
            signal_id=signal_id,
        )

        assert row.signal_id == signal_id

    def test_signal_id_is_none_by_default(self):
        session = _make_session()
        service = PersistenceSignalService(session)
        payload = _make_payload()
        row = service.persist_feature_snapshot(payload, asset_id=uuid4(), timeframe="1h")

        assert row.signal_id is None

    def test_market_quality_flag_true_stores_good(self):
        session = _make_session()
        service = PersistenceSignalService(session)
        row = service.persist_feature_snapshot(
            _make_payload(market_quality_flag=True),
            asset_id=uuid4(),
            timeframe="1h",
        )
        assert row.market_quality_flag == "good"

    def test_market_quality_flag_false_stores_poor(self):
        session = _make_session()
        service = PersistenceSignalService(session)
        row = service.persist_feature_snapshot(
            _make_payload(market_quality_flag=False),
            asset_id=uuid4(),
            timeframe="1h",
        )
        assert row.market_quality_flag == "poor"

    def test_uses_provided_scan_ts(self):
        session = _make_session()
        service = PersistenceSignalService(session)
        ts = datetime(2026, 6, 1, 9, 0, 0, tzinfo=UTC)
        row = service.persist_feature_snapshot(
            _make_payload(),
            asset_id=uuid4(),
            timeframe="15m",
            scan_ts=ts,
        )
        assert row.scan_ts == ts


class TestSignalFeaturesEndpoint:
    """QA-104 — GET /signals/{signal_id}/features endpoint unit test."""

    def test_endpoint_returns_404_when_no_snapshot(self):
        from unittest.mock import MagicMock
        from fastapi.testclient import TestClient
        from app.main import app
        from app.db.session import get_db_session

        mock_session = MagicMock(spec=Session)
        mock_session.execute.return_value.scalar_one_or_none.return_value = None

        def _override():
            yield mock_session

        app.dependency_overrides[get_db_session] = _override
        try:
            client = TestClient(app, raise_server_exceptions=True)
            signal_id = uuid4()
            response = client.get(f"/signals/{signal_id}/features")
        finally:
            app.dependency_overrides.pop(get_db_session, None)

        assert response.status_code == 404
        assert "feature snapshot" in response.json()["detail"].lower()

    def test_endpoint_returns_snapshot_when_found(self):
        from unittest.mock import MagicMock
        from fastapi.testclient import TestClient
        from app.main import app
        from app.db.session import get_db_session

        signal_id = uuid4()
        asset_id = uuid4()
        snapshot_id = uuid4()

        row = MagicMock(spec=FeatureSnapshot)
        row.id = snapshot_id
        row.asset_id = asset_id
        row.signal_id = signal_id
        row.scan_ts = datetime.now(UTC)
        row.timeframe = "1h"
        row.trend_score = 65.0
        row.momentum_score = 50.0
        row.volatility_score = 40.0
        row.liquidity_score = 75.0
        row.regime = RegimeType.TREND
        row.atr = 0.0012
        row.rsi = 58.4
        row.ema_fast = 1.0820
        row.ema_slow = 1.0750
        row.adx = 28.5
        row.market_quality_flag = "good"

        mock_session = MagicMock(spec=Session)
        mock_session.execute.return_value.scalar_one_or_none.return_value = row

        def _override():
            yield mock_session

        app.dependency_overrides[get_db_session] = _override
        try:
            client = TestClient(app, raise_server_exceptions=True)
            response = client.get(f"/signals/{signal_id}/features")
        finally:
            app.dependency_overrides.pop(get_db_session, None)

        assert response.status_code == 200
        data = response.json()
        assert data["signal_id"] == str(signal_id)
        assert data["timeframe"] == "1h"
        assert data["trend_score"] == pytest.approx(65.0)
        assert data["regime"] == "trend"
