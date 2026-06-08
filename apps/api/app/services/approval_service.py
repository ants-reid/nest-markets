"""Deterministic approval workflow service for confirm-before-trade mode."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.db.enums import ApprovalStatus
from app.db.models import ApprovalRequest as ApprovalRequestModel
from app.db.models import AuditLog, RiskDecision

ApprovalStatusType = Literal["pending", "approved", "rejected", "expired"]
ExecutionModeType = Literal["paper", "confirm_live", "auto_live"]


@dataclass(frozen=True)
class ApprovalRequest:
    """Typed approval request object for stateless confirm-before-trade workflow."""

    request_id: UUID
    status: ApprovalStatusType
    created_at: datetime
    expires_at: datetime
    asset: str
    timeframe: str
    execution_mode: ExecutionModeType


class ApprovalService:
    """Approval workflow service — supports both stateless and session-based operation."""

    def __init__(self, session: Session | None = None) -> None:
        self._session = session

    # ------------------------------------------------------------------ #
    # Session-based DB API (used by tests; session must be provided)      #
    # ------------------------------------------------------------------ #

    def create_request(self, risk_decision_id_or_signal=None, reason_or_mode=None, *args, **kwargs):
        """Create an approval request.

        Session-based: create_request(risk_decision_id: UUID, reason: str)
        Stateless:     create_request(signal, execution_mode, risk_approved, ...)
        """
        if risk_decision_id_or_signal is None and "signal" in kwargs:
            risk_decision_id_or_signal = kwargs.pop("signal")
        if reason_or_mode is None and "execution_mode" in kwargs:
            reason_or_mode = kwargs.pop("execution_mode")

        # Legacy positional support for stateless calls:
        # create_request(signal, execution_mode, risk_approved, ttl_minutes?, now?)
        if len(args) > 0 and "risk_approved" not in kwargs:
            kwargs["risk_approved"] = args[0]
        if len(args) > 1 and "ttl_minutes" not in kwargs:
            kwargs["ttl_minutes"] = args[1]
        if len(args) > 2 and "now" not in kwargs:
            kwargs["now"] = args[2]

        if self._session is not None and isinstance(risk_decision_id_or_signal, UUID):
            return self._create_db_request(risk_decision_id_or_signal, reason_or_mode or "")
        # Stateless legacy path
        return self._create_stateless_request(
            risk_decision_id_or_signal, reason_or_mode, **kwargs
        )

    def _create_db_request(
        self,
        risk_decision_id: UUID,
        reason: str,
    ) -> ApprovalRequestModel:
        """Create a pending DB approval request after validating risk decision."""
        decision: RiskDecision | None = (
            self._session.query(RiskDecision)
            .filter(RiskDecision.id == risk_decision_id)
            .first()
        )
        if decision is None or not decision.approved:
            raise ValueError("risk decision is not approved")

        request = ApprovalRequestModel(
            risk_decision_id=risk_decision_id,
            status=ApprovalStatus.PENDING,
            timestamp=datetime.now(UTC),
        )
        self._session.add(request)

        audit = AuditLog(
            entity_type="approval_request",
            entity_id=risk_decision_id,
            event_type="approval_requested",
            payload_json={"reason": reason},
        )
        self._session.add(audit)
        self._session.commit()
        self._session.refresh(request)
        return request

    def approve_request(
        self,
        request_id: UUID,
        approved_by: str,
    ) -> ApprovalRequestModel:
        """Approve a pending request."""
        request = self._get_pending_request(request_id)
        request.status = ApprovalStatus.APPROVED
        request.approved_by = approved_by
        request.approved_at = datetime.now(UTC)
        self._session.commit()
        return request

    def reject_request(
        self,
        request_id: UUID,
        rejected_by: str,
        reason: str = "",
    ) -> ApprovalRequestModel:
        """Reject a pending request."""
        request = self._get_pending_request(request_id)
        request.status = ApprovalStatus.REJECTED
        request.rejected_by = rejected_by
        self._session.commit()
        return request

    def expire_request(
        self,
        request_id: UUID,
        reason: str = "",
    ) -> ApprovalRequestModel:
        """Expire a pending request."""
        request = self._get_pending_request(request_id)
        request.status = ApprovalStatus.EXPIRED
        request.expired_at = datetime.now(UTC)
        self._session.commit()
        return request

    def _get_pending_request(self, request_id: UUID) -> ApprovalRequestModel:
        request: ApprovalRequestModel | None = (
            self._session.query(ApprovalRequestModel)
            .filter(ApprovalRequestModel.id == request_id)
            .first()
        )
        if request is None:
            raise ValueError(f"approval request {request_id} not found")
        current_status = request.status.value if hasattr(request.status, "value") else str(request.status)
        if current_status != "pending":
            raise ValueError(f"expected pending approval request, got '{request.status}'")
        return request

    # ------------------------------------------------------------------ #
    # Stateless legacy API (used by existing route handlers)              #
    # ------------------------------------------------------------------ #

    def _create_stateless_request(
        self,
        signal,
        execution_mode,
        risk_approved: bool = False,
        ttl_minutes: int = 30,
        now: datetime | None = None,
    ) -> ApprovalRequest:
        if not risk_approved:
            raise ValueError("Cannot create approval request for non-approved risk decision")

        created_at = now or datetime.now(UTC)
        expires_at = created_at + timedelta(minutes=ttl_minutes)

        return ApprovalRequest(
            request_id=uuid4(),
            status="pending",
            created_at=created_at,
            expires_at=expires_at,
            asset=signal.asset,
            timeframe=signal.timeframe,
            execution_mode=execution_mode,
        )

    def approve(self, request: ApprovalRequest) -> ApprovalRequest:
        self._assert_pending(request)
        return replace(request, status="approved")

    def reject(self, request: ApprovalRequest) -> ApprovalRequest:
        self._assert_pending(request)
        return replace(request, status="rejected")

    def expire(self, request: ApprovalRequest, now: datetime | None = None) -> ApprovalRequest:
        self._assert_pending(request)
        current_time = now or datetime.now(UTC)
        if current_time < request.expires_at:
            raise ValueError("Cannot expire request before expires_at")
        return replace(request, status="expired")

    def _assert_pending(self, request: ApprovalRequest) -> None:
        if request.status != "pending":
            raise ValueError(f"Invalid transition from status '{request.status}'")
