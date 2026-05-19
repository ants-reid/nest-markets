"""Drift-lock: OrderRequest dataclass field catalog (cycle 68).

Pins fields of ``app.clients.broker.broker_interface.OrderRequest`` —
the wire contract every adapter consumes. A silent rename of
``quantity`` to ``qty`` would break order submission everywhere with
no test reaching the failure outside this one.

Test-only / additive.
"""

from __future__ import annotations

import dataclasses

from app.clients.broker.broker_interface import OrderRequest

EXPECTED_ORDER_REQUEST_FIELDS: tuple[str, ...] = (
    "ticker",
    "side",
    "quantity",
    "order_type",
    "limit_price",
    "stop_price",
    "tif",
    "outside_rth",
    "client_order_id",
)

SAFETY_REQUIRED_FIELDS: frozenset[str] = frozenset(
    {"ticker", "side", "quantity", "order_type"}
)


def _field_names() -> tuple[str, ...]:
    return tuple(f.name for f in dataclasses.fields(OrderRequest))


def test_order_request_field_catalog_exact_match() -> None:
    actual = _field_names()
    assert actual == EXPECTED_ORDER_REQUEST_FIELDS, (
        "OrderRequest field-catalog drift detected.\n"
        f"  expected: {EXPECTED_ORDER_REQUEST_FIELDS}\n"
        f"  actual:   {actual}\n"
        "Renaming or reordering broker-contract fields silently "
        "changes every adapter's input mapping."
    )


def test_safety_required_fields_present() -> None:
    actual = set(_field_names())
    missing = SAFETY_REQUIRED_FIELDS - actual
    assert not missing, (
        f"OrderRequest is missing safety-required field(s): {sorted(missing)}. "
        "These are the four fields BrokerService.submit_auto_order "
        "depends on; without them every auto submission would fail."
    )
