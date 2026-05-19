"""Opportunities routes — ranked trade setups from the latest signal sweep."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.db.enums import AssetClass
from app.db.session import get_db_session
from app.services.opportunity_ranker_service import OpportunityRankerService
from app.workers.signal_sweep_worker import SignalSweepWorker

_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class RankedOpportunityResponse(BaseModel):
    """A single ranked opportunity."""

    model_config = ConfigDict(from_attributes=True)

    signal_id: UUID
    asset: str
    asset_class: AssetClass
    direction: str
    setup_type: str
    confidence: float
    score: float
    regime: str
    horizon: str
    entry_low: float
    entry_high: float
    stop_price: float
    target_price: float


class OpportunityListResponse(BaseModel):
    """Ranked opportunity list."""

    items: list[RankedOpportunityResponse]
    total: int


class SweepRunResponse(BaseModel):
    """Result of a manual signal sweep trigger."""

    worker_name: str
    status: str
    message: str
    started_at: str
    finished_at: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("", response_model=OpportunityListResponse)
def list_opportunities(
    session: Annotated[Session, Depends(get_db_session)],
    limit: int = Query(default=10, ge=1, le=50),
    recency_hours: int = Query(default=8, ge=1, le=168),
    include_visual_seed: bool = Query(default=False, description="Include visual seed demo data"),
) -> OpportunityListResponse:
    """Return the top-ranked trade opportunities from recent signal sweeps."""
    service = OpportunityRankerService(session)
    items = service.rank(limit=limit, recency_hours=recency_hours, include_visual_seed=include_visual_seed)
    return OpportunityListResponse(
        items=[
            RankedOpportunityResponse(
                signal_id=op.signal_id,
                asset=op.asset,
                asset_class=op.asset_class,
                direction=op.direction,
                setup_type=op.setup_type,
                confidence=op.confidence,
                score=op.score,
                regime=op.regime,
                horizon=op.horizon,
                entry_low=op.entry_low,
                entry_high=op.entry_high,
                stop_price=op.stop_price,
                target_price=op.target_price,
            )
            for op in items
        ],
        total=len(items),
    )


@router.post("/sweep/run", response_model=SweepRunResponse)
def trigger_sweep_run() -> SweepRunResponse:
    """Manually trigger a signal sweep across all active assets.

    Runs synchronously and returns when complete.  Use this to populate
    fresh opportunities without waiting for the next scheduled run.
    """
    started_at = datetime.now(timezone.utc).isoformat()
    worker = SignalSweepWorker()
    try:
        result = worker.run()
        status = "ok"
        message = result.message if hasattr(result, "message") else str(result)
    except Exception as exc:
        _logger.error("Manual sweep run failed: %s", exc)
        status = "error"
        message = str(exc)
    finished_at = datetime.now(timezone.utc).isoformat()
    return SweepRunResponse(
        worker_name="signal_sweep",
        status=status,
        message=message,
        started_at=started_at,
        finished_at=finished_at,
    )
