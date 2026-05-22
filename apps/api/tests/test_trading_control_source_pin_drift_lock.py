"""Drift-lock: SHA-256 hash-pin the source of the central trading-control
guards.

Cycle 59 — MH-DRIFTLOCK-TRADING-CONTROL-SOURCE-PIN (pure additive
test-only).

Why
---
Cycle 53–58 catalog pins detect *line-number* changes and *symbol
removal*, but they would not detect a silent edit to the *body* of
``assert_auto_trading_allowed`` (e.g. swapping ``raise`` for ``return``
to no-op the gate). This test pins the SHA-256 of
``inspect.getsource(...)`` for the four guard functions. Any byte-level
edit changes the hash and fails the test in PR review.

Pinned functions
----------------
* ``app.services.trading_control_service.assert_auto_trading_allowed``
* ``app.services.trading_control_service.assert_order_submission_allowed``
* ``app.services.broker_service.BrokerService.submit_auto_order``
* ``app.services.broker_service.BrokerService._submit_order_for_intent``

When you legitimately edit one of these functions (e.g. the eventual
MH-147/MH-148-C unlock), recompute the hash and update the pin in the
same PR — and document the change in docs/build-ledger.md.

Drift-lock guarantees
---------------------
* Read-only test — no DB, no HTTP, no monkey-patching.
* Auto-paper enforcement remains OFF.
* Auto trading remains OFF.
* Live trading remains OFF.
* ``assert_auto_trading_allowed()`` is unchanged (and now byte-for-byte
  pinned).
"""

from __future__ import annotations

import hashlib
import inspect

from app.services.broker_service import BrokerService
from app.services.trading_control_service import (
    assert_auto_trading_allowed,
    assert_order_submission_allowed,
)


# Pinned SHA-256 hashes of inspect.getsource(fn) for each guard, taken
# at cycle 59 against the unchanged-since-MH-36B safety surface.
EXPECTED_HASHES: dict[str, str] = {
    "assert_auto_trading_allowed":
        "a4ea8ee5d23d693ca635306d0cdf706e4e66be93a2a0c6c40ed48ec56a842452",
    "assert_order_submission_allowed":
        "490d9e879fb708d59aa0fe51b3efc797dc16fdae097848ab2587a511ea62750b",
    "BrokerService.submit_auto_order":
        "95a41e7ee8ae2442fd208fac1c3553308a859a3d68b637f052883c3c6447c19c",
    "BrokerService._submit_order_for_intent":
        "27df4656222fdf8e70930d5d4849dc0966a0cd7e85093ae11358c50d3ffd2e3f",
}

# (label, callable) pairs. Order does not matter; the assertion is per-key.
_FUNCTIONS = [
    ("assert_auto_trading_allowed", assert_auto_trading_allowed),
    ("assert_order_submission_allowed", assert_order_submission_allowed),
    ("BrokerService.submit_auto_order", BrokerService.submit_auto_order),
    ("BrokerService._submit_order_for_intent", BrokerService._submit_order_for_intent),
]


def _hash(fn) -> str:
    return hashlib.sha256(inspect.getsource(fn).encode("utf-8")).hexdigest()


def test_trading_control_source_hash_pinned() -> None:
    drift: list[tuple[str, str, str]] = []
    for label, fn in _FUNCTIONS:
        actual = _hash(fn)
        expected = EXPECTED_HASHES[label]
        if actual != expected:
            drift.append((label, expected, actual))
    assert not drift, (
        "Trading-control safety guard source drift detected. The body "
        "of one or more central safety functions has changed. "
        f"Drifted: {drift}. If the edit is intentional (e.g. an "
        "MH-147/MH-148-C unlock paired with explicit risk review), "
        "update EXPECTED_HASHES in tests/test_trading_control_source_"
        "pin_drift_lock.py and append a build-ledger entry that "
        "documents WHY the guard logic changed and confirms that "
        "auto/live trading remain OFF (or the explicit phase that "
        "unlocks them)."
    )


def test_assert_auto_trading_allowed_still_raises() -> None:
    """Behaviour pin: the guard must still raise unconditionally."""
    import pytest as _pytest
    from app.services.trading_control_service import AutoTradingBlockedError
    with _pytest.raises(AutoTradingBlockedError):
        assert_auto_trading_allowed()


def test_submit_auto_order_routes_through_intent_helper() -> None:
    """Source-level invariant: ``submit_auto_order`` must call the
    shared ``_submit_order_for_intent`` helper with ``intent='auto'``.
    Catches the failure mode where someone edits ``submit_auto_order``
    to bypass the helper (and therefore bypass
    ``assert_order_submission_allowed``).
    """
    src = inspect.getsource(BrokerService.submit_auto_order)
    assert "_submit_order_for_intent" in src, (
        "BrokerService.submit_auto_order no longer delegates to "
        "_submit_order_for_intent. The shared helper is the only "
        "place that calls assert_order_submission_allowed; bypassing "
        "it would silently disable the central auto-trading gate."
    )
    assert 'intent="auto"' in src, (
        "BrokerService.submit_auto_order no longer passes "
        'intent="auto" to _submit_order_for_intent. Without the '
        "auto intent the order would route through the manual gate, "
        "silently bypassing assert_auto_trading_allowed."
    )


def test_submit_order_for_intent_calls_assert_gate() -> None:
    """Source-level invariant: ``_submit_order_for_intent`` MUST call
    ``assert_order_submission_allowed`` before contacting the broker.
    """
    src = inspect.getsource(BrokerService._submit_order_for_intent)
    assert "assert_order_submission_allowed(intent=intent)" in src, (
        "BrokerService._submit_order_for_intent no longer calls "
        "assert_order_submission_allowed(intent=intent). This is the "
        "single chokepoint that delegates to assert_auto_trading_allowed "
        "for the auto intent; its removal would silently disable the "
        "central auto-trading gate."
    )
