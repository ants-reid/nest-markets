"""MH-DRIFTLOCK-ORDER-REQUEST-DATACLASS-SCHEMA-PIN

Pins ``broker_service.OrderRequest`` dataclass shape. Frozen state is
pinned (currently mutable) so a silent flip from mutable→frozen (or
vice versa) is loud.
"""
from __future__ import annotations

import dataclasses

from app.services.broker_service import OrderRequest

_EXPECTED_FIELDS: frozenset[str] = frozenset(
    {
        "ticker",
        "side",
        "quantity",
        "order_type",
        "limit_price",
        "stop_price",
        "tif",
        "outside_rth",
        "client_order_id",
    }
)
_EXPECTED_FROZEN = False


def test_order_request_is_dataclass() -> None:
    assert dataclasses.is_dataclass(OrderRequest), "OrderRequest must remain a dataclass."


def test_order_request_frozen_state_pin() -> None:
    actual = OrderRequest.__dataclass_params__.frozen
    assert actual is _EXPECTED_FROZEN, (
        f"OrderRequest dataclass frozen-state drift: expected {_EXPECTED_FROZEN}, got {actual}."
    )


def test_order_request_field_set_pin() -> None:
    actual = frozenset(f.name for f in dataclasses.fields(OrderRequest))
    assert actual == _EXPECTED_FIELDS, (
        f"OrderRequest field drift. missing={sorted(_EXPECTED_FIELDS - actual)} "
        f"extra={sorted(actual - _EXPECTED_FIELDS)}"
    )
