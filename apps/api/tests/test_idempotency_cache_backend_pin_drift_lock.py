"""Drift-lock: idempotency cache backend pin (cycle 67).

Existing test ``test_idempotency_middleware_source_pin_drift_lock.py``
SHA-pins the function bodies of ``check_idempotency_key`` and
``release_idempotency_key``. This file pins the surrounding module
state — the things the source pin doesn't directly cover:

* ``_cache`` is a ``dict`` (not silently swapped for an LRU / Redis
  client without an explicit phase).
* ``_TTL_SECONDS == 86400`` (24h). Lowering this could cause genuine
  retries to be re-processed; raising it could keep stale entries.
* The module exports BOTH ``check_idempotency_key`` and
  ``release_idempotency_key`` as public callables.

Test-only / additive.
"""

from __future__ import annotations

from app.middleware import idempotency

EXPECTED_TTL_SECONDS = 86_400  # 24h
EXPECTED_PUBLIC_CALLABLES = frozenset(
    {"check_idempotency_key", "release_idempotency_key"}
)


def test_idempotency_cache_is_dict_backed() -> None:
    assert isinstance(idempotency._cache, dict), (
        "idempotency._cache backing has changed type. The current "
        "in-memory dict implementation is a deliberate MVP choice; "
        "swapping to Redis or any networked store is a separate phase "
        "with operational implications (HA, eviction, persistence)."
    )


def test_idempotency_ttl_seconds_unchanged() -> None:
    assert idempotency._TTL_SECONDS == EXPECTED_TTL_SECONDS, (
        f"idempotency._TTL_SECONDS={idempotency._TTL_SECONDS} "
        f"(expected {EXPECTED_TTL_SECONDS}). Changing the TTL window "
        "alters the duplicate-submit guarantee for trade endpoints."
    )


def test_idempotency_public_callables_present() -> None:
    missing = [
        name for name in EXPECTED_PUBLIC_CALLABLES
        if not callable(getattr(idempotency, name, None))
    ]
    assert not missing, (
        "Idempotency module is missing public callable(s): "
        f"{missing}. Both check_idempotency_key (pre-handler) and "
        "release_idempotency_key (post-error) are required by the "
        "trade-submit flow."
    )
