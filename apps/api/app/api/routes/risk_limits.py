"""Risk-limit foundation endpoints for MH-38."""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.risk_limits import (
    RiskLimitCheckResult,
    RiskLimitConfigCreateRequest,
    RiskLimitConfigResponse,
    RiskLimitConfigUpdateRequest,
    RiskLimitEvaluateRequest,
    RiskLimitStatusResponse,
)
from app.services.risk_limit_service import RiskLimitService

router = APIRouter(prefix="/risk/limits", tags=["risk_limits"])


def _service(session: Annotated[Session, Depends(get_db_session)]) -> RiskLimitService:
    return RiskLimitService(session)


@router.get("", response_model=list[RiskLimitConfigResponse])
def list_risk_limits(service: Annotated[RiskLimitService, Depends(_service)]) -> list[RiskLimitConfigResponse]:
    return [RiskLimitConfigResponse.model_validate(item) for item in service.list_configs()]


@router.post("", response_model=RiskLimitConfigResponse, status_code=201)
def create_risk_limit_config(
    request: RiskLimitConfigCreateRequest,
    service: Annotated[RiskLimitService, Depends(_service)],
) -> RiskLimitConfigResponse:
    config = service.create_config(request)
    return RiskLimitConfigResponse.model_validate(config)


@router.patch("/{config_id}", response_model=RiskLimitConfigResponse)
def update_risk_limit_config(
    config_id: UUID,
    request: RiskLimitConfigUpdateRequest,
    service: Annotated[RiskLimitService, Depends(_service)],
) -> RiskLimitConfigResponse:
    config = service.update_config(config_id, request)
    if config is None:
        raise HTTPException(status_code=404, detail="Risk limit config not found.")
    return RiskLimitConfigResponse.model_validate(config)


@router.get("/status", response_model=RiskLimitStatusResponse)
def get_risk_limit_status(
    service: Annotated[RiskLimitService, Depends(_service)],
    trading_mode: str | None = Query(default=None),
) -> RiskLimitStatusResponse:
    return service.get_status(trading_mode=trading_mode)


@router.post("/evaluate", response_model=RiskLimitCheckResult)
def evaluate_risk_limits(
    request: RiskLimitEvaluateRequest,
    service: Annotated[RiskLimitService, Depends(_service)],
) -> RiskLimitCheckResult:
    return service.evaluate_order_against_limits(request.model_dump())