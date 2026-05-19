"""Thin orchestration layer for the MVP workflow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from sqlalchemy.orm import Session

from app.services.approval_service import ApprovalService
from app.services.live_execution_service import LiveExecutionRequest, LiveExecutionResult, LiveExecutionService
from app.services.paper_execution_service import PaperExecutionService
from app.services.persistence_approval_service import PersistenceApprovalService
from app.services.persistence_paper_execution_service import PersistencePaperExecutionService
from app.services.persistence_signal_service import PersistenceSignalService
from app.services.risk_service import RiskContext, RiskDecision, RiskService
from app.services.signal_service import SignalInput, SignalOutput


class SignalGenerator(Protocol):
    """Protocol for typed signal generation dependency."""

    async def generate_signal(self, signal_input: SignalInput) -> SignalOutput:
        """Generate a typed signal from a typed input."""


@dataclass(frozen=True)
class WorkflowResult:
    """Typed summary of one completed workflow run."""

    signal_id: UUID
    risk_approved: bool
    selected_execution_mode: str
    approval_request_id: UUID | None
    paper_execution_id: UUID | None
    blocked_reasons: list[str]
    live_execution_result: LiveExecutionResult | None


class WorkflowService:
    """Coordinate existing services and persistence mappers without owning business logic."""

    def __init__(
        self,
        session: Session,
        signal_service: SignalGenerator,
        risk_service: RiskService,
        approval_service: ApprovalService,
        paper_execution_service: PaperExecutionService,
        live_execution_service: LiveExecutionService,
        persistence_signal_service: PersistenceSignalService,
        persistence_approval_service: PersistenceApprovalService,
        persistence_paper_execution_service: PersistencePaperExecutionService,
    ) -> None:
        """Initialize workflow service with explicit dependencies."""
        self._session = session
        self._signal_service = signal_service
        self._risk_service = risk_service
        self._approval_service = approval_service
        self._paper_execution_service = paper_execution_service
        self._live_execution_service = live_execution_service
        self._persistence_signal_service = persistence_signal_service
        self._persistence_approval_service = persistence_approval_service
        self._persistence_paper_execution_service = persistence_paper_execution_service

    async def run(self, signal_input: SignalInput, risk_context: RiskContext) -> WorkflowResult:
        """Run the MVP workflow from signal generation through execution routing."""
        try:
            signal_output = await self._signal_service.generate_signal(signal_input)
            persisted_signal = self._persistence_signal_service.persist_signal(signal_output)

            risk_decision = self._risk_service.evaluate(signal_output, risk_context)
            self._persistence_signal_service.persist_risk_decision(persisted_signal.id, risk_decision)

            if risk_decision.selected_execution_mode == "blocked":
                result = self._blocked_result(persisted_signal.id, risk_decision)
            elif risk_decision.selected_execution_mode == "paper":
                result = self._run_paper_path(persisted_signal.id, signal_output, signal_input, risk_decision)
            elif risk_decision.selected_execution_mode == "confirm_live":
                result = self._run_confirm_live_path(persisted_signal.id, signal_output, risk_decision)
            elif risk_decision.selected_execution_mode == "auto_live":
                result = self._run_auto_live_path(signal_output, persisted_signal.id, signal_input, risk_decision)
            else:
                raise ValueError(
                    f"Unsupported execution mode '{risk_decision.selected_execution_mode}'"
                )

            self._session.commit()
            return result
        except Exception:
            self._session.rollback()
            raise

    def _blocked_result(self, signal_id: UUID, risk_decision: RiskDecision) -> WorkflowResult:
        """Build the summary for a blocked workflow."""
        return WorkflowResult(
            signal_id=signal_id,
            risk_approved=risk_decision.approved,
            selected_execution_mode=risk_decision.selected_execution_mode,
            approval_request_id=None,
            paper_execution_id=None,
            blocked_reasons=list(risk_decision.blocked_reasons),
            live_execution_result=None,
        )

    def _run_paper_path(
        self,
        signal_id: UUID,
        signal_output: SignalOutput,
        signal_input: SignalInput,
        risk_decision: RiskDecision,
    ) -> WorkflowResult:
        """Run paper execution and persist the resulting paper order."""
        paper_result = self._paper_execution_service.submit_order(
            signal=signal_output,
            allowed_risk_amount=risk_decision.allowed_risk_amount,
            latest_price=signal_input.latest_price,
        )
        persisted_order = self._persistence_paper_execution_service.persist_paper_execution(
            signal_id,
            paper_result,
        )

        return WorkflowResult(
            signal_id=signal_id,
            risk_approved=risk_decision.approved,
            selected_execution_mode=risk_decision.selected_execution_mode,
            approval_request_id=None,
            paper_execution_id=persisted_order.id,
            blocked_reasons=list(risk_decision.blocked_reasons),
            live_execution_result=None,
        )

    def _run_confirm_live_path(
        self,
        signal_id: UUID,
        signal_output: SignalOutput,
        risk_decision: RiskDecision,
    ) -> WorkflowResult:
        """Create and persist a pending approval request for confirm-live mode."""
        approval_request = self._approval_service.create_request(
            signal=signal_output,
            execution_mode="confirm_live",
            risk_approved=risk_decision.approved,
        )
        persisted_request = self._persistence_approval_service.persist_approval_request(
            signal_id,
            approval_request,
        )

        return WorkflowResult(
            signal_id=signal_id,
            risk_approved=risk_decision.approved,
            selected_execution_mode=risk_decision.selected_execution_mode,
            approval_request_id=persisted_request.id,
            paper_execution_id=None,
            blocked_reasons=list(risk_decision.blocked_reasons),
            live_execution_result=None,
        )

    def _run_auto_live_path(
        self,
        signal_output: SignalOutput,
        signal_id: UUID,
        signal_input: SignalInput,
        risk_decision: RiskDecision,
    ) -> WorkflowResult:
        """Call the live execution scaffold without persisting live trade rows."""
        live_request = self._build_live_request(signal_output, signal_input, risk_decision.allowed_risk_amount)
        live_result = self._live_execution_service.submit(live_request)

        return WorkflowResult(
            signal_id=signal_id,
            risk_approved=risk_decision.approved,
            selected_execution_mode=risk_decision.selected_execution_mode,
            approval_request_id=None,
            paper_execution_id=None,
            blocked_reasons=list(risk_decision.blocked_reasons),
            live_execution_result=live_result,
        )

    def _build_live_request(
        self,
        signal_output: SignalOutput,
        signal_input: SignalInput,
        allowed_risk_amount: float,
    ) -> LiveExecutionRequest:
        """Reuse existing paper execution sizing to shape a scaffold-only live request."""
        draft_result = self._paper_execution_service.submit_order(
            signal=signal_output,
            allowed_risk_amount=allowed_risk_amount,
            latest_price=signal_input.latest_price,
        )

        return LiveExecutionRequest(
            asset=signal_output.asset,
            side=draft_result.side,
            qty=draft_result.qty,
            notional=draft_result.notional,
            stop_price=signal_output.stop_price,
            target_price=signal_output.target_price,
            execution_mode="auto_live",
        )