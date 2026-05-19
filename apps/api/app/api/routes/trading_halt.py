"""Trading halt control and status endpoints for MH-39."""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.trading_halt import (
    TradingHaltCreateRequest,
    TradingHaltListResponse,
    TradingHaltResolveRequest,
    TradingHaltResponse,
    TradingHaltStatusResponse,
)
from app.services.trading_halt_service import TradingHaltService

router = APIRouter(prefix="/trading/halt", tags=["trading_halt"])


def _service(session: Annotated[Session, Depends(get_db_session)]) -> TradingHaltService:
    return TradingHaltService(session)


@router.get("/status", response_model=TradingHaltStatusResponse)
def get_trading_halt_status(
    service: Annotated[TradingHaltService, Depends(_service)],
    scope: str = Query(default="global"),
) -> TradingHaltStatusResponse:
    return service.get_status(scope=scope)


@router.get("", response_model=TradingHaltListResponse)
def list_trading_halts(
    service: Annotated[TradingHaltService, Depends(_service)],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    status: str | None = Query(default=None),
) -> TradingHaltListResponse:
    return service.list_halts(limit=limit, offset=offset, status=status)


@router.post("", response_model=TradingHaltResponse, status_code=201)
def create_trading_halt(
    request: TradingHaltCreateRequest,
    service: Annotated[TradingHaltService, Depends(_service)],
) -> TradingHaltResponse:
    halt = service.create_halt(request)
    return TradingHaltResponse.model_validate(halt)


@router.post("/{halt_id}/resolve", response_model=TradingHaltResponse)
def resolve_trading_halt(
    halt_id: UUID,
    request: TradingHaltResolveRequest,
    service: Annotated[TradingHaltService, Depends(_service)],
) -> TradingHaltResponse:
    halt = service.resolve_halt(halt_id, request)
    if halt is None:
        raise HTTPException(status_code=404, detail="Trading halt not found.")
    return TradingHaltResponse.model_validate(halt)