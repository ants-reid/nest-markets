"""Drift-lock: IBKRAdapter public method catalog (cycle 69).

Pins the public method names on ``IBKRAdapter`` — the sole live
broker adapter. Renaming ``submit_order`` here would silently break
``BrokerService.submit_auto_order``'s underlying call without
matching ``BrokerInterface``.

Test-only / additive.
"""

from __future__ import annotations

import inspect

from app.clients.broker.ibkr_adapter import IBKRAdapter

EXPECTED_PUBLIC_METHODS: frozenset[str] = frozenset(
    {
        "cancel_order",
        "connect",
        "disconnect",
        "get_account_info",
        "get_history",
        "get_option_contracts",
        "get_option_months",
        "get_option_strikes",
        "get_order_status",
        "get_pnl",
        "get_positions",
        "get_snapshot",
        "get_trades",
        "modify_order",
        "resolve_conid",
        "submit_bracket_order",
        "submit_oca_order",
        "submit_order",
        "tickle",
        "unsubscribe_all_snapshots",
        "unsubscribe_snapshot",
    }
)

SAFETY_REQUIRED_METHODS: frozenset[str] = frozenset(
    {
        "submit_order",
        "cancel_order",
        "get_account_info",
        "get_positions",
        "get_order_status",
    }
)


def _public_methods() -> set[str]:
    return {
        name
        for name, _ in inspect.getmembers(IBKRAdapter, inspect.isfunction)
        if not name.startswith("_")
    }


def test_ibkr_adapter_method_catalog_exact_match() -> None:
    actual = _public_methods()
    extra = actual - EXPECTED_PUBLIC_METHODS
    missing = EXPECTED_PUBLIC_METHODS - actual
    msg: list[str] = []
    if extra:
        msg.append("  Unexpected new IBKRAdapter method(s): "
                   + ", ".join(sorted(extra)))
    if missing:
        msg.append("  Missing expected IBKRAdapter method(s): "
                   + ", ".join(sorted(missing)))
    assert not msg, (
        "IBKRAdapter public-method catalog drift detected.\n"
        + "\n".join(msg)
        + "\nIf intentional, update EXPECTED_PUBLIC_METHODS and ensure "
        "the corresponding BrokerInterface method (where applicable) "
        "is also present so the adapter still satisfies the Protocol."
    )


def test_safety_required_ibkr_methods_present() -> None:
    actual = _public_methods()
    missing = SAFETY_REQUIRED_METHODS - actual
    assert not missing, (
        f"IBKRAdapter is missing safety-required method(s): {sorted(missing)}. "
        "These are the methods BrokerService relies on for the auto / "
        "manual / status / reconcile paths."
    )
