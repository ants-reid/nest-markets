"""Drift-lock pin: total mounted FastAPI route count must not regress.

Cycle 64 — MH-DRIFTLOCK-OPENAPI-PATH-COUNT-FLOOR.

Why this pin exists
-------------------
Cycles 58 + 62 + 63 catalog router prefixes/tags, auth-protected
routes, and response_model bindings on safety routes.  None of those
guards detects a *deletion* of an unrelated route — but a route that
silently disappears could remove a monitoring/observability surface
the operator relies on.  This pin fixes a floor on the live route
count so quiet removals get caught.

The floor is intentionally a >= comparison rather than equality:
adding new routes is always allowed (they'd be caught by the
prefix/tag/response_model catalogs as separate drift); deletions
require an explicit floor bump in the same PR.

Test-only / additive: zero edits under ``apps/api/app/``; no migration.
"""

from __future__ import annotations

import os

# Ensure import works in environments without DATABASE_URL set.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/market_hunter",
)

from app.main import app  # noqa: E402

# Pinned at cycle 64 against the live FastAPI app.
EXPECTED_ROUTE_COUNT_FLOOR = 191


def test_route_count_at_or_above_floor() -> None:
    actual = len(app.routes)
    assert actual >= EXPECTED_ROUTE_COUNT_FLOOR, (
        f"FastAPI mounted-route count regressed below floor.\n"
        f"  expected: >= {EXPECTED_ROUTE_COUNT_FLOOR}\n"
        f"  actual:   {actual}\n"
        "Routes have been silently removed. If this removal is "
        "intentional, lower the floor in the SAME PR with an explicit "
        "ledger entry justifying the reduction."
    )


def test_route_count_does_not_silently_balloon() -> None:
    """Upper sanity ceiling: catches accidental mass duplication
    (e.g. router include called twice). Set generously above current
    191 to allow normal growth without churn."""
    actual = len(app.routes)
    assert actual < 600, (
        f"FastAPI mounted-route count is implausibly high ({actual}). "
        "This usually means a router was registered more than once. "
        "Investigate before raising this ceiling."
    )


def test_safety_routes_are_present_in_app_routes() -> None:
    """Cross-check: the trading-surface routes pinned by cycle 63 must
    still appear in app.routes (not just in the source file)."""
    paths = {getattr(r, "path", None) for r in app.routes}
    required = {
        "/execution/paper",
        "/execution/live",
        "/workflow/run",
    }
    missing = required - paths
    assert not missing, (
        f"Safety-surface routes missing from live app.routes: {missing}. "
        "Either the router was deleted or its prefix changed without "
        "updating the catalog."
    )
