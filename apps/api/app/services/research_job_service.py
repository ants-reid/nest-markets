"""Research job orchestration service for MH-05."""

from __future__ import annotations

import uuid
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.research_job import ResearchJob
from app.schemas.research_data import ImportRequest, QualityRecalculateRequest
from app.services.historical_import_service import HistoricalImportService
from app.services.market_data_quality_service import MarketDataQualityService

JOB_TYPE_IMPORT = "historical_import"
JOB_TYPE_QUALITY = "quality_recalculate"
JOB_STATUS_QUEUED = "queued"
JOB_STATUS_RUNNING = "running"
JOB_STATUS_COMPLETED = "completed"
JOB_STATUS_PARTIAL = "partial"
JOB_STATUS_FAILED = "failed"
JOB_STATUS_CANCELLED = "cancelled"


class ResearchJobService:
    """Persist and execute research jobs with future-proof lifecycle states."""

    def __init__(self, session: Session) -> None:
        self._session = session

    async def create_and_run_import_job(
        self,
        request: ImportRequest,
        requested_by: str | None = None,
        retry_of_job_id: uuid.UUID | None = None,
    ) -> ResearchJob:
        payload = self._json_safe(request.model_dump())
        total = len(request.assets) * len(request.timeframes) * len(request.providers)
        job = self._create_job(
            job_type=JOB_TYPE_IMPORT,
            request_payload=payload,
            requested_by=requested_by,
            retry_of_job_id=retry_of_job_id,
            progress_total=total,
            progress_message="Queued import job",
        )
        self._mark_running(job, message="Running historical import job")

        try:
            result = await HistoricalImportService(self._session).run_import(
                assets=request.assets,
                timeframes=request.timeframes,
                providers=request.providers,
                requested_years=request.requested_years,
                dry_run=request.dry_run,
            )
            status = self._map_result_status(result.status)
            self._finish_job(
                job,
                status=status,
                result_payload=self._json_safe(asdict(result)),
                progress_current=total,
                progress_message=f"Import job finished with status: {status}",
            )
        except Exception as exc:  # noqa: BLE001
            self._fail_job(job, str(exc))

        self._session.commit()
        self._session.refresh(job)
        return job

    def create_and_run_quality_job(
        self,
        request: QualityRecalculateRequest,
        requested_by: str | None = None,
        retry_of_job_id: uuid.UUID | None = None,
    ) -> ResearchJob:
        payload = self._json_safe(request.model_dump())
        providers = request.providers or [None]
        total = len(request.assets) * len(request.timeframes) * len(providers)
        job = self._create_job(
            job_type=JOB_TYPE_QUALITY,
            request_payload=payload,
            requested_by=requested_by,
            retry_of_job_id=retry_of_job_id,
            progress_total=total,
            progress_message="Queued quality recalculation job",
        )
        self._mark_running(job, message="Running quality recalculation job")

        try:
            result = MarketDataQualityService(self._session).recalculate_quality(request)
            status = JOB_STATUS_COMPLETED if result.failed == 0 else JOB_STATUS_PARTIAL
            self._finish_job(
                job,
                status=status,
                result_payload=self._json_safe(result.model_dump()),
                progress_current=total,
                progress_message=f"Quality job finished with status: {status}",
            )
        except Exception as exc:  # noqa: BLE001
            self._fail_job(job, str(exc))

        self._session.commit()
        self._session.refresh(job)
        return job

    def list_jobs(self, limit: int = 50, offset: int = 0) -> tuple[int, list[ResearchJob]]:
        total = len(self._session.execute(select(ResearchJob)).scalars().all())
        rows = self._session.execute(
            select(ResearchJob)
            .order_by(ResearchJob.created_at.desc())
            .offset(offset)
            .limit(limit)
        ).scalars().all()
        return total, list(rows)

    def get_job(self, job_id: uuid.UUID) -> ResearchJob | None:
        return self._session.execute(
            select(ResearchJob).where(ResearchJob.id == job_id)
        ).scalar_one_or_none()

    def cancel_job(self, job_id: uuid.UUID) -> tuple[ResearchJob | None, str]:
        job = self.get_job(job_id)
        if job is None:
            return None, "job_not_found"
        if job.status == JOB_STATUS_QUEUED:
            job.status = JOB_STATUS_CANCELLED
            job.cancelled_at = datetime.now(UTC)
            job.progress_message = "Job cancelled before execution"
            self._session.commit()
            self._session.refresh(job)
            return job, "cancelled"
        if job.status == JOB_STATUS_RUNNING:
            job.progress_message = "Cancellation requested, but synchronous running jobs cannot be interrupted in MH-05"
            self._session.commit()
            self._session.refresh(job)
            return job, "cannot_cancel_running_sync_job"
        return job, f"job_not_cancellable_from_status:{job.status}"

    async def retry_job(self, job_id: uuid.UUID) -> ResearchJob | None:
        job = self.get_job(job_id)
        if job is None:
            return None
        if job.status not in {JOB_STATUS_FAILED, JOB_STATUS_PARTIAL, JOB_STATUS_CANCELLED}:
            return None

        if job.job_type == JOB_TYPE_IMPORT:
            request = ImportRequest(**job.request_payload)
            return await self.create_and_run_import_job(request, retry_of_job_id=job.id)
        if job.job_type == JOB_TYPE_QUALITY:
            request = QualityRecalculateRequest(**job.request_payload)
            return self.create_and_run_quality_job(request, retry_of_job_id=job.id)
        return None

    def create_queued_job(
        self,
        job_type: str,
        request_payload: dict[str, Any],
        requested_by: str | None = None,
        progress_total: int = 0,
    ) -> ResearchJob:
        job = self._create_job(
            job_type=job_type,
            request_payload=request_payload,
            requested_by=requested_by,
            progress_total=progress_total,
        )
        self._session.commit()
        self._session.refresh(job)
        return job

    def _create_job(
        self,
        job_type: str,
        request_payload: dict[str, Any],
        requested_by: str | None = None,
        retry_of_job_id: uuid.UUID | None = None,
        progress_total: int = 0,
        progress_message: str | None = None,
    ) -> ResearchJob:
        job = ResearchJob(
            job_type=job_type,
            status=JOB_STATUS_QUEUED,
            requested_by=requested_by,
            request_payload=request_payload,
            result_payload=None,
            progress_current=0,
            progress_total=progress_total,
            progress_message=progress_message,
            error_message=None,
            retry_of_job_id=retry_of_job_id,
        )
        self._session.add(job)
        self._session.flush()
        return job

    def _mark_running(self, job: ResearchJob, message: str) -> None:
        job.status = JOB_STATUS_RUNNING
        job.started_at = datetime.now(UTC)
        job.progress_message = message
        self._session.flush()

    def _finish_job(
        self,
        job: ResearchJob,
        status: str,
        result_payload: dict[str, Any],
        progress_current: int,
        progress_message: str,
    ) -> None:
        job.status = status
        job.result_payload = result_payload
        job.progress_current = progress_current
        job.progress_message = progress_message
        job.completed_at = datetime.now(UTC)
        job.error_message = None
        self._session.flush()

    def _fail_job(self, job: ResearchJob, message: str) -> None:
        job.status = JOB_STATUS_FAILED
        job.error_message = message
        job.progress_message = "Job failed"
        job.completed_at = datetime.now(UTC)
        self._session.flush()

    @staticmethod
    def _map_result_status(status: str) -> str:
        if status in {JOB_STATUS_COMPLETED, JOB_STATUS_FAILED, JOB_STATUS_PARTIAL, JOB_STATUS_CANCELLED}:
            return status
        if status == "dry_run":
            return JOB_STATUS_COMPLETED
        return JOB_STATUS_PARTIAL if status in {"skipped"} else JOB_STATUS_FAILED

    def _json_safe(self, value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, uuid.UUID):
            return str(value)
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, Decimal):
            return float(value)
        if is_dataclass(value):
            return self._json_safe(asdict(value))
        if hasattr(value, "model_dump"):
            return self._json_safe(value.model_dump())
        if isinstance(value, dict):
            return {str(k): self._json_safe(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._json_safe(v) for v in value]
        return str(value)
