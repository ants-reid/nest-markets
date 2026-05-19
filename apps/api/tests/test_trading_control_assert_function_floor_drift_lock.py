"""MH-DRIFTLOCK-TRADING-CONTROL-ASSERT-FUNCTION-FLOOR

Pins that the safety ``assert_*`` functions remain callable on
``trading_control_service``. Complements the existing public-API catalog by
specifically guarding the assertion entry-points used by every trading path.
"""
from __future__ import annotations

import inspect

from app.services import trading_control_service

_REQUIRED_ASSERTS: frozenset[str] = frozenset(
    {
        "assert_emergency_stop_clear",
        "assert_live_trading_armed",
        "assert_manual_trading_allowed",
        "assert_auto_trading_allowed",
        "assert_order_submission_allowed",
        "assert_mode_configuration_consistent",
    }
)


def test_trading_control_assert_functions_present() -> None:
    missing: list[str] = []
    for name in _REQUIRED_ASSERTS:
        fn = getattr(trading_control_service, name, None)
        if fn is None or not callable(fn):
            missing.append(name)
    assert not missing, (
        f"trading_control_service missing safety assert_* functions: {sorted(missing)}. "
        "Removing or renaming these silently weakens trade-path gating."
    )


def test_trading_control_assert_auto_trading_signature_no_args() -> None:
    fn = trading_control_service.assert_auto_trading_allowed
    sig = inspect.signature(fn)
    assert len(sig.parameters) == 0, (
        f"assert_auto_trading_allowed signature drift: "
        f"expected zero parameters, got {list(sig.parameters)!r}. "
        "Adding parameters could let callers smuggle bypass flags."
    )


def test_trading_control_assert_function_count_floor() -> None:
    actual = {
        n for n in dir(trading_control_service)
        if n.startswith("assert_") and callable(getattr(trading_control_service, n))
    }
    assert _REQUIRED_ASSERTS.issubset(actual), (
        f"Required assert_* set not subset of actual: missing={sorted(_REQUIRED_ASSERTS - actual)}"
    )
    assert len(actual) >= len(_REQUIRED_ASSERTS)
