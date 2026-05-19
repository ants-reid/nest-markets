"""Evals backend routes — list and inspect evaluation runs."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.eval_run import EvalRun
from app.db.models.eval_case import EvalCase
from app.db.session import get_db_session

router = APIRouter(prefix="/evals", tags=["evals"])


class EvalRunResponse(BaseModel):
    """Summary of a single evaluation run."""

    id: Any
    prompt_version_id: Any | None
    model_version_id: Any | None
    provider_name: str | None
    started_at: datetime | None
    completed_at: datetime | None
    summary_score: float | None
    pass_rate: float | None
    notes: str | None
    created_at: datetime


class EvalCaseSummary(BaseModel):
    """Summary of a single eval case."""

    id: Any
    name: str
    category: str
    is_active: bool
    created_at: datetime


class EvalRunDetailResponse(BaseModel):
    """Detailed eval run with case list."""

    run: EvalRunResponse
    cases: list[EvalCaseSummary]


def _to_run_response(r: EvalRun) -> EvalRunResponse:
    return EvalRunResponse(
        id=r.id,
        prompt_version_id=r.prompt_version_id,
        model_version_id=r.model_version_id,
        provider_name=r.provider_name,
        started_at=r.started_at,
        completed_at=r.completed_at,
        summary_score=float(r.summary_score) if r.summary_score is not None else None,
        pass_rate=float(r.pass_rate) if r.pass_rate is not None else None,
        notes=r.notes,
        created_at=r.created_at,
    )


@router.get("/runs", response_model=list[EvalRunResponse])
def list_eval_runs(
    session: Annotated[Session, Depends(get_db_session)],
    limit: int = 50,
) -> list[EvalRunResponse]:
    """Return the most recent evaluation runs (newest first)."""
    rows = (
        session.execute(
            select(EvalRun).order_by(EvalRun.created_at.desc()).limit(limit)
        )
        .scalars()
        .all()
    )
    return [_to_run_response(r) for r in rows]


@router.get("/runs/{run_id}", response_model=EvalRunDetailResponse)
def get_eval_run(
    run_id: str,
    session: Annotated[Session, Depends(get_db_session)],
) -> EvalRunDetailResponse:
    """Return a single eval run with a list of all active eval cases."""
    try:
        uid = UUID(run_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid run_id format.")

    run = session.get(EvalRun, uid)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Eval run '{run_id}' not found.")

    cases = (
        session.execute(
            select(EvalCase).where(EvalCase.is_active.is_(True)).order_by(EvalCase.name)
        )
        .scalars()
        .all()
    )

    return EvalRunDetailResponse(
        run=_to_run_response(run),
        cases=[
            EvalCaseSummary(
                id=c.id,
                name=c.name,
                category=c.category,
                is_active=c.is_active,
                created_at=c.created_at,
            )
            for c in cases
        ],
    )
