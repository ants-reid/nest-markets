"""Drift-lock pin: forbidden auto-/live-trading toggle patterns must not
appear anywhere in ``apps/web/``.

Cycle 62 — MH-DRIFTLOCK-FRONTEND-NO-AUTO-LIVE-TOGGLES.

Why this pin exists
-------------------
The repo's hard drift-lock rule states:

    "Frontend toggles for auto/live must not be added."

Until cycle 62 this rule was enforced by manual reading of PRs.  This
test programmatically enforces it by forbidding a precise set of
patterns that would only appear if someone tried to wire UI controls
that *enable / arm* trading from the frontend.  The patterns are
intentionally narrow to avoid false positives on existing read-only
status displays (which legitimately reference identifiers like
``auto_trading_enabled`` for *display*).

Test-only / additive: zero edits anywhere; pure assertion.
"""

from __future__ import annotations

import re
from pathlib import Path

# This test file lives at apps/api/tests/; the frontend is at apps/web/.
WEB_ROOT = (
    Path(__file__).resolve().parent.parent.parent / "web"
)

SCAN_SUBDIRS = ("app", "components", "lib", "hooks")
SCAN_EXTS = (".ts", ".tsx", ".js", ".jsx")

# Forbidden function/handler identifiers — these names only exist if a
# UI handler is being wired to enable/arm trading.  The repo's status
# displays use snake_case server response keys (``auto_trading_enabled``)
# and read-only ``on={...}`` props; those are not matched here.
FORBIDDEN_IDENTIFIERS: tuple[str, ...] = (
    "enableAutoTrading",
    "enableLiveTrading",
    "armLiveTrading",
    "enable_auto_trading_handler",
    "enable_live_trading_handler",
    "arm_live_trading_handler",
    "handleEnableAutoTrading",
    "handleEnableLiveTrading",
    "handleArmLiveTrading",
    "onArmLiveTrading",
    "onEnableAutoTrading",
    "onEnableLiveTrading",
)

# Forbidden URL/method literals — POST/PUT/PATCH calls to arming endpoints
# from the frontend.  Calls to GET endpoints are fine (read-only display).
# The patterns target the literal string forms that fetch/axios sites use.
FORBIDDEN_URL_LITERALS: tuple[str, ...] = (
    "/trading/arm/live",
    "/trading/auto/enable",
    "/trading/live/enable",
    "/auto-paper/enforcement/enable",
    "/risk/auto-trade/enable",
)

# Forbidden mutating-fetch constructions: a JSON body that explicitly
# sets a safety boolean to ``true`` from the frontend.  The exact byte
# pattern catches the literal ``"auto_trading_enabled": true``,
# ``"live_trading_enabled": true``, and similar.  These don't appear in
# read-only display code.
_FORBIDDEN_TRUE_PATTERNS = [
    re.compile(rf'["\']{key}["\']\s*:\s*true\b')
    for key in (
        "auto_trading_enabled",
        "live_trading_enabled",
        "auto_paper_enforcement_enabled",
        "live_order_submission_allowed",
        "live_execution_enabled",
    )
]


def _iter_frontend_files() -> list[Path]:
    files: list[Path] = []
    if not WEB_ROOT.exists():
        return files
    for sub in SCAN_SUBDIRS:
        d = WEB_ROOT / sub
        if not d.exists():
            continue
        for ext in SCAN_EXTS:
            files.extend(d.rglob(f"*{ext}"))
    return files


def test_frontend_tree_is_present() -> None:
    """Sanity guard: the frontend tree we scan must exist; otherwise the
    other tests would be vacuously true."""
    assert WEB_ROOT.exists() and WEB_ROOT.is_dir(), (
        f"Expected frontend root at {WEB_ROOT} but it is missing. "
        "If the web app has been moved, update WEB_ROOT in this test."
    )
    files = _iter_frontend_files()
    assert len(files) >= 50, (
        f"Frontend file count regressed unexpectedly: {len(files)} files. "
        "If the web app has been intentionally restructured, update the "
        "scan config; otherwise this test is silently scanning nothing."
    )


def test_no_forbidden_arming_identifiers_in_frontend() -> None:
    files = _iter_frontend_files()
    offenders: list[str] = []
    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        for ident in FORBIDDEN_IDENTIFIERS:
            if ident in text:
                rel = f.relative_to(WEB_ROOT).as_posix()
                offenders.append(f"  {rel}: contains forbidden identifier {ident!r}")
    assert not offenders, (
        "Frontend toggles for auto/live trading detected. The repo's "
        "drift-lock rule forbids any UI control that ENABLES / ARMS "
        "auto or live trading. Either revert the change or obtain "
        "explicit matrix unlock and update FORBIDDEN_IDENTIFIERS.\n"
        + "\n".join(offenders)
    )


def test_no_forbidden_arming_url_literals_in_frontend() -> None:
    files = _iter_frontend_files()
    offenders: list[str] = []
    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        for url in FORBIDDEN_URL_LITERALS:
            if url in text:
                rel = f.relative_to(WEB_ROOT).as_posix()
                offenders.append(f"  {rel}: references forbidden arming URL {url!r}")
    assert not offenders, (
        "Frontend references arming/enable URLs that would mutate "
        "trading posture. GET-based status reads are fine; POST/PUT/"
        "PATCH to these surfaces from the UI is not.\n"
        + "\n".join(offenders)
    )


def test_no_forbidden_true_safety_flags_in_frontend() -> None:
    """Forbid frontend payloads that explicitly set a safety flag to true.

    Read-only status displays receive these flags as response data; they
    must not be sent as request bodies.
    """
    files = _iter_frontend_files()
    offenders: list[str] = []
    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        for pat in _FORBIDDEN_TRUE_PATTERNS:
            for m in pat.finditer(text):
                rel = f.relative_to(WEB_ROOT).as_posix()
                offenders.append(
                    f"  {rel}: forbidden literal `{m.group(0)}`"
                )
    assert not offenders, (
        "Frontend code contains literals that set a safety flag to "
        "true. These would only appear in request bodies that mutate "
        "trading posture from the UI.\n"
        + "\n".join(offenders)
    )
