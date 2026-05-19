from __future__ import annotations

import os
from datetime import UTC, datetime

import pytest


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


@pytest.fixture(autouse=True)
def persist_eval_results_if_enabled(request):
    yield

    if os.getenv("PERSIST_EVALS") != "1":
        return

    from app.db.models.eval_case import EvalCase
    from app.db.models.eval_run import EvalRun
    from app.db.session import SessionLocal
    from app.services.eval_persistence_service import write_eval_results

    report = getattr(request.node, "rep_call", None)
    passed = bool(report and report.passed)

    session = SessionLocal()
    try:
        now = datetime.now(UTC)
        eval_run = EvalRun(
            provider_name="pytest",
            started_at=now,
            completed_at=now,
            summary_score=1.0 if passed else 0.0,
            pass_rate=1.0 if passed else 0.0,
            output_json={"nodeid": request.node.nodeid, "passed": passed},
            notes="Persisted from tests/evals autouse fixture",
        )
        eval_case = EvalCase(
            name=request.node.nodeid,
            category="signal_output_eval",
            input_json={"nodeid": request.node.nodeid},
            expected_json={"passed": passed},
            scoring_rules_json={"mode": "boolean_pass_fail"},
            is_active=True,
        )
        write_eval_results(session, eval_run, [eval_case])
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
