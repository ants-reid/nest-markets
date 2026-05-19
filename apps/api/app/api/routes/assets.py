"""Asset universe management routes — list, add, and deactivate assets."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.db.enums import AssetClass
from app.db.models.asset import Asset
from app.db.session import get_db_session

router = APIRouter(prefix="/assets", tags=["assets"])


# ---------------------------------------------------------------------------
# Response / request schemas
# ---------------------------------------------------------------------------


class AssetResponse(BaseModel):
    """Asset row returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    symbol: str
    name: str | None
    asset_class: AssetClass
    base_currency: str | None
    quote_currency: str | None
    exchange: str | None
    sector: str | None
    industry: str | None
    is_active: bool


class AssetListResponse(BaseModel):
    """Paginated asset list."""

    items: list[AssetResponse]
    total: int


class CreateAssetRequest(BaseModel):
    """Request body for adding a new asset."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    name: str | None = None
    asset_class: AssetClass
    base_currency: str | None = None
    quote_currency: str | None = None
    exchange: str | None = None
    sector: str | None = None
    industry: str | None = None


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------


@router.get("", response_model=AssetListResponse)
def list_assets(
    session: Annotated[Session, Depends(get_db_session)],
    asset_class: AssetClass | None = Query(default=None),
    active_only: bool = Query(default=True),
) -> AssetListResponse:
    """Return the active asset universe, optionally filtered by asset class."""
    q = session.query(Asset)
    if active_only:
        q = q.filter(Asset.is_active.is_(True))
    if asset_class is not None:
        q = q.filter(Asset.asset_class == asset_class)
    rows = q.order_by(Asset.symbol).all()
    return AssetListResponse(
        items=[AssetResponse.model_validate(r) for r in rows],
        total=len(rows),
    )


@router.post("", response_model=AssetResponse, status_code=201)
def create_asset(
    body: CreateAssetRequest,
    session: Annotated[Session, Depends(get_db_session)],
) -> AssetResponse:
    """Add a new asset to the universe."""
    existing = session.query(Asset).filter_by(symbol=body.symbol).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail=f"Asset '{body.symbol}' already exists.")
    asset = Asset(**body.model_dump())
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return AssetResponse.model_validate(asset)


@router.delete("/{asset_id}", status_code=204)
def deactivate_asset(
    asset_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
) -> None:
    """Soft-delete an asset by marking it inactive."""
    asset = session.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found.")
    asset.is_active = False
    session.commit()
