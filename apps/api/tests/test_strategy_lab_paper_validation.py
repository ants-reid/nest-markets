"""Tests for MH-16 paper validation gate service and route contracts."""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.api.routes import paper_validation as pv_routes
from app.db.models.baseline_candidate import BaselineCandidate
from app.db.models.paper_validation_plan import PaperValidationPlan
from app.main import app
from app.schemas.strategy_lab import (
    PaperValidationPlanActionRequest,
    PaperValidationPlanCreateRequest,
    PaperValidationPlanUpdateRequest,
)
from app.services.paper_validation_service import PaperValidationError, PaperValidationService


def _candidate() -> BaselineCandidate:
    c = BaselineCandidate(
        backtest_run_id=uuid.uuid4(),
        strategy_config_id=uuid.uuid4(),
        ai_backtest_report_id=None,
        asset="AAPL",
        timeframe="1d",
        strategy_type="ma_momentum",
        parameters={"fast_window": 5, "slow_window": 20},
        metrics={
            "total_trades": 122,
            "profit_factor": 1.72,
            "total_return_pct": 8.99,
            "max_drawdown_pct": 4.25,
        },
        status="baseline_candidate",
        review_notes=None,
        created_by="tester",
        reviewed_by=None,
        reviewed_at=None,
    )
    c.id = uuid.uuid4()
    c.created_at = datetime.now(timezone.utc)
    c.updated_at = datetime.now(timezone.utc)
    return c


def _plan(candidate: BaselineCandidate, status: str = "pending") -> PaperValidationPlan:
    p = PaperValidationPlan(
        baseline_candidate_id=candidate.id,
        backtest_run_id=candidate.backtest_run_id,
        strategy_config_id=candidate.strategy_config_id,
        status=status,
        required_trades=100,
        minimum_days=30,
        target_profit_factor=1.5,
        max_drawdown_pct=10.0,
        max_daily_loss_pct=2.0,
        starting_paper_capital=200000,
        backtest_metrics=dict(candidate.metrics or {}),
        paper_metrics=None,
        progress={},
        pass_fail_reasons=[],
        started_at=None,
        completed_at=None,
        created_by="tester",
        reviewed_by=None,
        review_notes=None,
    )
    p.id = uuid.uuid4()
    p.created_at = datetime.now(timezone.utc)
    p.updated_at = datetime.now(timezone.utc)
    return p


def _execute_first(value):
    result = MagicMock()
    scalars = MagicMock()
    scalars.first.return_value = value
    result.scalars.return_value = scalars
    return result


def _execute_all(values):
    result = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = values
    result.scalars.return_value = scalars
    return result


def test_create_plan_copies_candidate_metrics_into_backtest_metrics():
    candidate = _candidate()
    session = MagicMock()
    session.get.return_value = candidate
    session.execute.return_value = _execute_first(None)

    def _refresh(row):
        if getattr(row, "id", None) is None:
            row.id = uuid.uuid4()
        if getattr(row, "created_at", None) is None:
            row.created_at = datetime.now(timezone.utc)
        if getattr(row, "updated_at", None) is None:
            row.updated_at = datetime.now(timezone.utc)

    session.refresh.side_effect = _refresh

    service = PaperValidationService(session)
    response = service.create_plan(
        PaperValidationPlanCreateRequest(
            baseline_candidate_id=str(candidate.id),
            required_trades=120,
            minimum_days=40,
            created_by="qa",
        )
    )

    assert response.baseline_candidate_id == candidate.id
    assert response.required_trades == 120
    assert response.backtest_metrics is not None
    assert response.backtest_metrics.get("profit_factor") == 1.72


def test_list_and_get_plan_return_rows():
    candidate = _candidate()
    plan = _plan(candidate)

    session = MagicMock()
    session.execute.return_value = _execute_all([plan])
    session.get.return_value = plan

    service = PaperValidationService(session)
    listed = service.list_plans()
    got = service.get_plan(str(plan.id))

    assert listed.total == 1
    assert listed.items[0].id == plan.id
    assert got.id == plan.id


