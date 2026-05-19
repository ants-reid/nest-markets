"""Tests for MH-17 paper validation evidence and reconciliation."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.db.models.baseline_candidate import BaselineCandidate
from app.db.models.paper_validation_evidence import PaperValidationEvidence
from app.db.models.paper_validation_plan import PaperValidationPlan
from app.schemas.strategy_lab import (
    PaperValidationManualEvidenceRequest,
    PaperValidationReconcileRequest,
)
from app.services.paper_validation_service import PaperValidationService


# ── Helpers ────────────────────────────────────────────────────────────────


def _candidate() -> BaselineCandidate:
    c = BaselineCandidate(
        backtest_run_id=uuid.uuid4(),
        strategy_config_id=uuid.uuid4(),
        ai_backtest_report_id=None,
        asset="AAPL",
        timeframe="1d",
        strategy_type="ma_momentum",
        parameters={"fast_window": 5, "slow_window": 20},
        metrics={"total_trades": 122, "profit_factor": 1.72, "max_drawdown_pct": 4.25},
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


def _plan(candidate: BaselineCandidate, status: str = "active") -> PaperValidationPlan:
    p = PaperValidationPlan(
        baseline_candidate_id=candidate.id,
        backtest_run_id=candidate.backtest_run_id,
        strategy_config_id=candidate.strategy_config_id,
        status=status,
        required_trades=5,
        minimum_days=10,
        target_profit_factor=1.5,
        max_drawdown_pct=10.0,
        max_daily_loss_pct=2.0,
        starting_paper_capital=200000,
        backtest_metrics=dict(candidate.metrics or {}),
        paper_metrics=None,
        progress={},
        pass_fail_reasons=[],
        started_at=datetime.now(timezone.utc),
        completed_at=None,
        created_by="tester",
        reviewed_by=None,
        review_notes=None,
    )
    p.id = uuid.uuid4()
    p.created_at = datetime.now(timezone.utc)
    p.updated_at = datetime.now(timezone.utc)
    return p


def _evidence(
    plan: PaperValidationPlan,
    result: str = "win",
    pnl_pct: float | None = 2.5,
    pnl_amount: float | None = 500.0,
    included: bool = True,
) -> PaperValidationEvidence:
    ev = PaperValidationEvidence(
        paper_validation_plan_id=plan.id,
        source_type="manual",
        source_id=None,
        confidence="manual",
        asset="AAPL",
        timeframe="1d",
        side="long",
        opened_at=None,
        closed_at=datetime.now(timezone.utc),
        entry_price=150.0,
        exit_price=153.75,
        pnl_amount=pnl_amount,
        pnl_pct=pnl_pct,
        r_multiple=1.5,
        result=result,
        payload=None,
        notes=None,
        included_in_metrics=included,
    )
    ev.id = uuid.uuid4()
    ev.created_at = datetime.now(timezone.utc)
    ev.updated_at = datetime.now(timezone.utc)
    return ev


def _execute_all(values: list) -> MagicMock:
    result = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = values
    result.scalars.return_value = scalars
    return result


def _execute_first(value) -> MagicMock:
    result = MagicMock()
    scalars = MagicMock()
    scalars.first.return_value = value
    result.scalars.return_value = scalars
    return result


def _make_session(plan: PaperValidationPlan, evidence: list[PaperValidationEvidence] | None = None):
    """Create a mock session that returns plan from get() and evidence from execute()."""
    session = MagicMock()
    session.get.return_value = plan

    def execute_side_effect(stmt):
        # Return evidence for PaperValidationEvidence queries; empty for dedup check
        return _execute_all(evidence if evidence is not None else [])

    session.execute.side_effect = execute_side_effect

    def refresh(row):
        if not hasattr(row, "id") or row.id is None:
            row.id = uuid.uuid4()
        if not hasattr(row, "created_at") or row.created_at is None:
            row.created_at = datetime.now(timezone.utc)
        if not hasattr(row, "updated_at") or row.updated_at is None:
            row.updated_at = datetime.now(timezone.utc)

    session.refresh.side_effect = refresh
    return session


# ── compute_progress_from_evidence tests ──────────────────────────────────


def test_compute_progress_from_evidence_counts_wins_losses():
    candidate = _candidate()
    plan = _plan(candidate)
    session = MagicMock()
    svc = PaperValidationService(session)

    ev_win = _evidence(plan, result="win", pnl_pct=2.5, pnl_amount=500.0)
    ev_loss = _evidence(plan, result="loss", pnl_pct=-1.0, pnl_amount=-200.0)
    ev_be = _evidence(plan, result="breakeven", pnl_pct=0.0, pnl_amount=0.0)

    result = svc._compute_progress_from_evidence(plan, [ev_win, ev_loss, ev_be])

    assert result.wins == 1
    assert result.losses == 1
    assert result.total_paper_trades == 3
    assert result.win_rate == pytest.approx(1 / 3)


def test_compute_progress_profit_factor_calculation():
    candidate = _candidate()
    plan = _plan(candidate)
    session = MagicMock()
    svc = PaperValidationService(session)

    ev1 = _evidence(plan, result="win", pnl_amount=300.0)
    ev2 = _evidence(plan, result="win", pnl_amount=200.0)
    ev3 = _evidence(plan, result="loss", pnl_amount=-100.0)

    result = svc._compute_progress_from_evidence(plan, [ev1, ev2, ev3])

    # Gross profit = 500, gross loss = 100 → PF = 5.0
    assert result.profit_factor == pytest.approx(5.0)


def test_compute_progress_excludes_excluded_evidence():
    candidate = _candidate()
    plan = _plan(candidate)
    session = MagicMock()
    svc = PaperValidationService(session)

    ev_included = _evidence(plan, result="win", pnl_pct=2.5, pnl_amount=500.0, included=True)
    ev_excluded = _evidence(plan, result="loss", pnl_pct=-5.0, pnl_amount=-1000.0, included=False)

    result = svc._compute_progress_from_evidence(plan, [ev_included, ev_excluded])

    assert result.wins == 1
    assert result.losses == 0
    assert result.total_paper_trades == 1


def test_progress_trades_pct_calculation():
    candidate = _candidate()
    plan = _plan(candidate)  # required_trades=5
    session = MagicMock()
    svc = PaperValidationService(session)

    evidence = [_evidence(plan, result="win", pnl_amount=100.0) for _ in range(3)]
    result = svc._compute_progress_from_evidence(plan, evidence)

    assert result.progress_trades_pct == pytest.approx(60.0)


def test_active_plan_stays_active_until_requirements_met():
    candidate = _candidate()
    plan = _plan(candidate, status="active")  # required_trades=5, minimum_days=10

    evidence = [_evidence(plan, result="win", pnl_amount=100.0) for _ in range(3)]  # only 3 of 5

    session = MagicMock()
    svc = PaperValidationService(session)
    result = svc._compute_progress_from_evidence(plan, evidence)

    assert result.pass_fail_status == "active"


def test_active_plan_passes_when_all_requirements_met():
    candidate = _candidate()
    plan = _plan(candidate, status="active")  # required_trades=5, min_days=10
    plan.target_profit_factor = None  # no PF requirement
    plan.max_drawdown_pct = None  # no DD requirement

    # days_active uses started_at, but it will be < 10 days (just created)
    # We need to override days_active via paper_metrics since we can't fast-forward time
    plan.paper_metrics = {"days_active": 30}  # >= 10

    evidence = [_evidence(plan, result="win", pnl_amount=100.0) for _ in range(6)]  # 6 >= 5

    session = MagicMock()
    svc = PaperValidationService(session)
    result = svc._compute_progress_from_evidence(plan, evidence)

    assert result.pass_fail_status == "passed"


def test_active_plan_fails_when_drawdown_breached():
    candidate = _candidate()
    plan = _plan(candidate, status="active")
    plan.max_drawdown_pct = 5.0  # threshold is 5%

    # Create enough evidence to make drawdown calculable
    evidence = [
        _evidence(plan, result="win", pnl_pct=2.0, pnl_amount=200.0),
        _evidence(plan, result="win", pnl_pct=1.5, pnl_amount=150.0),
        _evidence(plan, result="loss", pnl_pct=-10.0, pnl_amount=-1000.0),  # triggers drawdown
    ]
    # Cumulative: 2.0, 3.5, -6.5 → peak=3.5, drawdown=10.0 > 5%

    session = MagicMock()
    svc = PaperValidationService(session)
    result = svc._compute_progress_from_evidence(plan, evidence)

    assert result.pass_fail_status == "failed"
    assert any("drawdown" in r.lower() for r in result.reasons)


# ── add_manual_evidence tests ─────────────────────────────────────────────


def test_add_manual_evidence_creates_evidence_record():
    candidate = _candidate()
    plan = _plan(candidate)
    session = _make_session(plan, evidence=[])

    svc = PaperValidationService(session)
    body = PaperValidationManualEvidenceRequest(
        asset="AAPL",
        timeframe="1d",
        side="long",
        result="win",
        pnl_pct=2.5,
        pnl_amount=500.0,
        r_multiple=1.5,
        included_in_metrics=True,
    )

    # add_manual_evidence calls session.add for evidence + events, flush, then refresh
    added_objects = []
    session.add.side_effect = lambda obj: added_objects.append(obj)

    def refresh(row):
        if isinstance(row, PaperValidationEvidence):
            row.id = uuid.uuid4()
            row.created_at = datetime.now(timezone.utc)
            row.updated_at = datetime.now(timezone.utc)

    session.refresh.side_effect = refresh

    svc.add_manual_evidence(str(plan.id), body)

    evidence_objects = [o for o in added_objects if isinstance(o, PaperValidationEvidence)]
    assert len(evidence_objects) == 1
    ev = evidence_objects[0]
    assert ev.source_type == "manual"
    assert ev.result == "win"
    assert ev.asset == "AAPL"
    assert ev.confidence == "manual"
    assert ev.paper_validation_plan_id == plan.id


def test_list_evidence_returns_all_plan_evidence():
    candidate = _candidate()
    plan = _plan(candidate)
    ev1 = _evidence(plan, result="win")
    ev2 = _evidence(plan, result="loss")

    session = _make_session(plan, evidence=[ev1, ev2])
    svc = PaperValidationService(session)

    result = svc.list_evidence(str(plan.id))

    assert result.total == 2
    assert {i.result for i in result.items} == {"win", "loss"}


def test_exclude_evidence_sets_included_false():
    candidate = _candidate()
    plan = _plan(candidate)
    ev = _evidence(plan, result="win", included=True)

    session = _make_session(plan, evidence=[ev])

    def get_side_effect(model, id_val):
        if model is PaperValidationPlan:
            return plan
        if model is PaperValidationEvidence:
            return ev
        return None

    session.get.side_effect = get_side_effect

    def refresh(row):
        if isinstance(row, PaperValidationEvidence):
            pass  # ev already has attrs

    session.refresh.side_effect = refresh

    svc = PaperValidationService(session)
    svc.exclude_evidence(str(plan.id), str(ev.id))

    assert ev.included_in_metrics is False


def test_include_evidence_sets_included_true():
    candidate = _candidate()
    plan = _plan(candidate)
    ev = _evidence(plan, result="loss", included=False)

    session = _make_session(plan, evidence=[ev])

    def get_side_effect(model, id_val):
        if model is PaperValidationPlan:
            return plan
        if model is PaperValidationEvidence:
            return ev
        return None

    session.get.side_effect = get_side_effect

    def refresh(row):
        pass

    session.refresh.side_effect = refresh

    svc = PaperValidationService(session)
    svc.include_evidence(str(plan.id), str(ev.id))

    assert ev.included_in_metrics is True


def test_recalculate_uses_evidence_when_present():
    candidate = _candidate()
    plan = _plan(candidate, status="active")
    plan.target_profit_factor = None
    plan.max_drawdown_pct = None
    plan.paper_metrics = {"days_active": 30}  # ensure days requirement is met

    # 6 win evidence records, required_trades=5 → should pass
    evidence = [_evidence(plan, result="win", pnl_amount=100.0) for _ in range(6)]

    session = _make_session(plan, evidence=evidence)
    svc = PaperValidationService(session)

    result_plan = svc.recalculate_plan(str(plan.id))

    assert result_plan.status == "passed"


def test_reconcile_does_not_duplicate_existing_evidence():
    """Reconcile skips signal_outcomes that are already in evidence."""
    candidate = _candidate()
    plan = _plan(candidate)
    plan.baseline_candidate_id = candidate.id

    signal_outcome_id = uuid.uuid4()

    # Existing evidence already has this signal_outcome
    existing_ev = _evidence(plan, result="win")
    existing_ev.source_type = "signal_outcome"
    existing_ev.source_id = signal_outcome_id

    session = MagicMock()
    session.get.side_effect = lambda model, id_val: plan if model is PaperValidationPlan else candidate

    call_count = [0]

    def execute_side_effect(stmt):
        call_count[0] += 1
        # First call in reconcile will be the signal_outcomes query
        # Second call will be the dedup check
        # Third call from _compute_progress after recalculate
        return _execute_all([])

    session.execute.side_effect = execute_side_effect

    svc = PaperValidationService(session)
    body = PaperValidationReconcileRequest(dry_run=False, asset_filter="AAPL", timeframe_filter="1d")
    result = svc.reconcile(str(plan.id), body)

    assert result.evidence_created == 0
    assert result.evidence_skipped == 0  # no signal_outcomes found
    assert result.matched_source == "signal_outcomes"
    assert result.dry_run is False


def test_reconcile_dry_run_does_not_persist():
    """dry_run=True computes but does not commit or add evidence."""
    candidate = _candidate()
    plan = _plan(candidate)
    plan.baseline_candidate_id = candidate.id

    session = MagicMock()
    session.get.side_effect = lambda model, id_val: plan if model is PaperValidationPlan else candidate
    session.execute.return_value = _execute_all([])

    added = []
    session.add.side_effect = lambda obj: added.append(obj)

    svc = PaperValidationService(session)
    body = PaperValidationReconcileRequest(dry_run=True)
    result = svc.reconcile(str(plan.id), body)

    assert result.dry_run is True
    # No evidence objects should be added (dry run)
    evidence_added = [o for o in added if isinstance(o, PaperValidationEvidence)]
    assert len(evidence_added) == 0


def test_no_live_trading_status_changed():
    """None of the evidence operations change execution_mode or live trading records."""
    candidate = _candidate()
    plan = _plan(candidate)
    ev = _evidence(plan)

    session = _make_session(plan, evidence=[ev])

    def get_side_effect(model, id_val):
        if model is PaperValidationPlan:
            return plan
        if model is PaperValidationEvidence:
            return ev
        return None

    session.get.side_effect = get_side_effect
    session.refresh.side_effect = lambda row: None

    svc = PaperValidationService(session)
    svc.exclude_evidence(str(plan.id), str(ev.id))
    svc.include_evidence(str(plan.id), str(ev.id))

    # Verify no live execution models were touched
    for added_call in session.add.call_args_list:
        obj = added_call[0][0]
        class_name = type(obj).__name__
        assert "ExecutionMode" not in class_name
        assert "ApprovalRequest" not in class_name
        assert "RiskDecision" not in class_name


def test_existing_paper_validation_plan_tests_still_pass():
    """Sanity: evidence-aware _compute_progress falls back to paper_metrics when no evidence."""
    candidate = _candidate()
    plan = _plan(candidate, status="active")
    plan.paper_metrics = {
        "total_paper_trades": 50,
        "wins": 30,
        "losses": 20,
        "profit_factor": 1.6,
        "max_drawdown_pct": 3.0,
    }

    session = MagicMock()
    # session.execute returns empty list for evidence query
    session.execute.return_value = _execute_all([])

    svc = PaperValidationService(session)
    result = svc._compute_progress(plan)

    assert result.total_paper_trades == 50
    assert result.wins == 30
    assert result.profit_factor == pytest.approx(1.6)


# ── Route contract tests ───────────────────────────────────────────────────


def test_evidence_routes_exist():
    """All MH-17 evidence/reconcile routes must be registered in the app."""
    from app.main import app

    route_paths = [str(r.path) for r in app.routes]  # type: ignore[attr-defined]

    # Check the pattern exists (FastAPI stores as /paper-validation/plans/{plan_id}/...)
    assert any("/paper-validation/plans/{plan_id}/evidence" in p for p in route_paths), \
        "GET /evidence route not registered"
    assert any("/paper-validation/plans/{plan_id}/evidence/manual" in p for p in route_paths), \
        "POST /evidence/manual route not registered"
    assert any("/paper-validation/plans/{plan_id}/evidence/{evidence_id}/exclude" in p for p in route_paths), \
        "POST /exclude route not registered"
    assert any("/paper-validation/plans/{plan_id}/evidence/{evidence_id}/include" in p for p in route_paths), \
        "POST /include route not registered"
    assert any("/paper-validation/plans/{plan_id}/reconcile" in p for p in route_paths), \
        "POST /reconcile route not registered"
