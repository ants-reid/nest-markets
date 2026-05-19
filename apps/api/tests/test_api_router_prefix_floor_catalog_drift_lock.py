"""MH-DRIFTLOCK-API-ROUTER-PREFIX-FLOOR-CATALOG

Pins a floor of safety-relevant top-segment prefixes mounted on
``app.main:app``. Silent removal of /approvals, /risk, /risk-decisions,
/trading, /broker, /execution, /paper, /paper-validation, /workflow would
disable safety/observability surface and is now a loud failure.
"""
from __future__ import annotations

from app.main import app

_REQUIRED_PREFIX_FLOOR: frozenset[str] = frozenset(
    {
        "/approvals",
        "/broker",
        "/execution",
        "/paper",
        "/paper-validation",
        "/risk",
        "/risk-decisions",
        "/trading",
        "/workflow",
    }
)


def _top_segments() -> set[str]:
    segments: set[str] = set()
    for r in app.routes:
        path = getattr(r, "path", "")
        if not path.startswith("/") or len(path) < 2:
            continue
        parts = path.split("/", 2)
        if len(parts) >= 2 and parts[1]:
            segments.add("/" + parts[1])
    return segments


def test_required_safety_prefix_floor_present() -> None:
    actual = _top_segments()
    missing = _REQUIRED_PREFIX_FLOOR - actual
    assert not missing, (
        f"app.main lost safety-relevant top-segment prefixes: {sorted(missing)}. "
        f"Removing these silently would disable observability/control surface."
    )


def test_prefix_count_floor() -> None:
    n = len(_top_segments())
    assert n >= len(_REQUIRED_PREFIX_FLOOR), (
        f"app.main top-segment prefix count regressed below safety floor: {n}"
    )
