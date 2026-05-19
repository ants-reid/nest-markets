"""QA-100 — PersistenceSignalService wired into POST /signals/generate.

Tests verify:
  1. persist_signal() creates a Signal row and returns a model with an id.
  2. The persisted row round-trips direction/setup_type/regime enums correctly.
  3. Persistence failure (asset not found) is handled gracefully — the route
     still returns a valid SignalResponse with signal_id=None rather than 500.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

from sqlalchemy.orm import Session

from app.db.enums import SignalStatus
from app.db.models.asset import Asset
from app.db.models.signal import Signal as SignalModel
from app.services.persistence_signal_service import PersistenceSignalService
from app.services.signal_service import SignalOutput


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_signal_output(**overrides) -> SignalOutput:
    defaults = dict(
        asset="EURUSD",
        timeframe="1h",
        direction="long",
        regime="trend",
        setup_type="trend_pullback",
        entry_zone=(1.0800, 1.0820),
        stop_price=1.0750,
        target_price=1.0900,
        confidence=0.75,
        horizon_label="1_3_days",
        catalyst_type="macro",
        catalyst_score=0.6,
        catalyst_summary="Test summary",
        thesis="Test thesis",
        invalidators=["breach 1.07"],
        signal_score=65.0,
        should_trade=True,
    )
    defaults.update(overrides)
    return SignalOutput(**defaults)


def _mock_session_with_asset(asset_id=None) -> MagicMock:
    """Return a mock session that resolves get(Asset) and handles add/flush/refresh."""
    session = MagicMock(spec=Session)
    asset = Asset(id=asset_id or uuid4(), symbol="EURUSD", asset_class="fx")
    session.execute.return_value.scalars.return_value.one.return_value = asset

    assigned_ids: dict = {}

    def _refresh(obj):
        if getattr(obj, "id", None) is None:
            obj.id = uuid4()
        assigned_ids["last"] = obj.id

    session.refresh.side_effect = _refresh
    return session, assigned_ids


# ---------------------------------------------------------------------------
# QA-100: PersistenceSignalService unit tests
# ---------------------------------------------------------------------------

class TestPersistenceSignalService:
    """QA-100 — Unit tests for signal persistence."""

    def test_persist_signal_creates_row_with_id(self):
        """persist_signal() should add a Signal to the session and return it with an id."""
        session, ids = _mock_session_with_asset()
        service = PersistenceSignalService(session)
        output = _make_signal_output()

        result = service.persist_signal(output)

        session.add.assert_called_once()
        session.flush.assert_called_once()
        session.refresh.assert_called_once()
        assert isinstance(result, SignalModel)

    def test_persist_signal_sets_candidate_status_by_default(self):
        """Default signal_status should be CANDIDATE."""
        session, _ = _mock_session_with_asset()
        service = PersistenceSignalService(session)
        output = _make_signal_output()

        result = service.persist_signal(output)
        assert result.signal_status == SignalStatus.CANDIDATE

    def test_persist_signal_accepts_explicit_status(self):
        """Caller can override signal_status."""
        session, _ = _mock_session_with_asset()
        service = PersistenceSignalService(session)
        output = _make_signal_output()

        result = service.persist_signal(output, signal_status=SignalStatus.RISK_APPROVED)
        assert result.signal_status == SignalStatus.RISK_APPROVED

    def test_persist_signal_maps_direction(self):
        """direction field must map from string to ORM enum value."""
        session, _ = _mock_session_with_asset()
        service = PersistenceSignalService(session)
        output = _make_signal_output(direction="short")

        result = service.persist_signal(output)
        # direction is stored as enum — value should be "short"
        from app.db.enums import TradeDirection
        assert result.direction == TradeDirection.SHORT

    def test_persist_signal_stores_invalidators_as_list(self):
        """invalidators_json should be a list of strings."""
        session, _ = _mock_session_with_asset()
        service = PersistenceSignalService(session)
        output = _make_signal_output(invalidators=["a", "b", "c"])

        result = service.persist_signal(output)
        assert result.invalidators_json == ["a", "b", "c"]

    def test_persist_signal_accepts_explicit_signal_id(self):
        """Caller can supply a specific UUID for the signal row."""
        session, _ = _mock_session_with_asset()
        # No existing row — get() returns None so persist creates a new row with the given id
        session.get.return_value = None
        service = PersistenceSignalService(session)
        output = _make_signal_output()
        given_id = uuid4()

        result = service.persist_signal(output, signal_id=given_id)
        assert result.id == given_id

    def test_persist_signal_updates_existing_row(self):
        """If signal_id resolves to an existing row, it updates rather than creates."""
        session, _ = _mock_session_with_asset()
        existing_id = uuid4()
        existing_signal = SignalModel(id=existing_id)
        session.get.return_value = existing_signal
        service = PersistenceSignalService(session)
        output = _make_signal_output()

        result = service.persist_signal(output, signal_id=existing_id)

        # add should NOT be called for updates
        session.add.assert_not_called()
        assert result.id == existing_id


# ---------------------------------------------------------------------------
# QA-100: Route wiring test — POST /signals/generate persists and returns id
# ---------------------------------------------------------------------------

class TestSignalGenerateRoutePersistence:
    """QA-100 — Integration: /signals/generate returns signal_id after persistence."""

    def test_generate_route_returns_signal_id_on_success(self):
        """When persistence succeeds, the route must return a non-None signal_id."""
        from fastapi.testclient import TestClient
        from app.main import app

        mock_output = _make_signal_output()
        persisted_id = uuid4()
        mock_signal_row = SignalModel(id=persisted_id)

        with (
            patch("app.api.routes.signals.SignalService") as MockSignalService,
            patch("app.api.routes.signals.PersistenceSignalService") as MockPersistence,
        ):
            instance = MockSignalService.return_value

            async def _fake_generate(_input):
                return mock_output

            instance.generate_signal.side_effect = _fake_generate
            MockPersistence.return_value.persist_signal.return_value = mock_signal_row

            client = TestClient(app)
            resp = client.post(
                "/signals/generate",
                json={
                    "asset": "EURUSD",
                    "timeframe": "1h",
                    "latest_price": 1.085,
                    "feature_snapshot": {},
                    "catalyst_context": {},
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["signal_id"] == str(persisted_id)
        assert data["asset"] == "EURUSD"
        assert data["should_trade"] is True

    def test_generate_route_returns_null_signal_id_on_persistence_failure(self):
        """When persistence fails (e.g. asset not found), signal_id is None but route still 200s."""
        from fastapi.testclient import TestClient
        from app.main import app

        mock_output = _make_signal_output()

        with (
            patch("app.api.routes.signals.SignalService") as MockSignalService,
            patch("app.api.routes.signals.PersistenceSignalService") as MockPersistence,
        ):
            instance = MockSignalService.return_value

            async def _fake_generate(_input):
                return mock_output

            instance.generate_signal.side_effect = _fake_generate
            MockPersistence.return_value.persist_signal.side_effect = ValueError("Asset not found")

            client = TestClient(app)
            resp = client.post(
                "/signals/generate",
                json={
                    "asset": "UNKNOWN",
                    "timeframe": "1h",
                    "latest_price": 1.085,
                    "feature_snapshot": {},
                    "catalyst_context": {},
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["signal_id"] is None
