"""Pydantic schemas for scoring endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ScoringWeightsSchema(BaseModel):
    """Active scoring weight configuration."""

    signal_score: float = Field(..., ge=0.0, le=1.0, description="Weight for LLM signal_score")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Weight for model confidence")
    catalyst_score: float = Field(..., ge=0.0, le=1.0, description="Weight for catalyst_score")
    historical_win_rate: float = Field(..., ge=0.0, le=1.0, description="Weight for historical win rate")


class ScoringWeightsResponse(BaseModel):
    """Response envelope for active weights."""

    weights: ScoringWeightsSchema


class ScoreContributionsSchema(BaseModel):
    signal_score: float
    confidence: float
    catalyst_score: float
    historical_win_rate: float


class ScoreInputsSchema(BaseModel):
    signal_score: float
    confidence: float
    catalyst_score: float
    historical_win_rate: float


class ScoreExplanationResponse(BaseModel):
    """Composite score breakdown for a single signal."""

    signal_id: str
    composite_score: float
    contributions: ScoreContributionsSchema
    weights: ScoringWeightsSchema
    inputs: ScoreInputsSchema
