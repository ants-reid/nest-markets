"""MH-COCKPIT-10 — Read-only ``/cockpit/alerts-needing-attention`` endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.cockpit_alerts_needing_attention import (
    CockpitAlertsNeedingAttentionResponseSchema,
)
from app.services.cockpit_alerts_attention_service import (
    get_cockpit_alerts_needing_attention,
)

router = APIRouter(prefix="/cockpit", tags=["cockpit"])


@router.get(
    "/alerts-needing-attention",
    response_model=CockpitAlertsNeedingAttentionResponseSchema,
)
def read_cockpit_alerts_needing_attention(
    session: Annotated[Session, Depends(get_db_session)],
) -> CockpitAlertsNeedingAttentionResponseSchema:
    """Return read-only paper attention visibility for cockpit operators."""
    return get_cockpit_alerts_needing_attention(session)
