"""Drift-lock: CORS + rate limiter + middleware kwargs catalog (cycle 72).

Pins the literal CORS configuration kwargs and the slowapi
``Limiter`` defaults that are wired in ``create_app()``. A renamed
header in ``allow_headers`` would silently break the
``X-Correlation-ID`` propagation invariant. A bumped
``default_limits`` would silently change the per-IP throttle floor.

Test-only / additive — does not start the app.
"""

from __future__ import annotations

import inspect

from app import main as app_main

EXPECTED_ALLOW_METHODS: frozenset[str] = frozenset(
    {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"}
)
EXPECTED_ALLOW_HEADERS: frozenset[str] = frozenset(
    {"Content-Type", "Authorization", "X-Correlation-ID"}
)
EXPECTED_EXPOSE_HEADERS: frozenset[str] = frozenset({"X-Correlation-ID"})
EXPECTED_DEFAULT_LIMIT = "200/minute"
EXPECTED_KEY_FUNC_NAME = "get_remote_address"


def _create_app_source() -> str:
    return inspect.getsource(app_main.create_app)


def test_cors_allow_methods_catalog() -> None:
    src = _create_app_source()
    for m in EXPECTED_ALLOW_METHODS:
        assert f'"{m}"' in src, (
            f"CORS allow_methods missing literal {m!r} in create_app(). "
            "Removing a method silently breaks browser preflight for "
            "that verb."
        )


def test_cors_allow_headers_catalog() -> None:
    src = _create_app_source()
    for h in EXPECTED_ALLOW_HEADERS:
        assert f'"{h}"' in src, (
            f"CORS allow_headers missing literal {h!r}. Removing "
            f"{h!r} would silently break authenticated or "
            "correlated requests from the browser."
        )


def test_cors_expose_correlation_id_header() -> None:
    src = _create_app_source()
    for h in EXPECTED_EXPOSE_HEADERS:
        assert f'"{h}"' in src, (
            f"CORS expose_headers missing {h!r} — browser clients "
            "would no longer be able to read the correlation id."
        )


def test_cors_allow_credentials_true() -> None:
    src = _create_app_source()
    assert "allow_credentials=True" in src, (
        "CORS allow_credentials no longer True — Authorization "
        "header would be stripped from cross-origin requests."
    )


def test_rate_limiter_default_limit_pinned() -> None:
    main_src = inspect.getsource(app_main)
    assert f'"{EXPECTED_DEFAULT_LIMIT}"' in main_src, (
        f"slowapi Limiter default_limits drift: expected literal "
        f"{EXPECTED_DEFAULT_LIMIT!r} not present in app/main.py."
    )
    # Sanity: limiter object is the configured one
    assert hasattr(app_main, "limiter"), (
        "app.main.limiter symbol missing — rate limiting wiring "
        "broken."
    )


def test_rate_limiter_key_func_pinned() -> None:
    """The per-IP key function MUST remain ``get_remote_address``;
    swapping in a constant key would make all callers share a single
    bucket."""
    main_src = inspect.getsource(app_main)
    assert f"key_func={EXPECTED_KEY_FUNC_NAME}" in main_src, (
        f"Limiter key_func is no longer {EXPECTED_KEY_FUNC_NAME!r}. "
        "All callers would share a single rate-limit bucket — DoS "
        "amplification risk."
    )
