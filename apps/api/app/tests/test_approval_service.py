from datetime import UTC, datetime, timedelta

import pytest

from app.services.approval_service import ApprovalService
from app.services.signal_service import SignalOutput


def _signal() -> SignalOutput:
    return SignalOutput(
        asset="EURUSD",
        timeframe="1h",
        direction="long",
        regime="trend",
        setup_type="trend_pullback",
        entry_zone=(1.081, 1.082),
        stop_price=1.078,
        target_price=1.088,
        confidence=0.74,
        horizon_label="1_3_days",
        catalyst_type="macro",
        catalyst_score=0.6,
        catalyst_summary="Macro context supportive",
        thesis="Trend continuation",
        invalidators=["Break below 1.078"],
        signal_score=75.0,
        should_trade=True,
    )


def test_approval_request_creation() -> None:
    service = ApprovalService()
    now = datetime.now(UTC)

    request = service.create_request(
        signal=_signal(),
        execution_mode="confirm_live",
        risk_approved=True,
        ttl_minutes=30,
        now=now,
    )

    assert request.status == "pending"
    assert request.asset == "EURUSD"
    assert request.execution_mode == "confirm_live"
    assert request.expires_at == now + timedelta(minutes=30)


def test_approval_transitions_approve_reject_expire() -> None:
    service = ApprovalService()
    now = datetime.now(UTC)

    pending_a = service.create_request(_signal(), "confirm_live", True, now=now)
    approved = service.approve(pending_a)
    assert approved.status == "approved"

    pending_b = service.create_request(_signal(), "confirm_live", True, now=now)
    rejected = service.reject(pending_b)
    assert rejected.status == "rejected"

    pending_c = service.create_request(_signal(), "confirm_live", True, ttl_minutes=1, now=now)
    expired = service.expire(pending_c, now=now + timedelta(minutes=2))
    assert expired.status == "expired"


def test_invalid_approval_transition() -> None:
    service = ApprovalService()
    pending = service.create_request(_signal(), "confirm_live", True)
    approved = service.approve(pending)

    with pytest.raises(ValueError):
        service.reject(approved)


def test_create_request_raises_when_risk_not_approved() -> None:
    service = ApprovalService()

    with pytest.raises(ValueError):
        service.create_request(
            signal=_signal(),
            execution_mode="confirm_live",
            risk_approved=False,
        )


def test_expire_raises_when_now_is_before_expires_at() -> None:
    service = ApprovalService()
    now = datetime.now(UTC)
    pending = service.create_request(
        signal=_signal(),
        execution_mode="confirm_live",
        risk_approved=True,
        ttl_minutes=30,
        now=now,
    )

    with pytest.raises(ValueError):
        service.expire(pending, now=now + timedelta(minutes=5))
