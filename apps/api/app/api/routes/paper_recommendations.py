"""Paper trading recommendation drafting endpoints (MH-36)."""
from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.broker_schemas import (
    BrokerModeSchema,
    PaperRecommendationBrokerDryRunPreviewResponseSchema,
    PaperRecommendationRouteCheckResponseSchema,
)
from app.schemas.paper_recommendation import (
    PaperRecommendationCreateRequest,
    PaperRecommendationListResponse,
    PaperRecommendationResponse,
    PaperRecommendationReviewRequest,
)
from app.services.paper_recommendation_broker_dry_run_preview_service import (
    PaperRecommendationBrokerDryRunPreviewService,
)
from app.services.paper_recommendation_route_check_service import PaperRecommendationRouteCheckService
from app.services.paper_recommendation_service import PaperRecommendationService

_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/paper/recommendations", tags=["paper_recommendations"])


@router.post("", response_model=PaperRecommendationResponse)
def draft_recommendation(
    request: PaperRecommendationCreateRequest,
    session: Annotated[Session, Depends(get_db_session)],
) -> PaperRecommendationResponse:
    """Draft a new paper trading recommendation.

    Parameters:
    - ticker: Trade ticker (e.g., 'AAPL')
    - side: 'BUY' or 'SELL'
    - quantity: Number of shares (> 0)
    - order_type: 'MARKET', 'LIMIT', 'STOP', 'STOP_LIMIT'
    - limit_price: Limit price (required for LIMIT orders)
    - signal_id: Optional reference to a signal
    - model_version_id: Optional reference to a model version
    - confidence: Optional confidence metric (0.0-1.0)
    - risk_score: Optional risk score (0.0-1.0)
    - rationale: Optional explanation

    Returns:
    - New recommendation in DRAFT status
    """
    service = PaperRecommendationService(session)

    # Validate limit_price for LIMIT orders
    if request.order_type == "LIMIT" and not request.limit_price:
        raise HTTPException(status_code=400, detail="limit_price is required for LIMIT orders")

    rec = service.draft_recommendation(
        ticker=request.ticker,
        side=request.side,
        quantity=request.quantity,
        order_type=request.order_type,
        limit_price=request.limit_price,
        signal_id=request.signal_id,
        model_version_id=request.model_version_id,
        confidence=request.confidence,
        risk_score=request.risk_score,
        rationale=request.rationale,
    )

    return PaperRecommendationResponse.model_validate(rec)


@router.get("", response_model=PaperRecommendationListResponse)
def list_recommendations(
    session: Annotated[Session, Depends(get_db_session)],
    status: str | None = Query(None, description="Filter by status (draft, approved, rejected, executed, reviewed)"),
    limit: int = Query(20, ge=1, le=100, description="Max number of results"),
) -> PaperRecommendationListResponse:
    """List paper trading recommendations.

    Parameters:
    - status: Optional status filter
    - limit: Maximum number of results (default 20, max 100)

    Returns:
    - List of recommendations (newest first)
    """
    service = PaperRecommendationService(session)
    items = service.list_recommendations(status=status, limit=limit)

    return PaperRecommendationListResponse(
        items=[PaperRecommendationResponse.model_validate(rec) for rec in items],
        total=len(items),
    )


@router.get("/{recommendation_id}", response_model=PaperRecommendationResponse)
def get_recommendation(
    recommendation_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
) -> PaperRecommendationResponse:
    """Get a specific recommendation by ID."""
    service = PaperRecommendationService(session)
    rec = service.get_recommendation(recommendation_id)

    if not rec:
        raise HTTPException(status_code=404, detail=f"Recommendation {recommendation_id} not found")

    return PaperRecommendationResponse.model_validate(rec)


