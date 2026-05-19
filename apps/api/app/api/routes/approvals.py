"""Thin approval workflow API routes for MVP."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.db.enums import ApprovalStatus
from app.schemas.approval import ApprovalCreateRequest, ApprovalRequestResponse
from app.schemas.execution import PaperExecutionResponse
from app.db.session import get_db_session
from app.services.approval_service import ApprovalService
from app.services.persistence_approval_service import PersistenceApprovalService
from app.services.persistence_paper_execution_service import PersistencePaperExecutionService
from app.services.persistence_signal_service import PersistenceSignalService
from app.services.persistence_alert_service import ActiveAlertRecord, AlertRuleState, PersistenceAlertService
from app.services.persistence_notification_service import NotificationRecord, PersistenceNotificationService
from app.services.paper_execution_service import StatelessPaperExecutionService as PaperExecutionService
from app.services.signal_service import SignalOutput

router = APIRouter(prefix="/approvals", tags=["approvals"])


class AlertRuleCreateRequest(BaseModel):
    """API request schema for creating one persisted alert rule."""

    model_config = ConfigDict(extra="forbid")

    asset: str = Field(min_length=1, max_length=50)
    condition: str = Field(min_length=1, max_length=200)


class AlertRuleSnoozeRequest(BaseModel):
    """API request schema for snoozing one alert rule."""

    model_config = ConfigDict(extra="forbid")

    minutes: int = Field(gt=0, le=1440)


class AlertRuleResponse(BaseModel):
    """API response schema for one persisted alert rule."""

    model_config = ConfigDict(extra="forbid")

    rule_id: UUID
    asset: str
    condition: str
    status: str
    created_at: datetime
    updated_at: datetime
    snoozed_until: datetime | None


class ActiveAlertResponse(BaseModel):
    """API response schema for one active alert derived from persisted rules."""

    model_config = ConfigDict(extra="forbid")

    alert_id: str
    rule_id: UUID
    execution_id: UUID
    asset: str
    status: str
    message: str
    level: str


class NotificationResponse(BaseModel):
    """API response schema for one in-app alert notification."""

    model_config = ConfigDict(extra="forbid")

    notification_id: str
    alert_id: str
    rule_id: UUID
    execution_id: UUID
    asset: str
    status: str
    message: str
    level: str
    is_read: bool
    read_at: datetime | None


def _to_rule_response(rule: AlertRuleState) -> AlertRuleResponse:
    """Map one materialized alert rule into route response schema."""
    return AlertRuleResponse(
        rule_id=rule.rule_id,
        asset=rule.asset,
        condition=rule.condition,
        status=rule.status,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
        snoozed_until=rule.snoozed_until,
    )


def _to_active_alert_response(alert: ActiveAlertRecord) -> ActiveAlertResponse:
    """Map one active alert record into route response schema."""
    return ActiveAlertResponse(
        alert_id=alert.alert_id,
        rule_id=alert.rule_id,
        execution_id=alert.execution_id,
        asset=alert.asset,
        status=alert.status,
        message=alert.message,
        level=alert.level,
    )


def _to_notification_response(notification: NotificationRecord) -> NotificationResponse:
    """Map one notification record into route response schema."""
    return NotificationResponse(
        notification_id=notification.notification_id,
        alert_id=notification.alert_id,
        rule_id=notification.rule_id,
        execution_id=notification.execution_id,
        asset=notification.asset,
        status=notification.status,
        message=notification.message,
        level=notification.level,
        is_read=notification.is_read,
        read_at=notification.read_at,
    )


@router.post("/create", response_model=ApprovalRequestResponse)
def create_approval_request(
    request: ApprovalCreateRequest,
    session: Annotated[Session, Depends(get_db_session)],
) -> ApprovalRequestResponse:
    """Create a typed pending approval request for confirm-before-trade mode."""
    signal = SignalOutput(**request.signal.model_dump(exclude={"signal_id"}))
    approval_request = ApprovalService().create_request(
        signal,
        request.execution_mode,
        risk_approved=request.risk_approved,
        ttl_minutes=request.ttl_minutes,
    )

    persisted_signal = PersistenceSignalService(session).persist_signal(signal)
    PersistenceApprovalService(session).persist_approval_request(persisted_signal.id, approval_request)
    session.commit()

    return ApprovalRequestResponse(**approval_request.__dict__)


@router.post("/alerts/rules", response_model=AlertRuleResponse)
def create_alert_rule(
    request: AlertRuleCreateRequest,
    session: Annotated[Session, Depends(get_db_session)],
) -> AlertRuleResponse:
    """Create one persisted alert rule for the alerts UI."""
    service = PersistenceAlertService(session)
    created = service.create_rule(asset=request.asset, condition=request.condition)
    session.commit()
    return _to_rule_response(created)


@router.get("/alerts/rules", response_model=list[AlertRuleResponse])
def list_alert_rules(
    session: Annotated[Session, Depends(get_db_session)],
) -> list[AlertRuleResponse]:
    """Return persisted alert rules for list views."""
    service = PersistenceAlertService(session)
    return [_to_rule_response(rule) for rule in service.list_rules()]


@router.post("/alerts/rules/{rule_id}/acknowledge", response_model=AlertRuleResponse)
def acknowledge_alert_rule(
    rule_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
) -> AlertRuleResponse:
    """Acknowledge one alert rule."""
    service = PersistenceAlertService(session)
    try:
        updated = service.acknowledge_rule(rule_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    session.commit()
    return _to_rule_response(updated)


@router.post("/alerts/rules/{rule_id}/snooze", response_model=AlertRuleResponse)
def snooze_alert_rule(
    rule_id: UUID,
    request: AlertRuleSnoozeRequest,
    session: Annotated[Session, Depends(get_db_session)],
) -> AlertRuleResponse:
    """Snooze one alert rule."""
    service = PersistenceAlertService(session)
    try:
        updated = service.snooze_rule(rule_id, request.minutes)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    session.commit()
    return _to_rule_response(updated)


@router.get("/alerts/active", response_model=list[ActiveAlertResponse])
def list_active_alerts(
    session: Annotated[Session, Depends(get_db_session)],
    include_visual_seed: Annotated[bool, Query(description="Include visual seed demo data")] = False,
) -> list[ActiveAlertResponse]:
    """Return active alerts generated from persisted rules and execution state."""
    service = PersistenceAlertService(session)
    alerts = service.list_active_alerts(include_visual_seed=include_visual_seed)
    return [_to_active_alert_response(alert) for alert in alerts]


@router.get("/alerts/notifications", response_model=list[NotificationResponse])
def list_alert_notifications(
    session: Annotated[Session, Depends(get_db_session)],
    include_visual_seed: Annotated[bool, Query(description="Include visual seed demo data")] = False,
) -> list[NotificationResponse]:
    """Return in-app notifications derived from persisted active alerts."""
    service = PersistenceNotificationService(session)
    return [_to_notification_response(item) for item in service.list_notifications(include_visual_seed=include_visual_seed)]


@router.post("/alerts/notifications/{notification_id}/read", response_model=NotificationResponse)
def mark_alert_notification_read(
    notification_id: str,
    session: Annotated[Session, Depends(get_db_session)],
    include_visual_seed: Annotated[bool, Query(description="Include visual seed demo data")] = False,
) -> NotificationResponse:
    """Mark one in-app alert notification as read."""
    service = PersistenceNotificationService(session)
    try:
        updated = service.mark_as_read(notification_id, include_visual_seed=include_visual_seed)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    session.commit()
    return _to_notification_response(updated)


def _load_persisted_approval_request(
    request_id: UUID,
    session: Session,
) -> tuple[object, object]:
    """Load persisted approval state and hydrate the typed request contract."""
    persistence_service = PersistenceApprovalService(session)
    row = persistence_service.get_approval_request(request_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Approval request '{request_id}' not found")

    try:
        approval_request = persistence_service.build_service_request(row)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return row, approval_request


def _persist_action_result(
    session: Session,
    signal_id: UUID,
    approval_request,
) -> ApprovalRequestResponse:
    """Persist one transitioned approval request and build the route response."""
    PersistenceApprovalService(session).persist_approval_request(signal_id, approval_request)
    session.commit()
    return ApprovalRequestResponse(**approval_request.__dict__)


@router.post("/{request_id}/approve", response_model=ApprovalRequestResponse)
def approve_approval_request(
    request_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
) -> ApprovalRequestResponse:
    """Transition one pending approval request to approved."""
    row, approval_request = _load_persisted_approval_request(request_id, session)

    try:
        approved_request = ApprovalService().approve(approval_request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    _ = row
    return _persist_action_result(session, row.signal_id, approved_request)


@router.post("/{request_id}/reject", response_model=ApprovalRequestResponse)
def reject_approval_request(
    request_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
) -> ApprovalRequestResponse:
    """Transition one pending approval request to rejected."""
    row, approval_request = _load_persisted_approval_request(request_id, session)

    try:
        rejected_request = ApprovalService().reject(approval_request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _persist_action_result(session, row.signal_id, rejected_request)


@router.post("/{request_id}/expire", response_model=ApprovalRequestResponse)
def expire_approval_request(
    request_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
) -> ApprovalRequestResponse:
    """Transition one pending approval request to expired when its TTL has elapsed."""
    row, approval_request = _load_persisted_approval_request(request_id, session)

    try:
        expired_request = ApprovalService().expire(approval_request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _persist_action_result(session, row.signal_id, expired_request)


@router.post("/{request_id}/execute", response_model=PaperExecutionResponse)
def execute_approved_approval_request(
    request_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
) -> PaperExecutionResponse:
    """Execute one approved confirm-live request through the MVP paper execution path."""
    row, _approval_request = _load_persisted_approval_request(request_id, session)
    if row.status != ApprovalStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Approval request must be approved before execution")

    persistence_service = PersistenceApprovalService(session)
    try:
        signal_output, allowed_risk_amount, latest_price = persistence_service.build_paper_execution_inputs(row)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    execution_result = PaperExecutionService().submit_order(
        signal=signal_output,
        allowed_risk_amount=allowed_risk_amount,
        latest_price=latest_price,
    )
    PersistencePaperExecutionService(session).persist_paper_execution(row.signal_id, execution_result)
    session.commit()

    return PaperExecutionResponse(**execution_result.__dict__)
