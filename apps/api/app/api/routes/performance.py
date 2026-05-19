"""Performance stats route — aggregate win rates for the operator dashboard."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.services.performance_stats_service import (
    DEFAULT_MIN_SAMPLES,
    DimensionWinRate,
    PerformanceStatsService,
)

router = APIRouter(prefix="/performance-stats", tags=["performance"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class DimensionWinRateResponse(BaseModel):
    key: str
    total: int
    wins: int
    win_rate: float


class PerformanceStatsResponse(BaseModel):
    total_trades: int
    total_wins: int
    overall_win_rate: float
    by_setup: list[DimensionWinRateResponse]
    by_asset: list[DimensionWinRateResponse]
    by_catalyst: list[DimensionWinRateResponse]
    by_regime: list[DimensionWinRateResponse]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=PerformanceStatsResponse)
def get_performance_stats(
    session: Annotated[Session, Depends(get_db_session)],
    min_samples: Annotated[int, Query(ge=1, le=100)] = DEFAULT_MIN_SAMPLES,
    include_visual_seed: Annotated[bool, Query(description="Include visual seed demo data")] = False,
) -> PerformanceStatsResponse:
    """Return aggregated signal outcome win rates by setup, asset, catalyst and regime."""
    service = PerformanceStatsService(session)
    stats = service.overall_stats(min_samples=min_samples, include_visual_seed=include_visual_seed)

    def _map_dim(dims: list[DimensionWinRate]) -> list[DimensionWinRateResponse]:
        return [
            DimensionWinRateResponse(
                key=d.key,
                total=d.total,
                wins=d.wins,
                win_rate=d.win_rate,
            )
            for d in dims
        ]

    return PerformanceStatsResponse(
        total_trades=stats.total_trades,
        total_wins=stats.total_wins,
        overall_win_rate=stats.overall_win_rate,
        by_setup=_map_dim(stats.by_setup),
        by_asset=_map_dim(stats.by_asset),
        by_catalyst=_map_dim(stats.by_catalyst),
        by_regime=_map_dim(stats.by_regime),
    )
