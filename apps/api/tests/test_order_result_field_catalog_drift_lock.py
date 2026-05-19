"""Drift-lock: OrderResult dataclass field catalog (cycle 68).

Pins fields of ``app.clients.broker.broker_interface.OrderResult``.
A silent rename of ``broker_order_id`` would break the audit-log
correlation back to the broker's order id.

Test-only / additive.
"""

from __future__ import annotations

import dataclasses

from app.clients.broker.broker_interface import OrderResult

EXPECTED_ORDER_RESULT_FIELDS: tuple[str, ...] = (
    "broker_order_id",
    "status",
    "filled_price",
    "filled_quantity",
    "error_message",
    "submitted_at",
)

SAFETY_REQUIRED_FIELDS: frozenset[str] = frozenset(
    {"broker_order_id", "status", "submitted_at"}
)


def _field_names() -> tuple[str, ...]:
    return tuple(f.name for f in dataclasses.fields(OrderResult))


def test_order_result_field_catalog_exact_match() -> None:
    actual = _field_names()
    assert actual == EXPECTED_ORDER_RESULT_FIELDS, (
        "OrderResult field-catalog drift detected.\n"
        f"  expected: {EXPECTED_ORDER_RESULT_FIELDS}\n"
        f"  actual:   {actual}\n"
        "Adapter return shape changed — every audit row written from "
        "submit_auto_order will be missing fields."
    )


def test_safety_required_fields_present() -> None:
    actual = set(_field_names())
    missing = SAFETY_REQUIRED_FIELDS - actual
    assert not missing, (
        f"OrderResult is missing safety-required field(s): {sorted(missing)}. "
        "These three fields are used by audit_log_service.log_broker_"
        "order_event to attribute the submission."
    )