@router.get(
    "/{recommendation_id}/serious-paper-route-check",
    response_model=PaperRecommendationRouteCheckResponseSchema,
)
def get_recommendation_serious_paper_route_check(
    recommendation_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
) -> PaperRecommendationRouteCheckResponseSchema:
    """Return the read-only serious-paper route-check for one recommendation."""
    decision = PaperRecommendationRouteCheckService(session).resolve_route_check(recommendation_id)

    if not decision:
        raise HTTPException(status_code=404, detail=f"Recommendation {recommendation_id} not found")

    return PaperRecommendationRouteCheckResponseSchema(
        recommendation_id=decision.recommendation_id,
        recommendation_status=decision.recommendation_status,
        ticker=decision.ticker,
        side=decision.side,
        quantity=decision.quantity,
        order_type=decision.order_type,
        limit_price=decision.limit_price,
        estimated_notional=decision.estimated_notional,
        risk_score=decision.risk_score,
        route_check_status=decision.route_check_status,
        resolved_route=decision.resolved_route,
        resolved_execution_source=decision.resolved_execution_source,
        execution_source=decision.execution_source,
        serious_paper_source=decision.serious_paper_source,
        is_canonical_paper=decision.is_canonical_paper,
        broker_account_mode=decision.broker_account_mode,
        live_state=decision.live_state,
        would_block=decision.would_block,
        blocked_reason=decision.blocked_reason,
        missing_data=decision.missing_data,
        next_required_action=decision.next_required_action,
        is_submit=decision.is_submit,
        workers_allowed_to_submit=decision.workers_allowed_to_submit,
        live_trading_enabled=decision.live_trading_enabled,
        canonical_paper_route=decision.canonical_paper_route,
        broker_mode=BrokerModeSchema(**decision.broker_mode),
    )


@router.post(
    "/{recommendation_id}/broker-dry-run-preview",
    response_model=PaperRecommendationBrokerDryRunPreviewResponseSchema,
)
def preview_recommendation_broker_dry_run(
    recommendation_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
) -> PaperRecommendationBrokerDryRunPreviewResponseSchema:
    """Return a guarded broker dry-run preview for one recommendation.

    The preview is recommendation-owned and never submits. The existing broker
    dry-run logic is only invoked after the recommendation passes the read-only
    serious-paper route-check.
    """
    decision = PaperRecommendationBrokerDryRunPreviewService(session).resolve_preview(recommendation_id)

    if not decision:
        raise HTTPException(status_code=404, detail=f"Recommendation {recommendation_id} not found")

    return PaperRecommendationBrokerDryRunPreviewResponseSchema(
        recommendation_id=decision.recommendation_id,
        recommendation_status=decision.recommendation_status,
        ticker=decision.ticker,
        side=decision.side,
        quantity=decision.quantity,
        order_type=decision.order_type,
        limit_price=decision.limit_price,
        estimated_notional=decision.estimated_notional,
        risk_score=decision.risk_score,
        route_check_status=decision.route_check_status,
        dry_run_status=decision.dry_run_status,
        dry_run_only=decision.dry_run_only,
        dry_run_executed=decision.dry_run_executed,
        allowed_to_submit=decision.allowed_to_submit,
        resolved_route=decision.resolved_route,
        resolved_execution_source=decision.resolved_execution_source,
        dry_run_execution_source=decision.dry_run_execution_source,
        balance_source=decision.balance_source,
        fees_source=decision.fees_source,
        fills_source=decision.fills_source,
        positions_source=decision.positions_source,
        serious_paper_source=decision.serious_paper_source,
        is_canonical_paper=decision.is_canonical_paper,
        broker_account_mode=decision.broker_account_mode,
        live_state=decision.live_state,
        would_block=decision.would_block,
        blocked_reason=decision.blocked_reason,
        missing_data=decision.missing_data,
        next_required_action=decision.next_required_action,
        is_submit=decision.is_submit,
        workers_allowed_to_submit=decision.workers_allowed_to_submit,
        live_trading_enabled=decision.live_trading_enabled,
        canonical_paper_route=decision.canonical_paper_route,
        broker_mode=BrokerModeSchema(**decision.broker_mode),
        mode_guard_ok=decision.mode_guard_ok,
        request_valid=decision.request_valid,
        issues=decision.issues,
        warnings=decision.warnings,
        preflight_decision=decision.preflight_decision,
        preflight_context=decision.preflight_context,
        paper_path_note=decision.paper_path_note,
    )


@router.patch("/{recommendation_id}/review", response_model=PaperRecommendationResponse)
def review_recommendation(
    recommendation_id: UUID,
    request: PaperRecommendationReviewRequest,
    session: Annotated[Session, Depends(get_db_session)],
) -> PaperRecommendationResponse:
    """Review and approve/reject a recommendation.

    Moves the recommendation from DRAFT to APPROVED or REJECTED status.

    Parameters:
    - approved: True to approve, False to reject
    - review_notes: Optional notes about the review decision

    Returns:
    - Updated recommendation
    """
    service = PaperRecommendationService(session)
    rec = service.review_recommendation(
        recommendation_id,
        approved=request.approved,
        reviewed_by="operator",  # In production, use auth context
        notes=request.review_notes,
    )

    if not rec:
        raise HTTPException(status_code=404, detail=f"Recommendation {recommendation_id} not found")

    return PaperRecommendationResponse.model_validate(rec)
