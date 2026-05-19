"""MH-COCKPIT-13-A — Read-only ``/cockpit/auto-paper/status`` endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from app.services.cockpit_auto_paper_status_service import (
    get_auto_paper_status_card,
)

router = APIRouter(prefix="/cockpit", tags=["cockpit"])


@router.get("/auto-paper/status")
def read_auto_paper_status_card() -> dict:
    """Return a read-only auto-paper status card.

    Surfaces drift-lock posture only. Never modifies any trading control.
    """
    return get_auto_paper_status_card()
