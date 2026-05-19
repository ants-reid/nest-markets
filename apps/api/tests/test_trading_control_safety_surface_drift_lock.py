"""Cycle 54 — Trading-control safety surface pin.

Pins the **public surface** of ``app.services.trading_control_service``:
the names of the four canonical safety functions, their callable type,
and their async-vs-sync nature. Also pins the four custom exception
class names.

Why this matters:
  * Renaming any of these silently breaks every callsite at import time
    (which IS a loud failure) — but renaming the EXCEPTION CLASSES would
    break ``except`` blocks elsewhere and silently cause safety errors
    to be swallowed by a broader ``except Exception`` clause.
  * Removing one of these is the path to silently weakening the safety
    perimeter (the function still appears callable from the outside if
    a test stub is left in place).
  * Adding a new function here is fine; this pin is anti-removal /
    anti-rename, not anti-addition.

Drift-lock notes:
    * Pure additive test; no production code change.
    * The auto-trading gate ``assert_auto_trading_allowed()`` is the
      function this pin most defends; this lock is itself part of the
      drift-lock perimeter.
    * Does NOT call any of these functions — pure introspection.
"""

from __future__ import annotations

import inspect

from app.services import trading_control_service as tcs


# Canonical safety functions. Removing or renaming any of these is a
# safety regression by definition.
PINNED_SAFETY_FUNCTIONS: list[str] = [
    "assert_mode_configuration_consistent",
    "assert_emergency_stop_clear",
    "assert_live_trading_armed",
    "assert_manual_trading_allowed",
    "assert_auto_trading_allowed",
    "assert_order_submission_allowed",
]


# Canonical exception classes. Renaming these would silently break
# ``except`` blocks at callsites.
PINNED_EXCEPTION_CLASSES: list[str] = [
    "TradingControlError",
    "TradingControlMisconfiguredError",
    "AutoTradingBlockedError",
    "LiveTradingNotArmedError",
    "EmergencyStopActiveError",
]


def test_safety_functions_exist():
    for name in PINNED_SAFETY_FUNCTIONS:
        assert hasattr(tcs, name), (
            f"trading_control_service.{name} is missing. Removing a "
            "safety function is a regression — every callsite that "
            "depended on it now silently bypasses the gate."
        )
        attr = getattr(tcs, name)
        assert callable(attr), (
            f"trading_control_service.{name} exists but is not callable: "
            f"{type(attr).__name__}. A safety function being shadowed by "
            "a non-callable silently breaks every caller."
        )


def test_safety_functions_are_synchronous():
    """All canonical safety asserts are synchronous so they can be called
    from any context (including non-async code paths). Drift to async
    would silently break every sync caller (the coroutine would be
    discarded and the gate would never run)."""
    for name in PINNED_SAFETY_FUNCTIONS:
        fn = getattr(tcs, name)
        assert not inspect.iscoroutinefunction(fn), (
            f"trading_control_service.{name} drifted to async. Sync "
            "callers will silently discard the coroutine, leaving the "
            "safety gate unrun. Keep the assert_* functions synchronous."
        )


def test_assert_auto_trading_allowed_raises_unconditionally():
    """The cornerstone safety guarantee: ``assert_auto_trading_allowed()``
    must raise unconditionally in the current build (auto trading is
    OFF). Drift here is the single highest-impact silent regression
    possible in this codebase."""
    raised = False
    try:
        tcs.assert_auto_trading_allowed()
    except tcs.AutoTradingBlockedError:
        raised = True
    except Exception as e:  # noqa: BLE001
        # Any other safety error is also acceptable (we just want to
        # confirm it doesn't return cleanly).
        raised = True
        assert isinstance(e, tcs.TradingControlError), (
            f"assert_auto_trading_allowed raised {type(e).__name__}, "
            "which is NOT a TradingControlError. Safety errors should "
            "always be in the TradingControlError hierarchy so that "
            "broad ``except`` blocks at callsites can catch them."
        )
    assert raised, (
        "assert_auto_trading_allowed() returned cleanly. Auto trading "
        "is supposed to be OFF — this is the cornerstone safety guarantee. "
        "If you are intentionally enabling auto trading, this pin is "
        "the signal that you must update the test in the SAME PR."
    )


def test_exception_hierarchy_intact():
    for name in PINNED_EXCEPTION_CLASSES:
        assert hasattr(tcs, name), (
            f"trading_control_service.{name} exception class is missing. "
            "Renaming/removing breaks every ``except`` block downstream."
        )
        cls = getattr(tcs, name)
        assert isinstance(cls, type), (
            f"trading_control_service.{name} is not a class: "
            f"{type(cls).__name__}."
        )
        assert issubclass(cls, Exception), (
            f"trading_control_service.{name} is not an Exception subclass."
        )


def test_specific_exceptions_subclass_trading_control_error():
    """Specific safety errors must remain in the TradingControlError
    hierarchy so callers' broad ``except TradingControlError`` keeps
    catching every safety event."""
    for name in [
        "TradingControlMisconfiguredError",
        "AutoTradingBlockedError",
        "LiveTradingNotArmedError",
        "EmergencyStopActiveError",
    ]:
        cls = getattr(tcs, name)
        assert issubclass(cls, tcs.TradingControlError), (
            f"{name} no longer subclasses TradingControlError. "
            "Callers using ``except TradingControlError`` will silently "
            "stop catching this safety event."
        )


def test_assert_auto_trading_allowed_takes_no_arguments():
    """Pin signature: zero positional args. Drift to require an arg
    would silently turn every existing call into a TypeError, which
    callers might catch and swallow."""
    sig = inspect.signature(tcs.assert_auto_trading_allowed)
    required_params = [
        p for p in sig.parameters.values()
        if p.default is inspect.Parameter.empty
        and p.kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        )
    ]
    assert required_params == [], (
        f"assert_auto_trading_allowed() now requires args: "
        f"{[p.name for p in required_params]}. Existing callsites pass "
        "no args — drift here silently raises TypeError that callers "
        "may swallow with broad ``except``."
    )
