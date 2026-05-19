"""Drift-lock pin: catalog of safety-related custom exception classes
including their MRO.

Cycle 61 — MH-DRIFTLOCK-EXCEPTION-CATALOG.

Why this pin exists
-------------------
Trading-safety code paths raise custom exceptions
(``AutoTradingBlockedError``, ``LiveTradingNotArmedError``,
``PaperPreflightBlockedError``, …) which downstream handlers catch *by
class*.  A silent base-class swap (e.g. inheriting from ``Warning``
instead of ``Exception``, or breaking the ``TradingControlError`` parent
chain) would silently break those ``except TradingControlError:`` handlers
without any test failure and without any guard-source change.

This pin freezes:
  1. the **set** of safety exception classes that must remain importable
     from their canonical modules, and
  2. the **MRO** (parent chain) of each class so a silent re-parenting
     is caught.

Test-only / additive: zero edits under ``apps/api/app/``; no migration.
"""

from __future__ import annotations

# Canonical imports — if any of these fail, the catalog is broken.
from app.services.broker_mode_guard import LiveExecutionBlockedError
from app.services.broker_service import PaperPreflightBlockedError
from app.services.live_execution_service import LiveExecutionDisabledError
from app.services.trading_control_service import (
    AutoTradingBlockedError,
    EmergencyStopActiveError,
    LiveTradingNotArmedError,
    TradingControlError,
    TradingControlMisconfiguredError,
)

# Each entry is (qualified_name, expected_mro_qualnames).  MRO is captured
# excluding the trailing ``object`` (always present) but INCLUDING
# ``Exception``/``BaseException`` so a regression that drops one is caught.
EXPECTED_EXCEPTION_CATALOG: dict[str, tuple[str, ...]] = {
    "app.services.trading_control_service.TradingControlError": (
        "TradingControlError",
        "Exception",
        "BaseException",
    ),
    "app.services.trading_control_service.TradingControlMisconfiguredError": (
        "TradingControlMisconfiguredError",
        "TradingControlError",
        "Exception",
        "BaseException",
    ),
    "app.services.trading_control_service.AutoTradingBlockedError": (
        "AutoTradingBlockedError",
        "TradingControlError",
        "Exception",
        "BaseException",
    ),
    "app.services.trading_control_service.LiveTradingNotArmedError": (
        "LiveTradingNotArmedError",
        "TradingControlError",
        "Exception",
        "BaseException",
    ),
    "app.services.trading_control_service.EmergencyStopActiveError": (
        "EmergencyStopActiveError",
        "TradingControlError",
        "Exception",
        "BaseException",
    ),
    "app.services.broker_service.PaperPreflightBlockedError": (
        "PaperPreflightBlockedError",
        "TradingControlError",
        "Exception",
        "BaseException",
    ),
    "app.services.broker_mode_guard.LiveExecutionBlockedError": (
        "LiveExecutionBlockedError",
        "Exception",
        "BaseException",
    ),
    "app.services.live_execution_service.LiveExecutionDisabledError": (
        "LiveExecutionDisabledError",
        "Exception",
        "BaseException",
    ),
}

# Subset whose parent-chain via TradingControlError is part of the safety
# contract: handlers in the codebase legitimately do
# ``except TradingControlError: ...`` to catch *any* control-layer block.
# Breaking the chain on any of these silently bypasses those handlers.
SAFETY_TRADING_CONTROL_SUBCLASSES: set[str] = {
    "app.services.trading_control_service.TradingControlMisconfiguredError",
    "app.services.trading_control_service.AutoTradingBlockedError",
    "app.services.trading_control_service.LiveTradingNotArmedError",
    "app.services.trading_control_service.EmergencyStopActiveError",
    "app.services.broker_service.PaperPreflightBlockedError",
}


_PINNED_CLASSES = (
    TradingControlError,
    TradingControlMisconfiguredError,
    AutoTradingBlockedError,
    LiveTradingNotArmedError,
    EmergencyStopActiveError,
    PaperPreflightBlockedError,
    LiveExecutionBlockedError,
    LiveExecutionDisabledError,
)


def _qual(cls: type) -> str:
    return f"{cls.__module__}.{cls.__qualname__}"


def _mro_qualnames(cls: type) -> tuple[str, ...]:
    # Strip trailing ``object`` to keep the catalog terse; everything is
    # implicitly an ``object``.
    return tuple(b.__qualname__ for b in cls.__mro__ if b is not object)


def test_safety_exception_catalog_exact_match() -> None:
    actual_keys = {_qual(c) for c in _PINNED_CLASSES}
    missing = set(EXPECTED_EXCEPTION_CATALOG.keys()) - actual_keys
    extra = actual_keys - set(EXPECTED_EXCEPTION_CATALOG.keys())
    assert not missing and not extra, (
        "Safety exception catalog drift detected. "
        f"Missing: {sorted(missing)}. Extra: {sorted(extra)}. "
        "Any change to the set of safety exception classes (rename, move, "
        "removal, addition) MUST be paired with an additive update here "
        "and a docs/build-ledger.md entry."
    )


def test_safety_exception_mro_unchanged() -> None:
    failures: list[str] = []
    for cls in _PINNED_CLASSES:
        qual = _qual(cls)
        expected = EXPECTED_EXCEPTION_CATALOG[qual]
        actual = _mro_qualnames(cls)
        if actual != expected:
            failures.append(
                f"  {qual}\n    expected: {expected}\n    actual:   {actual}"
            )
    assert not failures, (
        "Safety exception MRO drift detected. Re-parenting these classes "
        "silently breaks downstream `except TradingControlError:` and "
        "similar handlers. Any change MUST be reviewed.\n"
        + "\n".join(failures)
    )


def test_safety_subset_inherits_from_trading_control_error() -> None:
    """Stricter: every class in SAFETY_TRADING_CONTROL_SUBCLASSES must
    actually be a subclass of ``TradingControlError`` at runtime.

    This is redundant with the MRO test but exists separately so a
    regression is reported with a clear, actionable message rather than a
    diff of two MRO tuples.
    """
    by_qual = {_qual(c): c for c in _PINNED_CLASSES}
    failures: list[str] = []
    for qual in SAFETY_TRADING_CONTROL_SUBCLASSES:
        cls = by_qual[qual]
        if not issubclass(cls, TradingControlError):
            failures.append(
                f"  {qual} no longer inherits from TradingControlError"
            )
    assert not failures, (
        "Safety contract violated: the following classes must remain "
        "subclasses of TradingControlError so handlers can catch them "
        "uniformly:\n" + "\n".join(failures)
    )


def test_safety_exception_classes_are_exception_subclasses() -> None:
    """Defensive: none of the pinned classes may silently re-parent to
    ``Warning`` or to a non-Exception base."""
    failures: list[str] = []
    for cls in _PINNED_CLASSES:
        if not issubclass(cls, Exception):
            failures.append(f"  {_qual(cls)} no longer inherits from Exception")
        if issubclass(cls, Warning):
            failures.append(
                f"  {_qual(cls)} now inherits from Warning — would NOT halt control flow"
            )
    assert not failures, "\n".join(failures)
