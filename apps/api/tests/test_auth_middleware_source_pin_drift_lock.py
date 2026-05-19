"""Drift-lock pin: SHA-256 source-byte hashes of the API-key auth
middleware (``app.middleware.auth.APIKeyAuth``).

Cycle 63 — MH-DRIFTLOCK-AUTH-MIDDLEWARE-SOURCE-PIN.

Why this pin exists
-------------------
Cycle 62 pinned WHICH route files import ``api_key_auth`` and WHICH
safety routes carry ``Depends(api_key_auth)``.  But the auth check
itself could still be silently weakened (e.g. early-return on missing
header, accepting any non-empty key).  This pin freezes the byte image
of the ``APIKeyAuth`` class and its ``__call__`` so any structural
change requires explicit hash bump.

Test-only / additive: zero edits under ``apps/api/app/``; no migration.

Updating after a legitimate edit
--------------------------------
Recompute via::

    PYTHONPATH=. .venv/bin/python -c "
    import hashlib, inspect
    from app.middleware.auth import APIKeyAuth
    for fn in (APIKeyAuth, APIKeyAuth.__call__):
        s = inspect.getsource(fn).encode('utf-8')
        print(hashlib.sha256(s).hexdigest(), len(s))"

Update EXPECTED_HASHES below in the same PR with a ledger entry.
"""

from __future__ import annotations

import hashlib
import inspect

from app.middleware.auth import APIKeyAuth, api_key_auth

EXPECTED_HASHES: dict[str, tuple[str, int]] = {
    "APIKeyAuth": (
        "abb5725c8157327faa62d6303c930b9b4885f80cd6774dd1af84dd65b2b55e0f",
        1608,
    ),
    "APIKeyAuth.__call__": (
        "746b84931e64917f482205174568f9b0a0a189f54cb3bcd9a7009844a6f443da",
        1357,
    ),
}

_TARGETS = {
    "APIKeyAuth": APIKeyAuth,
    "APIKeyAuth.__call__": APIKeyAuth.__call__,
}


def _hash(obj) -> tuple[str, int]:
    src = inspect.getsource(obj).encode("utf-8")
    return hashlib.sha256(src).hexdigest(), len(src)


def test_auth_middleware_source_hashes_unchanged() -> None:
    drift: list[str] = []
    for name, obj in _TARGETS.items():
        actual = _hash(obj)
        expected = EXPECTED_HASHES[name]
        if actual != expected:
            drift.append(
                f"  {name}: expected sha256={expected[0]} size={expected[1]}; "
                f"actual sha256={actual[0]} size={actual[1]}"
            )
    assert not drift, (
        "API-key auth middleware source-byte drift detected. ANY "
        "structural change to APIKeyAuth or its __call__ MUST be "
        "reviewed and the new hash recorded in the same PR.\n"
        + "\n".join(drift)
    )


def test_api_key_auth_singleton_present() -> None:
    """The router-side dependency uses the module-level
    ``api_key_auth`` instance; that import surface must remain."""
    assert isinstance(api_key_auth, APIKeyAuth), (
        "app.middleware.auth.api_key_auth is no longer an APIKeyAuth "
        "instance. The Depends(api_key_auth) wiring at "
        "execution.py:/paper and workflow.py:/run depends on this."
    )


def test_api_key_auth_enforces_when_enabled() -> None:
    """Behavioural floor: when the auth instance has a configured key,
    invoking it without an Authorization header must raise.

    The default ``api_key_auth`` singleton may have ``enabled=False`` in
    development (no API_KEY env), so we construct a fresh instance with
    a synthetic key forced on to exercise the enforced path.
    """
    import asyncio

    from fastapi import HTTPException

    auth = APIKeyAuth()
    auth.api_key = "test-key-not-real"  # force enforcement on
    auth.enabled = True

    class _StubHeaders:
        def get(self, key, default=None):
            return None

    class _StubRequest:
        headers = _StubHeaders()

    raised = False
    try:
        asyncio.run(auth(_StubRequest()))
    except HTTPException:
        raised = True
    assert raised, (
        "APIKeyAuth(enabled=True) did NOT raise HTTPException when "
        "called without an Authorization header. The auth middleware "
        "enforcement path has been weakened."
    )
