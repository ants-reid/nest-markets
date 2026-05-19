"""Strategy Lab API routes — MH-06 data contracts + MH-07 replay.

Available endpoints:
    POST   /strategy-lab/configs
    GET    /strategy-lab/configs
    GET    /strategy-lab/configs/{config_id}

    POST   /strategy-lab/backtests
    GET    /strategy-lab/backtests
    GET    /strategy-lab/backtests/{backtest_id}
    POST   /strategy-lab/backtests/{backtest_id}/replay      (MH-07)
    GET    /strategy-lab/backtests/{backtest_id}/trades
    GET    /strategy-lab/backtests/{backtest_id}/results
    GET    /strategy-lab/backtests/{backtest_id}/equity-curve
    GET    /strategy-lab/backtests/{backtest_id}/drawdowns
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.strategy_lab import (
    BacktestReplayRequest,
    BacktestReplayResponse,
    BacktestRunCreateRequest,
    BacktestRunListResponse,
    BacktestRunResponse,
    DrawdownPeriodListResponse,
    EquityCurveResponse,
    MockTradeListResponse,
    StrategyComparisonRequest,
    StrategyComparisonDetailResponse,
    StrategyComparisonHistoryResponse,
    StrategyComparisonLabelRequest,
    StrategyComparisonLabelResponse,
    StrategyComparisonResponse,
    StrategyConfigCreateRequest,
    StrategyConfigListResponse,
    StrategyConfigResponse,
    StrategyResultListResponse,
    AIBacktestReportRequest,
    AIBacktestReportResponse,
    AIBacktestReportListResponse,
    CostModelProfileListResponse,
    CostModelStressPresetListResponse,
    StrategyResultQualitySummaryResponse,
    WalkForwardSplitRequest,
    WalkForwardValidationResponse,
)
from app.services.historical_replay_service import HistoricalReplayService, ReplayError
from app.services.strategy_comparison_service import ComparisonError, StrategyComparisonService
from app.services.strategy_lab_service import StrategyLabService
from app.services.ai_backtest_report_service import AIBacktestReportService
from app.services.execution_cost_model import list_cost_profiles, list_stress_presets

router = APIRouter(prefix="/strategy-lab", tags=["strategy_lab"])


def _svc(session: Session = Depends(get_db_session)) -> StrategyLabService:
    return StrategyLabService(session)


def _replay_svc(session: Session = Depends(get_db_session)) -> HistoricalReplayService:
    return HistoricalReplayService(session)


# ── Strategy Configs ───────────────────────────────────────────────────────

@router.post(
    "/configs",
    response_model=StrategyConfigResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_config(
    body: StrategyConfigCreateRequest,
    svc: StrategyLabService = Depends(_svc),
) -> StrategyConfigResponse:
    config = svc.create_config(
        name=body.name,
        strategy_type=body.strategy_type,
        asset=body.asset,
        timeframe=body.timeframe,
        parameters=body.parameters,
        risk_settings=body.risk_settings,
        enabled=body.enabled,
    )
    return StrategyConfigResponse.model_validate(config)


@router.get("/configs", response_model=StrategyConfigListResponse)
def list_configs(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    svc: StrategyLabService = Depends(_svc),
) -> StrategyConfigListResponse:
    total, items = svc.list_configs(limit=limit, offset=offset)
    return StrategyConfigListResponse(
        total=total,
        items=[StrategyConfigResponse.model_validate(c) for c in items],
    )


@router.get("/configs/{config_id}", response_model=StrategyConfigResponse)
def get_config(
    config_id: UUID,
    svc: StrategyLabService = Depends(_svc),
) -> StrategyConfigResponse:
    config = svc.get_config(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Strategy config not found")
    return StrategyConfigResponse.model_validate(config)


# ── Backtest Runs ──────────────────────────────────────────────────────────

@router.post(
    "/backtests",
    response_model=BacktestRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_backtest(
    body: BacktestRunCreateRequest,
    svc: StrategyLabService = Depends(_svc),
) -> BacktestRunResponse:
    run, message = svc.create_backtest_run(
        name=body.name,
        date_from=body.date_from,
        date_to=body.date_to,
        requested_assets=body.requested_assets,
        requested_timeframes=body.requested_timeframes,
        strategy_config_ids=body.strategy_config_ids,
        starting_capital=body.starting_capital,
    )
    response = BacktestRunResponse.model_validate(run)
    response.message = message
    return response


@router.get("/backtests", response_model=BacktestRunListResponse)
def list_backtests(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    svc: StrategyLabService = Depends(_svc),
) -> BacktestRunListResponse:
    total, items = svc.list_backtest_runs(limit=limit, offset=offset)
    return BacktestRunListResponse(
        total=total,
        items=[BacktestRunResponse.model_validate(r) for r in items],
    )


@router.get("/backtests/{backtest_id}", response_model=BacktestRunResponse)
def get_backtest(
    backtest_id: UUID,
    svc: StrategyLabService = Depends(_svc),
) -> BacktestRunResponse:
    run = svc.get_backtest_run(backtest_id)
    if not run:
        raise HTTPException(status_code=404, detail="Backtest run not found")
    return BacktestRunResponse.model_validate(run)


# ── Sub-resource routes ────────────────────────────────────────────────────

@router.get("/backtests/{backtest_id}/trades", response_model=MockTradeListResponse)
def list_trades(
    backtest_id: UUID,
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    svc: StrategyLabService = Depends(_svc),
) -> MockTradeListResponse:
    _assert_run_exists(backtest_id, svc)
    total, items = svc.list_trades(backtest_id, limit=limit, offset=offset)
    return MockTradeListResponse(total=total, items=items)  # type: ignore[arg-type]


@router.get("/backtests/{backtest_id}/results", response_model=StrategyResultListResponse)
def list_results(
    backtest_id: UUID,
    svc: StrategyLabService = Depends(_svc),
) -> StrategyResultListResponse:
    _assert_run_exists(backtest_id, svc)
    total, items = svc.list_results(backtest_id)
    return StrategyResultListResponse(total=total, items=items)  # type: ignore[arg-type]


@router.get(
    "/backtests/{backtest_id}/quality-summary",
    response_model=StrategyResultQualitySummaryResponse,
)
def get_quality_summary(
    backtest_id: UUID,
    svc: StrategyLabService = Depends(_svc),
) -> StrategyResultQualitySummaryResponse:
    _assert_run_exists(backtest_id, svc)
    summary = svc.get_quality_summary(backtest_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Backtest run not found")
    return StrategyResultQualitySummaryResponse.model_validate(summary)


@router.post(
    "/backtests/{backtest_id}/walk-forward",
    response_model=WalkForwardValidationResponse,
)
def run_walk_forward_validation(
    backtest_id: UUID,
    body: WalkForwardSplitRequest = WalkForwardSplitRequest(),  # noqa: B008
    svc: StrategyLabService = Depends(_svc),
) -> WalkForwardValidationResponse:
    _assert_run_exists(backtest_id, svc)
    try:
        payload = svc.run_walk_forward_validation(
            backtest_id,
            in_sample_pct=body.in_sample_pct,
            validation_pct=body.validation_pct,
            out_of_sample_pct=body.out_of_sample_pct,
            fold_count=body.fold_count,
            persist=True,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if payload is None:
        raise HTTPException(status_code=404, detail="Backtest run not found")
    return WalkForwardValidationResponse.model_validate(payload)


@router.get(
    "/backtests/{backtest_id}/walk-forward",
    response_model=WalkForwardValidationResponse,
)
def get_walk_forward_validation(
    backtest_id: UUID,
    svc: StrategyLabService = Depends(_svc),
) -> WalkForwardValidationResponse:
    _assert_run_exists(backtest_id, svc)
    stored = svc.get_walk_forward_validation(backtest_id)
    if stored is None:
        payload = svc.run_walk_forward_validation(backtest_id, persist=False)
    else:
        payload = stored

    if payload is None:
        raise HTTPException(status_code=404, detail="Backtest run not found")
    return WalkForwardValidationResponse.model_validate(payload)


@router.get("/backtests/{backtest_id}/equity-curve", response_model=EquityCurveResponse)
def list_equity_curve(
    backtest_id: UUID,
    limit: int = Query(5000, ge=1, le=50000),
    offset: int = Query(0, ge=0),
    svc: StrategyLabService = Depends(_svc),
) -> EquityCurveResponse:
    _assert_run_exists(backtest_id, svc)
    total, items = svc.list_equity_curve(backtest_id, limit=limit, offset=offset)
    return EquityCurveResponse(total=total, items=items)  # type: ignore[arg-type]


@router.get("/backtests/{backtest_id}/drawdowns", response_model=DrawdownPeriodListResponse)
def list_drawdowns(
    backtest_id: UUID,
    svc: StrategyLabService = Depends(_svc),
) -> DrawdownPeriodListResponse:
    _assert_run_exists(backtest_id, svc)
    total, items = svc.list_drawdowns(backtest_id)
    return DrawdownPeriodListResponse(total=total, items=items)  # type: ignore[arg-type]


# ── Replay (MH-07 / MH-08) ───────────────────────────────────────────────

@router.post(
    "/backtests/{backtest_id}/replay",
    response_model=BacktestReplayResponse,
    status_code=status.HTTP_200_OK,
)
def run_replay(
    backtest_id: UUID,
    body: BacktestReplayRequest = BacktestReplayRequest(),  # noqa: B008
    replay_svc: HistoricalReplayService = Depends(_replay_svc),
) -> BacktestReplayResponse:
    """Trigger a deterministic candle replay with optional mock trade simulation."""
    try:
        return replay_svc.replay(
            backtest_id,
            allow_unapproved_data=body.allow_unapproved_data,
            max_candles=body.max_candles,
            simulate_trades=body.simulate_trades,
            clear_existing_results=body.clear_existing_results,
        )
    except ReplayError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ── Strategy Comparison (MH-10) ───────────────────────────────────────────


def _comparison_svc(session: Session = Depends(get_db_session)) -> StrategyComparisonService:
    return StrategyComparisonService(session)


@router.post(
    "/comparisons/run",
    response_model=StrategyComparisonResponse,
    status_code=status.HTTP_200_OK,
)
def run_comparison(
    body: StrategyComparisonRequest,
    svc: StrategyComparisonService = Depends(_comparison_svc),
) -> StrategyComparisonResponse:
    """Run a multi-config ma_momentum comparison on a parameter grid."""
    try:
        return svc.run_comparison(body)
    except ComparisonError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/comparisons", response_model=StrategyComparisonHistoryResponse)
def list_comparisons(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    svc: StrategyLabService = Depends(_svc),
) -> StrategyComparisonHistoryResponse:
    """List historical comparison/backtest runs for dashboard review."""
    total, items = svc.list_comparison_runs(limit=limit, offset=offset)
    return StrategyComparisonHistoryResponse(total=total, items=items)  # type: ignore[arg-type]


@router.get(
    "/comparisons/{backtest_run_id}",
    response_model=StrategyComparisonDetailResponse,
)
def get_comparison_detail(
    backtest_run_id: UUID,
    svc: StrategyLabService = Depends(_svc),
) -> StrategyComparisonDetailResponse:
    """Return ranked comparison rows and compact run analytics for one backtest run."""
    detail = svc.get_comparison_detail(backtest_run_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Backtest run not found")
    return StrategyComparisonDetailResponse.model_validate(detail)


@router.post(
    "/comparisons/{backtest_run_id}/label",
    response_model=StrategyComparisonLabelResponse,
    status_code=status.HTTP_200_OK,
)
def set_comparison_label(
    backtest_run_id: UUID,
    body: StrategyComparisonLabelRequest,
    svc: StrategyLabService = Depends(_svc),
) -> StrategyComparisonLabelResponse:
    """Set manual research triage metadata on a historical comparison run."""
    result = svc.set_comparison_research_label(
        backtest_run_id,
        research_label=body.research_label,
        research_notes=body.research_notes,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Backtest run not found")
    return StrategyComparisonLabelResponse.model_validate(result)


# ── Helpers ────────────────────────────────────────────────────────────────

def _assert_run_exists(run_id: UUID, svc: StrategyLabService) -> None:
    if not svc.get_backtest_run(run_id):
        raise HTTPException(status_code=404, detail="Backtest run not found")


@router.get(
    "/cost-model/profiles",
    response_model=CostModelProfileListResponse,
)
def get_cost_model_profiles() -> CostModelProfileListResponse:
    """Read-only list of deterministic research cost calibration profiles."""
    items = list_cost_profiles()
    return CostModelProfileListResponse(total=len(items), items=items)  # type: ignore[arg-type]


@router.get(
    "/cost-model/stress-presets",
    response_model=CostModelStressPresetListResponse,
)
def get_cost_model_stress_presets() -> CostModelStressPresetListResponse:
    """Read-only list of deterministic stress presets for research cost modelling."""
    items = list_stress_presets()
    return CostModelStressPresetListResponse(total=len(items), items=items)  # type: ignore[arg-type]


# ── MH-14 AI Backtest Reports ──────────────────────────────────────────────

def _ai_svc(db: Session = Depends(get_db_session)) -> AIBacktestReportService:
    return AIBacktestReportService(db)


@router.post(
    "/backtests/{backtest_id}/ai-report",
    response_model=AIBacktestReportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_ai_report(
    backtest_id: UUID,
    body: AIBacktestReportRequest,
    svc: AIBacktestReportService = Depends(_ai_svc),
) -> AIBacktestReportResponse:
    """Generate an AI-powered research report for a completed backtest run."""
    try:
        return await svc.generate_report(str(backtest_id), body)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/backtests/{backtest_id}/ai-reports",
    response_model=AIBacktestReportListResponse,
)
def list_ai_reports(
    backtest_id: UUID,
    svc: AIBacktestReportService = Depends(_ai_svc),
) -> AIBacktestReportListResponse:
    """List all AI reports generated for a backtest run."""
    return svc.list_reports(str(backtest_id))


@router.get(
    "/ai-reports/{report_id}",
    response_model=AIBacktestReportResponse,
)
def get_ai_report(
    report_id: UUID,
    svc: AIBacktestReportService = Depends(_ai_svc),
) -> AIBacktestReportResponse:
    """Retrieve a single AI backtest report by ID."""
    report = svc.get_report(str(report_id))
    if report is None:
        raise HTTPException(status_code=404, detail="AI report not found")
    return report
