"""Tests for MH-15 baseline candidate routes."""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.api.routes import baseline_candidates as baseline_routes
from app.main import app
from app.schemas.strategy_lab import BaselineCandidateResponse
from app.services.baseline_candidate_service import BaselineCandidateError


def _candidate_response(
    *,
    candidate_id: uuid.UUID | None = None,
    status: str = "watchlist_candidate",
) -> BaselineCandidateResponse:
    now = datetime.now(timezone.utc)
    return BaselineCandidateResponse(
        id=candidate_id or uuid.uuid4(),
        backtest_run_id=uuid.uuid4(),
        strategy_config_id=uuid.uuid4(),
        ai_backtest_report_id=None,
        asset="AAPL",
        timeframe="1d",
        strategy_type="ma_momentum",
        parameters={"fast_window": 5, "slow_window": 20},
        metrics={"total_trades": 42, "score": 61.2},
        status=status,
        review_notes="note",
        created_by="tester",
        reviewed_by=None,
        reviewed_at=None,
        created_at=now,
        updated_at=now,
    )


@contextmanager
def _client_with_service(mock_service: MagicMock):
    app.dependency_overrides[baseline_routes._svc] = lambda: mock_service
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(baseline_routes._svc, None)


def test_create_candidate_returns_201():
    candidate = _candidate_response(status="watchlist_candidate")
    mock_service = MagicMock()
    mock_service.create_candidate.return_value = candidate

    with _client_with_service(mock_service) as client:
        response = client.post(
            "/baseline-candidates",
            json={
                "backtest_run_id": str(candidate.backtest_run_id),
                "strategy_config_id": str(candidate.strategy_config_id),
                "status": "watchlist_candidate",
            },
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "watchlist_candidate"
    assert payload["asset"] == "AAPL"


def test_create_candidate_duplicate_returns_400():
    mock_service = MagicMock()
    mock_service.create_candidate.side_effect = BaselineCandidateError("Active baseline candidate already exists")

    with _client_with_service(mock_service) as client:
        response = client.post(
            "/baseline-candidates",
            json={
                "backtest_run_id": str(uuid.uuid4()),
                "strategy_config_id": str(uuid.uuid4()),
                "status": "watchlist_candidate",
            },
        )

    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_list_candidates_returns_items():
    item_one = _candidate_response(status="watchlist_candidate")
    item_two = _candidate_response(status="needs_more_testing")

    mock_service = MagicMock()
    mock_service.list_candidates.return_value = {
        "total": 2,
        "items": [item_one.model_dump(mode="json"), item_two.model_dump(mode="json")],
    }

    with _client_with_service(mock_service) as client:
        response = client.get("/baseline-candidates")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert len(payload["items"]) == 2


def test_get_candidate_404_when_missing():
    mock_service = MagicMock()
    mock_service.get_candidate.return_value = None

    with _client_with_service(mock_service) as client:
        response = client.get(f"/baseline-candidates/{uuid.uuid4()}")

    assert response.status_code == 404


def test_patch_candidate_updates_status_and_notes():
    candidate = _candidate_response(status="baseline_candidate")
    mock_service = MagicMock()
    mock_service.update_candidate.return_value = candidate

    with _client_with_service(mock_service) as client:
        response = client.patch(
            f"/baseline-candidates/{candidate.id}",
            json={"status": "baseline_candidate", "review_notes": "promising"},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "baseline_candidate"


def test_reject_candidate_endpoint_marks_rejected():
    candidate = _candidate_response(status="rejected")
    mock_service = MagicMock()
    mock_service.reject_candidate.return_value = candidate

    with _client_with_service(mock_service) as client:
        response = client.post(
            f"/baseline-candidates/{candidate.id}/reject",
            json={"reviewed_by": "qa", "review_notes": "insufficient sample"},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
