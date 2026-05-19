"""Thin deterministic risk API routes for MVP."""

from __future__ import annotations

from fastapi import APIRouter

from app.schemas.risk import RiskDecisionResponse, RiskEvaluateRequest
from app.services.execution_mode_service import ExecutionModeService
from app.services.risk_profile_service import RiskProfileService
from app.services.risk_service import RiskContext, RiskEvaluator as RiskService
from app.services.signal_service import SignalOutput

router = APIRouter(prefix="/risk", tags=["risk"])


@router.post("/evaluate", response_model=RiskDecisionResponse)
def evaluate_risk(request: RiskEvaluateRequest) -> RiskDecisionResponse:
    """Evaluate a signal against deterministic risk rules."""
    signal = SignalOutput(**request.signal.model_dump(exclude={"signal_id"}))
    risk_context = RiskContext(**request.risk_context.model_dump())

    risk_service = RiskService(
        profile=RiskProfileService().get_default_profile(),
        execution_mode_service=ExecutionModeService(),
    )
    decision = risk_service.evaluate(signal=signal, context=risk_context)
    return RiskDecisionResponse(**decision.__dict__)
