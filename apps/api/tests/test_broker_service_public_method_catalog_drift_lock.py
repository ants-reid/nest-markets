"""Drift-lock: BrokerService public-method catalog (cycle 67).

Pins the set of public (non-underscore) methods on
``BrokerService``. Renaming ``submit_auto_order`` to anything else
would silently break the auto-trading guard surface; removing
``dry_run_order`` would silently disable the cockpit's dry-run path.

Test-only / additive.
"""

from __future__ import annotations

import inspect

from app.services.broker_service import BrokerService

EXPECTED_PUBLIC_METHODS: frozenset[str] = frozenset(
    {
        "cancel_order",
        "capture_daily_pnl_snapshot",
        "capture_pnl_snapshot",
        "dry_run_order",
        "ensure_connected",
        "get_account_info",
        "get_daily_pnl",
        "get_mode_metadata",
        "get_normalized_trade_events",
        "get_order_status",
        "get_positions",
        "normalize_and_stage_trade_events",
        "reconcile_positions",
        "submit_auto_order",
        "submit_order",
    }
)

SAFETY_REQUIRED_METHODS: frozenset[str] = frozenset(
    {
        "submit_auto_order",
        "submit_order",
        "dry_run_order",
        "cancel_order",
        "get_mode_metadata",
    }
)


def _public_methods() -> set[str]:
    return {
        name
        for name, _ in inspect.getmembers(BrokerService, predicate=inspect.isfunction)
        if not name.startswith("_")
    }


def test_broker_service_public_method_catalog_exact_match() -> None:
    actual = _public_methods()
    extra = actual - EXPECTED_PUBLIC_METHODS
    missing = EXPECTED_PUBLIC_METHODS - actual
    msg: list[str] = []
    if extra:
        msg.append("  Unexpected new BrokerService public method(s): "
                   + ", ".join(sorted(extra)))
    if missing:
        msg.append("  Missing expected BrokerService method(s): "
                   + ", ".join(sorted(missing)))
    assert not msg, (
        "BrokerService public-method catalog drift detected.\n"
        + "\n".join(msg)
        + "\nIf intentional, update EXPECTED_PUBLIC_METHODS and confirm "
        "no caller of a renamed/removed method silently routes around "
        "the auto-trading gate."
    )


def test_safety_required_broker_methods_present() -> None:
    actual = _public_methods()
    missing = SAFETY_REQUIRED_METHODS - actual
    assert not missing, (
        "SAFETY-required BrokerService methods missing: "
        f"{sorted(missing)}. submit_auto_order is the SOLE auto-intent "
        "submission path; dry_run_order is the cockpit preview; "
        "cancel_order is the only revocation path."
    )


def test_safety_subset_within_full_catalog() -> None:
    assert SAFETY_REQUIRED_METHODS <= EXPECTED_PUBLIC_METHODS, (
        "SAFETY_REQUIRED_METHODS is not a subset of "
        "EXPECTED_PUBLIC_METHODS — catalogs out of sync."
    )
