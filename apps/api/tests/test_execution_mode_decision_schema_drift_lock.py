"""MH-DRIFTLOCK-EXECUTION-MODE-DECISION-SCHEMA-PIN

Pins ``ExecutionModeDecision`` dataclass: frozen=True and exact field
set. Mutability would let downstream code rewrite the routing decision.
"""
from __future__ import annotations

import dataclasses

from app.services.execution_mode_service import ExecutionModeDecision

_EXPECTED_FIELDS: frozenset[str] = frozenset(
    {"proceed_to_execution", "selected_execution_mode"}
)


def test_execution_mode_decision_is_frozen_dataclass() -> None:
    assert dataclasses.is_dataclass(ExecutionModeDecision), (
        "ExecutionModeDecision must remain a dataclass."
    )
    assert ExecutionModeDecision.__dataclass_params__.frozen is True, (
        "ExecutionModeDecision must remain frozen=True so routing decisions are immutable."
    )


def test_execution_mode_decision_field_set_pin() -> None:
    actual = frozenset(f.name for f in dataclasses.fields(ExecutionModeDecision))
    assert actual == _EXPECTED_FIELDS, (
        f"ExecutionModeDecision field drift. missing={sorted(_EXPECTED_FIELDS - actual)} "
        f"extra={sorted(actual - _EXPECTED_FIELDS)}"
    )
