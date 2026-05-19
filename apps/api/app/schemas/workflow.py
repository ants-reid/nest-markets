"""Pydantic request and response schemas for the workflow endpoint."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RiskContextRequest(BaseModel):
    """Risk evaluation context supplied by the caller."""

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
    requested_execution_mode: Literal["paper", "confirm_live", "auto_live"]


class SignalInputRequest(BaseModel):
    """Signal generation inputs supplied by the caller."""

    model_config = ConfigDict(extra="forbid")

    asset: str = Field(min_length=1, max_length=20)
    timeframe: Literal["15m", "1h", "4h", "1d"]
    latest_price: float = Field(gt=0, lt=10_000_000, description="Current market price")
    feature_snapshot: dict[str, Any] = Field(default_factory=dict)
    catalyst_context: dict[str, Any] = Field(default_factory=dict)
    risk_notes: str | None = None


class LiveExecutionResultResponse(BaseModel):
    """Scaffold live execution result, always disabled in MVP."""

    model_config = ConfigDict(extra="forbid")

    accepted: bool
    status: str
    reason: str


class WorkflowRunRequest(BaseModel):
    """Full workflow run request combining signal inputs and risk context."""

    model_config = ConfigDict(extra="forbid")

    signal_input: SignalInputRequest
    risk_context: RiskContextRequest
    # Temporary MVP wiring: when True, skips the real LLM and returns a
    # deterministic flat signal so routes are testable without OpenAI calls.
    use_mock_signal: bool = False


class WorkflowRunResponse(BaseModel):
    """Typed workflow run result returned to the caller."""

    model_config = ConfigDict(extra="forbid")

    signal_id: UUID
    risk_approved: bool
    selected_execution_mode: str
    approval_request_id: UUID | None
    paper_execution_id: UUID | None
    blocked_reasons: list[str]
    live_execution_result: LiveExecutionResultResponse | None
