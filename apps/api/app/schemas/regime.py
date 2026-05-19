"""Pydantic schemas for regime detection endpoints (Phase 3 scaffold).

Full regime detection is implemented in Phase 7 (feature store + ML model).
These schemas define the contract so frontend/API consumers can code against
a stable interface from Phase 3 onwards.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


RegimeLabel = Literal[
    "trending_bull",
    "trending_bear",
    "ranging",
    "volatile",
    "crisis",
    "unknown",
]


class RegimeSnapshotResponse(BaseModel):
    """Current market regime assessment for an asset/universe."""

    asset: str
    regime: RegimeLabel
    confidence: float
    detected_at: datetime
    source: Literal["ml_model", "heuristic", "manual", "unknown"] = "unknown"
    notes: str | None = None


class RegimeSnapshotListResponse(BaseModel):
    items: list[RegimeSnapshotResponse]
