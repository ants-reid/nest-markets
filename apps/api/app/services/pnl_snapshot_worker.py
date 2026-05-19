"""MH-46A worker-safe scheduled P&L snapshot capture helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from app.services.broker_service import BrokerService


class PnlSnapshotWorker:
    """Lightweight, dependency-free coordinator for scheduled snapshot capture."""

    def __init__(
        self,
        broker_service: BrokerService | None = None,
        min_interval_seconds: int = 60,
    ) -> None:
        self._broker_service = broker_service or BrokerService()
        self._min_interval = timedelta(seconds=max(1, min_interval_seconds))
        self._last_capture_at: datetime | None = None

    async def capture_once(self) -> dict[str, Any]:
        """Capture exactly one scheduled snapshot for the active broker account."""
        result = await self._broker_service.capture_daily_pnl_snapshot(source="scheduled")
        self._last_capture_at = datetime.now(UTC)
        return result

    def should_capture_now(self, now: datetime | None = None) -> bool:
        """Return True when enough time elapsed since the previous capture."""
        current = now or datetime.now(UTC)
        if self._last_capture_at is None:
            return True
        return (current - self._last_capture_at) >= self._min_interval

    async def maybe_capture_snapshot(self) -> dict[str, Any] | None:
        """Capture a scheduled snapshot only when interval gate allows it."""
        if not self.should_capture_now():
            return None
        return await self.capture_once()


_default_worker = PnlSnapshotWorker()


async def capture_once() -> dict[str, Any]:
    """Module-level helper for schedulers/scripts."""
    return await _default_worker.capture_once()


def should_capture_now(now: datetime | None = None) -> bool:
    """Module-level interval gate helper for schedulers/scripts."""
    return _default_worker.should_capture_now(now=now)


async def maybe_capture_snapshot() -> dict[str, Any] | None:
    """Module-level conditional capture helper for schedulers/scripts."""
    return await _default_worker.maybe_capture_snapshot()
