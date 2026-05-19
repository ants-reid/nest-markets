"""MH-NEWS-03 — In-memory TTL cache + freshness window for news payloads.

Pure read-side helper. Never writes trading state, never invokes brokers,
never bypasses ``trading_control_service``. Not yet consumed by any worker
or route — wiring is deferred to MH-NEWS-04 / MH-NEWS-07.

The cache is intentionally process-local and synchronous-friendly. It
exposes ``async def get_or_fetch`` so the same instance can be shared by
async adapters (e.g. ``PerplexityNewsAdapter``) without forcing callers to
manage TTL bookkeeping themselves.

Drift-lock notes:
* No mutation of orders, positions, or arming state.
* TTL is configurable per call AND per instance (default 300 s) so callers
  can opt into shorter freshness windows; staleness is reported but never
  silently extended.
"""

from __future__ import annotations

import asyncio
import inspect
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, Generic, Optional, TypeVar, Union

T = TypeVar("T")

DEFAULT_TTL_SECONDS: float = 300.0
MIN_TTL_SECONDS: float = 1.0
MAX_TTL_SECONDS: float = 3600.0


class NewsCacheError(ValueError):
    """Raised when cache configuration is invalid."""


@dataclass(frozen=True)
class CachedEntry(Generic[T]):
    """Snapshot of a cached value with the timestamp it was stored at."""

    value: T
    stored_at: float
    ttl_seconds: float

    def age_seconds(self, now: Optional[float] = None) -> float:
        current = time.monotonic() if now is None else now
        return max(0.0, current - self.stored_at)

    def is_fresh(self, now: Optional[float] = None) -> bool:
        return self.age_seconds(now) < self.ttl_seconds


Fetcher = Callable[[], Union[T, Awaitable[T]]]


class NewsCacheService(Generic[T]):
    """Process-local TTL cache for normalized news payloads.

    Thread-safety is provided via a single ``asyncio.Lock`` that guards both
    the dict and concurrent fetcher invocations for the same key.
    """

    def __init__(self, default_ttl_seconds: float = DEFAULT_TTL_SECONDS) -> None:
        self._validate_ttl(default_ttl_seconds)
        self._default_ttl: float = float(default_ttl_seconds)
        self._store: Dict[str, CachedEntry[T]] = {}
        self._lock: asyncio.Lock = asyncio.Lock()

    @staticmethod
    def _validate_ttl(ttl_seconds: float) -> None:
        if ttl_seconds is None:
            raise NewsCacheError("ttl_seconds must not be None")
        try:
            ttl = float(ttl_seconds)
        except (TypeError, ValueError) as exc:
            raise NewsCacheError(f"ttl_seconds must be numeric: {ttl_seconds!r}") from exc
        if ttl < MIN_TTL_SECONDS or ttl > MAX_TTL_SECONDS:
            raise NewsCacheError(
                f"ttl_seconds={ttl} out of bounds [{MIN_TTL_SECONDS}, {MAX_TTL_SECONDS}]"
            )

    @staticmethod
    def _validate_key(key: str) -> None:
        if not isinstance(key, str) or not key.strip():
            raise NewsCacheError("cache key must be a non-empty string")

    @property
    def default_ttl_seconds(self) -> float:
        return self._default_ttl

    def peek(self, key: str) -> Optional[CachedEntry[T]]:
        """Return the entry without affecting lock state. None if absent."""
        self._validate_key(key)
        return self._store.get(key)

    def is_fresh(self, key: str) -> bool:
        entry = self._store.get(key)
        return bool(entry and entry.is_fresh())

    async def get_or_fetch(
        self,
        key: str,
        fetcher: Fetcher[T],
        ttl_seconds: Optional[float] = None,
    ) -> T:
        """Return cached value if fresh, otherwise call ``fetcher`` and cache.

        ``fetcher`` may be a sync callable returning ``T`` or an async callable
        returning an awaitable of ``T``. Concurrent callers for the same key
        will share the resulting fetch.
        """
        self._validate_key(key)
        ttl = self._default_ttl if ttl_seconds is None else float(ttl_seconds)
        self._validate_ttl(ttl)

        entry = self._store.get(key)
        if entry is not None and entry.is_fresh():
            return entry.value

        async with self._lock:
            entry = self._store.get(key)
            if entry is not None and entry.is_fresh():
                return entry.value

            result = fetcher()
            if inspect.isawaitable(result):
                value = await result
            else:
                value = result  # type: ignore[assignment]

            self._store[key] = CachedEntry(
                value=value,
                stored_at=time.monotonic(),
                ttl_seconds=ttl,
            )
            return value

    def invalidate(self, key: str) -> bool:
        """Drop a single key. Returns True if a value was removed."""
        self._validate_key(key)
        return self._store.pop(key, None) is not None

    def clear(self) -> None:
        """Drop all cached entries."""
        self._store.clear()

    def freshness_report(self) -> Dict[str, Dict[str, Any]]:
        """Diagnostic snapshot — read-only, suitable for /system-health."""
        now = time.monotonic()
        return {
            key: {
                "age_seconds": entry.age_seconds(now),
                "ttl_seconds": entry.ttl_seconds,
                "is_fresh": entry.is_fresh(now),
            }
            for key, entry in self._store.items()
        }
