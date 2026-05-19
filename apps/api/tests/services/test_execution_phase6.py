"""Tests for paper execution, approval workflow, and live scaffold."""

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.db.models import ApprovalRequest, AuditLog, PaperOrder, RiskDecision
from app.services.approval_service import ApprovalService
from app.services.live_execution_service import LiveExecutionDisabledError, LiveExecutionService
from app.services.paper_execution_service import PaperExecutionService


@pytest.fixture
def mock_session() -> MagicMock:
    """Create mock SQLAlchemy session."""
    session = MagicMock(spec=Session)

    def _refresh(obj):
        if getattr(obj, "id", None) is None:
            obj.id = uuid4()

    session.refresh.side_effect = _refresh
    return session


def _approved_risk_decision() -> RiskDecision:
    """Return an approved risk decision."""
    return RiskDecision(
        id=uuid4(),
        signal_id=uuid4(),
        approved="approved",
        timestamp=datetime.now(UTC),
    )


def _rejected_risk_decision() -> RiskDecision:
    """Return a rejected risk decision."""
    return RiskDecision(
        id=uuid4(),
        signal_id=uuid4(),
        approved="rejected",
        timestamp=datetime.now(UTC),
    )


class TestPaperExecutionService:
    """Tests for paper order and fill simulation."""

    def test_create_order_requires_approved_risk_decision(self, mock_session):
        """create_order should reject non-approved risk decisions."""
        mock_session.query.return_value.filter.return_value.first.return_value = (
            _rejected_risk_decision()
        )
        service = PaperExecutionService(mock_session)

        with pytest.raises(ValueError, match="not approved"):
            service.create_order(
                risk_decision_id=uuid4(),
                asset_id=uuid4(),
                direction="long",
                quantity=100,
            )

    def test_create_order_creates_pending_order_and_audit(self, mock_session):
        """create_order should persist pending order and audit hook."""
        decision = _approved_risk_decision()
        mock_session.query.return_value.filter.return_value.first.return_value = decision
        service = PaperExecutionService(mock_session)

        result = service.create_order(
            risk_decision_id=decision.id,
            asset_id=uuid4(),
            direction="long",
            quantity=50,
            limit_price=101.25,
        )

        assert result.status == "pending"
        assert result.direction == "buy"

        added_types = [type(call.args[0]) for call in mock_session.add.call_args_list]
        assert PaperOrder in added_types
        assert AuditLog in added_types

    def test_simulate_fill_transitions_pending_to_filled(self, mock_session):
        """simulate_fill should move state from pending to filled when full quantity is filled."""
        order_id = uuid4()
        order = PaperOrder(
            id=order_id,
            asset_id=uuid4(),
            risk_decision_id=uuid4(),
            timestamp=datetime.now(UTC),
            direction="buy",
            quantity=10,
            status="pending",
            filled_quantity=0.0,
        )
        mock_session.query.return_value.filter.return_value.first.return_value = order

        service = PaperExecutionService(mock_session)
        result = service.simulate_fill(order_id, fill_price=99.5)

        assert result.status == "filled"
        assert result.filled_quantity == 10
        assert order.status == "filled"

        added_types = [type(call.args[0]) for call in mock_session.add.call_args_list]
        assert AuditLog in added_types

    def test_simulate_fill_partial_keeps_pending(self, mock_session):
        """Partial fills should keep the order in pending status."""
        order_id = uuid4()
        order = PaperOrder(
            id=order_id,
            asset_id=uuid4(),
            risk_decision_id=uuid4(),
            timestamp=datetime.now(UTC),
            direction="buy",
            quantity=10,
            status="pending",
            filled_quantity=0.0,
        )
        mock_session.query.return_value.filter.return_value.first.return_value = order

        service = PaperExecutionService(mock_session)
        result = service.simulate_fill(order_id, fill_price=100.0, fill_quantity=4)

        assert result.status == "pending"
        assert result.filled_quantity == 4
        assert order.status == "pending"

    def test_cancel_order_transitions_pending_to_canceled(self, mock_session):
        """cancel_order should move state from pending to canceled."""
        order_id = uuid4()
        order = PaperOrder(
            id=order_id,
            asset_id=uuid4(),
            risk_decision_id=uuid4(),
            timestamp=datetime.now(UTC),
            direction="sell",
            quantity=10,
            status="pending",
            filled_quantity=0.0,
        )
        mock_session.query.return_value.filter.return_value.first.return_value = order

        service = PaperExecutionService(mock_session)
        result = service.cancel_order(order_id, reason="manual cancel")

        assert result.status == "canceled"
        assert order.status == "canceled"

    def test_create_then_fill_full_transition(self, mock_session):
        """create + simulate_fill should transition none -> pending -> filled."""
        decision = _approved_risk_decision()

        created_order = PaperOrder(
            id=uuid4(),
            asset_id=uuid4(),
            risk_decision_id=decision.id,
            timestamp=datetime.now(UTC),
            direction="buy",
            quantity=12,
            status="pending",
            filled_quantity=0.0,
        )

        mock_session.query.return_value.filter.return_value.first.side_effect = [
            decision,
            created_order,
        ]

        service = PaperExecutionService(mock_session)
        created = service.create_order(
            risk_decision_id=decision.id,
            asset_id=created_order.asset_id,
            direction="long",
            quantity=12,
        )
        result = service.simulate_fill(created.id, fill_price=102.0)

        assert result.status == "filled"
        assert result.filled_quantity == 12


