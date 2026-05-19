"""Drift-lock pin: SHA-256 source-byte hashes of the idempotency
middleware functions (``check_idempotency_key`` and
``release_idempotency_key``).

Cycle 64 — MH-DRIFTLOCK-IDEMPOTENCY-MIDDLEWARE-SOURCE-PIN.

Why this pin exists
-------------------
Cycle 63 SHA-256-pinned the auth middleware.  Idempotency is the
sister middleware: it protects mutating endpoints (paper exec, etc.)
from accidental double-submission.  A silent weakening
(e.g. always returning OK without recording the key) would not flip
any of the existing pins.

Test-only / additive: zero edits under ``apps/api/app/``; no migration.

Updating after a legitimate edit
--------------------------------
Recompute via::

    PYTHONPATH=. .venv/bin/python -c "
    import hashlib, inspect
    from app.middleware.idempotency import check_idempotency_key, release_idempotency_key
    for fn in (check_idempotency_key, release_idempotency_key):
        s = inspect.getsource(fn).encode('utf-8')
        print(hashlib.sha256(s).hexdigest(), len(s))"
"""

from __future__ import annotations

import hashlib
import inspect

from app.middleware.idempotency import (
    check_idempotency_key,
    release_idempotency_key,
)

EXPECTED_HASHES: dict[str, tuple[str, int]] = {
    "check_idempotency_key": (
        "fa861c8432f0208a8b7b82019228761cb77e4309c122b1f27b472f659b42881a",
        944,
    ),
    "release_idempotency_key": (
        "6c1cd599d905d135cdf7aa5fddc3c5ddd7737f77d016193b255c82a852834f79",
        150,
    ),
}

_TARGETS = {
    "check_idempotency_key": check_idempotency_key,
    "release_idempotency_key": release_idempotency_key,
}


def _hash(fn) -> tuple[str, int]:
    src = inspect.getsource(fn).encode("utf-8")
    return hashlib.sha256(src).hexdigest(), len(src)


def test_idempotency_middleware_source_hashes_unchanged() -> None:
    drift: list[str] = []
    for name, fn in _TARGETS.items():
        actual = _hash(fn)
        expected = EXPECTED_HASHES[name]
        if actual != expected:
            drift.append(
                f"  {name}: expected sha256={expected[0]} size={expected[1]}; "
                f"actual sha256={actual[0]} size={actual[1]}"
            )
    assert not drift, (
        "Idempotency middleware source-byte drift detected. ANY structural "
        "change MUST be reviewed and the new hash recorded in the same PR. "
        "These functions protect mutating endpoints from double-submission.\n"
        + "\n".join(drift)
    )


def test_idempotency_middleware_callables_present() -> None:
    """Sanity guard: import surface unchanged."""
    assert callable(check_idempotency_key)
    assert callable(release_idempotency_key)


def test_idempotency_middleware_raises_signature() -> None:
    """Behavioural floor: ``check_idempotency_key`` must signal collisions
    via HTTPException — not silent acceptance. Verify by source inspection
    so the test stays hermetic (no DB fixture)."""
    src = inspect.getsource(check_idempotency_key)
    assert "HTTPException" in src, (
        "check_idempotency_key no longer references HTTPException; "
        "it must raise on collision rather than silently accept."
    )
