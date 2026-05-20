"""MH-COCKPIT-03 — safe cockpit mode selector API."""

from __future__ import annotations

from fastapi import APIRouter

from app.schemas.cockpit_mode import CockpitModeResponseSchema, CockpitModeUpdateRequest
from app.services.cockpit_mode_service import get_cockpit_mode_state, set_cockpit_mode

router = APIRouter(prefix="/cockpit", tags=["cockpit"])


@router.get("/mode", response_model=CockpitModeResponseSchema)
def read_cockpit_mode() -> CockpitModeResponseSchema:
    """Return the current cockpit mode and safe mode metadata."""
    return get_cockpit_mode_state()


@router.post("/mode", response_model=CockpitModeResponseSchema)
def update_cockpit_mode(payload: CockpitModeUpdateRequest) -> CockpitModeResponseSchema:
    """Update the cockpit mode within the current safe selectable set only."""
    return set_cockpit_mode(payload.requested_mode)