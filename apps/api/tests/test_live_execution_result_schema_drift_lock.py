"""MH-DRIFTLOCK-LIVE-EXECUTION-RESULT-DATACLASS-SCHEMA-PIN

Pins ``LiveExecutionResult`` dataclass: frozen=True, field set immutable.
Extending this silently could drop fields from the live-execution sentinel.
"""
from __future__ import annotations

import dataclasses

from app.services.live_execution_service import LiveExecutionResult

_EXPECTED_FIELDS: frozenset[str] = frozenset(
    {"accepted", "status", "reason", "processed_at", "broker_order_id"}
)


def test_live_execution_result_is_frozen_dataclass() -> None:
    assert dataclasses.is_dataclass(LiveExecutionResult)
    assert LiveExecutionResult.__dataclass_params__.frozen is True, (
        "LiveExecutionResult must remain frozen=True so the disabled-sentinel cannot be mutated."
    )


def test_live_execution_result_field_set_pin() -> None:
    actual = frozenset(f.name for f in dataclasses.fields(LiveExecutionResult))
    assert actual == _EXPECTED_FIELDS, (
        f"LiveExecutionResult field drift. missing={sorted(_EXPECTED_FIELDS - actual)} "
        f"extra={sorted(actual - _EXPECTED_FIELDS)}"
    )
