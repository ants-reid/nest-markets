"""Drift-lock: rate-limit presence catalog (cycle 67).

Pins:
* ``app.state.limiter`` IS set (slowapi limiter wired by main.py).
* The ``RateLimitExceeded`` exception handler IS registered.
* The CURRENT count of ``@limiter.limit(...)`` decorators on safety
  routes — currently zero. Silently adding a ``@limiter.limit("1/min")``
  to ``/execution/paper`` would change throttling behaviour without
  going through a deliberate phase. If you genuinely want to add rate
  limits, that's a separate phase and the floor here must be moved
  with a ledger entry.

Test-only / additive.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg2://test:test@localhost:5432/test"
)
os.environ.setdefault("SECRET_KEY", "test-secret-not-real")

from slowapi.errors import RateLimitExceeded  # noqa: E402

from app.main import app  # noqa: E402

ROUTES_DIR = Path(__file__).resolve().parents[1] / "app" / "api" / "routes"

SAFETY_ROUTE_FILES = (
    "execution.py",
    "workflow.py",
)

# Currently every safety route file has ZERO @limiter.limit decorators.
# A non-zero count here means someone added rate limiting outside a
# tracked phase — investigate.
EXPECTED_LIMITER_DECORATOR_COUNT_BY_FILE: dict[str, int] = {
    "execution.py": 0,
    "workflow.py": 0,
}

_LIMITER_DEC_RE = re.compile(r"^\s*@limiter\.limit\(", re.MULTILINE)


def test_app_state_limiter_is_set() -> None:
    assert hasattr(app.state, "limiter"), (
        "app.state.limiter is missing. The slowapi limiter must be "
        "wired by app/main.py:create_app or rate limiting will silently "
        "no-op for any route that depends on it."
    )
    assert app.state.limiter is not None


def test_rate_limit_exceeded_handler_is_registered() -> None:
    assert RateLimitExceeded in app.exception_handlers, (
        "RateLimitExceeded handler missing from app.exception_handlers. "
        "Without it, throttle hits surface as 500s instead of 429s."
    )


def test_safety_routes_limiter_decorator_counts_unchanged() -> None:
    drift: list[str] = []
    for fname in SAFETY_ROUTE_FILES:
        path = ROUTES_DIR / fname
        text = path.read_text(encoding="utf-8")
        actual = len(_LIMITER_DEC_RE.findall(text))
        expected = EXPECTED_LIMITER_DECORATOR_COUNT_BY_FILE[fname]
        if actual != expected:
            drift.append(
                f"  {fname}: @limiter.limit(...) count={actual} "
                f"(expected {expected})"
            )
    assert not drift, (
        "Safety-route @limiter.limit(...) decorator count drift "
        "detected. Adding or removing a rate-limit decorator on a "
        "safety route silently changes throttling and may convert "
        "successful submits into 429s (or vice versa).\n"
        + "\n".join(drift)
        + "\nIf intentional, update EXPECTED_LIMITER_DECORATOR_COUNT_BY_FILE "
        "and append a ledger entry."
    )
