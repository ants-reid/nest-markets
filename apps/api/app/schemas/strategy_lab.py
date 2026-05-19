"""Pydantic schemas for Strategy Lab (MH-06 data contracts, MH-07 replay, MH-08 simulation)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# ── MH-14A Research-only safety constants ─────────────────────────────────

_RESEARCH_WARNING_TEXT = (
    "Execution costs (spread, slippage, fees, and commissions) are modelled using "
    "research assumptions, not broker-confirmed live execution costs. Results "
    "remain research-only."
)
_COST_MODEL_NOTES = (
    "Spread, slippage, and commission are modelled using deterministic research "
    "assumptions. Cost profiles and stress presets are deterministic research "
    "assumptions and not broker-calibrated. Use conservative or stress profiles "
    "before considering any paper/live promotion."
)


class ResearchWarnings(BaseModel):
    """MH-14A: Research-only safety metadata attached to all Strategy Lab outputs.

    All fields are hard-coded to their conservative defaults until an
    execution-cost modelling phase explicitly promotes them.
    """

    research_only: bool = True
    execution_costs_modelled: bool = True
    spread_modelled: bool = True
    slippage_modelled: bool = True
    fees_modelled: bool = True
    live_ready: bool = False
    warning: str = _RESEARCH_WARNING_TEXT
    cost_model_version: str | None = "mh15c_v1"
    cost_model_status: str = "modelled"
    cost_model_notes: str = _COST_MODEL_NOTES


# ── Strategy Config ────────────────────────────────────────────────────────

class StrategyConfigCreateRequest(BaseModel):
    """Payload for creating a new strategy configuration."""

    name: str = Field(..., min_length=1, max_length=255)
    strategy_type: str = Field(..., min_length=1, max_length=100)
    asset: str = Field(..., min_length=1, max_length=50)
    timeframe: str = Field(..., min_length=1, max_length=10)
    parameters: dict[str, Any] = Field(default_factory=dict)
    risk_settings: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class StrategyConfigResponse(BaseModel):
    """Single strategy configuration."""

    id: UUID
    name: str
    strategy_type: str
    asset: str
    timeframe: str
    parameters: dict[str, Any]
    risk_settings: dict[str, Any]
    enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StrategyConfigListResponse(BaseModel):
    """Paginated list of strategy configurations."""

    total: int
    items: list[StrategyConfigResponse]


# ── Backtest Run ───────────────────────────────────────────────────────────

class BacktestRunCreateRequest(BaseModel):
    """Payload to queue a new backtest run stub."""

    name: str = Field(..., min_length=1, max_length=255)
    date_from: datetime
    date_to: datetime
    requested_assets: list[str] = Field(default_factory=list)
    requested_timeframes: list[str] = Field(default_factory=list)
    strategy_config_ids: list[str] = Field(default_factory=list)
    starting_capital: float = Field(default=10000.0, gt=0)
    allow_unapproved_data: bool = False


class BacktestRunResponse(BaseModel):
    """Single backtest run record."""

    id: UUID
    name: str
    status: str
    date_from: datetime
    date_to: datetime
    requested_assets: list[str] | dict[str, Any]
    requested_timeframes: list[str] | dict[str, Any]
    strategy_config_ids: list[str] | dict[str, Any]
    starting_capital: float
    result_summary: dict[str, Any] | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    message: str | None = None
    research_warnings: ResearchWarnings = Field(default_factory=ResearchWarnings)

    model_config = {"from_attributes": True}


class BacktestRunListResponse(BaseModel):
    """Paginated list of backtest runs."""

    total: int
    items: list[BacktestRunResponse]


# ── Mock Trades ────────────────────────────────────────────────────────────

class MockTradeResponse(BaseModel):
    """Single simulated trade (written by MH-07+ replay engine)."""

    id: UUID
    backtest_run_id: UUID
    strategy_config_id: UUID | None
    asset: str
    timeframe: str
    side: str
    entry_time: datetime
    entry_price: float
    stop_price: float | None
    target_price: float | None
    exit_time: datetime | None
    exit_price: float | None
    status: str
    result: str | None
    pnl_amount: float | None
    pnl_pct: float | None
    r_multiple: float | None
    reason_for_entry: str | None
    reason_for_exit: str | None
    metadata_json: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MockTradeListResponse(BaseModel):
    """Paginated list of mock trades."""

    total: int
    items: list[MockTradeResponse]


# ── Strategy Results ───────────────────────────────────────────────────────

class StrategyResultResponse(BaseModel):
    """Aggregate metrics for a strategy within a backtest run."""

    id: UUID
    backtest_run_id: UUID
    strategy_config_id: UUID | None
    asset: str | None
    timeframe: str | None
    total_trades: int
    wins: int
    losses: int
    breakeven: int
    win_rate: float | None
    average_win: float | None
    average_loss: float | None
    profit_factor: float | None
    expectancy: float | None
    total_return_pct: float | None
    max_drawdown_pct: float | None
    score: float | None
    metrics: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime
    research_warnings: ResearchWarnings = Field(default_factory=ResearchWarnings)

    model_config = {"from_attributes": True}


class StrategyResultListResponse(BaseModel):
    """Paginated list of strategy results."""

    total: int
    items: list[StrategyResultResponse]


# ── Equity Curve ───────────────────────────────────────────────────────────

class EquityCurvePointResponse(BaseModel):
    """Single equity snapshot from the replay engine."""

    id: UUID
    backtest_run_id: UUID
    timestamp: datetime
    equity: float
    cash: float | None
    open_pnl: float | None
    drawdown_pct: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


class EquityCurveResponse(BaseModel):
    """Time-ordered equity curve for one backtest run."""

    total: int
    items: list[EquityCurvePointResponse]


# ── Drawdown Periods ───────────────────────────────────────────────────────

class DrawdownPeriodResponse(BaseModel):
    """Single identified drawdown window from the replay engine."""

    id: UUID
    backtest_run_id: UUID
    start_time: datetime
    trough_time: datetime | None
    end_time: datetime | None
    max_drawdown_pct: float
    duration_candles: int | None
    recovered: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class DrawdownPeriodListResponse(BaseModel):
    """List of drawdown periods for one backtest run."""

    total: int
    items: list[DrawdownPeriodResponse]


# ── Replay (MH-07) ─────────────────────────────────────────────────────────

class ReplayAssetSummary(BaseModel):
    """Per-asset result from one replay pass."""

    asset: str
    timeframe: str
    candles_loaded: int
    approved: bool
    first_timestamp: datetime | None
    last_timestamp: datetime | None
    skipped: bool
    skip_reason: str | None


class BacktestReplayRequest(BaseModel):
    """Options for triggering a historical replay on a queued backtest run."""

    allow_unapproved_data: bool = False
    max_candles: int = Field(default=10000, gt=0)
    simulate_trades: bool = True
    clear_existing_results: bool = False


class BacktestReplayResponse(BaseModel):
    """Summary returned after a replay pass completes (or fails)."""

    backtest_run_id: UUID
    status: str
    total_candles_loaded: int
    total_mock_trades: int = 0
    assets_replayed: list[str]
    timeframes_replayed: list[str]
    skipped_assets: list[str]
    first_timestamp: datetime | None
    last_timestamp: datetime | None
    warnings: list[str]
    asset_summaries: list[ReplayAssetSummary]
    win_rate: float | None = None
    profit_factor: float | None = None
    max_drawdown_pct: float | None = None
    total_return_pct: float | None = None
    message: str
    research_warnings: ResearchWarnings = Field(default_factory=ResearchWarnings)


# ── Strategy Comparison (MH-10) ────────────────────────────────────────────

class StrategyComparisonRequest(BaseModel):
    """Request payload for a multi-config ma_momentum comparison run."""

    name: str = Field(..., min_length=1, max_length=255)
    asset: str = Field(..., min_length=1, max_length=50)
    timeframe: str = Field(..., min_length=1, max_length=10)
    date_from: datetime
    date_to: datetime
    starting_capital: float = Field(default=10000.0, gt=0)
    allow_unapproved_data: bool = False
    max_candles: int = Field(default=10000, gt=0)
    fast_windows: list[int] = Field(default=[3, 5, 10])
    slow_windows: list[int] = Field(default=[5, 10, 20])
    risk_rewards: list[float] = Field(default=[1.5, 2.0, 2.5])
    hold_bars_options: list[int] = Field(default=[3, 5, 10])
    risk_per_trade_pct_options: list[float] = Field(default=[0.5])
    max_configs: int = Field(default=30, gt=0, le=100)


class StrategyComparisonRow(BaseModel):
    """Single row in a strategy comparison result, representing one config."""

    strategy_config_id: UUID
    strategy_name: str
    backtest_run_id: UUID
    asset: str
    timeframe: str
    parameters: dict[str, Any]
    total_trades: int
    wins: int
    losses: int
    win_rate: float | None
    profit_factor: float | None
    expectancy: float | None
    total_return_pct: float | None
    max_drawdown_pct: float | None
    scoring_cost_scenario: str | None = None
    high_cost_scenario_net_return_pct: float | None = None
    high_cost_scenario_profit_factor: float | None = None
    cost_sensitivity_level: str | None = None
    quality_grade: str | None = None
    research_confidence_score: float | None = None
    overfitting_risk_score: float | None = None
    quality_warnings: list[str] = Field(default_factory=list)
    validation_stability_score: float | None = None
    validation_stability_grade: str | None = None
    out_of_sample_pass: bool | None = None
    walk_forward_warnings: list[str] = Field(default_factory=list)
    score: float
    rank: int


class StrategyComparisonResponse(BaseModel):
    """Response from a multi-config strategy comparison run."""

    backtest_run_id: UUID
    total_configs_tested: int
    asset: str
    timeframe: str
    cost_profile_used: str | None = None
    stress_preset_used: str | None = None
    broker_calibrated: bool = False
    rows: list[StrategyComparisonRow]
    warnings: list[str]
    message: str
    research_warnings: ResearchWarnings = Field(default_factory=ResearchWarnings)


class CostModelProfileResponse(BaseModel):
    """Read-only metadata for one research cost calibration profile."""

    profile_name: str
    profile_label: str
    profile_description: str
    profile_multiplier: float
    intended_use: str
    is_broker_calibrated: bool
    live_ready: bool


class CostModelProfileListResponse(BaseModel):
    """Read-only list of research calibration profiles."""

    total: int
    items: list[CostModelProfileResponse]


class CostModelStressPresetResponse(BaseModel):
    """Read-only metadata for one stress preset."""

    preset_name: str
    preset_label: str
    preset_description: str
    spread_multiplier: float
    slippage_multiplier: float
    commission_multiplier: float
    is_broker_calibrated: bool
    live_ready: bool


class CostModelStressPresetListResponse(BaseModel):
    """Read-only list of stress presets."""

    total: int
    items: list[CostModelStressPresetResponse]


class StrategyResultQualitySummaryResponse(BaseModel):
    """Read-only aggregate quality summary for one backtest run."""

    backtest_run_id: UUID
    total_strategies: int
    average_confidence: float
    grade_distribution: dict[str, int]
    highest_overfitting_risk: float
    warnings: list[str]
    paper_trade_ready: bool = False
    live_ready: bool = False


class WalkForwardSplitRequest(BaseModel):
    """Optional custom split percentages for walk-forward validation."""

    in_sample_pct: int = Field(default=60, ge=1, le=98)
    validation_pct: int = Field(default=20, ge=1, le=98)
    out_of_sample_pct: int = Field(default=20, ge=1, le=98)
    fold_count: int = Field(default=1, ge=1, le=12)


class WalkForwardDateSplit(BaseModel):
    """One labelled walk-forward date split."""

    period: str
    start: datetime
    end: datetime
    percentage: int


class WalkForwardPeriodMetrics(BaseModel):
    """Per-period deterministic strategy metrics for walk-forward analysis."""

    period: str
    total_trades: int
    win_rate: float | None
    net_profit_factor: float | None
    net_total_return_pct: float | None
    max_drawdown_pct: float | None
    research_confidence_score: float | None
    quality_grade: str | None


class WalkForwardWarning(BaseModel):
    """Warning emitted by walk-forward analysis."""

    message: str


class WalkForwardStrategyValidation(BaseModel):
    """Walk-forward validation output for one strategy config."""

    strategy_config_id: UUID | None
    strategy_name: str | None = None
    in_sample: WalkForwardPeriodMetrics
    validation: WalkForwardPeriodMetrics
    out_of_sample: WalkForwardPeriodMetrics
    folds: list[RollingFoldValidation] = Field(default_factory=list)
    in_sample_return: float
    validation_return: float
    out_of_sample_return: float
    out_of_sample_profit_factor: float
    return_degradation_pct: float
    profit_factor_degradation_pct: float
    confidence_degradation_pct: float
    validation_stability_score: float
    validation_stability_grade: str
    out_of_sample_pass: bool
    paper_trade_ready: bool = False
    live_ready: bool = False
    warnings: list[WalkForwardWarning]


class RollingFoldValidation(BaseModel):
    """One rolling fold validation result for a strategy."""

    fold_index: int
    splits: list[WalkForwardDateSplit]
    in_sample: WalkForwardPeriodMetrics
    validation: WalkForwardPeriodMetrics
    out_of_sample: WalkForwardPeriodMetrics
    validation_stability_score: float
    validation_stability_grade: str
    out_of_sample_pass: bool
    return_degradation_pct: float
    profit_factor_degradation_pct: float
    confidence_degradation_pct: float
    warnings: list[WalkForwardWarning]


class RollingWindowSummary(BaseModel):
    """Aggregate stability across rolling folds."""

    fold_count: int
    stable_fold_ratio: float
    average_validation_stability_score: float
    stability_dispersion: float
    average_return_degradation_pct: float
    average_confidence_degradation_pct: float
    rolling_validation_grade: str
    rolling_out_of_sample_pass: bool
    warnings: list[WalkForwardWarning]


class WalkForwardValidationResponse(BaseModel):
    """Backtest-level walk-forward validation summary response."""

    backtest_run_id: UUID
    splits: list[WalkForwardDateSplit]
    strategies: list[WalkForwardStrategyValidation]
    rolling_window_summary: RollingWindowSummary | None = None
    warnings: list[WalkForwardWarning]
    paper_trade_ready: bool = False
    live_ready: bool = False


# ── Strategy Comparison Dashboard / History (MH-11) ───────────────────────

class StrategyComparisonHistoryRow(BaseModel):
    """Compact summary row for one historical comparison/backtest run."""

    backtest_run_id: UUID
    name: str
    status: str
    date_from: datetime
    date_to: datetime
    requested_assets: list[str]
    requested_timeframes: list[str]
    starting_capital: float
    created_at: datetime
    completed_at: datetime | None
    total_configs_tested: int
    best_score: float | None
    best_asset: str | None
    best_timeframe: str | None
    best_strategy_config_id: UUID | None
    best_strategy_name: str | None
    best_parameters: dict[str, Any] | None
    best_total_trades: int | None
    best_win_rate: float | None
    best_profit_factor: float | None
    best_total_return_pct: float | None
    best_max_drawdown_pct: float | None


class StrategyComparisonHistoryResponse(BaseModel):
    """Paginated history list for Strategy Lab comparisons."""

    total: int
    items: list[StrategyComparisonHistoryRow]


class EquityCurveSummary(BaseModel):
    """Small summary payload for rendering equity mini-chart and key stats."""

    total_points: int
    start_equity: float | None
    end_equity: float | None
    peak_equity: float | None
    latest_drawdown_pct: float | None
    total_return_pct: float | None
    preview_points: list[float]


class DrawdownSummary(BaseModel):
    """Aggregate drawdown stats for one comparison run."""

    total_periods: int
    worst_drawdown_pct: float | None
    recovered_periods: int
    open_periods: int


class StrategyComparisonDetailResponse(BaseModel):
    """Detailed comparison payload for one historical backtest run."""

    backtest_run: BacktestRunResponse
    ranked_rows: list[StrategyComparisonRow]
    mock_trade_count: int
    equity_curve_summary: EquityCurveSummary
    drawdown_summary: DrawdownSummary
    warnings: list[str]
    research_label: str | None = None
    research_notes: str | None = None
    research_warnings: ResearchWarnings = Field(default_factory=ResearchWarnings)


class StrategyComparisonLabelRequest(BaseModel):
    """Manual research triage metadata for a historical comparison run."""

    research_label: str = Field(
        ...,
        pattern="^(watchlist_candidate|rejected|needs_more_testing)$",
    )
    research_notes: str = Field(default="", max_length=4000)


class StrategyComparisonLabelResponse(BaseModel):
    """Response after saving manual research metadata for a run."""

    backtest_run_id: UUID
    research_label: str
    research_notes: str
    updated: bool


# ── MH-14 AI Backtest Report ───────────────────────────────────────────────

AIReportFocus = str  # "balanced" | "risk" | "performance" | "overfitting"
AIReportStatus = str  # "completed" | "failed"


class AIBacktestReportRequest(BaseModel):
    """Request to generate an AI research report for a backtest run."""

    focus: AIReportFocus = Field(
        default="balanced",
        pattern="^(balanced|risk|performance|overfitting)$",
    )
    include_trade_samples: bool = False


class AIReportContent(BaseModel):
    """Structured AI report content returned from OpenAI."""

    plain_english_summary: str
    strongest_configs: list[str | dict[str, Any]]
    weak_configs: list[str | dict[str, Any]]
    overfitting_warnings: list[str]
    sample_size_warnings: list[str]
    risk_notes: list[str]
    data_quality_notes: list[str]
    recommended_next_tests: list[str]
    reject_or_continue: str  # "continue_testing" | "needs_more_data" | "reject_for_now"
    confidence_score: float


class AIBacktestReportResponse(BaseModel):
    """Single AI backtest report record."""

    id: UUID
    backtest_run_id: UUID | None
    report_type: str
    focus: str
    status: AIReportStatus
    model_name: str | None
    input_summary: dict[str, Any] | None
    report_json: dict[str, Any] | None
    plain_english_summary: str | None
    confidence_score: float | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    research_warnings: ResearchWarnings = Field(default_factory=ResearchWarnings)

    model_config = {"from_attributes": True}


class AIBacktestReportListResponse(BaseModel):
    """Paginated list of AI backtest reports for a run."""

    total: int
    items: list[AIBacktestReportResponse]


# ── MH-15 Baseline Candidate Manager ───────────────────────────────────────

BaselineCandidateStatus = str  # watchlist_candidate | baseline_candidate | rejected | needs_more_testing


class BaselineCandidateCreateRequest(BaseModel):
    """Create a research-stage baseline candidate from strategy comparison results."""

    backtest_run_id: str
    strategy_config_id: str
    ai_backtest_report_id: str | None = None
    status: BaselineCandidateStatus = Field(
        default="watchlist_candidate",
        pattern="^(watchlist_candidate|baseline_candidate|rejected|needs_more_testing)$",
    )
    review_notes: str | None = None
    created_by: str | None = None


class BaselineCandidateUpdateRequest(BaseModel):
    """Patch candidate status and review notes."""

    status: BaselineCandidateStatus | None = Field(
        default=None,
        pattern="^(watchlist_candidate|baseline_candidate|rejected|needs_more_testing)$",
    )
    review_notes: str | None = None
    reviewed_by: str | None = None


class BaselineCandidateRejectRequest(BaseModel):
    """Reject a candidate with reviewer metadata."""

    reviewed_by: str | None = None
    review_notes: str | None = None


class BaselineCandidateResponse(BaseModel):
    """Single baseline candidate row."""

    id: UUID
    backtest_run_id: UUID | None
    strategy_config_id: UUID | None
    ai_backtest_report_id: UUID | None
    asset: str
    timeframe: str
    strategy_type: str
    parameters: dict[str, Any]
    metrics: dict[str, Any]
    status: BaselineCandidateStatus
    review_notes: str | None
    created_by: str | None
    reviewed_by: str | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BaselineCandidateListResponse(BaseModel):
    """Paginated list of baseline candidates."""

    total: int
    items: list[BaselineCandidateResponse]


# ── MH-16 Paper Validation Gate ────────────────────────────────────────────

PaperValidationStatus = str  # pending | active | passed | failed | stopped


class PaperValidationPlanCreateRequest(BaseModel):
    """Create paper validation requirements from a baseline candidate."""

    baseline_candidate_id: str
    required_trades: int = Field(default=100, ge=1)
    minimum_days: int = Field(default=30, ge=1)
    target_profit_factor: float | None = Field(default=None, ge=0)
    max_drawdown_pct: float | None = None
    max_daily_loss_pct: float | None = None
    starting_paper_capital: float = Field(default=200000, gt=0)
    created_by: str | None = None
    review_notes: str | None = None


class PaperValidationPlanUpdateRequest(BaseModel):
    """Update validation requirements/notes and optional manual paper metrics."""

    status: PaperValidationStatus | None = Field(
        default=None,
        pattern="^(pending|active|passed|failed|stopped)$",
    )
    required_trades: int | None = Field(default=None, ge=1)
    minimum_days: int | None = Field(default=None, ge=1)
    target_profit_factor: float | None = Field(default=None, ge=0)
    max_drawdown_pct: float | None = None
    max_daily_loss_pct: float | None = None
    starting_paper_capital: float | None = Field(default=None, gt=0)
    paper_metrics: dict[str, Any] | None = None
    reviewed_by: str | None = None
    review_notes: str | None = None


class PaperValidationPlanActionRequest(BaseModel):
    """Optional reviewer metadata for start/stop actions."""

    reviewed_by: str | None = None
    review_notes: str | None = None


class PaperValidationEventResponse(BaseModel):
    """Single plan event for timeline/audit display."""

    id: UUID
    paper_validation_plan_id: UUID
    event_type: str
    message: str
    payload: dict[str, Any] | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PaperValidationProgressResponse(BaseModel):
    """Computed progress and deterministic pass/fail determination."""

    total_paper_trades: int
    wins: int
    losses: int
    win_rate: float | None
    profit_factor: float | None
    total_return_pct: float | None
    max_drawdown_pct: float | None
    days_active: int
    progress_trades_pct: float
    progress_days_pct: float
    pass_fail_status: str
    reasons: list[str]


class PaperValidationPlanResponse(BaseModel):
    """Single paper validation plan row."""

    id: UUID
    baseline_candidate_id: UUID
    backtest_run_id: UUID | None
    strategy_config_id: UUID | None
    status: PaperValidationStatus
    required_trades: int
    minimum_days: int
    target_profit_factor: float | None
    max_drawdown_pct: float | None
    max_daily_loss_pct: float | None
    starting_paper_capital: float
    backtest_metrics: dict[str, Any] | None
    paper_metrics: dict[str, Any] | None
    progress: dict[str, Any] | None
    pass_fail_reasons: list[str] | dict[str, Any] | None
    started_at: datetime | None
    completed_at: datetime | None
    created_by: str | None
    reviewed_by: str | None
    review_notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaperValidationPlanListResponse(BaseModel):
    """Paginated list of paper validation plans."""

    total: int
    items: list[PaperValidationPlanResponse]


# ── MH-17 Paper Validation Evidence / Reconciliation ───────────────────────

class PaperValidationEvidenceResponse(BaseModel):
    """Single evidence record."""

    id: UUID
    paper_validation_plan_id: UUID
    source_type: str
    source_id: UUID | None
    confidence: str
    asset: str | None
    timeframe: str | None
    side: str | None
    opened_at: datetime | None
    closed_at: datetime | None
    entry_price: float | None
    exit_price: float | None
    pnl_amount: float | None
    pnl_pct: float | None
    r_multiple: float | None
    result: str
    payload: dict[str, Any] | None
    notes: str | None
    included_in_metrics: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaperValidationEvidenceListResponse(BaseModel):
    """List of evidence records for a plan."""

    total: int
    items: list[PaperValidationEvidenceResponse]


class PaperValidationManualEvidenceRequest(BaseModel):
    """Add a manual evidence record to a plan."""

    asset: str | None = None
    timeframe: str | None = None
    side: str | None = None
    opened_at: datetime | None = None
    closed_at: datetime | None = None
    entry_price: float | None = None
    exit_price: float | None = None
    pnl_amount: float | None = None
    pnl_pct: float | None = None
    r_multiple: float | None = None
    result: str = Field(
        default="unknown",
        pattern="^(win|loss|breakeven|open|unknown)$",
    )
    notes: str | None = None
    payload: dict[str, Any] | None = None
    included_in_metrics: bool = True


class PaperValidationReconcileRequest(BaseModel):
    """Request to reconcile existing paper execution records into evidence."""

    dry_run: bool = False
    asset_filter: str | None = None
    timeframe_filter: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None


class PaperValidationReconcileResponse(BaseModel):
    """Result of a reconciliation run."""

    evidence_created: int
    evidence_skipped: int
    matched_source: str
    warnings: list[str]
    dry_run: bool


# ── MH-18: Dashboard & Readiness Review ────────────────────────────────────


class PaperValidationMetricDeltas(BaseModel):
    """Metric differences between backtest and paper."""

    profit_factor_delta: float | None = None
    total_return_delta: float | None = None
    max_drawdown_delta: float | None = None
    win_rate_delta: float | None = None


class PaperValidationEvidenceSummary(BaseModel):
    """Summary of evidence collected for a plan."""

    total_evidence: int = 0
    included_evidence: int = 0
    excluded_evidence: int = 0
    manual_evidence_count: int = 0
    reconciled_evidence_count: int = 0
    high_confidence_count: int = 0
    medium_confidence_count: int = 0
    low_confidence_count: int = 0


class PaperValidationDashboardResponse(BaseModel):
    """Summary dashboard for all paper validation plans."""

    total_plans: int = 0
    pending_count: int = 0
    active_count: int = 0
    passed_count: int = 0
    failed_count: int = 0
    stopped_count: int = 0
    ready_for_review_count: int = 0
    average_progress_trades_pct: float = 0.0
    average_progress_days_pct: float = 0.0
    plans_needing_evidence: int = 0
    plans_with_low_confidence: int = 0
    plans_breaching_thresholds: int = 0
    recently_updated_plans: list[dict[str, Any]] = []
    warnings: list[str] = []


class PaperValidationReadinessResponse(BaseModel):
    """Readiness review for a single paper validation plan."""

    plan_id: UUID
    baseline_candidate_id: UUID
    status: str
    readiness_status: str  # not_started|collecting_evidence|ready_for_review|passed|failed|stopped
    readiness_score: int  # 0-100
    readiness_notes: str = ""
    progress_summary: dict[str, Any]
    backtest_metrics: dict[str, Any] | None = None
    paper_metrics: dict[str, Any] | None = None
    metric_deltas: PaperValidationMetricDeltas
    evidence_summary: PaperValidationEvidenceSummary
    warnings: list[str] = []
    suggested_next_action: str  # keep_collecting|review_candidate|reject_candidate|investigate_data|stop_validation
    recent_events: list[PaperValidationEventResponse] = []
