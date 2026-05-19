"""MH-DRIFTLOCK-ORDER-RESULT-DATACLASS-SCHEMA-PIN

Pins ``broker_service.OrderResult`` dataclass shape and frozen state.
"""
from __future__ import annotations

import dataclasses

from app.services.broker_service import OrderResult

_EXPECTED_FIELDS: frozenset[str] = frozenset(
    {
        "broker_order_id",
        "status",
        "filled_price",
        "filled_quantity",
        "error_message",
        "submitted_at",
    }
)
_EXPECTED_FROZEN = False


def test_order_result_is_dataclass() -> None:
    assert dataclasses.is_dataclass(OrderResult), "OrderResult must remain a dataclass."


def test_order_result_frozen_state_pin() -> None:
    actual = OrderResult.__dataclass_params__.frozen
    assert actual is _EXPECTED_FROZEN, (
        f"OrderResult dataclass frozen-state drift: expected {_EXPECTED_FROZEN}, got {actual}."
    )


def test_order_result_field_set_pin() -> None:
    actual = frozenset(f.name for f in dataclasses.fields(OrderResult))
    assert actual == _EXPECTED_FIELDS, (
        f"OrderResult field drift. missing={sorted(_EXPECTED_FIELDS - actual)} "
        f"extra={sorted(actual - _EXPECTED_FIELDS)}"
    )
