"""MH-COCKPIT-05 — Read-only ``/cockpit/eod-report`` endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.cockpit_eod_report import CockpitEodReportResponseSchema
from app.services.cockpit_eod_report_service import get_cockpit_eod_report

router = APIRouter(prefix="/cockpit", tags=["cockpit"])


@router.get("/eod-report", response_model=CockpitEodReportResponseSchema)
def read_cockpit_eod_report(
    session: Annotated[Session, Depends(get_db_session)],
) -> CockpitEodReportResponseSchema:
    """Return a read-only paper end-of-day report for cockpit operators."""
    return get_cockpit_eod_report(session)