class TestApprovalService:
    """Tests for approval request workflow and transitions."""

    def test_create_request_requires_approved_risk_decision(self, mock_session):
        """create_request should reject non-approved risk decisions."""
        mock_session.query.return_value.filter.return_value.first.return_value = (
            _rejected_risk_decision()
        )
        service = ApprovalService(mock_session)

        with pytest.raises(ValueError, match="not approved"):
            service.create_request(uuid4(), reason="needs review")

    def test_create_request_sets_pending_and_audit(self, mock_session):
        """create_request should persist pending request and audit record."""
        decision = _approved_risk_decision()
        mock_session.query.return_value.filter.return_value.first.return_value = decision
        service = ApprovalService(mock_session)

        output = service.create_request(decision.id, reason="manual confirmation")
        assert output.status == "pending"

        added_types = [type(call.args[0]) for call in mock_session.add.call_args_list]
        assert ApprovalRequest in added_types
        assert AuditLog in added_types

    def test_approve_request_transitions_pending_to_approved(self, mock_session):
        """approve_request should move pending request to approved."""
        request = ApprovalRequest(
            id=uuid4(),
            risk_decision_id=uuid4(),
            timestamp=datetime.now(UTC),
            status="pending",
        )
        mock_session.query.return_value.filter.return_value.first.return_value = request

        service = ApprovalService(mock_session)
        output = service.approve_request(request.id, approved_by="alice")

        assert output.status == "approved"
        assert request.status == "approved"
        assert request.approved_by == "alice"
        assert request.approved_at is not None

    def test_reject_request_transitions_pending_to_rejected(self, mock_session):
        """reject_request should move pending request to rejected."""
        request = ApprovalRequest(
            id=uuid4(),
            risk_decision_id=uuid4(),
            timestamp=datetime.now(UTC),
            status="pending",
        )
        mock_session.query.return_value.filter.return_value.first.return_value = request

        service = ApprovalService(mock_session)
        output = service.reject_request(request.id, rejected_by="bob", reason="too risky")

        assert output.status == "rejected"
        assert request.status == "rejected"

    def test_expire_request_transitions_pending_to_expired(self, mock_session):
        """expire_request should move pending request to expired."""
        request = ApprovalRequest(
            id=uuid4(),
            risk_decision_id=uuid4(),
            timestamp=datetime.now(UTC),
            status="pending",
        )
        mock_session.query.return_value.filter.return_value.first.return_value = request

        service = ApprovalService(mock_session)
        output = service.expire_request(request.id, reason="timeout")

        assert output.status == "expired"
        assert request.status == "expired"
        assert request.expired_at is not None

    def test_transition_blocked_when_request_not_pending(self, mock_session):
        """approve_request should fail when request already finalised."""
        request = ApprovalRequest(
            id=uuid4(),
            risk_decision_id=uuid4(),
            timestamp=datetime.now(UTC),
            status="approved",
        )
        mock_session.query.return_value.filter.return_value.first.return_value = request
        service = ApprovalService(mock_session)

        with pytest.raises(ValueError, match="expected pending"):
            service.approve_request(request.id, approved_by="alice")


class TestLiveExecutionService:
    """Tests for disabled live execution scaffold."""

    def test_is_enabled_always_false(self, mock_session):
        """Live execution must remain disabled in MVP."""
        service = LiveExecutionService(mock_session)
        assert service.is_enabled() is False

    def test_submit_order_raises_disabled_error_and_audits(self, mock_session):
        """submit_order should always raise and still trigger audit hook."""
        service = LiveExecutionService(mock_session)

        with pytest.raises(LiveExecutionDisabledError, match="disabled in MVP"):
            service.submit_order(
                risk_decision_id=uuid4(),
                asset_id=uuid4(),
                direction="buy",
                quantity=10,
            )

        added_types = [type(call.args[0]) for call in mock_session.add.call_args_list]
        assert AuditLog in added_types

    def test_cancel_order_raises_disabled_error(self, mock_session):
        """cancel_order should always raise while scaffold is disabled."""
        service = LiveExecutionService(mock_session)

        with pytest.raises(LiveExecutionDisabledError):
            service.cancel_order("broker-123")
