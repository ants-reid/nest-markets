"""Drift-lock pin: FastAPI ``app.exception_handlers`` registry.

Cycle 65 — MH-DRIFTLOCK-EXCEPTION-HANDLER-CATALOG.

Why this pin exists
-------------------
Cycle 61 SHA-256-pins the exception classes themselves; this pin
catches a silent change to which exception classes are bound to
HTTP-level handlers. Removing the ``RateLimitExceeded`` handler, for
example, would silently let rate-limit bypass turn into 500s rather
than the documented 429 response — a monitoring/safety regression
invisible to all prior pins.

Test-only / additive: zero edits under ``apps/api/app/``; no migration.
"""

from __future__ import annotations

import os

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/market_hunter",
)

from app.main import app  # noqa: E402

# Each entry: (exception class qualified name) -> handler function name
EXPECTED_HANDLER_BINDINGS: dict[str, str] = {
    "starlette.exceptions.HTTPException": "http_exception_handler",
    "fastapi.exceptions.RequestValidationError": "request_validation_exception_handler",
    "fastapi.exceptions.WebSocketRequestValidationError": "websocket_request_validation_exception_handler",
    "slowapi.errors.RateLimitExceeded": "_rate_limit_exceeded_handler",
}

# Hard safety subset — handlers whose presence is required.
SAFETY_REQUIRED_HANDLERS: set[str] = {
    "starlette.exceptions.HTTPException",
    "slowapi.errors.RateLimitExceeded",
}


def _qualname(cls) -> str:
    return f"{cls.__module__}.{cls.__name__}"


def _current_bindings() -> dict[str, str]:
    out: dict[str, str] = {}
    for exc_cls, handler in app.exception_handlers.items():
        # exception_handlers may have status-code int keys too (FastAPI
        # historically allows both); we only catalog class keys.
        if isinstance(exc_cls, type):
            out[_qualname(exc_cls)] = getattr(handler, "__name__", repr(handler))
    return out


def test_exception_handler_catalog_exact_match() -> None:
    actual = _current_bindings()
    expected_keys = set(EXPECTED_HANDLER_BINDINGS)
    actual_keys = set(actual)
    missing = expected_keys - actual_keys
    extra = actual_keys - expected_keys
    mismatched = [
        f"  {k}: expected handler={EXPECTED_HANDLER_BINDINGS[k]!r}, actual={actual[k]!r}"
        for k in expected_keys & actual_keys
        if actual[k] != EXPECTED_HANDLER_BINDINGS[k]
    ]
    msg_parts: list[str] = []
    if missing:
        msg_parts.append("  Missing handler bindings: " + ", ".join(sorted(missing)))
    if extra:
        msg_parts.append("  Unexpected new handler bindings: " + ", ".join(sorted(extra)))
    if mismatched:
        msg_parts.append("Mismatched handlers:\n" + "\n".join(mismatched))
    assert not msg_parts, (
        "FastAPI exception_handlers catalog drift detected.\n"
        + "\n".join(msg_parts)
        + "\nIf intentional, update EXPECTED_HANDLER_BINDINGS with a "
        "ledger entry."
    )


def test_safety_handlers_present() -> None:
    actual_keys = set(_current_bindings())
    missing = SAFETY_REQUIRED_HANDLERS - actual_keys
    assert not missing, (
        "Safety-required exception handlers are missing from "
        f"app.exception_handlers: {sorted(missing)}. "
        "Removing these handlers turns documented 4xx responses into "
        "500s, which is a monitoring regression."
    )


def test_safety_subset_is_subset_of_full_catalog() -> None:
    full = set(EXPECTED_HANDLER_BINDINGS)
    assert SAFETY_REQUIRED_HANDLERS <= full, (
        f"SAFETY_REQUIRED_HANDLERS contains entries missing from "
        f"EXPECTED_HANDLER_BINDINGS: {SAFETY_REQUIRED_HANDLERS - full}"
    )
