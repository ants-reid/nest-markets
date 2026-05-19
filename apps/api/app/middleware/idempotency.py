"""Idempotency key handling for trade submission endpoints.

Clients send X-Idempotency-Key header with a UUID.
If the same key is seen again within the TTL window, the
cached response is returned instead of re-processing the trade.

Uses an in-memory dict for MVP. Replace with Redis for multi-process deployments.
"""

from __future__ import annotations

import time
from typing import Any
from fastapi import Header, HTTPException, status

# { key -> (response_payload, expiry_timestamp) }
_cache: dict[str, tuple[Any, float]] = {}

# Keys expire after 24 hours
_TTL_SECONDS = 86400


def _evict_expired() -> None:
    """Remove expired keys to prevent unbounded memory growth."""
    now = time.monotonic()
    expired = [k for k, (_, exp) in _cache.items() if exp < now]
    for k in expired:
        del _cache[k]


def check_idempotency_key(
    x_idempotency_key: str | None = Header(default=None),
) -> str | None:
    """FastAPI dependency — validates and tracks idempotency keys.
    
    If a key is provided and was already used, raises 409 Conflict.
    Returns the key for downstream use (e.g. storing with the response).
    """
    if not x_idempotency_key:
        return None

    _evict_expired()

    if x_idempotency_key in _cache:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "duplicate_request",
                "message": "This idempotency key was already used. The original request was already processed.",
                "idempotency_key": x_idempotency_key,
            },
        )

    # Reserve the key — will be committed after successful response
    _cache[x_idempotency_key] = (None, time.monotonic() + _TTL_SECONDS)
    return x_idempotency_key


def release_idempotency_key(key: str) -> None:
    """Remove a key from the cache (called on error so client can retry)."""
    _cache.pop(key, None)
