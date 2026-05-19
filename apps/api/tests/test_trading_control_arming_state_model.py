"""Model metadata tests for MH-125 trading control arming state."""

from __future__ import annotations

from sqlalchemy import CheckConstraint, UniqueConstraint

from app.db.models import TradingControlArmingState


def test_trading_control_arming_state_model_is_exported() -> None:
    assert TradingControlArmingState.__tablename__ == "trading_control_arming_states"


def test_trading_control_arming_state_declares_expected_columns_constraints_and_indexes() -> None:
    table = TradingControlArmingState.__table__

    assert set(table.c.keys()) >= {
        "scope",
        "trading_mode",
        "state",
        "armed_at",
        "armed_by",
        "expires_at",
        "last_enablement_status",
        "last_enablement_blockers",
        "last_enablement_warnings",
        "disarmed_at",
        "disarmed_by",
        "metadata_json",
    }
    assert table.c.state.server_default is not None

    unique_constraints = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    check_constraints = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    index_names = {index.name for index in table.indexes}

    assert "uq_trading_control_arming_states_scope_mode" in unique_constraints
    assert {
        "ck_trading_control_arming_states_state",
        "ck_trading_control_arming_states_enablement_status",
        "ck_trading_control_arming_states_armed_fields",
        "ck_trading_control_arming_states_disarmed_expiry",
    } <= check_constraints
    assert "ix_trading_control_arming_states_state_expires_at" in index_names
    assert "ix_trading_control_arming_states_updated_at" in index_names