"""Thin workflow API route — runs the MVP WorkflowService end to end."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.middleware.auth import api_key_auth
from app.middleware.idempotency import check_idempotency_key, release_idempotency_key
from app.services import audit_log_service
from app.clients.llm.router import LLMProviderRouter
from app.config import get_settings
from app.db.session import get_db_session
from app.schemas.workflow import WorkflowRunRequest, WorkflowRunResponse
from app.services.approval_service import ApprovalService
from app.services.execution_mode_service import ExecutionModeService
from app.services.live_execution_service import LiveExecutionService
from app.services.paper_execution_service import StatelessPaperExecutionService as PaperExecutionService
from app.services.persistence_approval_service import PersistenceApprovalService
from app.services.persistence_paper_execution_service import PersistencePaperExecutionService
from app.services.persistence_signal_service import PersistenceSignalService
from app.services.risk_profile_service import RiskProfileService
from app.services.risk_service import RiskContext, RiskEvaluator as RiskService
from app.services.signal_service import SignalInput, SignalService
from app.services.workflow_service import WorkflowService
from app.services.mock_signal_service import MockSignalService
from app.schemas.workflow import LiveExecutionResultResponse

router = APIRouter(prefix="/workflow", tags=["workflow"])



def _build_workflow_service(session: Session, use_mock: bool) -> WorkflowService:
    """Construct WorkflowService with all real dependencies except optional mock signal."""
    settings = get_settings()
    risk_service = RiskService(
        profile=RiskProfileService().get_default_profile(),
        execution_mode_service=ExecutionModeService(),
    )

    if use_mock:
        signal_service = MockSignalService()
    else:
        router_llm = LLMProviderRouter(settings)
        signal_service = SignalService(router=router_llm)

    return WorkflowService(
        session=session,
        signal_service=signal_service,
        risk_service=risk_service,
        approval_service=ApprovalService(),
        paper_execution_service=PaperExecutionService(),
        live_execution_service=LiveExecutionService(),
        persistence_signal_service=PersistenceSignalService(session),
        persistence_approval_service=PersistenceApprovalService(session),
        persistence_paper_execution_service=PersistencePaperExecutionService(session),
    )


@router.post("/run", response_model=WorkflowRunResponse)
async def run_workflow(
    request: WorkflowRunRequest,
    session: Annotated[Session, Depends(get_db_session)],
    _: Annotated[str, Depends(api_key_auth)] = None,
    idempotency_key: Annotated[str | None, Depends(check_idempotency_key)] = None,
) -> WorkflowRunResponse:
    """Run the full MVP workflow: signal → risk → route → persist."""
    signal_input = SignalInput(
        asset=request.signal_input.asset,
        timeframe=request.signal_input.timeframe,
        latest_price=request.signal_input.latest_price,
        feature_snapshot=request.signal_input.feature_snapshot,
        catalyst_context=request.signal_input.catalyst_context,
        risk_notes=request.signal_input.risk_notes,
    )
    risk_context = RiskContext(
        spread_bps=request.risk_context.spread_bps,
        daily_drawdown_pct=request.risk_context.daily_drawdown_pct,
        consecutive_losses=request.risk_context.consecutive_losses,
        minutes_since_last_loss=request.risk_context.minutes_since_last_loss,
        correlated_exposure_count=request.risk_context.correlated_exposure_count,
        open_positions_count=request.risk_context.open_positions_count,
        session_allowed=request.risk_context.session_allowed,
        kill_switch_active=request.risk_context.kill_switch_active,
        market_quality_flag=request.risk_context.market_quality_flag,
        account_equity=request.risk_context.account_equity,
        requested_execution_mode=request.risk_context.requested_execution_mode,
    )

    workflow_service = _build_workflow_service(session, use_mock=request.use_mock_signal)
    try:
        result = await workflow_service.run(signal_input, risk_context)
    except Exception:
        if idempotency_key:
            release_idempotency_key(idempotency_key)
        raise

    audit_log_service.log_workflow_run(
        asset=request.signal_input.asset,
        timeframe=request.signal_input.timeframe,
        execution_mode=request.risk_context.requested_execution_mode,
        outcome="approved" if result.risk_approved else "blocked",
        idempotency_key=idempotency_key,
    )

    live_result = None
    if result.live_execution_result is not None:
        live_result_obj = result.live_execution_result
        live_result = LiveExecutionResultResponse(
            accepted=live_result_obj.accepted,
            status=live_result_obj.status,
            reason=live_result_obj.reason,
        )

    return WorkflowRunResponse(
        signal_id=result.signal_id,
        risk_approved=result.risk_approved,
        selected_execution_mode=result.selected_execution_mode,
        approval_request_id=result.approval_request_id,
        paper_execution_id=result.paper_execution_id,
        blocked_reasons=result.blocked_reasons,
        live_execution_result=live_result,
    )
