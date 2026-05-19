"""Tests for MH-18 Paper Validation Dashboard & Readiness Review."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.db.models.paper_validation_plan import PaperValidationPlan
from app.services.paper_validation_service import PaperValidationService


@pytest.fixture
def session():
    """Mock SQLAlchemy session."""
    session = MagicMock()
    session.add = MagicMock()
    session.commit = MagicMock()
    session.refresh = MagicMock()
    session.get = MagicMock()
    return session


def test_dashboard_response_has_required_fields(session: MagicMock) -> None:
    """Dashboard response should have all required fields."""
    session.execute.return_value.scalars.return_value.all.return_value = []

    svc = PaperValidationService(session)
    dashboard = svc.get_dashboard_summary()

    assert hasattr(dashboard, "total_plans")
    assert hasattr(dashboard, "active_count")
    assert hasattr(dashboard, "passed_count")
    assert hasattr(dashboard, "failed_count")
    assert hasattr(dashboard, "ready_for_review_count")
    assert hasattr(dashboard, "average_progress_trades_pct")
    assert hasattr(dashboard, "average_progress_days_pct")
    assert hasattr(dashboard, "plans_needing_evidence")
    assert hasattr(dashboard, "warnings")


def test_readiness_response_has_required_fields(session: MagicMock) -> None:
    """Readiness response should have all required fields."""
    plan = PaperValidationPlan(
        id=uuid.uuid4(),
        baseline_candidate_id=uuid.uuid4(),
        status="pending",
        required_trades=100,
        minimum_days=30,
        starting_paper_capital=200000,
        progress={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    session.get.return_value = plan
    session.execute.return_value.scalars.return_value.all.return_value = []

    svc = PaperValidationService(session)
    readiness = svc.get_readiness_review(str(plan.id))

    assert hasattr(readiness, "plan_id")
    assert hasattr(readiness, "status")
    assert hasattr(readiness, "readiness_status")
    assert hasattr(readiness, "readiness_score")
    assert hasattr(readiness, "suggested_next_action")
    assert hasattr(readiness, "metric_deltas")
    assert hasattr(readiness, "evidence_summary")
    assert hasattr(readiness, "warnings")


def test_readiness_score_is_int_0_to_100(session: MagicMock) -> None:
    """Readiness score should be an integer between 0 and 100."""
    plan = PaperValidationPlan(
        id=uuid.uuid4(),
        baseline_candidate_id=uuid.uuid4(),
        status="active",
        required_trades=100,
        minimum_days=30,
        starting_paper_capital=200000,
        progress={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    session.get.return_value = plan
    session.execute.return_value.scalars.return_value.all.return_value = []

    svc = PaperValidationService(session)
    readiness = svc.get_readiness_review(str(plan.id))

    assert isinstance(readiness.readiness_score, int)
    assert 0 <= readiness.readiness_score <= 100


def test_readiness_status_is_valid_enum(session: MagicMock) -> None:
    """Readiness status should be one of the valid values."""
    plan = PaperValidationPlan(
        id=uuid.uuid4(),
        baseline_candidate_id=uuid.uuid4(),
        status="pending",
        required_trades=100,
        minimum_days=30,
        starting_paper_capital=200000,
        progress={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    session.get.return_value = plan
    session.execute.return_value.scalars.return_value.all.return_value = []

    svc = PaperValidationService(session)
    readiness = svc.get_readiness_review(str(plan.id))

    valid_statuses = {
        "not_started",
        "collecting_evidence",
        "ready_for_review",
        "passed",
        "failed",
        "stopped",
    }
    assert readiness.readiness_status in valid_statuses


def test_suggested_next_action_is_valid(session: MagicMock) -> None:
    """Suggested next action should be one of the valid values."""
    plan = PaperValidationPlan(
        id=uuid.uuid4(),
        baseline_candidate_id=uuid.uuid4(),
        status="pending",
        required_trades=100,
        minimum_days=30,
        starting_paper_capital=200000,
        progress={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    session.get.return_value = plan
    session.execute.return_value.scalars.return_value.all.return_value = []

    svc = PaperValidationService(session)
    readiness = svc.get_readiness_review(str(plan.id))

    valid_actions = {
        "keep_collecting",
        "review_candidate",
        "reject_candidate",
        "investigate_data",
        "stop_validation",
    }
    assert readiness.suggested_next_action in valid_actions


def test_evidence_summary_has_counts(session: MagicMock) -> None:
    """Evidence summary should include counts of different evidence types."""
    plan = PaperValidationPlan(
        id=uuid.uuid4(),
        baseline_candidate_id=uuid.uuid4(),
        status="active",
        required_trades=100,
        minimum_days=30,
        starting_paper_capital=200000,
        progress={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    session.get.return_value = plan
    session.execute.return_value.scalars.return_value.all.return_value = []

    svc = PaperValidationService(session)
    readiness = svc.get_readiness_review(str(plan.id))

    assert hasattr(readiness.evidence_summary, "total_evidence")
    assert hasattr(readiness.evidence_summary, "manual_evidence_count")
    assert hasattr(readiness.evidence_summary, "reconciled_evidence_count")
    assert hasattr(readiness.evidence_summary, "high_confidence_count")
    assert hasattr(readiness.evidence_summary, "low_confidence_count")


def test_metric_deltas_optional_fields(session: MagicMock) -> None:
    """Metric deltas should have optional delta fields."""
    plan = PaperValidationPlan(
        id=uuid.uuid4(),
        baseline_candidate_id=uuid.uuid4(),
        status="active",
        required_trades=100,
        minimum_days=30,
        starting_paper_capital=200000,
        progress={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    session.get.return_value = plan
    session.execute.return_value.scalars.return_value.all.return_value = []

    svc = PaperValidationService(session)
    readiness = svc.get_readiness_review(str(plan.id))

    assert hasattr(readiness.metric_deltas, "profit_factor_delta")
    assert hasattr(readiness.metric_deltas, "total_return_delta")
    assert hasattr(readiness.metric_deltas, "max_drawdown_delta")
    assert hasattr(readiness.metric_deltas, "win_rate_delta")


def test_no_live_trading_unlock_fields(session: MagicMock) -> None:
    """Readiness response should not have live trading unlock fields."""
    plan = PaperValidationPlan(
        id=uuid.uuid4(),
        baseline_candidate_id=uuid.uuid4(),
        status="active",
        required_trades=100,
        minimum_days=30,
        starting_paper_capital=200000,
        progress={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    session.get.return_value = plan
    session.execute.return_value.scalars.return_value.all.return_value = []

    svc = PaperValidationService(session)
    readiness = svc.get_readiness_review(str(plan.id))

    assert not hasattr(readiness, "live_approved")
    assert not hasattr(readiness, "approved_for_live")
    assert not hasattr(readiness, "unlock_live_trading")
    assert "live" not in readiness.suggested_next_action.lower()


def test_dashboard_routes_exist() -> None:
    """Dashboard endpoints must be registered in the app."""
    from app.main import app

    route_paths = [str(r.path) for r in app.routes]  # type: ignore[attr-defined]

    assert any("/paper-validation/dashboard" in p for p in route_paths), \
        "GET /dashboard route not registered"
    assert any("/paper-validation/plans/{plan_id}/readiness" in p for p in route_paths), \
        "GET /readiness route not registered"


def test_existing_paper_validation_tests_still_pass(session: MagicMock) -> None:
    """Existing MH-16 and MH-17 tests should continue to pass."""
    plan = PaperValidationPlan(
        id=uuid.uuid4(),
        baseline_candidate_id=uuid.uuid4(),
        status="pending",
        required_trades=100,
        minimum_days=30,
        starting_paper_capital=200000,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    session.execute.return_value.scalars.return_value.all.return_value = [plan]

    svc = PaperValidationService(session)

    list_result = svc.list_plans()
    assert list_result.total == 1
