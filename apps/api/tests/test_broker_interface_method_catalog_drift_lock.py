"""Drift-lock: BrokerInterface Protocol method catalog (cycle 69).

Pins the four methods on ``BrokerInterface``. Adding a new method
silently makes existing adapters non-compliant; removing one breaks
``BrokerService`` consumers.

Test-only / additive.
"""

from __future__ import annotations

import inspect

from app.clients.broker.broker_interface import BrokerInterface

EXPECTED_PROTOCOL_METHODS: frozenset[str] = frozenset(
    {
        "submit_order",
        "cancel_order",
        "get_account_info",
        "get_positions",
    }
)

SAFETY_REQUIRED_METHODS: frozenset[str] = frozenset(
    {"submit_order", "cancel_order"}
)


def _protocol_methods() -> set[str]:
    return {
        name
        for name, _ in inspect.getmembers(BrokerInterface, inspect.isfunction)
        if not name.startswith("_")
    }


def test_broker_interface_method_catalog_exact_match() -> None:
    actual = _protocol_methods()
    extra = actual - EXPECTED_PROTOCOL_METHODS
    missing = EXPECTED_PROTOCOL_METHODS - actual
    msg: list[str] = []
    if extra:
        msg.append("  Unexpected new BrokerInterface method(s): "
                   + ", ".join(sorted(extra)))
    if missing:
        msg.append("  Missing expected BrokerInterface method(s): "
                   + ", ".join(sorted(missing)))
    assert not msg, (
        "BrokerInterface Protocol method catalog drift.\n"
        + "\n".join(msg)
        + "\nIf adding a method, update EXPECTED_PROTOCOL_METHODS AND "
        "implement it on every adapter (currently IBKRAdapter)."
    )


def test_safety_required_protocol_methods_present() -> None:
    actual = _protocol_methods()
    missing = SAFETY_REQUIRED_METHODS - actual
    assert not missing, (
        "BrokerInterface missing safety-required method(s): "
        f"{sorted(missing)}. submit_order is the only adapter-level "
        "submission seam; cancel_order is the only revocation seam."
    )
