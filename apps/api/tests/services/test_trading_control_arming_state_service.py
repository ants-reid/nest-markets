"""Service tests for MH-125 durable arming state behavior."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from app.db.models import TradingControlArmingState
from app.services import audit_log_service
from app.services.trading_control_arming_state_service import (
    TradingControlArmingAuditSummary,
    TradingControlArmingReadbackPosture,
    TradingControlArmingStateService,
    _FAIL_CLOSED_REASONS,
)


def _build_session(rows: list[TradingControlArmingState]) -> MagicMock:
    session = MagicMock()
    session.query.return_value.filter.return_value.all.return_value = rows
    return session


def _build_row(*, state: str = "disarmed", expires_at: datetime | None = None) -> TradingControlArmingState:
    return TradingControlArmingState(
        scope="auto_paper",
        trading_mode="paper",
        state=state,
        armed_at=datetime.now(UTC),
        armed_by="ops",
        expires_at=expires_at,
    )


def _audit_event(**overrides) -> dict:
    event = {
        "event": "auto_paper_arming_action",
        "ts": datetime(2026, 5, 1, 14, 0, 0, tzinfo=UTC).isoformat(),
        "action": "arm",
        "requested_by": "ops@example.com",
        "reason": "operator approval",
        "result_status": "armed",
        "client_request_id": "req-123",
        "failure_reasons": [],
        "warning_codes": [],
        "arming_state_before": "disarmed",
        "arming_state_after": "armed",
    }
    event.update(overrides)
    return event


def test_readback_contract_dataclass_field_sets_are_locked():
    assert tuple(TradingControlArmingAuditSummary.__dataclass_fields__) == (
        "event_type",
        "recorded_at",
        "action",
        "result_status",
        "requested_by",
        "reason",
        "client_request_id",
        "arming_state_before",
        "arming_state_after",
        "failure_reasons",
        "warning_codes",
    )
    assert tuple(TradingControlArmingReadbackPosture.__dataclass_fields__) == (
        "status",
        "arming_state",
        "scope",
        "trading_mode",
        "evaluated_at",
        "fail_closed_reason",
        "durable_row_present",
        "duplicate_rows_detected",
        "stored_state",
        "armed_at",
        "armed_by",
        "arm_reason",
        "expires_at",
        "expired",
        "last_enablement_checked_at",
        "last_enablement_status",
        "last_enablement_blockers",
        "last_enablement_warnings",
        "client_request_id",
        "disarmed_at",
        "disarmed_by",
        "disarm_reason",
        "last_audit",
    )


def test_readback_fail_closed_reason_vocabulary_is_locked():
    assert _FAIL_CLOSED_REASONS == {
        "durable_state_missing",
        "durable_state_duplicate",
        "durable_state_invalid",
        "durable_state_expired",
        "durable_state_read_failed",
    }


def test_get_effective_state_defaults_to_disarmed_when_row_missing():
    service = TradingControlArmingStateService(_build_session([]))

    assert service.get_effective_state() == "disarmed"
    assert service.is_currently_armed() is False


def test_get_effective_state_returns_armed_for_valid_unexpired_row():
    row = _build_row(state="armed", expires_at=datetime.now(UTC) + timedelta(minutes=30))
    service = TradingControlArmingStateService(_build_session([row]))

    assert service.get_effective_state() == "armed"
    assert service.is_currently_armed() is True


def test_get_effective_state_fails_closed_for_expired_duplicate_and_invalid_rows():
    expired = _build_row(state="armed", expires_at=datetime.now(UTC) - timedelta(minutes=1))
    invalid = _build_row(state="unexpected", expires_at=datetime.now(UTC) + timedelta(minutes=30))

    assert TradingControlArmingStateService(_build_session([expired])).get_effective_state() == "disarmed"
    assert TradingControlArmingStateService(_build_session([invalid])).get_effective_state() == "disarmed"
    assert TradingControlArmingStateService(_build_session([expired, invalid])).get_effective_state() == "disarmed"


def test_arm_state_updates_existing_row_without_creating_duplicate():
    row = _build_row(state="disarmed", expires_at=None)
    session = _build_session([row])
    service = TradingControlArmingStateService(session)
    expires_at = datetime.now(UTC) + timedelta(hours=1)

    updated = service.arm_state(
        armed_by="ops",
        expires_at=expires_at,
        arm_reason="preflight verified",
        last_enablement_status="ready",
        last_enablement_blockers=[],
        last_enablement_warnings=["history_window_short"],
        client_request_id="req-123",
    )

    assert updated is row
    assert row.state == "armed"
    assert row.expires_at == expires_at
    assert row.arm_reason == "preflight verified"
    assert row.last_enablement_status == "ready"
    assert row.client_request_id == "req-123"
    session.add.assert_not_called()
    session.commit.assert_called_once()
    session.refresh.assert_called_once_with(row)


def test_arm_state_creates_missing_row_and_rejects_duplicate_write_surface():
    missing_session = _build_session([])
    missing_service = TradingControlArmingStateService(missing_session)
    expires_at = datetime.now(UTC) + timedelta(hours=1)

    created = missing_service.arm_state(armed_by="ops", expires_at=expires_at)

    assert created.scope == "auto_paper"
    assert created.trading_mode == "paper"
    assert created.state == "armed"
    missing_session.add.assert_called_once_with(created)

    duplicate_row = _build_row(state="disarmed", expires_at=None)
    duplicate_session = _build_session([duplicate_row, _build_row(state="disarmed", expires_at=None)])
    duplicate_service = TradingControlArmingStateService(duplicate_session)

    with pytest.raises(ValueError, match="Duplicate arming state rows"):
        duplicate_service.arm_state(armed_by="ops", expires_at=expires_at)


def test_disarm_state_clears_expiry_and_sets_disarm_metadata():
    row = _build_row(state="armed", expires_at=datetime.now(UTC) + timedelta(hours=1))
    session = _build_session([row])
    service = TradingControlArmingStateService(session)

    disarmed = service.disarm_state(disarmed_by="ops", disarm_reason="operator reset")

    assert disarmed is row
    assert row.state == "disarmed"
    assert row.expires_at is None
    assert row.disarmed_by == "ops"
    assert row.disarm_reason == "operator reset"
    session.commit.assert_called_once()
    session.refresh.assert_called_once_with(row)


def test_get_readback_posture_returns_armed_for_valid_unexpired_row(monkeypatch):
    row = _build_row(state="armed", expires_at=datetime.now(UTC) + timedelta(minutes=30))
    service = TradingControlArmingStateService(_build_session([row]))
    monkeypatch.setattr(audit_log_service, "get_latest_auto_paper_arming_action", lambda: _audit_event())

    posture = service.get_readback_posture(now=datetime.now(UTC))

    assert posture.status == "armed"
    assert posture.arming_state == "armed"
    assert posture.fail_closed_reason is None
    assert posture.durable_row_present is True
    assert posture.duplicate_rows_detected is False
    assert posture.stored_state == "armed"
    assert posture.expired is False
    assert posture.last_audit is not None
    assert set(posture.__dict__) == {
        "status",
        "arming_state",
        "scope",
        "trading_mode",
        "evaluated_at",
        "fail_closed_reason",
        "durable_row_present",
        "duplicate_rows_detected",
        "stored_state",
        "armed_at",
        "armed_by",
        "arm_reason",
        "expires_at",
        "expired",
        "last_enablement_checked_at",
        "last_enablement_status",
        "last_enablement_blockers",
        "last_enablement_warnings",
        "client_request_id",
        "disarmed_at",
        "disarmed_by",
        "disarm_reason",
        "last_audit",
    }
    assert set(posture.last_audit.__dict__) == {
        "event_type",
        "recorded_at",
        "action",
        "result_status",
        "requested_by",
        "reason",
        "client_request_id",
        "arming_state_before",
        "arming_state_after",
        "failure_reasons",
        "warning_codes",
    }
    assert posture.last_audit.event_type == "auto_paper_arming_action"
    assert posture.last_audit.requested_by == "ops@example.com"
    assert posture.last_audit.failure_reasons == []
    assert posture.last_audit.warning_codes == []


def test_get_readback_posture_returns_disarmed_for_valid_disarmed_row(monkeypatch):
    row = _build_row(state="disarmed", expires_at=None)
    row.armed_at = None
    row.armed_by = None
    row.disarmed_by = "ops"
    row.disarm_reason = "manual reset"
    service = TradingControlArmingStateService(_build_session([row]))
    monkeypatch.setattr(audit_log_service, "get_latest_auto_paper_arming_action", lambda: None)

    posture = service.get_readback_posture(now=datetime.now(UTC))

    assert posture.status == "disarmed"
    assert posture.arming_state == "disarmed"
    assert posture.fail_closed_reason is None
    assert posture.durable_row_present is True
    assert posture.stored_state == "disarmed"
    assert posture.disarmed_by == "ops"
    assert posture.disarm_reason == "manual reset"
    assert posture.last_audit is None


@pytest.mark.parametrize(
    ("rows", "expected_reason", "expected_present", "expected_duplicate"),
    [
        ([], "durable_state_missing", False, False),
        ([_build_row(state="disarmed", expires_at=None), _build_row(state="disarmed", expires_at=None)], "durable_state_duplicate", True, True),
    ],
)
def test_get_readback_posture_classifies_missing_and_duplicate_rows(
    monkeypatch,
    rows,
    expected_reason,
    expected_present,
    expected_duplicate,
):
    service = TradingControlArmingStateService(_build_session(rows))
    monkeypatch.setattr(audit_log_service, "get_latest_auto_paper_arming_action", lambda: None)

    posture = service.get_readback_posture(now=datetime.now(UTC))

    assert posture.status == "fail_closed"
    assert posture.arming_state == "disarmed"
    assert posture.fail_closed_reason == expected_reason
    assert posture.durable_row_present is expected_present
    assert posture.duplicate_rows_detected is expected_duplicate


def test_get_readback_posture_classifies_invalid_and_expired_rows(monkeypatch):
    invalid = _build_row(state="unexpected", expires_at=datetime.now(UTC) + timedelta(minutes=30))
    expired = _build_row(state="armed", expires_at=datetime.now(UTC) - timedelta(minutes=1))
    monkeypatch.setattr(audit_log_service, "get_latest_auto_paper_arming_action", lambda: None)

    invalid_posture = TradingControlArmingStateService(_build_session([invalid])).get_readback_posture(now=datetime.now(UTC))
    expired_posture = TradingControlArmingStateService(_build_session([expired])).get_readback_posture(now=datetime.now(UTC))

    assert invalid_posture.status == "fail_closed"
    assert invalid_posture.fail_closed_reason == "durable_state_invalid"
    assert invalid_posture.stored_state == "unexpected"
    assert invalid_posture.expired is False

    assert expired_posture.status == "fail_closed"
    assert expired_posture.fail_closed_reason == "durable_state_expired"
    assert expired_posture.stored_state == "armed"
    assert expired_posture.expired is True


def test_get_readback_posture_classifies_read_failure_and_ignores_audit_failure(monkeypatch):
    session = MagicMock()
    session.query.return_value.filter.return_value.all.side_effect = RuntimeError("db down")
    service = TradingControlArmingStateService(session)
    monkeypatch.setattr(audit_log_service, "get_latest_auto_paper_arming_action", lambda: (_ for _ in ()).throw(RuntimeError("audit down")))

    posture = service.get_readback_posture(now=datetime.now(UTC))

    assert posture.status == "fail_closed"
    assert posture.arming_state == "disarmed"
    assert posture.fail_closed_reason == "durable_state_read_failed"
    assert posture.durable_row_present is False
    assert posture.duplicate_rows_detected is False
    assert posture.last_audit is None


def test_readback_audit_summary_boundary_excludes_raw_audit_payload_fields(monkeypatch):
    row = _build_row(state="armed", expires_at=datetime.now(UTC) + timedelta(minutes=30))
    service = TradingControlArmingStateService(_build_session([row]))
    monkeypatch.setattr(
        audit_log_service,
        "get_latest_auto_paper_arming_action",
        lambda: _audit_event(
            enablement_status="ready",
            enablement_blockers=["unused"],
            extra_debug_key="should_not_escape",
        ),
    )

    posture = service.get_readback_posture(now=datetime.now(UTC))

    assert posture.last_audit is not None
    assert not hasattr(posture.last_audit, "enablement_status")
    assert not hasattr(posture.last_audit, "enablement_blockers")
    assert not hasattr(posture.last_audit, "extra_debug_key")