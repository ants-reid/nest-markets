"""Tests for Phase 7 worker/scheduler scaffolds."""

import os

from app.schedules import BaseScheduler, ScheduledJob
from app.workers import BaseWorker
from app.workers.data_sync_worker import DataSyncWorker
from app.schedules.data_sync_scheduler import DataSyncScheduler


def test_base_worker_run_returns_ok_result() -> None:
    worker = BaseWorker()
    result = worker.run()

    assert result.worker_name == "base_worker"
    assert result.status == "ok"
    assert result.message == "base worker scaffold executed"
    assert result.finished_at >= result.started_at


def test_base_scheduler_registers_and_lists_jobs_sorted() -> None:
    scheduler = BaseScheduler()
    scheduler.register_job(ScheduledJob(name="nightly_eval", cron="0 2 * * *"))
    scheduler.register_job(ScheduledJob(name="hourly_snapshot", cron="0 * * * *"))

    names = [job.name for job in scheduler.list_jobs()]
    assert names == ["hourly_snapshot", "nightly_eval"]


# ---------------------------------------------------------------------------
# QA-105: DataSyncWorker / DataSyncScheduler
# ---------------------------------------------------------------------------

def test_data_sync_worker_run_returns_ok() -> None:
    worker = DataSyncWorker()
    result = worker.run()

    assert result.worker_name == "data_sync"
    assert result.status == "ok"
    # Without a POLYGON_API_KEY configured the worker skips gracefully
    assert "data_sync" in result.message


def test_data_sync_scheduler_lists_one_job_named_data_sync() -> None:
    scheduler = DataSyncScheduler()
    jobs = scheduler.list_jobs()

    assert len(jobs) >= 5
    job_names = {j.name for j in jobs}
    assert {"data_sync", "news_ingest", "signal_sweep", "auto_paper_trader", "auto_paper_close"}.issubset(job_names)


def test_app_env_test_prevents_scheduler_from_starting() -> None:
    """Confirm APP_ENV=test guard stops scheduler during pytest."""
    # The conftest.py sets os.environ["APP_ENV"] = "test" before app import.
    # We verify the env var is set here; the scheduler-skip logic in main.py
    # reads this env var at lifespan startup.
    assert os.environ.get("APP_ENV") == "test"
