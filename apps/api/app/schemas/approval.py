"""Pydantic request and response schemas for approval endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.signal import SignalResponse
from app.services.execution_mode_service import ExecutionModeType


class ApprovalCreateRequest(BaseModel):
    """API request schema for approval request creation."""

    model_config = ConfigDict(extra="forbid")

    signal: SignalResponse
    execution_mode: ExecutionModeType
    risk_approved: bool = Field(default=False)
    ttl_minutes: int = Field(default=30, gt=0)


class ApprovalRequestResponse(BaseModel):
    """API response schema for approval requests."""

    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    status: str
    created_at: datetime
    expires_at: datetime
    asset: str
    timeframe: str
    execution_mode: str
