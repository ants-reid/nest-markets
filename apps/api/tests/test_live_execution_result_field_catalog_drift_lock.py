"""Drift-lock: LiveExecutionResult dataclass field catalog (cycle 70).

Pins the response contract returned by ``LiveExecutionService.submit``.
Renaming ``broker_order_id`` here would silently break audit/cockpit
consumers even with the cycle-66 SHA pin still green.

Test-only / additive.
"""

from __future__ import annotations

import dataclasses
import typing

from app.services.live_execution_service import LiveExecutionResult

EXPECTED_FIELD_NAMES: tuple[str, ...] = (
    "accepted",
    "status",
    "reason",
    "processed_at",
    "broker_order_id",
)

SAFETY_REQUIRED_FIELDS: frozenset[str] = frozenset(
    {"accepted", "status", "broker_order_id", "processed_at"}
)

EXPECTED_STATUS_VALUES: frozenset[str] = frozenset(
    {"disabled", "submitted", "paper_submitted"}
)


def test_live_execution_result_field_catalog() -> None:
    actual = tuple(f.name for f in dataclasses.fields(LiveExecutionResult))
    assert actual == EXPECTED_FIELD_NAMES, (
        "LiveExecutionResult field catalog drift.\n"
        f"  expected: {EXPECTED_FIELD_NAMES}\n"
        f"  actual:   {actual}"
    )


def test_live_execution_result_safety_fields_present() -> None:
    actual = {f.name for f in dataclasses.fields(LiveExecutionResult)}
    missing = SAFETY_REQUIRED_FIELDS - actual
    assert not missing, (
        f"LiveExecutionResult missing safety field(s): {sorted(missing)}."
    )


def test_live_execution_result_is_frozen() -> None:
    assert dataclasses.is_dataclass(LiveExecutionResult)
    params = LiveExecutionResult.__dataclass_params__  # type: ignore[attr-defined]
    assert params.frozen, (
        "LiveExecutionResult must remain frozen=True to prevent post-hoc "
        "mutation of audit-relevant fields."
    )


def test_live_execution_result_status_literal_values() -> None:
    """Status literal must remain {disabled, submitted, paper_submitted} —
    a new 'live_submitted' value would imply live trading is wired."""
    hints = typing.get_type_hints(LiveExecutionResult)
    status_type = hints["status"]
    args = frozenset(typing.get_args(status_type))
    assert args == EXPECTED_STATUS_VALUES, (
        "LiveExecutionResult.status literal drift.\n"
        f"  expected: {sorted(EXPECTED_STATUS_VALUES)}\n"
        f"  actual:   {sorted(args)}\n"
        "Adding a 'live_submitted' value would imply live trading "
        "wiring — review against the drift lock before updating this."
    )