def test_start_and_stop_plan_transitions_are_controlled():
    candidate = _candidate()
    plan = _plan(candidate, status="pending")

    session = MagicMock()
    session.get.return_value = plan

    service = PaperValidationService(session)
    started = service.start_plan(str(plan.id), PaperValidationPlanActionRequest(reviewed_by="qa"))
    assert started.status in {"active", "passed", "failed"}

    # Ensure we can stop from active by forcing active state.
    plan.status = "active"
    stopped = service.stop_plan(str(plan.id), PaperValidationPlanActionRequest(reviewed_by="qa"))
    assert stopped.status == "stopped"


def test_recalculate_without_paper_metrics_is_safe_zero_state():
    candidate = _candidate()
    plan = _plan(candidate, status="pending")

    session = MagicMock()
    session.get.return_value = plan

    service = PaperValidationService(session)
    recalculated = service.recalculate_plan(str(plan.id))

    assert isinstance(recalculated.progress, dict)
    assert recalculated.progress.get("total_paper_trades") == 0
    assert recalculated.progress.get("progress_trades_pct") == 0.0


def test_manual_paper_metrics_update_is_supported():
    candidate = _candidate()
    plan = _plan(candidate, status="active")
    plan.started_at = datetime.now(timezone.utc)

    session = MagicMock()
    session.get.return_value = plan

    service = PaperValidationService(session)
    updated = service.update_plan(
        str(plan.id),
        PaperValidationPlanUpdateRequest(
            paper_metrics={
                "total_paper_trades": 120,
                "wins": 70,
                "losses": 50,
                "profit_factor": 1.8,
                "max_drawdown_pct": 6.0,
                "days_active": 40,
            }
        ),
    )

    assert updated.paper_metrics is not None
    assert updated.paper_metrics.get("total_paper_trades") == 120


def test_update_cannot_force_passed_or_failed_status():
    candidate = _candidate()
    plan = _plan(candidate, status="active")

    session = MagicMock()
    session.get.return_value = plan

    service = PaperValidationService(session)

    try:
        service.update_plan(
            str(plan.id),
            PaperValidationPlanUpdateRequest(status="passed"),
        )
        assert False, "Expected PaperValidationError"
    except PaperValidationError as exc:
        assert "deterministic-only" in str(exc)


@contextmanager
def _client_with_service(mock_service: MagicMock):
    app.dependency_overrides[pv_routes._svc] = lambda: mock_service
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(pv_routes._svc, None)


def test_routes_expose_create_list_start_stop_recalculate_events():
    candidate = _candidate()
    plan = _plan(candidate)
    payload = {
        "id": str(plan.id),
        "baseline_candidate_id": str(plan.baseline_candidate_id),
        "backtest_run_id": str(plan.backtest_run_id),
        "strategy_config_id": str(plan.strategy_config_id),
        "status": "pending",
        "required_trades": 100,
        "minimum_days": 30,
        "target_profit_factor": 1.5,
        "max_drawdown_pct": 10.0,
        "max_daily_loss_pct": 2.0,
        "starting_paper_capital": 200000,
        "backtest_metrics": {"profit_factor": 1.7},
        "paper_metrics": None,
        "progress": {"progress_trades_pct": 0.0},
        "pass_fail_reasons": [],
        "started_at": None,
        "completed_at": None,
        "created_by": "tester",
        "reviewed_by": None,
        "review_notes": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    mock_service = MagicMock()
    mock_service.create_plan.return_value = payload
    mock_service.list_plans.return_value = {"total": 1, "items": [payload]}
    mock_service.get_plan.return_value = payload
    mock_service.start_plan.return_value = payload
    mock_service.stop_plan.return_value = payload
    mock_service.recalculate_plan.return_value = payload
    mock_service.list_events.return_value = []

    with _client_with_service(mock_service) as client:
        create = client.post(
            "/paper-validation/plans",
            json={"baseline_candidate_id": str(candidate.id)},
        )
        listed = client.get("/paper-validation/plans")
        got = client.get(f"/paper-validation/plans/{plan.id}")
        started = client.post(f"/paper-validation/plans/{plan.id}/start", json={})
        stopped = client.post(f"/paper-validation/plans/{plan.id}/stop", json={})
        recalculated = client.post(f"/paper-validation/plans/{plan.id}/recalculate")
        events = client.get(f"/paper-validation/plans/{plan.id}/events")

    assert create.status_code == 201
    assert listed.status_code == 200
    assert got.status_code == 200
    assert started.status_code == 200
    assert stopped.status_code == 200
    assert recalculated.status_code == 200
    assert events.status_code == 200
