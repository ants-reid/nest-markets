"""Tests for scoring, models, governance, and regime routes — QA-305 through QA-325."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.db.models.model_version import ModelVersion
from app.db.session import get_db_session
from app.main import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_version(**kwargs) -> MagicMock:
    defaults = dict(
        id=uuid.uuid4(),
        provider_name="openai",
        provider="openai",
        model_name="gpt-4o",
        alias_name=None,
        temperature=0.7,
        top_p=None,
        max_output_tokens=None,
        reasoning_level=None,
        supports_structured_output=True,
        is_active=False,
        notes=None,
        created_at=datetime(2026, 4, 25, tzinfo=UTC),
    )
    defaults.update(kwargs)
    obj = MagicMock(spec=ModelVersion)
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


@pytest.fixture()
def client():
    mock_db = MagicMock()
    app.dependency_overrides[get_db_session] = lambda: (yield mock_db)
    try:
        with TestClient(app) as c:
            yield c, mock_db
    finally:
        app.dependency_overrides.pop(get_db_session, None)


# ---------------------------------------------------------------------------
# GET /scoring/active
# ---------------------------------------------------------------------------


def test_get_active_weights_returns_default(client) -> None:
    c, _ = client
    resp = c.get("/scoring/active")
    assert resp.status_code == 200
    data = resp.json()
    assert "weights" in data
    w = data["weights"]
    assert abs(w["signal_score"] - 0.40) < 1e-6
    assert abs(w["confidence"] - 0.30) < 1e-6
    assert abs(w["catalyst_score"] - 0.10) < 1e-6
    assert abs(w["historical_win_rate"] - 0.20) < 1e-6


# ---------------------------------------------------------------------------
# GET /scoring/explain/{signal_id}
# ---------------------------------------------------------------------------


def test_explain_score_returns_breakdown(client) -> None:
    c, mock_db = client
    signal_id = uuid.uuid4()
    mock_signal = MagicMock()
    mock_signal.signal_score = 80.0
    mock_signal.confidence = 0.8
    mock_signal.catalyst_score = 0.7
    mock_db.get.return_value = mock_signal

    resp = c.get(f"/scoring/explain/{signal_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["signal_id"] == str(signal_id)
    assert "composite_score" in data
    assert "contributions" in data
    assert "weights" in data


def test_explain_score_returns_404_on_missing_signal(client) -> None:
    c, mock_db = client
    mock_db.get.return_value = None
    resp = c.get(f"/scoring/explain/{uuid.uuid4()}")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /models
# ---------------------------------------------------------------------------


def test_list_models_returns_empty(client) -> None:
    c, mock_db = client
    mock_db.execute.return_value.scalars.return_value.all.return_value = []
    resp = c.get("/models")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


def test_list_models_returns_items(client) -> None:
    c, mock_db = client
    v1 = _make_version(is_active=True)
    v2 = _make_version(is_active=False)
    mock_db.execute.return_value.scalars.return_value.all.return_value = [v1, v2]
    resp = c.get("/models")
    assert resp.status_code == 200
    assert resp.json()["total"] == 2


# ---------------------------------------------------------------------------
# GET /models/active
# ---------------------------------------------------------------------------


def test_get_active_model_returns_active(client) -> None:
    c, mock_db = client
    active = _make_version(is_active=True)
    mock_db.execute.return_value.scalars.return_value.first.return_value = active
    resp = c.get("/models/active")
    assert resp.status_code == 200
    assert resp.json()["is_active"] is True


def test_get_active_model_404_when_none(client) -> None:
    c, mock_db = client
    mock_db.execute.return_value.scalars.return_value.first.return_value = None
    resp = c.get("/models/active")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /models/{id}
# ---------------------------------------------------------------------------


def test_get_model_by_id(client) -> None:
    c, mock_db = client
    vid = uuid.uuid4()
    version = _make_version(id=vid)
    mock_db.get.return_value = version
    resp = c.get(f"/models/{vid}")
    assert resp.status_code == 200
    assert resp.json()["id"] == str(vid)


def test_get_model_by_id_404_on_missing(client) -> None:
    c, mock_db = client
    mock_db.get.return_value = None
    resp = c.get(f"/models/{uuid.uuid4()}")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /models
# ---------------------------------------------------------------------------


def test_create_model_returns_201(client) -> None:
    c, mock_db = client
    new_version = _make_version(provider_name="openai", model_name="gpt-4o-mini")

    # Simulate flush + refresh setting id
    def fake_refresh(obj):
        obj.id = new_version.id
        obj.created_at = new_version.created_at
        obj.provider_name = new_version.provider_name
        obj.model_name = new_version.model_name
        obj.alias_name = new_version.alias_name
        obj.temperature = new_version.temperature
        obj.top_p = new_version.top_p
        obj.max_output_tokens = new_version.max_output_tokens
        obj.reasoning_level = new_version.reasoning_level
        obj.supports_structured_output = new_version.supports_structured_output
        obj.is_active = new_version.is_active
        obj.notes = new_version.notes

    mock_db.refresh.side_effect = fake_refresh

    resp = c.post("/models", json={"provider_name": "openai", "model_name": "gpt-4o-mini"})
    assert resp.status_code == 201
    assert resp.json()["model_name"] == "gpt-4o-mini"


# ---------------------------------------------------------------------------
# DELETE /models/{id}
# ---------------------------------------------------------------------------


def test_deactivate_model(client) -> None:
    c, mock_db = client
    vid = uuid.uuid4()
    version = _make_version(id=vid, is_active=True)
    mock_db.get.return_value = version
    mock_db.execute.return_value.scalars.return_value.all.return_value = [version]

    resp = c.delete(f"/models/{vid}")
    assert resp.status_code == 200
    assert resp.json()["action"] == "deactivate"
    assert version.is_active is False


def test_deactivate_model_404_on_missing(client) -> None:
    c, mock_db = client
    mock_db.get.return_value = None
    resp = c.delete(f"/models/{uuid.uuid4()}")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /governance/promote
# ---------------------------------------------------------------------------


def test_promote_model_success(client) -> None:
    c, mock_db = client
    vid = uuid.uuid4()
    candidate = _make_version(id=vid, is_active=False)
    mock_db.get.return_value = candidate
    mock_db.execute.return_value.scalars.return_value.first.return_value = None  # no current active

    resp = c.post("/governance/promote", json={"model_version_id": str(vid)})
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == "promote"
    assert data["is_active"] is True


def test_promote_model_404_on_missing(client) -> None:
    c, mock_db = client
    mock_db.get.return_value = None
    resp = c.post("/governance/promote", json={"model_version_id": str(uuid.uuid4())})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /governance/rollback
# ---------------------------------------------------------------------------


def test_rollback_fails_when_no_active(client) -> None:
    c, mock_db = client
    # No active version
    mock_db.execute.return_value.scalars.return_value.first.return_value = None
    resp = c.post("/governance/rollback")
    assert resp.status_code == 400
    assert "No active model version" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# GET /regime/current
# ---------------------------------------------------------------------------


def test_regime_current_returns_placeholder(client) -> None:
    c, _ = client
    resp = c.get("/regime/current")
    assert resp.status_code == 200
    data = resp.json()
    assert data["regime"] == "unknown"
    assert "asset" in data
    assert "confidence" in data


# ---------------------------------------------------------------------------
# GET /regime/history
# ---------------------------------------------------------------------------


def test_regime_history_returns_empty_list(client) -> None:
    c, _ = client
    resp = c.get("/regime/history")
    assert resp.status_code == 200
    assert resp.json()["items"] == []
