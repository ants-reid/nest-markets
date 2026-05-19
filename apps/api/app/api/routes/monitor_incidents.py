"""MH-MON-05 — Read-only ``/monitor/incidents`` endpoint."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.services.incident_log_service import (
    IncidentLogError,
    list_incidents,
)

router = APIRouter(prefix="/monitor", tags=["monitor"])


@router.get("/incidents")
def get_incidents(
    limit: int = Query(100, ge=1, le=500),
    severity: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    session: Session = Depends(get_db_session),
) -> dict:
    """Append-only incident log reader.

    Read-only by design. There is no POST endpoint in this phase; incidents are
    written by backend services via ``app.services.incident_log_service``.
    """
    try:
        rows = list_incidents(session, limit=limit, severity=severity, source=source)
    except IncidentLogError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "count": len(rows),
        "limit": limit,
        "incidents": [r.to_dict() for r in rows],
    }
