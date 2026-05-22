"""MH-COCKPIT-08 — Read-only ``/cockpit/trade-close-explanations`` endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.cockpit_trade_close_explanations import (
    CockpitTradeCloseExplanationsResponseSchema,
)
from app.services.cockpit_trade_close_explanations_service import (
    get_cockpit_trade_close_explanations,
)

router = APIRouter(prefix="/cockpit", tags=["cockpit"])


@router.get(
    "/trade-close-explanations",
    response_model=CockpitTradeCloseExplanationsResponseSchema,
)
def read_cockpit_trade_close_explanations(
    session: Annotated[Session, Depends(get_db_session)],
) -> CockpitTradeCloseExplanationsResponseSchema:
    """Return read-only explanations for recently closed paper trades."""
    return get_cockpit_trade_close_explanations(session)
