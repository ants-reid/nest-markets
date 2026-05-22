"""MH-COCKPIT-07 — Read-only ``/cockpit/in-flight-adjustments`` endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.cockpit_in_flight_adjustments import CockpitInFlightAdjustmentsResponseSchema
from app.services.cockpit_in_flight_adjustments_service import get_cockpit_in_flight_adjustments

router = APIRouter(prefix="/cockpit", tags=["cockpit"])


@router.get("/in-flight-adjustments", response_model=CockpitInFlightAdjustmentsResponseSchema)
def read_cockpit_in_flight_adjustments(
    session: Annotated[Session, Depends(get_db_session)],
) -> CockpitInFlightAdjustmentsResponseSchema:
    """Return read-only in-flight paper adjustment visibility for cockpit operators."""
    return get_cockpit_in_flight_adjustments(session)
