"""Drift-lock: APIKeyAuth runtime guard (cycle 69).

Behavioural floor: a freshly-constructed ``APIKeyAuth(enabled=True)``
MUST raise an HTTP 401 for missing OR wrong API-key headers. The
existing source-pin (cycle 63) covers the BYTES; this file covers
the actual runtime behaviour so a future refactor that preserves the
function shape but breaks 401 returns would still fail this test.

Test-only / additive.
"""

from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.middleware.auth import APIKeyAuth


def _make_request(headers: list[tuple[bytes, bytes]]) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/x",
        "headers": headers,
    }
    return Request(scope)


def _enabled_auth(secret: str = "test-secret-not-real") -> APIKeyAuth:
    auth = APIKeyAuth()
    auth.api_key = secret
    auth.enabled = True
    return auth


def test_missing_authorization_header_returns_401() -> None:
    auth = _enabled_auth()
    req = _make_request(headers=[])
    with pytest.raises(HTTPException) as exc:
        asyncio.run(auth(req))
    assert exc.value.status_code == 401, (
        "APIKeyAuth must return 401 when Authorization header is "
        "missing; got "
        f"{exc.value.status_code}."
    )


def test_wrong_bearer_token_returns_401() -> None:
    auth = _enabled_auth("real-key")
    req = _make_request(
        headers=[(b"authorization", b"Bearer wrong-key")]
    )
    with pytest.raises(HTTPException) as exc:
        asyncio.run(auth(req))
    assert exc.value.status_code == 401, (
        "APIKeyAuth must return 401 when Bearer token does not match "
        "the configured api_key."
    )


def test_correct_bearer_token_passes() -> None:
    auth = _enabled_auth("real-key")
    req = _make_request(
        headers=[(b"authorization", b"Bearer real-key")]
    )
    # Should NOT raise.
    asyncio.run(auth(req))


def test_disabled_auth_passes_without_header() -> None:
    """Sanity floor: when enabled=False (dev mode) the auth call is
    a no-op. This is the behaviour the existing dev singleton relies
    on; the safety guard is the source pin + the catalog test that
    enabled is wired off in dev defaults.
    """
    auth = APIKeyAuth()
    auth.enabled = False
    req = _make_request(headers=[])
    asyncio.run(auth(req))
