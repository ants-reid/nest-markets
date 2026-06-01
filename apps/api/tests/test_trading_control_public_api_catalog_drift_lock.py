"""Drift-lock: trading_control_service public-API catalog (cycle 67).

Pins the set of public functions exported by
``app.services.trading_control_service``. The cycle-59 source pin
covers BYTES; this catalog covers EXISTENCE — silently dropping
``assert_auto_trading_allowed`` from the module surface would cause
import-time failures only at the call sites that imported it
explicitly (and would silently pass at any site that imported the
whole module and used ``getattr``).

Test-only / additive.
"""

from __future__ import annotations

import inspect

from app.services import trading_control_service as tc

EXPECTED_PUBLIC_FUNCTIONS: frozenset[str] = frozenset(
    {
        "assert_auto_trading_allowed",
        "assert_emergency_stop_clear",
        "assert_live_trading_armed",
        "assert_manual_trading_allowed",
        "assert_mode_configuration_consistent",
        "assert_order_submission_allowed",
        "get_trading_mode",
        "is_controlled_auto_paper_allowed",
    }
)

SAFETY_REQUIRED_FUNCTIONS: frozenset[str] = frozenset(
    {
        "assert_auto_trading_allowed",
        "assert_live_trading_armed",
        "assert_emergency_stop_clear",
        "assert_order_submission_allowed",
    }
)

EXPECTED_EXCEPTION_CLASSES: frozenset[str] = frozenset(
    {
        "TradingControlError",
        "TradingControlMisconfiguredError",
        "AutoTradingBlockedError",
        "LiveTradingNotArmedError",
        "EmergencyStopActiveError",
    }
)


def _public_functions() -> set[str]:
    return {
        name
        for name, fn in inspect.getmembers(tc, predicate=inspect.isfunction)
        if not name.startswith("_") and fn.__module__ == tc.__name__
    }


def _public_classes() -> set[str]:
    return {
        name
        for name, cls in inspect.getmembers(tc, predicate=inspect.isclass)
        if not name.startswith("_") and cls.__module__ == tc.__name__
    }


def test_trading_control_function_catalog_exact_match() -> None:
    actual = _public_functions()
    extra = actual - EXPECTED_PUBLIC_FUNCTIONS
    missing = EXPECTED_PUBLIC_FUNCTIONS - actual
    msg: list[str] = []
    if extra:
        msg.append("  Unexpected new trading_control_service function(s): "
                   + ", ".join(sorted(extra)))
    if missing:
        msg.append("  Missing expected trading_control_service function(s): "
                   + ", ".join(sorted(missing)))
    assert not msg, (
        "trading_control_service public-function catalog drift "
        "detected.\n" + "\n".join(msg)
        + "\nIf intentional, update EXPECTED_PUBLIC_FUNCTIONS AND "
        "confirm every caller of a renamed/removed guard is migrated."
    )


def test_safety_guards_present_in_public_surface() -> None:
    actual = _public_functions()
    missing = SAFETY_REQUIRED_FUNCTIONS - actual
    assert not missing, (
        "SAFETY-required trading_control guards missing from public "
        f"surface: {sorted(missing)}. Removing any of these silently "
        "removes the gate they enforce."
    )


def test_trading_control_exception_classes_present() -> None:
    actual = _public_classes()
    missing = EXPECTED_EXCEPTION_CLASSES - actual
    extra_specific = (actual - EXPECTED_EXCEPTION_CLASSES) - {"TradingControlState"}
    msg: list[str] = []
    if missing:
        msg.append("  Missing trading_control exception class(es): "
                   + ", ".join(sorted(missing)))
    if extra_specific:
        msg.append("  Unexpected new trading_control class(es): "
                   + ", ".join(sorted(extra_specific)))
    assert not msg, (
        "trading_control_service exception/class catalog drift.\n"
        + "\n".join(msg)
        + "\nNew exception types route through different except blocks "
        "in the broker / workflow / execution paths."
    )
