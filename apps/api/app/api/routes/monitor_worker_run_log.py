"""MH-158-A — Read-only ``/monitor/worker-run-log/overview`` endpoint."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.services.worker_run_log_overview_service import (
    WorkerRunLogOverviewError,
    get_worker_run_log_overview,
)

router = APIRouter(prefix="/monitor", tags=["monitor"])


@router.get("/worker-run-log/overview")
def read_worker_run_log_overview(
    limit: int = Query(20, ge=1, le=200),
) -> dict:
    """Return retention metadata + recent auto-paper worker runs.

    Read-only consolidator. Never modifies the run log or any trading control.
    """
    try:
        return get_worker_run_log_overview(limit=limit)
    except WorkerRunLogOverviewError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
