"""Paper validation routes for MH-16/MH-17 validation gate."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.strategy_lab import (
    PaperValidationDashboardResponse,
    PaperValidationEvidenceListResponse,
    PaperValidationEvidenceResponse,
    PaperValidationEventResponse,
    PaperValidationManualEvidenceRequest,
    PaperValidationPlanActionRequest,
    PaperValidationPlanCreateRequest,
    PaperValidationPlanListResponse,
    PaperValidationPlanResponse,
    PaperValidationPlanUpdateRequest,
    PaperValidationProgressResponse,
    PaperValidationReadinessResponse,
    PaperValidationReconcileRequest,
    PaperValidationReconcileResponse,
)
from app.services.paper_validation_service import PaperValidationError, PaperValidationService

router = APIRouter(prefix="/paper-validation", tags=["paper_validation"])


def _svc(session: Session = Depends(get_db_session)) -> PaperValidationService:
    return PaperValidationService(session)


@router.post("/plans", response_model=PaperValidationPlanResponse, status_code=status.HTTP_201_CREATED)
def create_plan(
    body: PaperValidationPlanCreateRequest,
    svc: PaperValidationService = Depends(_svc),
) -> PaperValidationPlanResponse:
    try:
        return svc.create_plan(body)
    except PaperValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/plans", response_model=PaperValidationPlanListResponse)
def list_plans(
    status_filter: str | None = Query(default=None, alias="status"),
    baseline_candidate_id: str | None = Query(default=None),
    backtest_run_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    svc: PaperValidationService = Depends(_svc),
) -> PaperValidationPlanListResponse:
    try:
        return svc.list_plans(
            status=status_filter,
            baseline_candidate_id=baseline_candidate_id,
            backtest_run_id=backtest_run_id,
            limit=limit,
            offset=offset,
        )
    except PaperValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/plans/{plan_id}", response_model=PaperValidationPlanResponse)
def get_plan(
    plan_id: str,
    svc: PaperValidationService = Depends(_svc),
) -> PaperValidationPlanResponse:
    try:
        return svc.get_plan(plan_id)
    except PaperValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/plans/{plan_id}", response_model=PaperValidationPlanResponse)
def update_plan(
    plan_id: str,
    body: PaperValidationPlanUpdateRequest,
    svc: PaperValidationService = Depends(_svc),
) -> PaperValidationPlanResponse:
    try:
        return svc.update_plan(plan_id, body)
    except PaperValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/plans/{plan_id}/start", response_model=PaperValidationPlanResponse)
def start_plan(
    plan_id: str,
    body: PaperValidationPlanActionRequest,
    svc: PaperValidationService = Depends(_svc),
) -> PaperValidationPlanResponse:
    try:
        return svc.start_plan(plan_id, body)
    except PaperValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/plans/{plan_id}/stop", response_model=PaperValidationPlanResponse)
def stop_plan(
    plan_id: str,
    body: PaperValidationPlanActionRequest,
    svc: PaperValidationService = Depends(_svc),
) -> PaperValidationPlanResponse:
    try:
        return svc.stop_plan(plan_id, body)
    except PaperValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/plans/{plan_id}/recalculate", response_model=PaperValidationPlanResponse)
def recalculate_plan(
    plan_id: str,
    svc: PaperValidationService = Depends(_svc),
) -> PaperValidationPlanResponse:
    try:
        return svc.recalculate_plan(plan_id)
    except PaperValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/plans/{plan_id}/progress", response_model=PaperValidationProgressResponse)
def get_progress(
    plan_id: str,
    svc: PaperValidationService = Depends(_svc),
) -> PaperValidationProgressResponse:
    try:
        return svc.get_progress(plan_id)
    except PaperValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/plans/{plan_id}/events", response_model=list[PaperValidationEventResponse])
def list_events(
    plan_id: str,
    svc: PaperValidationService = Depends(_svc),
) -> list[PaperValidationEventResponse]:
    try:
        return svc.list_events(plan_id)
    except PaperValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ── MH-17 Evidence / Reconciliation ─────────────────────────────────────────

@router.post(
    "/plans/{plan_id}/evidence/manual",
    response_model=PaperValidationEvidenceResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_manual_evidence(
    plan_id: str,
    body: PaperValidationManualEvidenceRequest,
    svc: PaperValidationService = Depends(_svc),
) -> PaperValidationEvidenceResponse:
    try:
        return svc.add_manual_evidence(plan_id, body)
    except PaperValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/plans/{plan_id}/evidence", response_model=PaperValidationEvidenceListResponse)
def list_evidence(
    plan_id: str,
    svc: PaperValidationService = Depends(_svc),
) -> PaperValidationEvidenceListResponse:
    try:
        return svc.list_evidence(plan_id)
    except PaperValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/plans/{plan_id}/evidence/{evidence_id}/exclude",
    response_model=PaperValidationEvidenceResponse,
)
def exclude_evidence(
    plan_id: str,
    evidence_id: str,
    svc: PaperValidationService = Depends(_svc),
) -> PaperValidationEvidenceResponse:
    try:
        return svc.exclude_evidence(plan_id, evidence_id)
    except PaperValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/plans/{plan_id}/evidence/{evidence_id}/include",
    response_model=PaperValidationEvidenceResponse,
)
def include_evidence(
    plan_id: str,
    evidence_id: str,
    svc: PaperValidationService = Depends(_svc),
) -> PaperValidationEvidenceResponse:
    try:
        return svc.include_evidence(plan_id, evidence_id)
    except PaperValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/plans/{plan_id}/reconcile", response_model=PaperValidationReconcileResponse)
def reconcile_plan(
    plan_id: str,
    body: PaperValidationReconcileRequest,
    svc: PaperValidationService = Depends(_svc),
) -> PaperValidationReconcileResponse:
    try:
        return svc.reconcile(plan_id, body)
    except PaperValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ── MH-18: Dashboard & Readiness Review ────────────────────────────────────


@router.get("/dashboard", response_model=PaperValidationDashboardResponse)
def get_dashboard(
    svc: PaperValidationService = Depends(_svc),
) -> PaperValidationDashboardResponse:
    """Get dashboard summary for all paper validation plans."""
    try:
        return svc.get_dashboard_summary()
    except PaperValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/plans/{plan_id}/readiness", response_model=PaperValidationReadinessResponse)
def get_readiness_review(
    plan_id: str,
    svc: PaperValidationService = Depends(_svc),
) -> PaperValidationReadinessResponse:
    """Get readiness review for a single paper validation plan."""
    try:
        return svc.get_readiness_review(plan_id)
    except PaperValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
