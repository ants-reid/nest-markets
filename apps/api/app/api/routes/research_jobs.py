"""Research job orchestration routes for MH-05."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.models.research_job import ResearchJob
from app.db.session import get_db_session
from app.schemas.research_data import (
    ImportRequest,
    QualityRecalculateRequest,
    ResearchJobCancelResponse,
    ResearchJobDetailResponse,
    ResearchJobListResponse,
    ResearchJobResponse,
    ResearchJobRetryResponse,
)
from app.services.research_job_service import ResearchJobService

router = APIRouter(prefix="/research/jobs", tags=["research_jobs"])


def _to_response(job: ResearchJob) -> ResearchJobResponse:
    return ResearchJobResponse(
        id=job.id,
        job_type=job.job_type,  # type: ignore[arg-type]
        status=job.status,  # type: ignore[arg-type]
        requested_by=job.requested_by,
        request_payload=job.request_payload,
        result_payload=job.result_payload,
        progress_current=job.progress_current,
        progress_total=job.progress_total,
        progress_message=job.progress_message,
        error_message=job.error_message,
        retry_of_job_id=job.retry_of_job_id,
        started_at=job.started_at,
        completed_at=job.completed_at,
        cancelled_at=job.cancelled_at,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.post("/import", response_model=ResearchJobDetailResponse, status_code=202)
async def start_import_job(
    request: ImportRequest,
    session: Annotated[Session, Depends(get_db_session)],
) -> ResearchJobDetailResponse:
    job = await ResearchJobService(session).create_and_run_import_job(request)
    return ResearchJobDetailResponse(job=_to_response(job))


@router.post("/quality/recalculate", response_model=ResearchJobDetailResponse, status_code=202)
def start_quality_job(
    request: QualityRecalculateRequest,
    session: Annotated[Session, Depends(get_db_session)],
) -> ResearchJobDetailResponse:
    job = ResearchJobService(session).create_and_run_quality_job(request)
    return ResearchJobDetailResponse(job=_to_response(job))


@router.get("", response_model=ResearchJobListResponse)
def list_research_jobs(
    session: Annotated[Session, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ResearchJobListResponse:
    total, items = ResearchJobService(session).list_jobs(limit=limit, offset=offset)
    return ResearchJobListResponse(total=total, items=[_to_response(item) for item in items])


@router.get("/{job_id}", response_model=ResearchJobDetailResponse)
def get_research_job(
    job_id: uuid.UUID,
    session: Annotated[Session, Depends(get_db_session)],
) -> ResearchJobDetailResponse:
    job = ResearchJobService(session).get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Research job not found")
    return ResearchJobDetailResponse(job=_to_response(job))


@router.post("/{job_id}/cancel", response_model=ResearchJobCancelResponse)
def cancel_research_job(
    job_id: uuid.UUID,
    session: Annotated[Session, Depends(get_db_session)],
) -> ResearchJobCancelResponse:
    job, message = ResearchJobService(session).cancel_job(job_id)
    return ResearchJobCancelResponse(
        success=job is not None and message == "cancelled",
        message=message,
        job=_to_response(job) if job is not None else None,
    )


@router.post("/{job_id}/retry", response_model=ResearchJobRetryResponse, status_code=202)
async def retry_research_job(
    job_id: uuid.UUID,
    session: Annotated[Session, Depends(get_db_session)],
) -> ResearchJobRetryResponse:
    original = ResearchJobService(session).get_job(job_id)
    if original is None:
        return ResearchJobRetryResponse(success=False, message="job_not_found", job=None)

    retried = await ResearchJobService(session).retry_job(job_id)
    if retried is None:
        return ResearchJobRetryResponse(success=False, message="job_not_retryable", job=None)

    return ResearchJobRetryResponse(success=True, message="retried", job=_to_response(retried))
