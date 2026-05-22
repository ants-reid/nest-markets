"""Pydantic request and response schemas for execution endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.signal import SignalResponse


class PaperExecutionRequest(BaseModel):
    """API request schema for paper execution simulation."""

    model_config = ConfigDict(extra="forbid")

    signal: SignalResponse
    allowed_risk_amount: float = Field(gt=0, le=100_000, description="Allowable risk in account currency")
    latest_price: float = Field(gt=0, lt=10_000_000, description="Current market price")


class PaperExecutionResponse(BaseModel):
    """API response schema for paper execution results."""

    model_config = ConfigDict(extra="forbid")

    execution_id: UUID
    status: str
    asset: str
    timeframe: str
    side: str
    qty: float
    notional: float
    stop_price: float
    target_price: float
    fill_price: float
    reason: str | None = None
    execution_source: str = "internal_mock_simulator"
    balance_source: str = "app_simulated"
    fees_source: str = "estimated"
    fills_source: str = "simulated"


class LiveExecutionRequestSchema(BaseModel):
    """API request schema for scaffolded live execution submission."""

    model_config = ConfigDict(extra="forbid")

    asset: str = Field(min_length=1, max_length=20)
    side: str = Field(pattern="^(long|short|buy|sell)$")
    qty: float = Field(gt=0, le=1_000_000)
    notional: float = Field(gt=0, le=100_000_000)
    stop_price: float = Field(gt=0, lt=10_000_000)
    target_price: float = Field(gt=0, lt=10_000_000)


class LiveExecutionResponse(BaseModel):
    """API response schema for disabled live execution results."""

    model_config = ConfigDict(extra="forbid")

    accepted: bool
    status: str
    reason: str
    processed_at: datetime
    execution_source: str = "ibkr_live_locked"
    balance_source: str = "ibkr_live_locked"
    fees_source: str = "unavailable"
    fills_source: str = "unavailable"
