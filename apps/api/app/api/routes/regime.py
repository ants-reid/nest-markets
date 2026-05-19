"""Regime detection endpoints (Phase 3 scaffold).

GET /regime/current  — Return the current regime snapshot (placeholder in Phase 3).
GET /regime/history  — List historical regime snapshots (placeholder in Phase 3).

Full regime detection is implemented in Phase 7 when the feature store and
ML regime model are available.  These endpoints return a placeholder response
in Phase 3 so downstream consumers can code against a stable contract.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter

from app.schemas.regime import RegimeSnapshotListResponse, RegimeSnapshotResponse

router = APIRouter(prefix="/regime", tags=["regime"])

_PLACEHOLDER_REGIME = RegimeSnapshotResponse(
    asset="universe",
    regime="unknown",
    confidence=0.0,
    detected_at=datetime(2026, 1, 1, tzinfo=UTC),
    source="unknown",
    notes="Regime detection not yet implemented (Phase 7).",
)


@router.get("/current", response_model=RegimeSnapshotResponse)
def get_current_regime() -> RegimeSnapshotResponse:
    """Return the current market regime (Phase 3: placeholder scaffold)."""
    return _PLACEHOLDER_REGIME


@router.get("/history", response_model=RegimeSnapshotListResponse)
def get_regime_history() -> RegimeSnapshotListResponse:
    """Return historical regime snapshots (Phase 3: empty scaffold)."""
    return RegimeSnapshotListResponse(items=[])
