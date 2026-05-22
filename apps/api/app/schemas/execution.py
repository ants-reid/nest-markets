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
    positions_source: str = "app_db_simulated"
    serious_paper_source: str = "ibkr_paper"
    is_canonical_paper: bool = False
    canonical_paper_route: str = "/broker/orders"
    broker_account_mode: str = "simulator"
    live_state: str = "ibkr_live_locked"
    paper_path_note: str = (
        "Internal simulator path only. Use IBKR paper broker routes for serious paper validation."
    )
    simulator_warning: str = (
        "Internal simulator only. This is not the canonical IBKR paper proving path."
    )


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
    positions_source: str = "ibkr_live_locked"
    serious_paper_source: str = "ibkr_paper"
    is_canonical_paper: bool = False
    canonical_paper_route: str = "/broker/orders"
    broker_account_mode: str = "live"
    live_state: str = "ibkr_live_locked"
    paper_path_note: str = "Live trading remains locked in this phase."
