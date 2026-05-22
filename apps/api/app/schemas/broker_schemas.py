"""Pydantic schemas for broker endpoint requests/responses."""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class BrokerModeSchema(BaseModel):
    """Broker mode status — surfaces paper/live isolation state."""
    broker: str
    mode: str
    live_execution_enabled: bool
    paper_trading_enabled: bool


class BrokerHealthSchema(BaseModel):
    """Runtime health check for the IBKR broker setup.

    status values:
      paper_ready       — all checks pass; ready to accept paper orders
    live_ready        — live config is coherent and gateway is reachable
      paper_config_only — mode guard OK but gateway not yet reachable (not started)
    live_config_only  — live config is coherent but gateway not yet reachable
      misconfigured     — live-mode config detected; orders will be rejected
    """
    status: str
    mode_guard_ok: bool
    gateway_reachable: bool
    gateway_url: str
    account_id: str
    account_is_paper: bool
    broker_mode: BrokerModeSchema


class SeriousPaperRouteCheckResponseSchema(BaseModel):
    """Read-only routing decision for intentional serious-paper workflows."""

    requested_mode: str = "serious_paper"
    resolved_execution_source: Optional[str] = None
    resolved_route: Optional[str] = None
    simulator_route: str = "/execution/paper"
    simulator_allowed_for_serious_paper: bool = False
    broker_account_mode_required: str = "paper"
    current_broker_account_mode: str
    can_route_to_broker_paper: bool
    blocked_reason: Optional[str] = None
    live_state: str = "ibkr_live_locked"
    would_block: bool
    is_submit: bool = False
    next_required_action: str
    serious_paper_source: str = "ibkr_paper"
    canonical_paper_route: str = "/broker/orders"
    broker_mode: BrokerModeSchema


class PaperRecommendationRouteCheckResponseSchema(BaseModel):
    """Read-only recommendation route-check result for manual serious-paper review."""

    recommendation_id: UUID
    recommendation_status: str
    ticker: Optional[str] = None
    side: Optional[str] = None
    quantity: Optional[float] = None
    order_type: Optional[str] = None
    limit_price: Optional[float] = None
    estimated_notional: Optional[float] = None
    risk_score: Optional[float] = None
    route_check_status: str
    resolved_route: Optional[str] = None
    resolved_execution_source: Optional[str] = None
    execution_source: str = "recommendation_route_check"
    serious_paper_source: str = "ibkr_paper"
    is_canonical_paper: bool = False
    broker_account_mode: str
    live_state: str = "ibkr_live_locked"
    would_block: bool
    blocked_reason: Optional[str] = None
    missing_data: list[str] = Field(default_factory=list)
    next_required_action: str
    is_submit: bool = False
    workers_allowed_to_submit: bool = False
    live_trading_enabled: bool = False
    canonical_paper_route: str = "/broker/orders"
    broker_mode: BrokerModeSchema


class PaperRecommendationBrokerDryRunPreviewResponseSchema(BaseModel):
    """Guarded dry-run preview for a persisted recommendation.

    This surface is recommendation-owned, never submits, and only executes the
    existing broker dry-run path when the recommendation first passes the
    read-only serious-paper route-check.
    """

    recommendation_id: UUID
    recommendation_status: str
    ticker: Optional[str] = None
    side: Optional[str] = None
    quantity: Optional[float] = None
    order_type: Optional[str] = None
    limit_price: Optional[float] = None
    estimated_notional: Optional[float] = None
    risk_score: Optional[float] = None
    route_check_status: str
    dry_run_status: str
    dry_run_only: bool = True
    dry_run_executed: bool = False
    allowed_to_submit: Optional[bool] = None
    resolved_route: Optional[str] = None
    resolved_execution_source: Optional[str] = None
    dry_run_execution_source: Optional[str] = None
    balance_source: Optional[str] = None
    fees_source: Optional[str] = None
    fills_source: Optional[str] = None
    positions_source: Optional[str] = None
    serious_paper_source: str = "ibkr_paper"
    is_canonical_paper: bool = False
    broker_account_mode: str
    live_state: str = "ibkr_live_locked"
    would_block: bool
    blocked_reason: Optional[str] = None
    missing_data: list[str] = Field(default_factory=list)
    next_required_action: str
    is_submit: bool = False
    workers_allowed_to_submit: bool = False
    live_trading_enabled: bool = False
    canonical_paper_route: str = "/broker/orders"
    broker_mode: BrokerModeSchema
    mode_guard_ok: Optional[bool] = None
    request_valid: Optional[bool] = None
    issues: list[OrderDryRunIssueSchema] = Field(default_factory=list)
    warnings: list[OrderDryRunIssueSchema] = Field(default_factory=list)
    preflight_decision: Optional[OrderDryRunPreflightDecisionSchema] = None
    preflight_context: Optional[OrderDryRunPreflightContextSchema] = None
    paper_path_note: Optional[str] = None


