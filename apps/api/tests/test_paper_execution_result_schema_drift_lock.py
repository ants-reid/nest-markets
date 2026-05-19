"""MH-DRIFTLOCK-PAPER-EXECUTION-RESULT-DATACLASS-SCHEMA-PIN

Pins ``paper_execution_service.PaperExecutionResult`` dataclass:
frozen=True and the 11-field set.
"""
from __future__ import annotations

import dataclasses

from app.services.paper_execution_service import PaperExecutionResult

_EXPECTED_FIELDS: frozenset[str] = frozenset(
    {
        "execution_id",
        "status",
        "asset",
        "timeframe",
        "side",
        "qty",
        "notional",
        "stop_price",
        "target_price",
        "fill_price",
        "reason",
    }
)


def test_paper_execution_result_is_frozen_dataclass() -> None:
    assert dataclasses.is_dataclass(PaperExecutionResult)
    assert PaperExecutionResult.__dataclass_params__.frozen is True, (
        "PaperExecutionResult must remain frozen=True."
    )


def test_paper_execution_result_field_set_pin() -> None:
    actual = frozenset(f.name for f in dataclasses.fields(PaperExecutionResult))
    assert actual == _EXPECTED_FIELDS, (
        f"PaperExecutionResult field drift. missing={sorted(_EXPECTED_FIELDS - actual)} "
        f"extra={sorted(actual - _EXPECTED_FIELDS)}"
    )
