"""MH-46A tests for scheduled P&L snapshot worker helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.pnl_snapshot_worker import PnlSnapshotWorker


@pytest.mark.asyncio
async def test_capture_once_uses_scheduled_source():
    broker_service = MagicMock()
    broker_service.capture_daily_pnl_snapshot = AsyncMock(
        return_value={"snapshot_ts": "2026-04-28T12:00:00+00:00", "source": "scheduled"}
    )
    worker = PnlSnapshotWorker(broker_service=broker_service, min_interval_seconds=60)

    result = await worker.capture_once()

    assert result["source"] == "scheduled"
    broker_service.capture_daily_pnl_snapshot.assert_awaited_once_with(source="scheduled")


def test_should_capture_now_respects_interval_gate():
    broker_service = MagicMock()
    worker = PnlSnapshotWorker(broker_service=broker_service, min_interval_seconds=60)

    base = datetime(2026, 4, 28, 12, 0, 0, tzinfo=UTC)
    worker._last_capture_at = base

    assert worker.should_capture_now(now=base + timedelta(seconds=30)) is False
    assert worker.should_capture_now(now=base + timedelta(seconds=61)) is True


@pytest.mark.asyncio
async def test_maybe_capture_snapshot_skips_when_not_due():
    broker_service = MagicMock()
    worker = PnlSnapshotWorker(broker_service=broker_service, min_interval_seconds=60)
    worker._last_capture_at = datetime.now(UTC)

    result = await worker.maybe_capture_snapshot()

    assert result is None
    broker_service.capture_daily_pnl_snapshot.assert_not_called()
