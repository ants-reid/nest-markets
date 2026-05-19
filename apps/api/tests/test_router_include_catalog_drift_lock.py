"""Drift-lock: router-include catalog (cycle 66).

Pins:
  * a hard FLOOR on the number of ``app.include_router(...)`` calls in
    ``app/main.py`` so a refactor can't silently drop routers; and
  * a SAFETY SUBSET of router names that MUST be wired (execution,
    workflow, broker, health). Removing ``execution_router`` would
    silently kill ``/execution/paper`` and ``/execution/live``.

Source-text scan only — no live import of ``app.main`` to keep the test
fast and immune to settings/env requirements.

Test-only / additive.
"""

from __future__ import annotations

import re
from pathlib import Path

APP_MAIN = Path(__file__).resolve().parents[1] / "app" / "main.py"

# Floor — current count is 39. We pin a floor a few below to allow
# additive growth without weakening the guard.
EXPECTED_INCLUDE_ROUTER_FLOOR = 35

SAFETY_REQUIRED_ROUTERS: frozenset[str] = frozenset(
    {
        "health_router",
        "execution_router",
        "workflow_router",
        "broker_router",
        "approvals_router",
        "trading_halt_router",
    }
)

_INCLUDE_ROUTER_RE = re.compile(
    r"app\.include_router\(\s*([A-Za-z_][A-Za-z0-9_]*)\b"
)


def _included_routers() -> list[str]:
    text = APP_MAIN.read_text(encoding="utf-8")
    return _INCLUDE_ROUTER_RE.findall(text)


def test_include_router_count_floor() -> None:
    n = len(_included_routers())
    assert n >= EXPECTED_INCLUDE_ROUTER_FLOOR, (
        f"app.include_router(...) count={n} dropped below floor "
        f"{EXPECTED_INCLUDE_ROUTER_FLOOR}. A router was removed from "
        "app/main.py — investigate for a silent route surface shrink."
    )


def test_safety_routers_are_included() -> None:
    included = set(_included_routers())
    missing = SAFETY_REQUIRED_ROUTERS - included
    assert not missing, (
        "Safety-critical routers missing from app.include_router(...) "
        f"in app/main.py: {sorted(missing)}. Removing any of these "
        "would silently disable a trading-surface endpoint."
    )


def test_include_router_calls_have_no_duplicates() -> None:
    names = _included_routers()
    seen: set[str] = set()
    dupes: list[str] = []
    for n in names:
        if n in seen:
            dupes.append(n)
        else:
            seen.add(n)
    assert not dupes, (
        "Duplicate app.include_router(...) calls in app/main.py: "
        f"{sorted(set(dupes))}. Duplicates can register ambiguous "
        "routes or double-wire a router with different prefixes."
    )
