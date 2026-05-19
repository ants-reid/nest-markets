from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

from sqlalchemy.orm import Session

from app.db.models.eval_case import EvalCase
from app.db.models.eval_run import EvalRun
from app.services.eval_persistence_service import write_eval_results


def test_write_eval_results_adds_new_cases_and_run():
    session = MagicMock(spec=Session)
    session.execute.return_value.scalar_one_or_none.return_value = None

    def _refresh(obj):
        if getattr(obj, "id", None) is None:
            obj.id = uuid4()

    session.refresh.side_effect = _refresh

    run = EvalRun(provider_name="pytest", started_at=datetime.now(UTC), completed_at=datetime.now(UTC), summary_score=1.0, pass_rate=1.0)
    case = EvalCase(name="qa-case-1", category="signal_output_eval", input_json={"x": 1}, is_active=True)

    result = write_eval_results(session, run, [case])

    assert result.id is not None
    assert session.add.call_count == 2


def test_write_eval_results_deduplicates_existing_case_names():
    session = MagicMock(spec=Session)
    session.execute.return_value.scalar_one_or_none.return_value = EvalCase(name="qa-case-1", category="signal_output_eval", input_json={}, is_active=True)

    def _refresh(obj):
        if getattr(obj, "id", None) is None:
            obj.id = uuid4()

    session.refresh.side_effect = _refresh

    run = EvalRun(provider_name="pytest", started_at=datetime.now(UTC), completed_at=datetime.now(UTC), summary_score=1.0, pass_rate=1.0)
    case = EvalCase(name="qa-case-1", category="signal_output_eval", input_json={"x": 1}, is_active=True)

    write_eval_results(session, run, [case])

    assert session.add.call_count == 1
