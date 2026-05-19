"""MH-MON-08-A — Read-only ``/monitor/health-history`` endpoint."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.services.health_history_service import (
    HealthHistoryError,
    get_health_history,
)

router = APIRouter(prefix="/monitor", tags=["monitor"])


@router.get("/health-history")
def read_health_history(
    hours: int = Query(24, ge=1, le=168),
    bucket_minutes: int = Query(60),
    source: Optional[str] = Query(None),
    session: Session = Depends(get_db_session),
) -> dict:
    """Return time-bucketed incident counts.

    Read-only aggregator over the append-only ``incident_logs`` table. Never
    influences any trading control.
    """
    try:
        return get_health_history(
            session,
            hours=hours,
            source=source,
            bucket_minutes=bucket_minutes,
        )
    except HealthHistoryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
