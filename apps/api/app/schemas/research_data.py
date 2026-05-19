"""Pydantic response schemas for the Data Centre (MH-01/MH-02 /research/data/* endpoints)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field


# ── Asset coverage item ────────────────────────────────────────────────────

class AssetCoverageItem(BaseModel):
    """Coverage summary for one asset across all tracked timeframes."""

    asset_symbol: str
    asset_name: str | None
    is_active: bool
    timeframes: list[str]
    total_bars: int
    earliest_bar_ts: datetime | None
    latest_bar_ts: datetime | None
    providers: list[str]


class AssetCoverageResponse(BaseModel):
    """Full asset coverage matrix derived from existing bars data."""

    evaluated_at: datetime
    total_assets: int
    covered_assets: int
    uncovered_assets: int
    items: list[AssetCoverageItem]


# ── Provider info ──────────────────────────────────────────────────────────

class ProviderInfo(BaseModel):
    """Static descriptor for a known market-data provider."""

    name: str
    label: str
    supported_asset_classes: list[str]
    supported_timeframes: list[str]
    notes: str | None


class ProviderListResponse(BaseModel):
    """Known provider catalogue."""

    providers: list[ProviderInfo]


# ── Quality report ─────────────────────────────────────────────────────────

class QualityReportItem(BaseModel):
    """Quality snapshot for one (asset_symbol, timeframe) pair."""

    asset_symbol: str
    timeframe: str
    provider: str | None
    expected_bars: int | None = None
    actual_bars: int | None = None
    total_bars: int
    completeness_pct: float | None
    missing_pct: float | None = None
    missing_bars: int
    duplicate_bars: int
    bad_price_bars: int = 0
    suspicious_spike_bars: int = 0
    stale_bars: int
    earliest_bar_ts: datetime | None
    latest_bar_ts: datetime | None
    quality_score: float | None = None
    approved_for_backtest: bool | None = None
    notes: str | None


class QualityReportResponse(BaseModel):
    """Aggregated quality summary across all tracked assets and timeframes."""

    evaluated_at: datetime
    total_items: int
    items: list[QualityReportItem]


# ── Gap records ────────────────────────────────────────────────────────────

class GapItem(BaseModel):
    """One recorded bar gap."""

    id: UUID
    asset_symbol: str
    timeframe: str
    provider: str | None
    gap_start: datetime
    gap_end: datetime
    expected_candles_missing: int = 1
    severity: Literal["low", "medium", "high"] = "low"
    status: Literal["open", "filling", "resolved", "ignored"]
    import_run_id: UUID | None
    notes: str | None
    created_at: datetime


class GapsResponse(BaseModel):
    """List of recorded bar gaps."""

    total: int
    items: list[GapItem]


# ── Import run records ─────────────────────────────────────────────────────

class ImportRunItem(BaseModel):
    """One market data import run record."""

    id: UUID
    provider: str
    asset_symbol: str
    timeframe: str
    from_date: datetime | None
    to_date: datetime | None
    rows_requested: int | None
    rows_upserted: int | None
    rows_skipped: int | None
    status: str
    error_message: str | None
    duration_seconds: float | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime


# ── MH-02: Import request / response ──────────────────────────────────────

class ImportRequest(BaseModel):
    """Request payload for POST /research/data/import."""

    assets: Annotated[list[str], Field(min_length=1, max_length=50)]
    timeframes: Annotated[list[str], Field(min_length=1, max_length=10)]
    requested_years: Annotated[int, Field(ge=1, le=20)] = 5
    providers: Annotated[list[str], Field(min_length=1, max_length=10)] = Field(
        default_factory=lambda: ["yfinance"]
    )
    dry_run: bool = False


ImportStatus = Literal["completed", "partial", "failed", "dry_run", "skipped"]


class AssetImportResult(BaseModel):
    """Per-asset/timeframe/provider result within a batch import."""

    asset_symbol: str
    timeframe: str
    provider: str
    requested_start: datetime
    requested_end: datetime
    available_from: datetime | None
    available_to: datetime | None
    candles_imported: int
    status: ImportStatus
    message: str | None


class ImportResponse(BaseModel):
    """Response payload for POST /research/data/import."""

    batch_id: UUID
    status: ImportStatus
    requested_years: int
    dry_run: bool
    started_at: datetime
    completed_at: datetime
    total_candles_imported: int
    results: list[AssetImportResult]


# ── MH-02: Import run list ─────────────────────────────────────────────────

class ImportRunSummary(BaseModel):
    """Summary of one batch import request for GET /research/data/import-runs."""

    batch_id: UUID
    status: str
    dry_run: bool
    requested_years: int
    assets: list[str]
    timeframes: list[str]
    providers: list[str]
    started_at: datetime
    completed_at: datetime | None
    total_candles_imported: int
    failed_count: int
    run_count: int


class ImportRunListResponse(BaseModel):
    """List of recent batch import runs."""

    total: int
    items: list[ImportRunSummary]


# ── MH-03: Quality recalculation ──────────────────────────────────────────

class QualityRecalculateRequest(BaseModel):
    """Request payload for POST /research/data/quality/recalculate."""

    assets: Annotated[list[str], Field(min_length=1, max_length=100)]
    timeframes: Annotated[list[str], Field(min_length=1, max_length=20)]
    providers: list[str] | None = None


class QualityRecalculateItem(BaseModel):
    """One recalculated quality result item."""

    asset_symbol: str
    timeframe: str
    provider: str | None
    quality_score: float
    completeness_pct: float | None
    missing_bars: int
    duplicate_bars: int
    bad_price_bars: int
    suspicious_spike_bars: int
    approved_for_backtest: bool
    gap_count: int
    notes: str | None


class QualityRecalculateResponse(BaseModel):
    """Response payload for POST /research/data/quality/recalculate."""

    total: int
    succeeded: int
    failed: int
    items: list[QualityRecalculateItem]


# ── MH-05: Research jobs ───────────────────────────────────────────────────

ResearchJobType = Literal["historical_import", "quality_recalculate"]
ResearchJobStatus = Literal["queued", "running", "completed", "partial", "failed", "cancelled"]


class ResearchJobResponse(BaseModel):
    """Base response for a persisted research job."""

    id: UUID
    job_type: ResearchJobType
    status: ResearchJobStatus
    requested_by: str | None
    request_payload: dict
    result_payload: dict | None
    progress_current: int
    progress_total: int
    progress_message: str | None
    error_message: str | None
    retry_of_job_id: UUID | None
    started_at: datetime | None
    completed_at: datetime | None
    cancelled_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ResearchJobListResponse(BaseModel):
    """List response for research jobs."""

    total: int
    items: list[ResearchJobResponse]


class ResearchJobDetailResponse(BaseModel):
    """Detailed research job response."""

    job: ResearchJobResponse


class ResearchJobCancelResponse(BaseModel):
    """Cancel action response."""

    success: bool
    message: str
    job: ResearchJobResponse | None


class ResearchJobRetryResponse(BaseModel):
    """Retry action response."""

    success: bool
    message: str
    job: ResearchJobResponse | None


# ── MH-12 Data Quality Review (outlier triage) ────────────────────────────

ReviewStatusLiteral = Literal[
    "unreviewed",
    "valid_market_move",
    "bad_data",
    "needs_provider_check",
    "ignore_for_now",
]


class OutlierItem(BaseModel):
    """A quality report row flagged as a potential outlier requiring review."""

    id: UUID
    asset_symbol: str
    timeframe: str
    provider: str | None
    quality_score: float | None
    approved_for_backtest: bool
    suspicious_spike_bars: int
    bad_price_bars: int
    missing_bars: int
    completeness_pct: float | None
    total_bars: int
    evaluated_at: datetime
    review_status: ReviewStatusLiteral
    review_notes: str | None
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None


class OutlierListResponse(BaseModel):
    """Paginated list of flagged outlier quality reports."""

    total: int
    items: list[OutlierItem]


class OutlierReviewRequest(BaseModel):
    """Triage payload for a single quality report."""

    review_status: ReviewStatusLiteral
    review_notes: Annotated[str | None, Field(max_length=2000)] = None
    reviewed_by: Annotated[str | None, Field(max_length=255)] = None


class OutlierReviewResponse(BaseModel):
    """Confirmation after saving a review status."""

    id: UUID
    asset_symbol: str
    timeframe: str
    review_status: ReviewStatusLiteral
    review_notes: str | None
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None


# ── MH-13 Audit history + summary ─────────────────────────────────────────

class QualityReviewAuditEntry(BaseModel):
    """One audit trail entry for a triage decision."""

    id: UUID
    report_id: str
    asset_symbol: str
    timeframe: str
    provider: str | None
    previous_status: str | None
    new_status: str
    review_notes: str | None
    reviewed_by: str | None
    reviewed_at: datetime
    created_at: datetime


class QualityReviewAuditResponse(BaseModel):
    """Audit trail for one quality report."""

    total: int
    entries: list[QualityReviewAuditEntry]


class UnreviewedSummaryResponse(BaseModel):
    """Summary counts of unreviewed quality issues — used in Data Centre card."""

    total_flagged: int
    unreviewed: int
    reviewed: int
    by_status: dict[str, int]


