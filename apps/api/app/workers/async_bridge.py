"""Sync-to-async bridge utilities for worker entry points.

Workers expose synchronous ``execute``/``run`` methods so scheduler callers
can invoke them uniformly. This helper runs async callables from those sync
paths without relying on ``asyncio.run``.
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Awaitable, Callable, TypeVar

T = TypeVar("T")


def _run_in_new_event_loop(factory: Callable[[], Awaitable[T]]) -> T:
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(factory())
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()


def run_async(factory: Callable[[], Awaitable[T]]) -> T:
    """Run an async callable from sync worker code.

    If no event loop is running in the current thread we execute directly in a
    fresh loop. If a loop is already running we offload to a one-shot worker
    thread to avoid nested-loop runtime errors.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return _run_in_new_event_loop(factory)

    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(_run_in_new_event_loop, factory).result()