class OrderRequestSchema(BaseModel):
    """Request body for submitting an order."""
    ticker: str
    side: str  # "BUY" | "SELL"
    quantity: float
    order_type: str  # "MARKET" | "LIMIT" | "STOP" | "STOP_LIMIT" | "TRAIL"
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    tif: str = "DAY"  # time-in-force
    outside_rth: bool = False
    client_order_id: Optional[str] = None


class OrderResultSchema(BaseModel):
    """Response body after order submission."""
    broker_order_id: str
    status: str  # "SUBMITTED" | "FILLED" | "REJECTED" | "CANCELLED"
    filled_price: Optional[float] = None
    filled_quantity: Optional[float] = None
    error_message: Optional[str] = None
    broker_mode: Optional[BrokerModeSchema] = None
    execution_source: str = "ibkr_paper"
    balance_source: str = "ibkr_paper"
    fees_source: str = "ibkr_reported"
    fills_source: str = "ibkr_paper"
    positions_source: str = "ibkr_paper"
    serious_paper_source: str = "ibkr_paper"
    is_canonical_paper: bool = True
    canonical_paper_route: str = "/broker/orders"
    broker_account_mode: str = "paper"
    live_state: str = "ibkr_live_locked"
    paper_path_note: str = "IBKR paper is the canonical serious paper trading path."


class OrderDryRunIssueSchema(BaseModel):
    """Single validation/guard issue found during order dry-run."""

    code: str
    message: str
    severity: str | None = None
    source: str | None = None
    enforcement_enabled: bool | None = None


class OrderPreflightDecisionItemSchema(BaseModel):
    """One classified preflight finding for future enforcement planning."""

    code: str
    message: str
    severity: str | None = None
    source: str | None = None
    enforcement_enabled: bool
    classification: str  # advisory | would_block | blocking


class OrderDryRunPreflightDecisionSchema(BaseModel):
    """Structured preflight decision view derived from dry-run findings.

    This is additive to the existing dry-run `status` and does not alter submit or
    execution behavior in MH-77.
    """

    decision_status: str  # allowed | advisory | would_block | blocked
    submit_gate: str  # not_applied
    advisory_count: int
    would_block_count: int
    blocking_count: int
    advisory_items: list[OrderPreflightDecisionItemSchema] = Field(default_factory=list)
    would_block_items: list[OrderPreflightDecisionItemSchema] = Field(default_factory=list)
    blocking_items: list[OrderPreflightDecisionItemSchema] = Field(default_factory=list)


class RiskLimitSnapshotSchema(BaseModel):
    """Compact snapshot of the active risk limit config for advisory dry-run context."""

    scope: Optional[str] = None
    trading_mode: Optional[str] = None
    max_order_notional: Optional[float] = None
    daily_loss_limit_amount: Optional[float] = None
    daily_loss_limit_pct: Optional[float] = None
    max_open_positions: Optional[int] = None
    max_total_exposure: Optional[float] = None
    max_symbol_exposure: Optional[float] = None
    max_trades_per_day: Optional[int] = None
    min_cash_buffer: Optional[float] = None


class OrderDryRunPreflightContextSchema(BaseModel):
    """Rich preflight portfolio/account context snapshot returned with dry-run result.

    All fields are optional — only populated when caller supplies portfolio context
    or when a risk limit config is active in the DB.
    """

    cash_balance: Optional[float] = None
    buying_power: Optional[float] = None
    open_position_count: Optional[int] = None
    current_symbol_exposure: Optional[float] = None
    estimated_post_trade_symbol_exposure: Optional[float] = None
    current_total_exposure: Optional[float] = None
    estimated_post_trade_total_exposure: Optional[float] = None
    daily_pnl: Optional[float] = None
    daily_loss: Optional[float] = None
    risk_limit_snapshot: Optional[RiskLimitSnapshotSchema] = None


