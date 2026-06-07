"""Market data routes — status, worker trigger, scheduler control, and kill-switch."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models.bar import Bar
from app.db.models.asset import Asset
from app.db.models.news_article import NewsArticle
from app.db.models.risk_profile import RiskProfile
from app.db.session import get_db_session
from app.services import audit_log_service
from app.schemas.broker_schemas import (
    BrokerHealthSchema,
    BrokerModeSchema,
    OrderDryRunPreflightDecisionSchema,
    TradingControlSchema,
)
from app.schemas.risk_limits import RiskLimitStatusResponse
from app.schemas.trading_halt import TradingHaltStatusResponse
from app.services.broker_mode_guard import (
    check_ibkr_gateway,
    get_broker_mode_metadata,
    is_live_mode_enabled,
    is_paper_account_id,
)
from app.services.broker_service import BrokerService
from app.services.risk_limit_service import RiskLimitService
from app.services.paper_candidate_hygiene_service import PaperCandidateHygieneService
from app.services.paper_candidate_refresh_service import PaperCandidateRefreshService
from app.services.trading_control_arming_state_service import TradingControlArmingStateService
from app.services.trading_control_service import (
    TradingControlMisconfiguredError,
    assert_mode_configuration_consistent,
    get_trading_mode,
)
from app.services.trading_halt_service import TradingHaltService
from app.services.worker_run_log_service import (
    WorkerRunLogService,
    build_auto_paper_run_entry,
    extract_auto_paper_outcome_counts,
)
from app.workers.auto_paper_trader_worker import AutoPaperTraderWorker
from app.workers.data_sync_worker import DataSyncWorker

_run_log = WorkerRunLogService()

router = APIRouter(prefix="/market-data", tags=["market-data"])


class IngestStatusItem(BaseModel):
    """Last ingest timestamp for one asset/timeframe combination."""

    asset_symbol: str
    timeframe: str
    last_bar_ts: datetime | None
    bar_count: int


class MarketDataStatusResponse(BaseModel):
    """Response payload for GET /market-data/status."""

    items: list[IngestStatusItem]


class WorkerResultResponse(BaseModel):
    """Response payload for POST /market-data/sync."""

    worker_name: str
    status: str
    message: str
    started_at: datetime
    finished_at: datetime


class CandidateRefreshItemResponse(BaseModel):
    """One candidate refresh action record."""

    symbol: str
    action: str
    reason: str
    signal_id: str | None = None


class CandidateRefreshResponse(BaseModel):
    """Response payload for paper candidate refresh endpoint."""

    created_count: int
    skipped_count: int
    dry_run: bool
    candidates: list[CandidateRefreshItemResponse]


class CandidateHygieneCandidateResponse(BaseModel):
    """One affected candidate returned by hygiene scan."""

    signal_id: str
    symbol: str
    provider_name: str | None = None
    signal_status: str
    scan_ts: str | None = None
    signal_score: float
    reasons: list[str]


class CandidateHygieneResponse(BaseModel):
    """Response payload for paper candidate hygiene endpoint."""

    dry_run: bool
    apply: bool
    stale_count: int
    duplicate_count: int
    outside_allowlist_count: int
    would_update_count: int
    updated_count: int
    recommendations: list[str]
    affected_candidates: list[CandidateHygieneCandidateResponse]


class AutoPaperOutcomeCounts(BaseModel):
    """Structured outcome counts for one auto-paper worker run."""

    accepted_count: int = 0
    rejected_count: int = 0
    cancelled_count: int = 0
    blocked_count: int = 0
    risk_blocked_count: int = 0
    gate_blocked_count: int = 0
    skipped_cap_count: int = 0
    legacy_broker_rejected_count: int = 0


class NewsArticleResponse(BaseModel):
    """News feed item returned by the market data route."""

    id: Any
    headline: str
    source_name: str | None
    published_at: datetime
    url: str | None
    tickers: list[str]


class MarketDataBarResponse(BaseModel):
    """OHLCV bar item for charting."""

    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float | None


class MarketDataBarsPayload(BaseModel):
    """Historical bars payload for one symbol/timeframe."""

    asset_symbol: str
    timeframe: str
    items: list[MarketDataBarResponse]


@router.get("/status", response_model=MarketDataStatusResponse)
def get_market_data_status(
    session: Annotated[Session, Depends(get_db_session)],
) -> MarketDataStatusResponse:
    """Return the last ingest timestamp and bar count per asset/timeframe."""
    rows = (
        session.query(
            Asset.symbol,
            Bar.timeframe,
            func.max(Bar.ts).label("last_bar_ts"),
            func.count(Bar.id).label("bar_count"),
        )
        .join(Asset, Bar.asset_id == Asset.id)
        .group_by(Asset.symbol, Bar.timeframe)
        .order_by(Asset.symbol, Bar.timeframe)
        .all()
    )
    items = [
        IngestStatusItem(
            asset_symbol=r.symbol,
            timeframe=r.timeframe,
            last_bar_ts=r.last_bar_ts,
            bar_count=r.bar_count,
        )
        for r in rows
    ]
    return MarketDataStatusResponse(items=items)


@router.get("/bars/{asset_symbol}", response_model=MarketDataBarsPayload)
def get_market_data_bars(
    asset_symbol: str,
    session: Annotated[Session, Depends(get_db_session)],
    timeframe: str = "1h",
    limit: int = 120,
) -> MarketDataBarsPayload:
    """Return recent OHLCV bars for one asset symbol/timeframe."""
    safe_limit = max(5, min(limit, 500))
    stmt = (
        select(Bar)
        .join(Asset, Bar.asset_id == Asset.id)
        .where(Asset.symbol == asset_symbol.upper(), Bar.timeframe == timeframe)
        .order_by(Bar.ts.desc())
        .limit(safe_limit)
    )
    rows = session.execute(stmt).scalars().all()
    rows.reverse()

    return MarketDataBarsPayload(
        asset_symbol=asset_symbol.upper(),
        timeframe=timeframe,
        items=[
            MarketDataBarResponse(
                ts=row.ts,
                open=float(row.open),
                high=float(row.high),
                low=float(row.low),
                close=float(row.close),
                volume=float(row.volume) if row.volume is not None else None,
            )
            for row in rows
        ],
    )


@router.post("/sync", response_model=WorkerResultResponse)
def trigger_data_sync() -> WorkerResultResponse:
    """Manually trigger the DataSyncWorker and return its result."""
    worker = DataSyncWorker()
    result = worker.run()
    return WorkerResultResponse(
        worker_name=result.worker_name,
        status=result.status,
        message=result.message,
        started_at=result.started_at,
        finished_at=result.finished_at,
    )


@router.post("/auto-paper/run", response_model=WorkerResultResponse)
def trigger_auto_paper_trader(source: str = "manual") -> WorkerResultResponse:
    """Manually trigger one auto-paper batch execution cycle and persist the result."""
    worker = AutoPaperTraderWorker()
    result = worker.run()
    _run_log.append(build_auto_paper_run_entry(result, source=source))
    return WorkerResultResponse(
        worker_name=result.worker_name,
        status=result.status,
        message=result.message,
        started_at=result.started_at,
        finished_at=result.finished_at,
    )


@router.post("/auto-paper/candidates/refresh", response_model=CandidateRefreshResponse)
def refresh_auto_paper_candidates(
    session: Annotated[Session, Depends(get_db_session)],
    dry_run: bool = False,
) -> CandidateRefreshResponse:
    """Refresh paper-only candidates for allowlisted symbols when queue is empty."""
    settings = get_settings()
    if settings.broker_mode.lower() != "paper":
        raise HTTPException(
            status_code=409,
            detail="Candidate refresh is allowed only when BROKER_MODE is paper.",
        )
    if settings.live_execution_enabled:
        raise HTTPException(
            status_code=409,
            detail="Candidate refresh is blocked while LIVE_EXECUTION_ENABLED is true.",
        )
    if not settings.auto_paper_enabled:
        raise HTTPException(
            status_code=409,
            detail="Candidate refresh requires AUTO_PAPER_ENABLED=true.",
        )

    symbols = [
        symbol.strip().upper()
        for symbol in settings.auto_paper_symbol_allowlist.split(",")
        if symbol and symbol.strip()
    ]

    service = PaperCandidateRefreshService(session=session)
    result = service.refresh(symbols=symbols, dry_run=dry_run)

    if not dry_run and result["created_count"] > 0:
        session.commit()

    return CandidateRefreshResponse(
        created_count=int(result["created_count"]),
        skipped_count=int(result["skipped_count"]),
        dry_run=bool(dry_run),
        candidates=[CandidateRefreshItemResponse(**item) for item in result["candidates"]],
    )


@router.post("/auto-paper/candidates/hygiene", response_model=CandidateHygieneResponse)
def maintain_auto_paper_candidate_hygiene(
    session: Annotated[Session, Depends(get_db_session)],
    dry_run: bool = True,
    apply: bool = False,
    max_age_hours: int | None = None,
    keep_per_symbol: int = 1,
) -> CandidateHygieneResponse:
    """Dry-run/apply paper candidate queue hygiene for paper-test candidate rows."""
    settings = get_settings()
    if settings.broker_mode.lower() != "paper":
        raise HTTPException(
            status_code=409,
            detail="Candidate hygiene is allowed only when BROKER_MODE is paper.",
        )
    if settings.live_execution_enabled:
        raise HTTPException(
            status_code=409,
            detail="Candidate hygiene is blocked while LIVE_EXECUTION_ENABLED is true.",
        )
    if not settings.auto_paper_enabled:
        raise HTTPException(
            status_code=409,
            detail="Candidate hygiene requires AUTO_PAPER_ENABLED=true.",
        )
    if apply and dry_run:
        raise HTTPException(
            status_code=409,
            detail="Set dry_run=false when apply=true.",
        )

    symbols = [
        symbol.strip().upper()
        for symbol in settings.auto_paper_symbol_allowlist.split(",")
        if symbol and symbol.strip()
    ]

    service = PaperCandidateHygieneService(session=session)
    result = service.run(
        dry_run=dry_run,
        apply=apply,
        max_age_hours=max_age_hours,
        keep_per_symbol=keep_per_symbol,
        allowlist_symbols=symbols,
    )

    if apply and not dry_run and result["updated_count"] > 0:
        session.commit()

    return CandidateHygieneResponse(
        dry_run=bool(result["dry_run"]),
        apply=bool(result["apply"]),
        stale_count=int(result["stale_count"]),
        duplicate_count=int(result["duplicate_count"]),
        outside_allowlist_count=int(result["outside_allowlist_count"]),
        would_update_count=int(result["would_update_count"]),
        updated_count=int(result["updated_count"]),
        recommendations=list(result["recommendations"]),
        affected_candidates=[CandidateHygieneCandidateResponse(**item) for item in result["affected_candidates"]],
    )


# ---------------------------------------------------------------------------
# Run history
# ---------------------------------------------------------------------------


class RunHistoryEntry(BaseModel):
    """One auto-paper run log entry."""

    worker_name: str
    status: str
    message: str
    started_at: str
    finished_at: str
    source: str
    outcome_counts: AutoPaperOutcomeCounts


class AutoPaperHistorySummary(BaseModel):
    """Aggregated summary over filtered auto-paper history entries."""

    total_runs: int
    manual_run_count: int
    scheduled_run_count: int
    success_run_count: int
    error_run_count: int
    accepted_total: int
    rejected_total: int
    cancelled_total: int
    blocked_total: int
    risk_blocked_total: int
    gate_blocked_total: int
    latest_run_started_at: str | None


class AutoPaperHistoryExportFilters(BaseModel):
    """Applied filters for one auto-paper history export payload."""

    limit: int
    source: Literal["manual", "scheduled"] | None
    outcome: Literal["accepted", "rejected", "cancelled", "blocked"] | None
    started_after: datetime | None
    started_before: datetime | None


class AutoPaperHistoryExportPayload(BaseModel):
    """Read-only export bundle for filtered auto-paper history data."""

    exported_at: datetime
    filters: AutoPaperHistoryExportFilters
    summary: AutoPaperHistorySummary
    entries: list[RunHistoryEntry]


class AutoPaperHistoryRetentionMetadata(BaseModel):
    """Read-only retention metadata for the auto-paper history log."""

    storage_backend: str
    trim_on_append: bool
    max_entries: int
    current_entry_count: int
    entries_remaining: int
    utilization_pct: float
    warning_threshold_pct: float
    near_capacity: bool
    retention_status: Literal["ok", "near_capacity"]
    retention_warning: str | None
    retained_span_hours: float | None
    average_entries_per_day: float | None
    estimated_days_until_capacity: float | None
    retention_trend_status: Literal["insufficient_data", "growing"]
    log_exists: bool
    oldest_started_at: str | None
    latest_started_at: str | None


class AutoPaperSharedPreflightPosture(BaseModel):
    """Read-only view of the shared paper preflight seam used by broker submit."""

    status: str
    mode_guard_ok: bool
    request_valid: bool
    estimated_notional: float | None
    preflight_decision: OrderDryRunPreflightDecisionSchema
    broker_mode: BrokerModeSchema


class AutoPaperHistoryReadinessPosture(BaseModel):
    """Recent history and retention posture for auto-paper readiness review."""

    window_limit: int
    latest_run: RunHistoryEntry | None
    summary: AutoPaperHistorySummary
    retention: AutoPaperHistoryRetentionMetadata


class AutoPaperReadinessResponse(BaseModel):
    """Composed read-only readiness contract for the auto-paper safety surface."""

    status: Literal["blocked", "warning", "ready"]
    ready_for_auto_submit: bool
    blocking_reasons: list[str]
    warning_reasons: list[str]
    broker_control: TradingControlSchema
    broker_health: BrokerHealthSchema
    scheduler: "SchedulerJobStatus"
    shared_paper_preflight: AutoPaperSharedPreflightPosture
    recent_history: AutoPaperHistoryReadinessPosture


class AutoPaperEnablementPreconditionsResponse(BaseModel):
    """Read-only pre-enable checklist surface for future paper auto trading review."""

    status: Literal["blocked", "warning", "ready"]
    enableable: bool
    blockers: list[str]
    warnings: list[str]
    satisfied_checks: list[str]
    missing_checks: list[str]
    supporting_routes: dict[str, str]
    checked_at: datetime
    broker_control: TradingControlSchema
    broker_health: BrokerHealthSchema
    trading_halt: TradingHaltStatusResponse
    risk_limits: RiskLimitStatusResponse
    scheduler: "SchedulerJobStatus"
    shared_paper_preflight: AutoPaperSharedPreflightPosture
    recent_history: AutoPaperHistoryReadinessPosture


# Long-term API vocabulary for the enablement-preconditions surface.
# Treat these codes as contract-level identifiers once published.
_AUTO_PAPER_ENABLEMENT_BLOCKER_CODE_DESCRIPTIONS = {
    "trading_mode_not_paper": "Paper trading mode is not configured for the current broker control state.",
    "paper_order_submission_disabled": "Paper order submission is not currently allowed by trading control.",
    "auto_trading_disabled_by_trading_control": "Auto trading remains disabled by the trading control guard.",
    "live_trading_enabled": "Live trading is still enabled and must remain blocked for paper-auto pre-enable review.",
    "broker_mode_misconfigured": "Broker mode guard configuration is inconsistent.",
    "broker_gateway_unreachable": "Broker gateway reachability is not healthy enough for enablement review.",
    "ibkr_account_not_paper": "Configured IBKR account does not look like a paper account.",
    "active_trading_halt": "An active trading halt is still in force.",
    "shared_paper_preflight_blocking_findings": "The shared paper preflight seam is already returning blocking findings.",
}

_AUTO_PAPER_ENABLEMENT_WARNING_CODE_DESCRIPTIONS = {
    "risk_limits_not_configured": "No paper risk-limit configuration is currently present.",
    "risk_limit_coverage_incomplete": "Risk-limit configuration exists but does not cover the full expected paper checklist.",
    "auto_paper_scheduler_paused": "The auto-paper scheduler exists but is currently paused.",
    "auto_paper_scheduler_missing": "The auto-paper scheduler job is not currently registered.",
    "auto_paper_scheduler_scheduler_unavailable": "The scheduler runtime is not currently available.",
    "shared_paper_preflight_would_block_findings": "The shared paper preflight seam shows would-block findings that still need review.",
    "shared_paper_preflight_advisory_findings": "The shared paper preflight seam shows advisory findings that still need review.",
    "history_retention_near_capacity": "The retained auto-paper history window is nearing capacity.",
    "history_log_not_initialized": "The retained auto-paper history log has not been initialized yet.",
    "no_recent_auto_paper_history": "There is no recent retained auto-paper run history yet.",
}

_AUTO_PAPER_ENABLEMENT_CHECK_CODE_DESCRIPTIONS = {
    "paper_mode_configured": "Broker control is configured for paper trading mode.",
    "paper_order_submission_available": "Paper order submission is currently allowed by trading control.",
    "auto_trading_control_allows_enablement": "Trading control would allow auto trading if all other prerequisites were satisfied.",
    "live_trading_disabled": "Live trading remains disabled.",
    "broker_mode_guard_consistent": "Broker mode guard configuration is internally consistent.",
    "broker_gateway_reachable": "The configured broker gateway is reachable.",
    "paper_account_configured": "The configured IBKR account looks like a paper account.",
    "trading_halt_clear": "No active global trading halt is present.",
    "risk_limits_configured": "At least one active paper risk-limit configuration is present.",
    "risk_limit_coverage_complete": "The current paper risk-limit configuration covers the expected checklist fields.",
    "auto_paper_scheduler_running": "The auto-paper scheduler job is present and running.",
    "shared_paper_preflight_clear": "The shared paper preflight seam currently reports no blocking or advisory findings.",
    "history_retention_has_headroom": "The retained auto-paper history window still has capacity headroom.",
    "history_log_initialized": "The retained auto-paper history log exists.",
    "recent_auto_paper_history_present": "There is recent retained auto-paper run history to inspect.",
}


_AUTO_PAPER_ENABLEMENT_SUPPORTING_ROUTES = {
    "readiness": "/market-data/auto-paper/readiness",
    "broker_control": "/broker/control",
    "broker_health": "/broker/health",
    "trading_halt": "/trading/halt/status?scope=global",
    "risk_limits": "/risk/limits/status?trading_mode=paper",
    "shared_paper_preflight": "/broker/orders/dry-run",
    "scheduler": "/market-data/auto-paper/scheduler/status",
    "history": "/market-data/auto-paper/history",
    "history_summary": "/market-data/auto-paper/history/summary",
    "history_retention": "/market-data/auto-paper/history/retention",
    "history_export": "/market-data/auto-paper/history/export",
}

_AUTO_PAPER_ARMING_AUDIT_EVENT_TYPE = "auto_paper_arming_action"
_AUTO_PAPER_ARMING_MAX_SNAPSHOT_AGE = timedelta(minutes=5)
_AUTO_PAPER_ARMING_FAILURE_CODE_DESCRIPTIONS = {
    "enablement_preconditions_not_ready": "The recomputed enablement-preconditions contract is not ready for arming.",
    "enablement_snapshot_stale": "The operator-supplied enablement snapshot is stale or no longer matches current backend posture.",
    "auto_paper_already_armed": "The auto-paper arming surface is already in the armed state.",
    "durable_arming_state_write_failed": "The durable arming-state write failed, so the arming mutation was rejected fail-closed.",
    "auto_trading_still_disabled": "Trading control still reports auto trading as disabled.",
    "trading_mode_not_paper": "Trading mode is not paper.",
    "live_trading_not_disabled": "Live trading is not fully disabled.",
    "active_trading_halt": "A global trading halt is active.",
    "shared_preflight_not_clear": "The shared paper preflight seam is not clear.",
    "operator_reason_required": "A non-empty arming reason is required.",
    "requested_by_required": "A non-empty requested_by value is required.",
}

_AUTO_PAPER_DISARM_FAILURE_CODE_DESCRIPTIONS = {
    "already_disarmed": "The auto-paper arming surface is already in the disarmed state.",
    "durable_state_missing": "No durable arming-state row found; cannot safely disarm.",
    "durable_state_duplicate": "Duplicate durable arming-state rows detected; cannot safely disarm.",
    "durable_state_invalid": "The durable arming-state row is in an invalid state; cannot safely disarm.",
    "durable_arming_state_read_failed": "A DB exception prevented reading the current arming state.",
    "durable_arming_state_write_failed": "The durable disarm-state write failed; the disarm mutation was rejected fail-closed.",
    "operator_reason_required": "A non-empty disarm reason is required.",
    "requested_by_required": "A non-empty requested_by value is required.",
}


class AutoPaperArmingRequest(BaseModel):
    """Operator arming request for the future paper auto-trading surface."""

    requested_by: str
    reason: str
    expected_enablement_checked_at: datetime
    expected_enablement_status: Literal["ready"]
    expected_blockers: list[str] = Field(default_factory=list)
    expected_warnings: list[str] = Field(default_factory=list)
    acknowledged_warning_codes: list[str] = Field(default_factory=list)
    client_request_id: str | None = None


class AutoPaperArmingResponse(BaseModel):
    """Controlled arming mutation result for the auto-paper surface."""

    status: Literal["armed", "rejected"]
    arming_state: Literal["armed", "disarmed"]
    evaluated_at: datetime
    failure_reasons: list[str]
    warning_codes: list[str]
    enablement_snapshot: AutoPaperEnablementPreconditionsResponse
    audit_recorded: bool
    audit_event_type: str
    requested_by: str
    reason: str
    client_request_id: str | None


class AutoPaperArmingAuditSummaryResponse(BaseModel):
    """Safe provenance summary of the latest arming audit event."""

    event_type: str
    recorded_at: datetime | None
    action: str | None
    result_status: str | None
    requested_by: str | None
    reason: str | None
    client_request_id: str | None
    arming_state_before: str | None
    arming_state_after: str | None
    failure_reasons: list[str]
    warning_codes: list[str]


class AutoPaperArmingReadbackResponse(BaseModel):
    """Read-only operator diagnostic readback for durable auto-paper arming posture."""

    status: Literal["armed", "disarmed", "fail_closed"]
    arming_state: Literal["armed", "disarmed"]
    scope: str
    trading_mode: str
    evaluated_at: datetime
    fail_closed_reason: str | None
    durable_row_present: bool
    duplicate_rows_detected: bool
    stored_state: str | None
    armed_at: datetime | None
    armed_by: str | None
    arm_reason: str | None
    expires_at: datetime | None
    expired: bool
    last_enablement_checked_at: datetime | None
    last_enablement_status: str | None
    last_enablement_blockers: list[str]
    last_enablement_warnings: list[str]
    client_request_id: str | None
    disarmed_at: datetime | None
    disarmed_by: str | None
    disarm_reason: str | None
    last_audit: AutoPaperArmingAuditSummaryResponse | None


class AutoPaperDisarmRequest(BaseModel):
    """Operator disarm request for the paper auto-trading arming surface."""

    requested_by: str
    reason: str
    client_request_id: str | None = None


class AutoPaperDisarmResponse(BaseModel):
    """Controlled disarm mutation result for the auto-paper arming surface."""

    status: Literal["disarmed", "rejected"]
    arming_state: Literal["armed", "disarmed"]
    evaluated_at: datetime
    failure_reasons: list[str]
    audit_recorded: bool
    audit_event_type: str
    requested_by: str
    reason: str
    client_request_id: str | None


def _matches_outcome_filter(counts: AutoPaperOutcomeCounts, outcome: str | None) -> bool:
    if outcome is None:
        return True
    if outcome == "accepted":
        return counts.accepted_count > 0
    if outcome == "rejected":
        return counts.rejected_count > 0
    if outcome == "cancelled":
        return counts.cancelled_count > 0
    if outcome == "blocked":
        return counts.blocked_count > 0
    return False


def _get_filtered_auto_paper_history_entries(
    *,
    limit: int,
    source: Literal["manual", "scheduled"] | None,
    outcome: Literal["accepted", "rejected", "cancelled", "blocked"] | None,
    started_after: datetime | None,
    started_before: datetime | None,
) -> list[RunHistoryEntry]:
    entries = _run_log.recent(limit=max(1, min(limit, 200)))
    filtered_entries: list[RunHistoryEntry] = []
    for e in entries:
        started_at = datetime.fromisoformat(e.started_at)
        outcome_counts = (
            AutoPaperOutcomeCounts(**e.outcome_counts)
            if e.outcome_counts is not None
            else AutoPaperOutcomeCounts(**extract_auto_paper_outcome_counts(e.message))
        )

        if source is not None and e.source != source:
            continue
        if started_after is not None and started_at < started_after:
            continue
        if started_before is not None and started_at > started_before:
            continue
        if not _matches_outcome_filter(outcome_counts, outcome):
            continue

        filtered_entries.append(
            RunHistoryEntry(
                worker_name=e.worker_name,
                status=e.status,
                message=e.message,
                started_at=e.started_at,
                finished_at=e.finished_at,
                source=e.source,
                outcome_counts=outcome_counts,
            )
        )

    return filtered_entries


def _build_auto_paper_history_summary(entries: list[RunHistoryEntry]) -> AutoPaperHistorySummary:
    latest_run_started_at = entries[0].started_at if entries else None
    return AutoPaperHistorySummary(
        total_runs=len(entries),
        manual_run_count=sum(1 for entry in entries if entry.source == "manual"),
        scheduled_run_count=sum(1 for entry in entries if entry.source == "scheduled"),
        success_run_count=sum(1 for entry in entries if entry.status == "ok"),
        error_run_count=sum(1 for entry in entries if entry.status != "ok"),
        accepted_total=sum(entry.outcome_counts.accepted_count for entry in entries),
        rejected_total=sum(entry.outcome_counts.rejected_count for entry in entries),
        cancelled_total=sum(entry.outcome_counts.cancelled_count for entry in entries),
        blocked_total=sum(entry.outcome_counts.blocked_count for entry in entries),
        risk_blocked_total=sum(entry.outcome_counts.risk_blocked_count for entry in entries),
        gate_blocked_total=sum(entry.outcome_counts.gate_blocked_count for entry in entries),
        latest_run_started_at=latest_run_started_at,
    )


def _build_auto_paper_history_readiness_posture(*, window_limit: int = 20) -> AutoPaperHistoryReadinessPosture:
    entries = _get_filtered_auto_paper_history_entries(
        limit=window_limit,
        source=None,
        outcome=None,
        started_after=None,
        started_before=None,
    )
    return AutoPaperHistoryReadinessPosture(
        window_limit=window_limit,
        latest_run=entries[0] if entries else None,
        summary=_build_auto_paper_history_summary(entries),
        retention=AutoPaperHistoryRetentionMetadata(**_run_log.get_retention_metadata()),
    )


def _build_auto_paper_shared_preflight_posture() -> AutoPaperSharedPreflightPosture:
    result = BrokerService().dry_run_order(
        SimpleNamespace(
            ticker="AAPL",
            side="BUY",
            quantity=Decimal("1"),
            order_type="LIMIT",
            limit_price=Decimal("100"),
            stop_price=None,
            tif="DAY",
            outside_rth=False,
            client_order_id=None,
        )
    )
    return AutoPaperSharedPreflightPosture(
        status=result["status"],
        mode_guard_ok=result["mode_guard_ok"],
        request_valid=result["request_valid"],
        estimated_notional=result["estimated_notional"],
        preflight_decision=OrderDryRunPreflightDecisionSchema(**result["preflight_decision"]),
        broker_mode=BrokerModeSchema(**result["broker_mode"]),
    )


def _build_auto_paper_broker_control() -> TradingControlSchema:
    trading_state = get_trading_mode()
    return TradingControlSchema(
        trading_mode=trading_state.trading_mode,
        execution_control=trading_state.execution_control,
        arming_state=trading_state.arming_state,
        live_order_submission_allowed=trading_state.live_order_submission_allowed,
        paper_order_submission_allowed=trading_state.paper_order_submission_allowed,
        auto_trading_allowed=trading_state.auto_trading_allowed,
        emergency_stop_active=trading_state.emergency_stop_active,
        reasons=list(trading_state.reasons),
    )


async def _build_auto_paper_broker_health() -> BrokerHealthSchema:
    settings = get_settings()
    mode_guard_ok = True
    try:
        assert_mode_configuration_consistent()
    except TradingControlMisconfiguredError:
        mode_guard_ok = False

    gateway_reachable = await check_ibkr_gateway(settings.ibkr_gateway_url, timeout=5.0)
    account_id = settings.ibkr_account_id or ""
    live_enabled = is_live_mode_enabled()
    if not mode_guard_ok:
        health_status = "misconfigured"
    elif live_enabled:
        health_status = "live_ready" if gateway_reachable else "live_config_only"
    else:
        health_status = "paper_ready" if gateway_reachable else "paper_config_only"

    diagnostics = BrokerService().get_runtime_diagnostics()
    return BrokerHealthSchema(
        status=health_status,
        mode_guard_ok=mode_guard_ok,
        gateway_reachable=gateway_reachable,
        gateway_url=settings.ibkr_gateway_url,
        account_id=account_id,
        account_is_paper=is_paper_account_id(account_id),
        broker_mode=BrokerModeSchema(**get_broker_mode_metadata()),
        tws_runtime_client_id=diagnostics.get("tws_runtime_client_id"),
        tws_connection_state=diagnostics.get("tws_connection_state"),
        tws_last_error_code=diagnostics.get("tws_last_error_code"),
        tws_last_error_message=diagnostics.get("tws_last_error_message"),
    )


def _build_auto_paper_readiness_findings(
    *,
    broker_control: TradingControlSchema,
    broker_health: BrokerHealthSchema,
    scheduler: "SchedulerJobStatus",
    shared_paper_preflight: AutoPaperSharedPreflightPosture,
    recent_history: AutoPaperHistoryReadinessPosture,
) -> tuple[list[str], list[str]]:
    blocking_reasons: list[str] = []
    warning_reasons: list[str] = []

    if not broker_control.auto_trading_allowed:
        blocking_reasons.append("auto_trading_disabled_by_trading_control")

    if broker_health.status == "misconfigured":
        blocking_reasons.append("broker_mode_misconfigured")
    elif not broker_health.gateway_reachable:
        blocking_reasons.append("broker_gateway_unreachable")

    if not broker_health.account_is_paper:
        blocking_reasons.append("ibkr_account_not_paper")

    if scheduler.state == "scheduler_unavailable":
        blocking_reasons.append("auto_paper_scheduler_unavailable")
    elif scheduler.state == "missing":
        blocking_reasons.append("auto_paper_scheduler_missing")
    elif scheduler.state == "paused":
        blocking_reasons.append("auto_paper_scheduler_paused")

    if shared_paper_preflight.preflight_decision.blocking_count > 0:
        blocking_reasons.append("shared_paper_preflight_blocking_findings")

    if shared_paper_preflight.preflight_decision.would_block_count > 0:
        warning_reasons.append("shared_paper_preflight_would_block_findings")

    if recent_history.retention.near_capacity:
        warning_reasons.append("history_retention_near_capacity")

    if not recent_history.retention.log_exists:
        warning_reasons.append("history_log_not_initialized")

    if recent_history.summary.total_runs == 0:
        warning_reasons.append("no_recent_auto_paper_history")

    return blocking_reasons, warning_reasons


def _build_auto_paper_enablement_findings(
    *,
    broker_control: TradingControlSchema,
    broker_health: BrokerHealthSchema,
    trading_halt: TradingHaltStatusResponse,
    risk_limits: RiskLimitStatusResponse,
    scheduler: "SchedulerJobStatus",
    shared_paper_preflight: AutoPaperSharedPreflightPosture,
    recent_history: AutoPaperHistoryReadinessPosture,
) -> tuple[list[str], list[str], list[str], list[str]]:
    blockers: list[str] = []
    warnings: list[str] = []
    satisfied_checks: list[str] = []
    missing_checks: list[str] = []

    if broker_control.trading_mode == "paper":
        satisfied_checks.append("paper_mode_configured")
    else:
        blockers.append("trading_mode_not_paper")
        missing_checks.append("paper_mode_configured")

    if broker_control.paper_order_submission_allowed:
        satisfied_checks.append("paper_order_submission_available")
    else:
        blockers.append("paper_order_submission_disabled")
        missing_checks.append("paper_order_submission_available")

    if broker_control.auto_trading_allowed:
        satisfied_checks.append("auto_trading_control_allows_enablement")
    else:
        blockers.append("auto_trading_disabled_by_trading_control")
        missing_checks.append("auto_trading_control_allows_enablement")

    if not broker_control.live_order_submission_allowed and not broker_health.broker_mode.live_execution_enabled:
        satisfied_checks.append("live_trading_disabled")
    else:
        blockers.append("live_trading_enabled")
        missing_checks.append("live_trading_disabled")

    if broker_health.mode_guard_ok:
        satisfied_checks.append("broker_mode_guard_consistent")
    else:
        blockers.append("broker_mode_misconfigured")
        missing_checks.append("broker_mode_guard_consistent")

    if broker_health.gateway_reachable:
        satisfied_checks.append("broker_gateway_reachable")
    else:
        blockers.append("broker_gateway_unreachable")
        missing_checks.append("broker_gateway_reachable")

    if broker_health.account_is_paper:
        satisfied_checks.append("paper_account_configured")
    else:
        blockers.append("ibkr_account_not_paper")
        missing_checks.append("paper_account_configured")

    if trading_halt.emergency_stop_active:
        blockers.append("active_trading_halt")
        missing_checks.append("trading_halt_clear")
    else:
        satisfied_checks.append("trading_halt_clear")

    if risk_limits.risk_limits_configured:
        satisfied_checks.append("risk_limits_configured")
    else:
        warnings.append("risk_limits_not_configured")
        missing_checks.append("risk_limits_configured")

    if risk_limits.missing_limits:
        warnings.append("risk_limit_coverage_incomplete")
        missing_checks.append("risk_limit_coverage_complete")
    else:
        satisfied_checks.append("risk_limit_coverage_complete")

    if scheduler.state == "running":
        satisfied_checks.append("auto_paper_scheduler_running")
    else:
        warnings.append(f"auto_paper_scheduler_{scheduler.state}")
        missing_checks.append("auto_paper_scheduler_running")

    if shared_paper_preflight.preflight_decision.blocking_count > 0:
        blockers.append("shared_paper_preflight_blocking_findings")
        missing_checks.append("shared_paper_preflight_clear")
    elif shared_paper_preflight.preflight_decision.would_block_count > 0:
        warnings.append("shared_paper_preflight_would_block_findings")
        missing_checks.append("shared_paper_preflight_clear")
    elif shared_paper_preflight.preflight_decision.advisory_count > 0:
        warnings.append("shared_paper_preflight_advisory_findings")
        missing_checks.append("shared_paper_preflight_clear")
    else:
        satisfied_checks.append("shared_paper_preflight_clear")

    if recent_history.retention.near_capacity:
        warnings.append("history_retention_near_capacity")
        missing_checks.append("history_retention_has_headroom")
    else:
        satisfied_checks.append("history_retention_has_headroom")

    if recent_history.retention.log_exists:
        satisfied_checks.append("history_log_initialized")
    else:
        warnings.append("history_log_not_initialized")
        missing_checks.append("history_log_initialized")

    if recent_history.summary.total_runs > 0:
        satisfied_checks.append("recent_auto_paper_history_present")
    else:
        warnings.append("no_recent_auto_paper_history")
        missing_checks.append("recent_auto_paper_history_present")

    return (
        list(dict.fromkeys(blockers)),
        list(dict.fromkeys(warnings)),
        list(dict.fromkeys(satisfied_checks)),
        list(dict.fromkeys(missing_checks)),
    )


async def _build_auto_paper_enablement_preconditions_response(
    *,
    request: Request,
    session: Session,
    checked_at: datetime | None = None,
) -> AutoPaperEnablementPreconditionsResponse:
    broker_control = _build_auto_paper_broker_control()
    broker_health = await _build_auto_paper_broker_health()
    trading_halt = TradingHaltService(session).get_status(scope="global")
    risk_limits = RiskLimitService(session).get_status(trading_mode="paper")
    scheduler = get_scheduler_status(request)
    shared_paper_preflight = _build_auto_paper_shared_preflight_posture()
    recent_history = _build_auto_paper_history_readiness_posture()
    blockers, warnings, satisfied_checks, missing_checks = _build_auto_paper_enablement_findings(
        broker_control=broker_control,
        broker_health=broker_health,
        trading_halt=trading_halt,
        risk_limits=risk_limits,
        scheduler=scheduler,
        shared_paper_preflight=shared_paper_preflight,
        recent_history=recent_history,
    )

    if blockers:
        status: Literal["blocked", "warning", "ready"] = "blocked"
    elif warnings:
        status = "warning"
    else:
        status = "ready"

    return AutoPaperEnablementPreconditionsResponse(
        status=status,
        enableable=status == "ready",
        blockers=blockers,
        warnings=warnings,
        satisfied_checks=satisfied_checks,
        missing_checks=missing_checks,
        supporting_routes=dict(_AUTO_PAPER_ENABLEMENT_SUPPORTING_ROUTES),
        checked_at=checked_at or datetime.now(timezone.utc),
        broker_control=broker_control,
        broker_health=broker_health,
        trading_halt=trading_halt,
        risk_limits=risk_limits,
        scheduler=scheduler,
        shared_paper_preflight=shared_paper_preflight,
        recent_history=recent_history,
    )


def _get_auto_paper_arming_surface_state(session: Session) -> Literal["armed", "disarmed"]:
    state = TradingControlArmingStateService(session).get_effective_state(
        scope="auto_paper",
        trading_mode="paper",
    )
    return "armed" if state == "armed" else "disarmed"


def _get_auto_paper_arming_expiry(evaluated_at: datetime) -> datetime:
    # Use a day-bounded UTC expiry until a session-aware market-calendar seam exists.
    return (evaluated_at + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)


def _build_auto_paper_arming_failure_reasons(
    *,
    body: AutoPaperArmingRequest,
    enablement_snapshot: AutoPaperEnablementPreconditionsResponse,
    arming_state_before: Literal["armed", "disarmed"],
    evaluated_at: datetime,
) -> list[str]:
    failure_reasons: list[str] = []

    if not body.requested_by.strip():
        failure_reasons.append("requested_by_required")
    if not body.reason.strip():
        failure_reasons.append("operator_reason_required")

    if arming_state_before == "armed":
        failure_reasons.append("auto_paper_already_armed")

    if (
        body.expected_enablement_status != enablement_snapshot.status
        or body.expected_blockers != enablement_snapshot.blockers
        or body.expected_warnings != enablement_snapshot.warnings
        or body.expected_enablement_checked_at > evaluated_at
        or evaluated_at - body.expected_enablement_checked_at > _AUTO_PAPER_ARMING_MAX_SNAPSHOT_AGE
    ):
        failure_reasons.append("enablement_snapshot_stale")

    if not enablement_snapshot.enableable or enablement_snapshot.status != "ready":
        failure_reasons.append("enablement_preconditions_not_ready")

    if not enablement_snapshot.broker_control.auto_trading_allowed:
        failure_reasons.append("auto_trading_still_disabled")
    if enablement_snapshot.broker_control.trading_mode != "paper":
        failure_reasons.append("trading_mode_not_paper")
    if (
        enablement_snapshot.broker_control.live_order_submission_allowed
        or enablement_snapshot.broker_health.broker_mode.live_execution_enabled
    ):
        failure_reasons.append("live_trading_not_disabled")
    if enablement_snapshot.trading_halt.emergency_stop_active:
        failure_reasons.append("active_trading_halt")
    if enablement_snapshot.shared_paper_preflight.preflight_decision.blocking_count > 0:
        failure_reasons.append("shared_preflight_not_clear")
    if enablement_snapshot.warning_codes if False else False:
        pass

    return list(dict.fromkeys(failure_reasons))


@router.get("/auto-paper/history", response_model=list[RunHistoryEntry])
def get_auto_paper_history(
    limit: int = 20,
    source: Literal["manual", "scheduled"] | None = None,
    outcome: Literal["accepted", "rejected", "cancelled", "blocked"] | None = None,
    started_after: datetime | None = None,
    started_before: datetime | None = None,
) -> list[RunHistoryEntry]:
    """Return up to *limit* most-recent auto-paper run log entries, newest first."""
    return _get_filtered_auto_paper_history_entries(
        limit=limit,
        source=source,
        outcome=outcome,
        started_after=started_after,
        started_before=started_before,
    )


@router.get("/auto-paper/history/summary", response_model=AutoPaperHistorySummary)
def get_auto_paper_history_summary(
    limit: int = 200,
    source: Literal["manual", "scheduled"] | None = None,
    outcome: Literal["accepted", "rejected", "cancelled", "blocked"] | None = None,
    started_after: datetime | None = None,
    started_before: datetime | None = None,
) -> AutoPaperHistorySummary:
    """Return aggregate counts over filtered auto-paper history entries."""
    entries = _get_filtered_auto_paper_history_entries(
        limit=limit,
        source=source,
        outcome=outcome,
        started_after=started_after,
        started_before=started_before,
    )

    return _build_auto_paper_history_summary(entries)


@router.get("/auto-paper/history/export", response_model=AutoPaperHistoryExportPayload)
def export_auto_paper_history(
    limit: int = 200,
    source: Literal["manual", "scheduled"] | None = None,
    outcome: Literal["accepted", "rejected", "cancelled", "blocked"] | None = None,
    started_after: datetime | None = None,
    started_before: datetime | None = None,
) -> AutoPaperHistoryExportPayload:
    """Return a read-only export bundle for filtered auto-paper history and summary data."""
    entries = _get_filtered_auto_paper_history_entries(
        limit=limit,
        source=source,
        outcome=outcome,
        started_after=started_after,
        started_before=started_before,
    )

    return AutoPaperHistoryExportPayload(
        exported_at=datetime.now(timezone.utc),
        filters=AutoPaperHistoryExportFilters(
            limit=max(1, min(limit, 200)),
            source=source,
            outcome=outcome,
            started_after=started_after,
            started_before=started_before,
        ),
        summary=_build_auto_paper_history_summary(entries),
        entries=entries,
    )


@router.get("/auto-paper/history/retention", response_model=AutoPaperHistoryRetentionMetadata)
def get_auto_paper_history_retention() -> AutoPaperHistoryRetentionMetadata:
    """Return read-only retention metadata for the file-backed auto-paper history log."""
    return AutoPaperHistoryRetentionMetadata(**_run_log.get_retention_metadata())


@router.get("/auto-paper/readiness", response_model=AutoPaperReadinessResponse)
async def get_auto_paper_readiness(request: Request) -> AutoPaperReadinessResponse:
    """Return one read-only readiness contract for the current auto-paper safety posture."""
    broker_control = _build_auto_paper_broker_control()
    broker_health = await _build_auto_paper_broker_health()
    scheduler = get_scheduler_status(request)
    shared_paper_preflight = _build_auto_paper_shared_preflight_posture()
    recent_history = _build_auto_paper_history_readiness_posture()
    blocking_reasons, warning_reasons = _build_auto_paper_readiness_findings(
        broker_control=broker_control,
        broker_health=broker_health,
        scheduler=scheduler,
        shared_paper_preflight=shared_paper_preflight,
        recent_history=recent_history,
    )

    if blocking_reasons:
        status: Literal["blocked", "warning", "ready"] = "blocked"
    elif warning_reasons:
        status = "warning"
    else:
        status = "ready"

    return AutoPaperReadinessResponse(
        status=status,
        ready_for_auto_submit=not blocking_reasons,
        blocking_reasons=blocking_reasons,
        warning_reasons=warning_reasons,
        broker_control=broker_control,
        broker_health=broker_health,
        scheduler=scheduler,
        shared_paper_preflight=shared_paper_preflight,
        recent_history=recent_history,
    )


@router.get("/auto-paper/enablement-preconditions", response_model=AutoPaperEnablementPreconditionsResponse)
async def get_auto_paper_enablement_preconditions(
    request: Request,
    session: Annotated[Session, Depends(get_db_session)],
) -> AutoPaperEnablementPreconditionsResponse:
    """Return one read-only pre-enable checklist for future paper auto trading review."""
    return await _build_auto_paper_enablement_preconditions_response(
        request=request,
        session=session,
    )


@router.post("/auto-paper/arming", response_model=AutoPaperArmingResponse)
async def arm_auto_paper(
    body: AutoPaperArmingRequest,
    request: Request,
    session: Annotated[Session, Depends(get_db_session)],
) -> AutoPaperArmingResponse:
    """Record a controlled auto-paper arming decision without changing runtime enforcement."""
    evaluated_at = datetime.now(timezone.utc)
    enablement_snapshot = await _build_auto_paper_enablement_preconditions_response(
        request=request,
        session=session,
        checked_at=evaluated_at,
    )
    arming_state_before = _get_auto_paper_arming_surface_state(session)
    failure_reasons = _build_auto_paper_arming_failure_reasons(
        body=body,
        enablement_snapshot=enablement_snapshot,
        arming_state_before=arming_state_before,
        evaluated_at=evaluated_at,
    )
    if enablement_snapshot.warnings:
        failure_reasons.append("enablement_preconditions_not_ready")
    failure_reasons = list(dict.fromkeys(failure_reasons))

    if failure_reasons:
        status: Literal["armed", "rejected"] = "rejected"
        arming_state_after: Literal["armed", "disarmed"] = arming_state_before
    else:
        try:
            TradingControlArmingStateService(session).arm_state(
                armed_by=body.requested_by,
                expires_at=_get_auto_paper_arming_expiry(evaluated_at),
                scope="auto_paper",
                trading_mode="paper",
                arm_reason=body.reason,
                last_enablement_checked_at=enablement_snapshot.checked_at,
                last_enablement_status=enablement_snapshot.status,
                last_enablement_blockers=list(enablement_snapshot.blockers),
                last_enablement_warnings=list(enablement_snapshot.warnings),
                client_request_id=body.client_request_id,
                metadata_json={
                    "acknowledged_warning_codes": list(body.acknowledged_warning_codes),
                },
                armed_at=evaluated_at,
            )
            status = "armed"
            arming_state_after = "armed"
        except Exception:
            failure_reasons.append("durable_arming_state_write_failed")
            failure_reasons = list(dict.fromkeys(failure_reasons))
            status = "rejected"
            arming_state_after = arming_state_before

    audit_log_service.log_auto_paper_arming_action(
        action="arm",
        requested_by=body.requested_by,
        reason=body.reason,
        result_status=status,
        client_request_id=body.client_request_id,
        failure_reasons=failure_reasons,
        warning_codes=list(enablement_snapshot.warnings),
        enablement_checked_at=enablement_snapshot.checked_at.isoformat(),
        enablement_status=enablement_snapshot.status,
        enablement_blockers=list(enablement_snapshot.blockers),
        enablement_warnings=list(enablement_snapshot.warnings),
        trading_mode=enablement_snapshot.broker_control.trading_mode,
        execution_control=enablement_snapshot.broker_control.execution_control,
        arming_state_before=arming_state_before,
        arming_state_after=arming_state_after,
        extra={
            "acknowledged_warning_codes": list(body.acknowledged_warning_codes),
        },
    )

    return AutoPaperArmingResponse(
        status=status,
        arming_state=arming_state_after,
        evaluated_at=evaluated_at,
        failure_reasons=failure_reasons,
        warning_codes=list(enablement_snapshot.warnings),
        enablement_snapshot=enablement_snapshot,
        audit_recorded=True,
        audit_event_type=_AUTO_PAPER_ARMING_AUDIT_EVENT_TYPE,
        requested_by=body.requested_by,
        reason=body.reason,
        client_request_id=body.client_request_id,
    )


@router.get("/auto-paper/arming", response_model=AutoPaperArmingReadbackResponse)
def get_auto_paper_arming(
    session: Annotated[Session, Depends(get_db_session)],
) -> AutoPaperArmingReadbackResponse:
    """Return a read-only operator diagnostic readback of the current durable auto-paper arming posture."""
    posture = TradingControlArmingStateService(session).get_readback_posture(
        scope="auto_paper",
        trading_mode="paper",
    )
    last_audit: AutoPaperArmingAuditSummaryResponse | None = None
    if posture.last_audit is not None:
        a = posture.last_audit
        last_audit = AutoPaperArmingAuditSummaryResponse(
            event_type=a.event_type,
            recorded_at=a.recorded_at,
            action=a.action,
            result_status=a.result_status,
            requested_by=a.requested_by,
            reason=a.reason,
            client_request_id=a.client_request_id,
            arming_state_before=a.arming_state_before,
            arming_state_after=a.arming_state_after,
            failure_reasons=list(a.failure_reasons),
            warning_codes=list(a.warning_codes),
        )
    return AutoPaperArmingReadbackResponse(
        status=posture.status,  # type: ignore[arg-type]
        arming_state=posture.arming_state,  # type: ignore[arg-type]
        scope=posture.scope,
        trading_mode=posture.trading_mode,
        evaluated_at=posture.evaluated_at,
        fail_closed_reason=posture.fail_closed_reason,
        durable_row_present=posture.durable_row_present,
        duplicate_rows_detected=posture.duplicate_rows_detected,
        stored_state=posture.stored_state,
        armed_at=posture.armed_at,
        armed_by=posture.armed_by,
        arm_reason=posture.arm_reason,
        expires_at=posture.expires_at,
        expired=posture.expired,
        last_enablement_checked_at=posture.last_enablement_checked_at,
        last_enablement_status=posture.last_enablement_status,
        last_enablement_blockers=list(posture.last_enablement_blockers),
        last_enablement_warnings=list(posture.last_enablement_warnings),
        client_request_id=posture.client_request_id,
        disarmed_at=posture.disarmed_at,
        disarmed_by=posture.disarmed_by,
        disarm_reason=posture.disarm_reason,
        last_audit=last_audit,
    )


@router.post("/auto-paper/arming/disarm", response_model=AutoPaperDisarmResponse)
def disarm_auto_paper(
    body: AutoPaperDisarmRequest,
    session: Annotated[Session, Depends(get_db_session)],
) -> AutoPaperDisarmResponse:
    """Record a controlled auto-paper disarm decision without changing runtime enforcement."""
    evaluated_at = datetime.now(timezone.utc)
    trading_state = get_trading_mode()

    failure_reasons: list[str] = []
    if not body.requested_by:
        failure_reasons.append("requested_by_required")
    if not body.reason:
        failure_reasons.append("operator_reason_required")

    arming_state_before: Literal["armed", "disarmed"] = "disarmed"
    arming_state_after: Literal["armed", "disarmed"] = "disarmed"

    if not failure_reasons:
        try:
            posture = TradingControlArmingStateService(session).get_readback_posture(
                scope="auto_paper",
                trading_mode="paper",
                now=evaluated_at,
            )
        except Exception:
            failure_reasons.append("durable_arming_state_read_failed")
            posture = None  # type: ignore[assignment]

        if not failure_reasons:
            arming_state_before = posture.arming_state  # type: ignore[union-attr]
            if posture.status == "fail_closed":  # type: ignore[union-attr]
                reason_map = {
                    "durable_state_missing": "durable_state_missing",
                    "durable_state_duplicate": "durable_state_duplicate",
                    "durable_state_invalid": "durable_state_invalid",
                    "durable_state_read_failed": "durable_arming_state_read_failed",
                    "durable_state_expired": None,  # expired armed is allowed to disarm
                }
                fc_reason = posture.fail_closed_reason  # type: ignore[union-attr]
                mapped = reason_map.get(fc_reason or "", None)
                if mapped is not None:
                    failure_reasons.append(mapped)
            elif posture.status == "disarmed":  # type: ignore[union-attr]
                failure_reasons.append("already_disarmed")

    failure_reasons = list(dict.fromkeys(failure_reasons))

    if failure_reasons:
        status: Literal["disarmed", "rejected"] = "rejected"
        arming_state_after = arming_state_before
    else:
        try:
            TradingControlArmingStateService(session).disarm_state(
                disarmed_by=body.requested_by,
                scope="auto_paper",
                trading_mode="paper",
                disarm_reason=body.reason,
                metadata_json={"client_request_id": body.client_request_id},
                disarmed_at=evaluated_at,
            )
            status = "disarmed"
            arming_state_after = "disarmed"
        except Exception:
            failure_reasons.append("durable_arming_state_write_failed")
            failure_reasons = list(dict.fromkeys(failure_reasons))
            status = "rejected"
            arming_state_after = arming_state_before

    audit_log_service.log_auto_paper_arming_action(
        action="disarm",
        requested_by=body.requested_by,
        reason=body.reason,
        result_status=status,
        client_request_id=body.client_request_id,
        failure_reasons=failure_reasons,
        trading_mode="paper",
        execution_control=trading_state.execution_control,
        arming_state_before=arming_state_before,
        arming_state_after=arming_state_after,
    )

    return AutoPaperDisarmResponse(
        status=status,
        arming_state=arming_state_after,
        evaluated_at=evaluated_at,
        failure_reasons=failure_reasons,
        audit_recorded=True,
        audit_event_type=_AUTO_PAPER_ARMING_AUDIT_EVENT_TYPE,
        requested_by=body.requested_by,
        reason=body.reason,
        client_request_id=body.client_request_id,
    )


# ---------------------------------------------------------------------------
# Scheduler control (pause / resume / status for the auto_paper_trader job)
# ---------------------------------------------------------------------------


class SchedulerJobStatus(BaseModel):
    """Status of one APScheduler job."""

    job_id: str
    next_run_time: datetime | None
    state: Literal["running", "paused", "missing", "scheduler_unavailable"]


@router.get("/auto-paper/scheduler/status", response_model=SchedulerJobStatus)
def get_scheduler_status(request: Request) -> SchedulerJobStatus:
    """Return the current APScheduler state for the auto_paper_trader job."""
    scheduler = getattr(request.app.state, "scheduler", None)
    if scheduler is None:
        return SchedulerJobStatus(job_id="auto_paper_trader", next_run_time=None, state="scheduler_unavailable")
    job = scheduler.get_job("auto_paper_trader")
    if job is None:
        return SchedulerJobStatus(job_id="auto_paper_trader", next_run_time=None, state="missing")
    next_run = getattr(job, "next_run_time", None)
    state: Literal["running", "paused"] = "paused" if next_run is None else "running"
    return SchedulerJobStatus(job_id="auto_paper_trader", next_run_time=next_run, state=state)


@router.post("/auto-paper/scheduler/pause", response_model=SchedulerJobStatus)
def pause_scheduler(request: Request) -> SchedulerJobStatus:
    """Pause the scheduled auto_paper_trader cron job."""
    scheduler = getattr(request.app.state, "scheduler", None)
    if scheduler is None:
        raise HTTPException(status_code=503, detail="Scheduler not running")
    job = scheduler.get_job("auto_paper_trader")
    if job is None:
        raise HTTPException(status_code=404, detail="auto_paper_trader job not found")
    job.pause()
    return SchedulerJobStatus(job_id="auto_paper_trader", next_run_time=None, state="paused")


@router.post("/auto-paper/scheduler/resume", response_model=SchedulerJobStatus)
def resume_scheduler(request: Request) -> SchedulerJobStatus:
    """Resume the scheduled auto_paper_trader cron job."""
    scheduler = getattr(request.app.state, "scheduler", None)
    if scheduler is None:
        raise HTTPException(status_code=503, detail="Scheduler not running")
    job = scheduler.get_job("auto_paper_trader")
    if job is None:
        raise HTTPException(status_code=404, detail="auto_paper_trader job not found")
    job.resume()
    next_run = getattr(job, "next_run_time", None)
    return SchedulerJobStatus(job_id="auto_paper_trader", next_run_time=next_run, state="running")


# ---------------------------------------------------------------------------
# Kill-switch
# ---------------------------------------------------------------------------


class KillSwitchResponse(BaseModel):
    """Current kill-switch state."""

    kill_switch_active: bool
    profile_name: str | None
    profile_is_active: str | None


@router.get("/auto-paper/kill-switch", response_model=KillSwitchResponse)
def get_kill_switch(
    session: Annotated[Session, Depends(get_db_session)],
) -> KillSwitchResponse:
    """Return whether the kill-switch is currently active on the active risk profile."""
    profile = session.query(RiskProfile).filter(RiskProfile.is_active == "active").first()
    if profile is None:
        return KillSwitchResponse(kill_switch_active=False, profile_name=None, profile_is_active=None)
    return KillSwitchResponse(
        kill_switch_active=bool(profile.kill_switch_enabled),
        profile_name=profile.name,
        profile_is_active=profile.is_active,
    )


@router.post("/auto-paper/kill-switch/activate", response_model=KillSwitchResponse)
def activate_kill_switch(
    session: Annotated[Session, Depends(get_db_session)],
) -> KillSwitchResponse:
    """Hard-stop: enable kill_switch_enabled on the active risk profile."""
    profile = session.query(RiskProfile).filter(RiskProfile.is_active == "active").first()
    if profile is None:
        raise HTTPException(status_code=404, detail="No active risk profile found")
    profile.kill_switch_enabled = True
    session.commit()
    return KillSwitchResponse(
        kill_switch_active=True,
        profile_name=profile.name,
        profile_is_active=profile.is_active,
    )


@router.post("/auto-paper/kill-switch/deactivate", response_model=KillSwitchResponse)
def deactivate_kill_switch(
    session: Annotated[Session, Depends(get_db_session)],
) -> KillSwitchResponse:
    """Resume trading: disable kill_switch_enabled on the active risk profile."""
    profile = session.query(RiskProfile).filter(RiskProfile.is_active == "active").first()
    if profile is None:
        raise HTTPException(status_code=404, detail="No active risk profile found")
    profile.kill_switch_enabled = False
    session.commit()
    return KillSwitchResponse(
        kill_switch_active=False,
        profile_name=profile.name,
        profile_is_active=profile.is_active,
    )


@router.get("/news/{ticker}", response_model=list[NewsArticleResponse])
def get_market_data_news(
    ticker: str,
    session: Annotated[Session, Depends(get_db_session)],
    limit: int = 5,
) -> list[NewsArticleResponse]:
    """Return recent persisted news items for a ticker symbol."""
    normalized = ticker.upper()
    rows = (
        session.execute(
            select(NewsArticle).order_by(NewsArticle.published_at.desc()).limit(max(limit * 5, 25))
        )
        .scalars()
        .all()
    )

    filtered: list[NewsArticleResponse] = []
    for row in rows:
        tickers = [str(item).upper() for item in (row.tickers_json or [])]
        if normalized not in tickers:
            continue
        filtered.append(
            NewsArticleResponse(
                id=row.id,
                headline=row.headline,
                source_name=row.source_name,
                published_at=row.published_at,
                url=row.url,
                tickers=tickers,
            )
        )
        if len(filtered) >= limit:
            break

    return filtered
