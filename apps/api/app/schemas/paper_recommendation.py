"""Pydantic schemas for paper recommendations."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PaperRecommendationCreateRequest(BaseModel):
    """Request to draft a new paper trading recommendation."""

    signal_id: UUID | None = None
    model_version_id: UUID | None = None

    ticker: str = Field(..., min_length=1, max_length=20)
    side: str = Field(..., pattern="^(BUY|SELL)$")
    quantity: float = Field(..., gt=0)
    order_type: str = Field(..., pattern="^(MARKET|LIMIT|STOP|STOP_LIMIT)$")
    limit_price: float | None = None

    confidence: float | None = Field(None, ge=0.0, le=1.0)
    risk_score: float | None = Field(None, ge=0.0, le=1.0)
    rationale: str | None = None


class PaperRecommendationReviewRequest(BaseModel):
    """Request to review a recommendation draft."""

    approved: bool
    review_notes: str | None = None


class PaperRecommendationResponse(BaseModel):
    """Response model for a paper recommendation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    signal_id: UUID | None = None
    model_version_id: UUID | None = None

    ticker: str
    side: str
    quantity: float
    order_type: str
    limit_price: float | None = None

    confidence: float | None = None
    risk_score: float | None = None
    estimated_notional: float | None = None
    rationale: str | None = None

    status: str
    created_at: datetime
    reviewed_at: datetime | None = None
    reviewed_by: str | None = None
    review_notes: str | None = None

    executed_at: datetime | None = None
    paper_order_ids: list[str] | None = None


class PaperRecommendationListResponse(BaseModel):
    """List of paper recommendations."""

    items: list[PaperRecommendationResponse]
    total: int