class OrderDryRunResultSchema(BaseModel):
    """Dry-run verification result for broker order submission.

    status values:
      ready   — paper-mode guard passes and request is valid
      invalid — request fails schema/business validation
      blocked — live-execution guard trips; order would be rejected
    """

    status: str
    mode_guard_ok: bool
    request_valid: bool
    estimated_notional: Optional[float] = None
    issues: list[OrderDryRunIssueSchema]
    warnings: list[OrderDryRunIssueSchema] = Field(default_factory=list)
    preflight_decision: OrderDryRunPreflightDecisionSchema
    preflight_context: Optional[OrderDryRunPreflightContextSchema] = None
    broker_mode: BrokerModeSchema
    execution_source: str = "broker_dry_run"
    balance_source: str = "ibkr_paper"
    fees_source: str = "pending_broker_report"
    fills_source: str = "pending_broker_fill"
    positions_source: str = "ibkr_paper"
    serious_paper_source: str = "ibkr_paper"
    is_canonical_paper: bool = True
    canonical_paper_route: str = "/broker/orders"
    broker_account_mode: str = "paper"
    live_state: str = "ibkr_live_locked"
    paper_path_note: str = "Dry-run validates the IBKR paper submit path without placing an order."


class OrderDryRunRequestSchema(OrderRequestSchema):
    """Extended dry-run request body — order fields plus optional portfolio context.

    The portfolio context fields are caller-supplied account/position state used to
    compute post-trade exposure estimates and enrich advisory warnings.  They never
    affect dry-run ``status``; they are advisory only.
    """

    cash_balance: Optional[float] = None
    buying_power: Optional[float] = None
    open_position_count: Optional[int] = None
    current_symbol_exposure: Optional[float] = None
    current_total_exposure: Optional[float] = None
    daily_pnl: Optional[float] = None
    daily_loss: Optional[float] = None


class BrokerOrderAuditEntrySchema(BaseModel):
    """One append-only broker order audit event."""

    ts: str
    event: str
    action: str
    ticker: str
    side: str
    quantity: Optional[float] = None
    status: str
    broker_order_id: Optional[str] = None
    reason: Optional[str] = None
    dry_run: bool = False
    issues: list[dict] = Field(default_factory=list)


class BrokerOrderAuditTrailSchema(BaseModel):
    """Recent broker order audit events."""

    entries: list[BrokerOrderAuditEntrySchema]


class AccountInfoSchema(BaseModel):
    """Account balance summary."""
    net_liquidation: float
    cash_balance: float
    buying_power: float
    currency: str = "USD"
    excess_liquidity: float = 0.0
    margin: float = 0.0
    unrealized_pnl: float = 0.0
    broker_mode: Optional[BrokerModeSchema] = None
    execution_source: str = "ibkr_paper"
    balance_source: str = "ibkr_paper"
    fees_source: str = "ibkr_reported"
    fills_source: str = "ibkr_paper"
    positions_source: str = "ibkr_paper"
    serious_paper_source: str = "ibkr_paper"
    is_canonical_paper: bool = True
    canonical_paper_route: str = "/broker/orders"
    broker_account_mode: str = "paper"
    live_state: str = "ibkr_live_locked"
    paper_path_note: str = "IBKR paper is the canonical serious paper trading path."


class PositionInfoSchema(BaseModel):
    """Single open position."""
    conid: int
    ticker: str
    side: str  # "BUY" | "SELL"
    quantity: float
    avg_cost: float
    market_price: Optional[float] = None
    market_value: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    asset_class: str = "STK"
    currency: str = "USD"
    execution_source: str = "ibkr_paper"
    balance_source: str = "ibkr_paper"
    fees_source: str = "ibkr_reported"
    fills_source: str = "ibkr_paper"
    positions_source: str = "ibkr_paper"
    serious_paper_source: str = "ibkr_paper"
    is_canonical_paper: bool = True
    canonical_paper_route: str = "/broker/orders"
    broker_account_mode: str = "paper"
    live_state: str = "ibkr_live_locked"
    paper_path_note: str = "IBKR paper is the canonical serious paper trading path."


