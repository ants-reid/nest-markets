"""Pydantic request and response schemas for risk endpoints."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.signal import SignalResponse
from app.services.execution_mode_service import ExecutionModeType


class RiskContextRequest(BaseModel):
    """API request schema for deterministic risk context."""

    model_config = ConfigDict(extra="forbid")

    spread_bps: float = Field(ge=0)
    daily_drawdown_pct: float = Field(ge=0)
    consecutive_losses: int = Field(ge=0)
    minutes_since_last_loss: int | None = Field(default=None, ge=0)
    correlated_exposure_count: int = Field(ge=0)
    open_positions_count: int = Field(default=0, ge=0)
    session_allowed: bool = True
    kill_switch_active: bool = False
    market_quality_flag: bool
    account_equity: float = Field(ge=0)
    requested_execution_mode: ExecutionModeType


class RiskEvaluateRequest(BaseModel):
    """API request schema for risk evaluation."""

    model_config = ConfigDict(extra="forbid")

    signal: SignalResponse
    risk_context: RiskContextRequest


class RiskDecisionResponse(BaseModel):
    """API response schema for deterministic risk decisions."""

    model_config = ConfigDict(extra="forbid")

    approved: bool
    blocked_reasons: list[str]
    allowed_risk_amount: float
    selected_execution_mode: str
