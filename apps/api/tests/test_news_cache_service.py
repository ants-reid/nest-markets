"""Tests for MH-NEWS-03 — NewsCacheService."""

from __future__ import annotations

import asyncio

import pytest

from app.services.news_cache_service import (
    DEFAULT_TTL_SECONDS,
    MAX_TTL_SECONDS,
    MIN_TTL_SECONDS,
    NewsCacheError,
    NewsCacheService,
)


@pytest.mark.asyncio
async def test_default_ttl_used_when_not_overridden():
    cache: NewsCacheService[int] = NewsCacheService()
    assert cache.default_ttl_seconds == DEFAULT_TTL_SECONDS

    calls = {"n": 0}

    def fetch() -> int:
        calls["n"] += 1
        return 42

    assert await cache.get_or_fetch("k", fetch) == 42
    assert await cache.get_or_fetch("k", fetch) == 42
    assert calls["n"] == 1


@pytest.mark.asyncio
async def test_async_fetcher_is_awaited():
    cache: NewsCacheService[str] = NewsCacheService(default_ttl_seconds=60)

    async def fetch() -> str:
        await asyncio.sleep(0)
        return "hello"

    assert await cache.get_or_fetch("k", fetch) == "hello"
    assert cache.is_fresh("k")


@pytest.mark.asyncio
async def test_expired_entry_triggers_refetch(monkeypatch):
    cache: NewsCacheService[int] = NewsCacheService(default_ttl_seconds=2)

    fake_now = {"t": 1000.0}

    def now() -> float:
        return fake_now["t"]

    monkeypatch.setattr("app.services.news_cache_service.time.monotonic", now)

    counter = {"n": 0}

    def fetch() -> int:
        counter["n"] += 1
        return counter["n"]

    assert await cache.get_or_fetch("k", fetch) == 1
    fake_now["t"] += 5  # past 2s TTL
    assert await cache.get_or_fetch("k", fetch) == 2
    assert counter["n"] == 2


@pytest.mark.asyncio
async def test_per_call_ttl_overrides_default():
    cache: NewsCacheService[int] = NewsCacheService(default_ttl_seconds=600)
    await cache.get_or_fetch("k", lambda: 7, ttl_seconds=10)
    entry = cache.peek("k")
    assert entry is not None
    assert entry.ttl_seconds == 10.0


@pytest.mark.asyncio
async def test_invalidate_and_clear():
    cache: NewsCacheService[int] = NewsCacheService()
    await cache.get_or_fetch("a", lambda: 1)
    await cache.get_or_fetch("b", lambda: 2)
    assert cache.invalidate("a") is True
    assert cache.invalidate("a") is False
    assert cache.is_fresh("b")
    cache.clear()
    assert cache.peek("b") is None


@pytest.mark.asyncio
async def test_freshness_report_contains_keys():
    cache: NewsCacheService[int] = NewsCacheService(default_ttl_seconds=60)
    await cache.get_or_fetch("a", lambda: 1)
    await cache.get_or_fetch("b", lambda: 2)
    report = cache.freshness_report()
    assert set(report.keys()) == {"a", "b"}
    for entry in report.values():
        assert entry["is_fresh"] is True
        assert entry["ttl_seconds"] == 60.0
        assert entry["age_seconds"] >= 0.0


@pytest.mark.asyncio
async def test_concurrent_fetchers_share_result():
    cache: NewsCacheService[int] = NewsCacheService(default_ttl_seconds=60)
    counter = {"n": 0}

    async def fetch() -> int:
        counter["n"] += 1
        await asyncio.sleep(0.01)
        return counter["n"]

    results = await asyncio.gather(
        cache.get_or_fetch("k", fetch),
        cache.get_or_fetch("k", fetch),
        cache.get_or_fetch("k", fetch),
    )
    assert results == [1, 1, 1]
    assert counter["n"] == 1


def test_ttl_bounds_rejected():
    with pytest.raises(NewsCacheError):
        NewsCacheService(default_ttl_seconds=0)
    with pytest.raises(NewsCacheError):
        NewsCacheService(default_ttl_seconds=MAX_TTL_SECONDS + 1)


@pytest.mark.asyncio
async def test_per_call_ttl_validation():
    cache: NewsCacheService[int] = NewsCacheService()
    with pytest.raises(NewsCacheError):
        await cache.get_or_fetch("k", lambda: 1, ttl_seconds=MIN_TTL_SECONDS - 0.5)


def test_empty_key_rejected():
    cache: NewsCacheService[int] = NewsCacheService()
    with pytest.raises(NewsCacheError):
        cache.peek("")
    with pytest.raises(NewsCacheError):
        cache.invalidate("   ")
