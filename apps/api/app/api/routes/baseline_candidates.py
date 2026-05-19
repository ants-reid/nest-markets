"""Baseline candidate routes — MH-15 research-stage candidate manager."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.strategy_lab import (
    BaselineCandidateCreateRequest,
    BaselineCandidateListResponse,
    BaselineCandidateRejectRequest,
    BaselineCandidateResponse,
    BaselineCandidateUpdateRequest,
)
from app.services.baseline_candidate_service import (
    BaselineCandidateError,
    BaselineCandidateService,
)

router = APIRouter(prefix="/baseline-candidates", tags=["baseline_candidates"])


def _svc(session: Session = Depends(get_db_session)) -> BaselineCandidateService:
    return BaselineCandidateService(session)


@router.post("", response_model=BaselineCandidateResponse, status_code=status.HTTP_201_CREATED)
def create_candidate(
    body: BaselineCandidateCreateRequest,
    svc: BaselineCandidateService = Depends(_svc),
) -> BaselineCandidateResponse:
    try:
        return svc.create_candidate(body)
    except BaselineCandidateError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("", response_model=BaselineCandidateListResponse)
def list_candidates(
    status_filter: str | None = Query(default=None, alias="status"),
    backtest_run_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    svc: BaselineCandidateService = Depends(_svc),
) -> BaselineCandidateListResponse:
    return svc.list_candidates(
        status=status_filter,
        backtest_run_id=backtest_run_id,
        limit=limit,
        offset=offset,
    )


@router.get("/{candidate_id}", response_model=BaselineCandidateResponse)
def get_candidate(
    candidate_id: str,
    svc: BaselineCandidateService = Depends(_svc),
) -> BaselineCandidateResponse:
    row = svc.get_candidate(candidate_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Baseline candidate not found")
    return row


@router.patch("/{candidate_id}", response_model=BaselineCandidateResponse)
def update_candidate(
    candidate_id: str,
    body: BaselineCandidateUpdateRequest,
    svc: BaselineCandidateService = Depends(_svc),
) -> BaselineCandidateResponse:
    row = svc.update_candidate(candidate_id, body)
    if row is None:
        raise HTTPException(status_code=404, detail="Baseline candidate not found")
    return row


@router.post("/{candidate_id}/reject", response_model=BaselineCandidateResponse)
def reject_candidate(
    candidate_id: str,
    body: BaselineCandidateRejectRequest,
    svc: BaselineCandidateService = Depends(_svc),
) -> BaselineCandidateResponse:
    row = svc.reject_candidate(
        candidate_id,
        reviewed_by=body.reviewed_by,
        review_notes=body.review_notes,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Baseline candidate not found")
    return row
