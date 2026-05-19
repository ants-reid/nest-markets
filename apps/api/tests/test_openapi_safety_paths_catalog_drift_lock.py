"""MH-DRIFTLOCK-OPENAPI-SAFETY-PATHS-CATALOG

Pins that the OpenAPI schema exposes the safety-critical paths. Renaming any
of these would silently break clients and potentially mask trading-surface
removals.
"""
from __future__ import annotations

from app.main import app

_REQUIRED_OPENAPI_PATHS: frozenset[str] = frozenset(
    {
        "/execution/live",
        "/execution/paper",
        "/risk-decisions/recent",
        "/approvals/create",
        "/trading/halt",
        "/broker/control",
        "/broker/mode",
        "/risk/limits",
    }
)


def _openapi_paths() -> set[str]:
    spec = app.openapi()
    return set((spec.get("paths") or {}).keys())


def test_openapi_safety_paths_present() -> None:
    paths = _openapi_paths()
    # Match any path in the spec that starts with a required prefix or equals it.
    missing: list[str] = []
    for required in _REQUIRED_OPENAPI_PATHS:
        if required in paths:
            continue
        if any(p.startswith(required) for p in paths):
            continue
        missing.append(required)
    assert not missing, f"OpenAPI spec missing safety paths: {sorted(missing)}"


def test_openapi_total_path_floor() -> None:
    n = len(_openapi_paths())
    # Floor — current spec exposes well over 50 paths.
    assert n >= 50, f"OpenAPI path count {n} below floor 50"
