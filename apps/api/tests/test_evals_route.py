"""QA-111: /evals route tests."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.db.models.eval_case import EvalCase
from app.db.models.eval_run import EvalRun
from app.db.session import get_db_session
from app.main import app


def _make_run(**kwargs) -> EvalRun:
    defaults = dict(
        id=uuid.uuid4(),
        prompt_version_id=None,
        model_version_id=None,
        provider_name="openai",
        started_at=None,
        completed_at=None,
        summary_score=None,
        pass_rate=None,
        notes=None,
        created_at=datetime.now(timezone.utc),
    )
    defaults.update(kwargs)
    obj = MagicMock(spec=EvalRun)
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _make_case(**kwargs) -> EvalCase:
    defaults = dict(
        id=uuid.uuid4(),
        name="case-1",
        category="signal",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    defaults.update(kwargs)
    obj = MagicMock(spec=EvalCase)
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


# ---------------------------------------------------------------------------
# GET /evals/runs
# ---------------------------------------------------------------------------


def test_list_eval_runs_returns_empty_list(client):
    c, session = client
    session.execute.return_value.scalars.return_value.all.return_value = []
    resp = c.get("/evals/runs")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_eval_runs_returns_runs(client):
    c, session = client
    run = _make_run()
    session.execute.return_value.scalars.return_value.all.return_value = [run]
    resp = c.get("/evals/runs")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["provider_name"] == "openai"


# ---------------------------------------------------------------------------
# GET /evals/runs/{run_id}
# ---------------------------------------------------------------------------


def test_get_eval_run_not_found(client):
    c, session = client
    session.get.return_value = None
    uid = str(uuid.uuid4())
    resp = c.get(f"/evals/runs/{uid}")
    assert resp.status_code == 404


def test_get_eval_run_invalid_uuid(client):
    c, session = client
    resp = c.get("/evals/runs/not-a-uuid")
    assert resp.status_code == 422


def test_get_eval_run_returns_detail(client):
    c, session = client
    run = _make_run()
    case = _make_case()
    session.get.return_value = run
    session.execute.return_value.scalars.return_value.all.return_value = [case]
    resp = c.get(f"/evals/runs/{run.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert "run" in data
    assert "cases" in data
    assert data["run"]["provider_name"] == "openai"
    assert len(data["cases"]) == 1
