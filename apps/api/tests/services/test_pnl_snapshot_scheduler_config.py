"""MH-46B-1 tests for scheduler cadence registration."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.main import _register_pnl_snapshot_scheduler


def test_register_pnl_snapshot_scheduler_skips_when_disabled():
    scheduler = MagicMock()

    _register_pnl_snapshot_scheduler(
        scheduler,
        enabled=False,
        interval_seconds=60,
    )

    scheduler.add_job.assert_not_called()


def test_register_pnl_snapshot_scheduler_adds_interval_job_when_enabled():
    scheduler = MagicMock()

    _register_pnl_snapshot_scheduler(
        scheduler,
        enabled=True,
        interval_seconds=45,
    )

    scheduler.add_job.assert_called_once()
    _, kwargs = scheduler.add_job.call_args
    assert kwargs["id"] == "pnl_snapshot_capture"
    assert kwargs["replace_existing"] is True


def test_register_pnl_snapshot_scheduler_enforces_min_interval_floor():
    scheduler = MagicMock()

    _register_pnl_snapshot_scheduler(
        scheduler,
        enabled=True,
        interval_seconds=1,
    )

    args, _ = scheduler.add_job.call_args
    trigger = args[1]
    assert trigger.interval.total_seconds() == 15
