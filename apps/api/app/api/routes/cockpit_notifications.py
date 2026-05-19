"""MH-COCKPIT-06-A — Read-only ``/cockpit/notifications/digest`` endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.services.notifications_digest_service import (
    NotificationsDigestError,
    get_notifications_digest,
)

router = APIRouter(prefix="/cockpit", tags=["cockpit"])


@router.get("/notifications/digest")
def read_notifications_digest(
    hours: int = Query(24, ge=1, le=168),
    min_severity: str = Query("warn"),
    limit: int = Query(10, ge=1, le=50),
    session: Session = Depends(get_db_session),
) -> dict:
    """Return an operator-facing notifications digest.

    Read-only aggregator over the append-only ``incident_logs`` table. Never
    influences any trading control.
    """
    try:
        return get_notifications_digest(
            session,
            hours=hours,
            min_severity=min_severity,
            limit=limit,
        )
    except NotificationsDigestError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
