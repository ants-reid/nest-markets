"""Drift-lock: assert no conftest patches the central auto-trading guard.

Cycle 58 — MH-DRIFTLOCK-CONFTEST-FIXTURE-SAFETY (pure additive test-only).

A subtle drift mode the cycle 53–57 catalogs do not catch: a future
contributor adds an autouse fixture in ``tests/conftest.py`` (or a
sibling sub-conftest) that monkey-patches
``app.services.trading_control_service.assert_auto_trading_allowed`` to
a no-op or replaces ``BrokerService.submit_auto_order`` with a stub
that bypasses the gate. The test suite would then go green even after
a regression that broke the runtime safety check, because every test
would silently see the guard disabled.

This test reads every ``conftest.py`` under ``apps/api/tests/`` and
asserts that none of them mention the safety symbols at all. Conftest
files are the only places where suite-wide fixture replacement happens
implicitly via ``autouse=True``; per-test patches are visible at the
test site.

Drift-lock guarantees
---------------------
* Read-only test — no DB access, no HTTP calls, no monkey-patching.
* Auto-paper enforcement remains OFF.
* Auto trading remains OFF.
* Live trading remains OFF.
* ``assert_auto_trading_allowed()`` is unchanged.
"""

from __future__ import annotations

from pathlib import Path

# Symbols a conftest must NEVER reference, since referencing them in a
# fixture would imply a suite-wide override that could disable the
# central runtime safety check.
FORBIDDEN_SAFETY_SYMBOLS = (
    "assert_auto_trading_allowed",
    "submit_auto_order",
    "_submit_order_for_intent",
    "trading_control_service",
)

# Generic patch/monkey-patch markers that, combined with the symbols
# above, would indicate a fixture-level override. We only check these
# show up *together* in the same conftest file with a forbidden symbol.
PATCH_MARKERS = (
    "monkeypatch.setattr",
    "monkeypatch.setenv",
    "unittest.mock",
    "mock.patch",
    "patch(",
)


def _conftest_files() -> list[Path]:
    tests_root = Path(__file__).parent
    return sorted(tests_root.rglob("conftest.py"))


def test_conftest_files_do_not_reference_safety_symbols() -> None:
    """No conftest may even mention the central safety symbols.

    Rationale: if a conftest references these symbols at all, it is
    almost certainly setting up a fixture that overrides them. The
    only legitimate references would live in the production code under
    ``apps/api/app/`` or in a per-test file that is reviewable in
    isolation.
    """
    offenders: list[tuple[Path, str]] = []
    for conftest in _conftest_files():
        text = conftest.read_text(encoding="utf-8")
        for symbol in FORBIDDEN_SAFETY_SYMBOLS:
            if symbol in text:
                offenders.append((conftest, symbol))
    assert not offenders, (
        "conftest.py file(s) reference forbidden safety symbol(s): "
        f"{[(str(p), s) for p, s in offenders]}. Suite-wide fixture "
        "patches of the central trading safety guards would silently "
        "disable runtime enforcement during the entire test suite. "
        "If you need to stub these for a specific test, do so inline "
        "in that test file (and add a ledger entry justifying the "
        "stub)."
    )


def test_conftest_files_have_no_autouse_safety_overrides() -> None:
    """Even without referencing the safety symbol names, an autouse
    fixture combined with patch machinery is suspicious in a conftest
    that also mentions ``broker`` or ``trading`` modules. This test
    enforces a stricter version: no conftest may combine ``autouse=True``
    with any patch marker AND a ``broker``/``trading`` substring.
    """
    offenders: list[tuple[Path, str]] = []
    for conftest in _conftest_files():
        text = conftest.read_text(encoding="utf-8")
        if "autouse=True" not in text:
            continue
        if "broker" not in text.lower() and "trading" not in text.lower():
            continue
        for marker in PATCH_MARKERS:
            if marker in text:
                offenders.append((conftest, marker))
    assert not offenders, (
        "conftest.py file(s) combine autouse fixtures with patch "
        f"markers and broker/trading references: {[(str(p), m) for p, m in offenders]}. "
        "This is the exact signature of a fixture-level safety override. "
        "Move the patch into the specific test that requires it and add "
        "a ledger entry."
    )


def test_conftest_files_present() -> None:
    """Sanity floor: at least one conftest.py exists under tests/."""
    files = _conftest_files()
    assert len(files) >= 1, (
        f"Expected at least one conftest.py under apps/api/tests/, "
        f"found {len(files)}."
    )
