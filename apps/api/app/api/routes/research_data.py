"""Research / Data Centre API routes - MH-01/MH-02 Data Centre.

Prefix: /research/data
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.market_data_gap import MarketDataGap
from app.db.models.market_data_import_run import MarketDataImportRun
from app.db.session import get_db_session
from app.schemas.research_data import (
    AssetCoverageResponse,
    GapItem,
    GapsResponse,
    ImportRequest,
    ImportResponse,
    AssetImportResult as AssetImportResultSchema,
    ImportRunListResponse,
    ImportRunSummary,
    OutlierListResponse,
    OutlierReviewRequest,
    OutlierReviewResponse,
    ProviderInfo,
    ProviderListResponse,
    QualityRecalculateRequest,
    QualityRecalculateResponse,
    QualityReportResponse,
    QualityReviewAuditResponse,
    UnreviewedSummaryResponse,
)
from app.services.historical_import_service import (
    BatchImportResult,
    HistoricalImportService,
)
from app.services.market_data_coverage_service import MarketDataCoverageService
from app.services.market_data_quality_service import MarketDataQualityService

router = APIRouter(prefix="/research/data", tags=["research_data"])

_KNOWN_PROVIDERS: list[ProviderInfo] = [
    ProviderInfo(
        name="polygon",
        label="Polygon.io",
        supported_asset_classes=["equity", "fx", "crypto", "options"],
        supported_timeframes=["1m", "5m", "15m", "1h", "4h", "1d"],
        notes="Primary data provider. Requires POLYGON_API_KEY.",
    ),
    ProviderInfo(
        name="tiingo",
        label="Tiingo",
        supported_asset_classes=["equity", "fx", "crypto"],
        supported_timeframes=["1d"],
        notes="EOD / daily bars. Requires TIINGO_API_KEY.",
    ),
    ProviderInfo(
        name="twelve_data",
        label="Twelve Data",
        supported_asset_classes=["equity", "fx", "crypto", "etf"],
        supported_timeframes=["1m", "5m", "15m", "1h", "4h", "1d"],
        notes="Intraday and daily bars. Requires TWELVE_DATA_API_KEY.",
    ),
    ProviderInfo(
        name="yfinance",
        label="yfinance (Yahoo Finance)",
        supported_asset_classes=["equity", "etf", "crypto"],
        supported_timeframes=["1m", "5m", "15m", "1h", "1d"],
        notes="Free, no key required. Rate-limited; not suitable for production bulk imports.",
    ),
    ProviderInfo(
        name="ibkr",
        label="Interactive Brokers",
        supported_asset_classes=["equity", "fx", "futures", "options", "crypto"],
        supported_timeframes=["1m", "5m", "15m", "1h", "4h", "1d"],
        notes="Requires active IBKR gateway session. Live and paper accounts supported.",
    ),
    ProviderInfo(
        name="mock",
        label="Mock / Test Provider",
        supported_asset_classes=["equity", "fx"],
        supported_timeframes=["1m", "1h", "1d"],
        notes="In-process mock for testing. Returns deterministic synthetic bars.",
    ),
]


@router.get("/assets", response_model=AssetCoverageResponse)
def get_data_assets(
    session: Annotated[Session, Depends(get_db_session)],
) -> AssetCoverageResponse:
    """Return all tracked assets with their bar coverage summary."""
    return MarketDataCoverageService(session).get_coverage()


@router.get("/providers", response_model=ProviderListResponse)
def get_data_providers() -> ProviderListResponse:
    """Return the known market-data provider catalogue."""
    return ProviderListResponse(providers=_KNOWN_PROVIDERS)


@router.get("/coverage", response_model=AssetCoverageResponse)
def get_data_coverage(
    session: Annotated[Session, Depends(get_db_session)],
) -> AssetCoverageResponse:
    """Return per-asset coverage matrix derived from the existing bars table."""
    return MarketDataCoverageService(session).get_coverage()


@router.get("/quality", response_model=QualityReportResponse)
def get_data_quality(
    session: Annotated[Session, Depends(get_db_session)],
    asset_symbol: Annotated[str | None, Query(description="Filter to one asset symbol")] = None,
) -> QualityReportResponse:
    """Return quality summary for tracked assets and timeframes."""
    return MarketDataQualityService(session).get_quality_report(asset_symbol=asset_symbol)


@router.post("/quality/recalculate", response_model=QualityRecalculateResponse)
def recalculate_data_quality(
    request: QualityRecalculateRequest,
    session: Annotated[Session, Depends(get_db_session)],
) -> QualityRecalculateResponse:
    """Recalculate quality reports and gap records for selected combos."""
    return MarketDataQualityService(session).recalculate_quality(request)


@router.get("/gaps", response_model=GapsResponse)
def get_data_gaps(
    session: Annotated[Session, Depends(get_db_session)],
    asset_symbol: Annotated[str | None, Query(description="Filter to one asset symbol")] = None,
    status: Annotated[
        Literal["open", "filling", "resolved", "ignored"] | None,
        Query(description="Filter by gap status"),
    ] = None,
) -> GapsResponse:
    """Return recorded bar gaps from the market_data_gaps table."""
    query = select(MarketDataGap).order_by(MarketDataGap.gap_start.desc())
    if asset_symbol:
        query = query.where(MarketDataGap.asset_symbol == asset_symbol)
    if status:
        query = query.where(MarketDataGap.status == status)

    rows = session.execute(query).scalars().all()
    items = [
        GapItem(
            id=row.id,
            asset_symbol=row.asset_symbol,
            timeframe=row.timeframe,
            provider=row.provider,
            gap_start=row.gap_start,
            gap_end=row.gap_end,
            expected_candles_missing=row.expected_candles_missing,
            severity=row.severity,  # type: ignore[arg-type]
            status=row.status,  # type: ignore[arg-type]
            import_run_id=row.import_run_id,
            notes=row.notes,
            created_at=row.created_at,
        )
        for row in rows
    ]
    return GapsResponse(total=len(items), items=items)


@router.post("/import", response_model=ImportResponse, status_code=202)
async def run_historical_import(
    request: ImportRequest,
    session: Annotated[Session, Depends(get_db_session)],
) -> ImportResponse:
    """Trigger a batch historical bar import."""
    svc = HistoricalImportService(session)
    result: BatchImportResult = await svc.run_import(
        assets=request.assets,
        timeframes=request.timeframes,
        providers=request.providers,
        requested_years=request.requested_years,
        dry_run=request.dry_run,
    )
    return ImportResponse(
        batch_id=result.batch_id,
        status=result.status,  # type: ignore[arg-type]
        requested_years=result.requested_years,
        dry_run=result.dry_run,
        started_at=result.started_at,
        completed_at=result.completed_at,
        total_candles_imported=result.total_candles_imported,
        results=[
            AssetImportResultSchema(
                asset_symbol=r.asset_symbol,
                timeframe=r.timeframe,
                provider=r.provider,
                requested_start=r.requested_start,
                requested_end=r.requested_end,
                available_from=r.available_from,
                available_to=r.available_to,
                candles_imported=r.candles_imported,
                status=r.status,  # type: ignore[arg-type]
                message=r.message,
            )
            for r in result.results
        ],
    )


@router.get("/import-runs", response_model=ImportRunListResponse)
def list_import_runs(
    session: Annotated[Session, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    batch_id: Annotated[str | None, Query(description="Filter by batch UUID")] = None,
) -> ImportRunListResponse:
    """Return recent import run records."""
    query = select(MarketDataImportRun).order_by(MarketDataImportRun.created_at.desc())
    if batch_id:
        try:
            parsed_batch = uuid.UUID(batch_id)
        except ValueError:
            return ImportRunListResponse(total=0, items=[])
        query = query.where(MarketDataImportRun.batch_id == parsed_batch)

    total_query = select(MarketDataImportRun)
    if batch_id:
        total_query = total_query.where(MarketDataImportRun.batch_id == parsed_batch)

    all_runs = session.execute(total_query).scalars().all()
    total = len(all_runs)

    runs = session.execute(query.offset(offset).limit(limit)).scalars().all()

    batches: dict[str, list[MarketDataImportRun]] = defaultdict(list)
    for run in runs:
        key = str(run.batch_id) if run.batch_id else str(run.id)
        batches[key].append(run)

    items: list[ImportRunSummary] = []
    for _bid, batch_runs in batches.items():
        first = batch_runs[0]
        all_assets = list({r.asset_symbol for r in batch_runs})
        all_timeframes = list({r.timeframe for r in batch_runs})
        all_providers = list({r.provider for r in batch_runs})
        candles = sum(r.rows_upserted or 0 for r in batch_runs)
        failed = sum(1 for r in batch_runs if r.status == "failed")
        statuses = {r.status for r in batch_runs}
        if "dry_run" in statuses:
            batch_status = "dry_run"
        elif "failed" in statuses and all(r.status == "failed" for r in batch_runs):
            batch_status = "failed"
        elif "failed" in statuses:
            batch_status = "partial"
        else:
            batch_status = "completed"

        finished_at = max(
            (r.finished_at for r in batch_runs if r.finished_at is not None),
            default=None,
        )
        dry_run = all(r.status == "dry_run" for r in batch_runs)
        req_years = 0
        if first.from_date and first.to_date:
            req_years = max(1, (first.to_date - first.from_date).days // 365)

        items.append(
            ImportRunSummary(
                batch_id=first.batch_id or first.id,
                status=batch_status,
                dry_run=dry_run,
                requested_years=req_years,
                assets=all_assets,
                timeframes=all_timeframes,
                providers=all_providers,
                started_at=first.started_at or first.created_at,
                completed_at=finished_at,
                total_candles_imported=candles,
                failed_count=failed,
                run_count=len(batch_runs),
            )
        )

    return ImportRunListResponse(total=total, items=items)


@router.get("/quality/outliers", response_model=OutlierListResponse)
def list_quality_outliers(
    session: Annotated[Session, Depends(get_db_session)],
    review_status: Annotated[str | None, Query()] = None,
    asset: Annotated[str | None, Query()] = None,
    provider: Annotated[str | None, Query()] = None,
    timeframe: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> OutlierListResponse:
    """Return persisted quality reports flagged as outliers."""
    return MarketDataQualityService(session).list_outliers(
        review_status=review_status,
        asset=asset,
        provider=provider,
        timeframe=timeframe,
        limit=limit,
        offset=offset,
    )


@router.get("/quality/outliers/summary", response_model=UnreviewedSummaryResponse)
def get_quality_outliers_summary(
    session: Annotated[Session, Depends(get_db_session)],
) -> UnreviewedSummaryResponse:
    """Return counts of flagged quality reports by review_status."""
    return MarketDataQualityService(session).get_unreviewed_summary()


@router.post(
    "/quality/outliers/{report_id}/review",
    response_model=OutlierReviewResponse,
    status_code=200,
)
def review_quality_outlier(
    report_id: str,
    body: OutlierReviewRequest,
    session: Annotated[Session, Depends(get_db_session)],
) -> OutlierReviewResponse:
    """Set triage review_status and optional notes on a quality report."""
    try:
        parsed_id = UUID(report_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid report_id UUID") from exc

    result = MarketDataQualityService(session).review_outlier(parsed_id, body)
    if result is None:
        raise HTTPException(status_code=404, detail="Quality report not found")
    return result


@router.get(
    "/quality/outliers/{report_id}/audit",
    response_model=QualityReviewAuditResponse,
)
def get_quality_outlier_audit(
    report_id: str,
    session: Annotated[Session, Depends(get_db_session)],
) -> QualityReviewAuditResponse:
    """Return the full audit trail for a quality report."""
    try:
        parsed_id = UUID(report_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid report_id UUID") from exc

    return MarketDataQualityService(session).get_audit_trail(parsed_id)
