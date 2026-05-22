"""MH-COCKPIT-09 — Read-only ``/cockpit/daily-scoreboard`` endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.cockpit_daily_scoreboard import CockpitDailyScoreboardResponseSchema
from app.services.cockpit_daily_scoreboard_service import get_cockpit_daily_scoreboard

router = APIRouter(prefix="/cockpit", tags=["cockpit"])


@router.get("/daily-scoreboard", response_model=CockpitDailyScoreboardResponseSchema)
def read_cockpit_daily_scoreboard(
    session: Annotated[Session, Depends(get_db_session)],
) -> CockpitDailyScoreboardResponseSchema:
    """Return a read-only daily paper-trading scoreboard for cockpit operators."""
    return get_cockpit_daily_scoreboard(session)
