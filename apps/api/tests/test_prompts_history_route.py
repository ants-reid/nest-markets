"""QA-110: GET /prompts/{subdir}/{filename}/history endpoint tests."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.db.enums import PromptRole
from app.db.models.prompt_version import PromptVersion
from app.db.session import get_db_session
from app.main import app


def _make_version(**kwargs) -> PromptVersion:
    defaults = dict(
        id=uuid.uuid4(),
        name="signal_engine_v1.md",
        role=PromptRole.SIGNAL_ENGINE,
        version="v1",
        is_active=True,
        schema_json={"hash": "abc123"},
        created_at=datetime.now(timezone.utc),
    )
    defaults.update(kwargs)
    obj = MagicMock(spec=PromptVersion)
    for k, v in defaults.items():
        setattr(obj, k, v)
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


def test_history_returns_versions(client):
    c, session = client
    pv = _make_version()
    session.execute.return_value.scalars.return_value.all.return_value = [pv]
    resp = c.get("/prompts/system/signal_engine_v1.md/history")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["version"] == "v1"
    assert data[0]["file_hash"] == "abc123"


def test_history_404_no_rows(client):
    c, session = client
    session.execute.return_value.scalars.return_value.all.return_value = []
    resp = c.get("/prompts/system/signal_engine_v1.md/history")
    assert resp.status_code == 404


def test_history_404_unknown_role(client):
    c, session = client
    resp = c.get("/prompts/system/unknown_file_v1.md/history")
    assert resp.status_code == 404


def test_history_404_bad_subdir(client):
    c, session = client
    resp = c.get("/prompts/bad_subdir/signal_engine_v1.md/history")
    assert resp.status_code == 404
