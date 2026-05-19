"""Drift-lock: middleware-stack catalog (cycle 66).

Pins the FastAPI middleware stack:

* ``CORSMiddleware`` MUST be present in ``app.user_middleware``.
* ``CorrelationIDMiddleware`` MUST be present.
* The CORS middleware MUST be installed BEFORE (i.e. wraps) the
  Correlation middleware. ``app.user_middleware`` is in install order
  with the LAST-added middleware appearing FIRST in the list (FastAPI
  stores them in reverse install order). Removing or reordering can
  silently change preflight behaviour or break correlation IDs.
* ``ServerErrorMiddleware`` (FastAPI's outer wrapper) is present via
  the framework — we don't pin that one.

Test-only / additive.
"""

from __future__ import annotations

import os

# Ensure import succeeds without a real database URL.
os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg2://test:test@localhost:5432/test"
)
os.environ.setdefault("SECRET_KEY", "test-secret-not-real")

from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from app.main import app  # noqa: E402
from app.services.correlation_context import (  # noqa: E402
    CorrelationIDMiddleware,
)

REQUIRED_MIDDLEWARE_CLASSES = (CORSMiddleware, CorrelationIDMiddleware)


def _installed_middleware_classes() -> list[type]:
    # Each entry in user_middleware is a Middleware dataclass with .cls.
    return [m.cls for m in app.user_middleware]


def test_required_middleware_classes_installed() -> None:
    installed = _installed_middleware_classes()
    missing = [
        cls.__name__ for cls in REQUIRED_MIDDLEWARE_CLASSES if cls not in installed
    ]
    assert not missing, (
        f"Required middleware missing from app.user_middleware: {missing}. "
        "Removing CORS would break browser callers; removing Correlation "
        "would break trace propagation across services."
    )


def test_middleware_stack_floor() -> None:
    n = len(app.user_middleware)
    assert n >= len(REQUIRED_MIDDLEWARE_CLASSES), (
        f"app.user_middleware has {n} entries; floor is "
        f"{len(REQUIRED_MIDDLEWARE_CLASSES)}."
    )


def test_cors_installed_before_correlation() -> None:
    """In FastAPI, ``user_middleware`` lists middleware in REVERSE install
    order (last added is first). Since main.py installs CORS first, then
    Correlation, the runtime list should be [Correlation, CORS, ...].

    This test asserts CORS appears AFTER Correlation in user_middleware,
    which is equivalent to "CORS was installed before Correlation" and
    therefore wraps requests/responses on the outside.
    """
    classes = _installed_middleware_classes()
    assert CORSMiddleware in classes
    assert CorrelationIDMiddleware in classes
    cors_idx = classes.index(CORSMiddleware)
    corr_idx = classes.index(CorrelationIDMiddleware)
    assert corr_idx < cors_idx, (
        "Middleware install order drift: CORSMiddleware must be installed "
        "BEFORE CorrelationIDMiddleware so CORS handles preflight first. "
        f"user_middleware order={[c.__name__ for c in classes]}"
    )
