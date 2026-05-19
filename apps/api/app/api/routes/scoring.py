"""Scoring configuration endpoints.

GET /scoring/active  — Return the currently active scoring weights.
GET /scoring/explain/{signal_id}  — Return composite score breakdown for a signal.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db_session as get_db
from app.db.models.signal import Signal
from app.schemas.scoring import (
    ScoreContributionsSchema,
    ScoreExplanationResponse,
    ScoreInputsSchema,
    ScoringWeightsResponse,
    ScoringWeightsSchema,
)
from app.services.runtime.scoring_config_service import ScoringConfigService
from app.services.runtime.scoring_service import ScoringService

router = APIRouter(prefix="/scoring", tags=["scoring"])

_config_service = ScoringConfigService()
_scoring_service = ScoringService(_config_service)


@router.get("/active", response_model=ScoringWeightsResponse)
def get_active_weights() -> ScoringWeightsResponse:
    """Return the currently active composite scoring weights."""
    weights = _config_service.get_active_weights()
    return ScoringWeightsResponse(
        weights=ScoringWeightsSchema(
            signal_score=weights.signal_score,
            confidence=weights.confidence,
            catalyst_score=weights.catalyst_score,
            historical_win_rate=weights.historical_win_rate,
        )
    )


@router.get("/explain/{signal_id}", response_model=ScoreExplanationResponse)
def explain_signal_score(
    signal_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ScoreExplanationResponse:
    """Return a composite score breakdown for a given signal."""
    signal = db.get(Signal, signal_id)
    if signal is None:
        raise HTTPException(status_code=404, detail="Signal not found")

    explanation = _scoring_service.explain(
        signal_score=float(signal.signal_score or 0.0),
        confidence=float(signal.confidence or 0.0),
        catalyst_score=float(signal.catalyst_score or 0.0),
    )

    return ScoreExplanationResponse(
        signal_id=str(signal_id),
        composite_score=explanation["composite_score"],
        contributions=ScoreContributionsSchema(**explanation["contributions"]),
        weights=ScoringWeightsSchema(**explanation["weights"]),
        inputs=ScoreInputsSchema(**explanation["inputs"]),
    )