class PositionMismatchSchema(BaseModel):
    """Position reconciliation mismatch detail."""
    expected: str
    actual: str
    delta: str


class ReconciliationReportSchema(BaseModel):
    """Position reconciliation report."""
    matched_count: int
    mismatch_count: int
    mismatches: dict[str, PositionMismatchSchema]
    actual_positions: list[dict]  # List of position dicts


class TradingControlSchema(BaseModel):
    """Mode-aware trading control state for MH-36B."""

    trading_mode: str
    execution_control: str
    arming_state: str
    live_order_submission_allowed: bool
    paper_order_submission_allowed: bool
    auto_trading_allowed: bool
    emergency_stop_active: bool
    reasons: list[str] = Field(default_factory=list)


class BrokerDailyPnlSchema(BaseModel):
    """Daily P&L summary derived from today's pnl_snapshots rows (MH-43).

    Calculation rules:
    - ``closed_pnl``  — sum of closed_pnl from all rows where snapshot_ts >= UTC midnight today.
    - ``open_pnl``    — open_pnl from the most-recent row today (point-in-time mark-to-market).
    - ``total_pnl``   — closed_pnl + open_pnl (null when both are absent).
    - ``daily_pnl``   — same as total_pnl; primary field consumed by dry-run context.
    - ``daily_loss``  — abs(daily_pnl) when daily_pnl < 0, otherwise 0.0.
    - ``snapshot_count`` — number of pnl_snapshot rows found for today.
    - When no rows exist all numeric fields are None and note explains the absence.
    """

    date: str                               # ISO date string e.g. "2026-04-28"
    daily_pnl: Optional[float] = None       # total intraday P&L (closed + open)
    daily_loss: Optional[float] = None      # positive magnitude of loss (0 when profitable)
    closed_pnl: Optional[float] = None      # sum of realised fills today
    open_pnl: Optional[float] = None        # latest unrealised mark-to-market
    total_pnl: Optional[float] = None       # closed_pnl + open_pnl
    latest_snapshot_ts: Optional[str] = None  # ISO timestamp of most recent row
    snapshot_count: int = 0
    source: str = "pnl_snapshots"
    note: Optional[str] = None


class BrokerPnlSnapshotCaptureSchema(BaseModel):
    """Response body for MH-46A pnl snapshot ingestion capture endpoint."""

    snapshot_ts: str
    equity: Optional[float] = None
    cash: Optional[float] = None
    gross_exposure: Optional[float] = None
    net_exposure: Optional[float] = None
    open_pnl: Optional[float] = None
    closed_pnl: Optional[float] = None
    closed_pnl_source: Optional[str] = None
    source: str = "manual"
    account_id: Optional[str] = None
    broker_mode: Optional[BrokerModeSchema] = None
    position_count: int = 0


class BrokerTradeNormalizationResultSchema(BaseModel):
    """Summary response for broker trade/fill normalization ingestion (MH-47)."""

    received: int = 0
    inserted: int = 0
    skipped: int = 0
    source: str = "broker_account_trades"
    account_id: Optional[str] = None
    broker_mode: Optional[BrokerModeSchema] = None
    note: Optional[str] = None


class NormalizedBrokerTradeEventSchema(BaseModel):
    """Single normalized broker trade/fill event for provenance audit reads."""

    event_fingerprint: str
    external_trade_id: Optional[str] = None
    broker_order_id: Optional[str] = None
    symbol: Optional[str] = None
    side: Optional[str] = None
    quantity: Optional[float] = None
    fill_price: Optional[float] = None
    commission: Optional[float] = None
    net_amount: Optional[float] = None
    realized_pnl: Optional[float] = None
    trade_ts: Optional[str] = None
    source: str
    account_id: Optional[str] = None
    broker_provider: str
    created_at: str


class BrokerTradeEventAuditTrailSchema(BaseModel):
    """Readback payload for normalized broker trade/fill provenance audit (MH-47B)."""

    entries: list[NormalizedBrokerTradeEventSchema]
    returned: int
    account_id: Optional[str] = None
    broker_mode: Optional[BrokerModeSchema] = None
