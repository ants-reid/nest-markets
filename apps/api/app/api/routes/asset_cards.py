"""Read-only asset-cards endpoints (MH-COCKPIT-02-A + MH-COCKPIT-11-A)."""

from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.db.enums import AssetClass
from app.db.session import SessionLocal
from app.services.asset_card_service import (
    AssetCardNotFoundError,
    get_asset_card_detail,
    get_asset_card_snapshot,
)

router = APIRouter(prefix="/asset-cards", tags=["asset-cards"])


@router.get("/snapshot")
def asset_cards_snapshot(
    limit: int = Query(50, ge=1, le=200),
    asset_class: Optional[AssetClass] = Query(None),
    active_only: bool = Query(True),
) -> Dict[str, Any]:
    """Return a snapshot of asset cards with derived market-quality metrics.

    Read-only. Operator hint only.
    """

    with SessionLocal() as session:
        return get_asset_card_snapshot(
            session,
            asset_class=asset_class,
            active_only=active_only,
            limit=limit,
        )


@router.get("/{asset_id}")
def asset_card_detail(
    asset_id: UUID,
    recent_bars_limit: int = Query(30, ge=1, le=200),
) -> Dict[str, Any]:
    """Return a single asset's card detail + recent bars (read-only)."""

    with SessionLocal() as session:
        try:
            return get_asset_card_detail(
                session,
                asset_id,
                recent_bars_limit=recent_bars_limit,
            )
        except AssetCardNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
