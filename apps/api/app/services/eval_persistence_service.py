"""Optional persistence helpers for eval harness results."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.eval_case import EvalCase
from app.db.models.eval_run import EvalRun


def write_eval_results(session: Session, eval_run: EvalRun, cases: list[EvalCase]) -> EvalRun:
    """Persist an eval run plus its cases.

    Existing cases are deduplicated by name; new cases are inserted.
    The eval run is always inserted as a new row.
    """
    for case in cases:
        existing = session.execute(
            select(EvalCase).where(EvalCase.name == case.name)
        ).scalar_one_or_none()
        if existing is None:
            session.add(case)

    session.add(eval_run)
    session.flush()
    session.refresh(eval_run)
    return eval_run
