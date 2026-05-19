"""Paper trading recommendation drafting endpoints (MH-36)."""
from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.paper_recommendation import (
    PaperRecommendationCreateRequest,
    PaperRecommendationListResponse,
    PaperRecommendationResponse,
    PaperRecommendationReviewRequest,
)
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
