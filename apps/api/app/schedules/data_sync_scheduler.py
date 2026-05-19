"""DataSyncScheduler — cron registry for the data synchronisation worker."""

from __future__ import annotations

from app.schedules.base_scheduler import BaseScheduler, ScheduledJob
from app.workers.auto_paper_close_worker import AutoPaperCloseWorker
from app.workers.auto_paper_trader_worker import AutoPaperTraderWorker
from app.workers.data_sync_worker import DataSyncWorker
from app.workers.news_ingest_worker import NewsIngestWorker
from app.workers.signal_sweep_worker import SignalSweepWorker


class DataSyncScheduler(BaseScheduler):
    """Register all scheduled background jobs."""

    def __init__(self) -> None:
        super().__init__()
        self.register_job(
            ScheduledJob(
                name="data_sync",
                cron="*/5 * * * *",
                enabled=True,
            )
        )
        self.register_job(
            ScheduledJob(
                name="news_ingest",
                cron="0 * * * *",
                enabled=True,
            )
        )
        self.register_job(
            ScheduledJob(
                name="signal_sweep",
                cron="0 */4 * * *",  # every 4 hours
                enabled=True,
            )
        )
        self.register_job(
            ScheduledJob(
                name="auto_paper_trader",
                cron="30 */4 * * *",  # 30 min after each sweep
                enabled=True,
            )
        )
        self.register_job(
            ScheduledJob(
                name="auto_paper_close",
                cron="0 2 * * *",  # daily at 02:00 UTC
                enabled=True,
            )
        )

    def get_worker(self, job_name: str):
        """Return the worker instance matching a scheduled job name."""
        if job_name == "data_sync":
            return DataSyncWorker()
        if job_name == "news_ingest":
            return NewsIngestWorker()
        if job_name == "signal_sweep":
            return SignalSweepWorker()
        if job_name == "auto_paper_trader":
            return AutoPaperTraderWorker()
        if job_name == "auto_paper_close":
            return AutoPaperCloseWorker()
        raise KeyError(f"Unknown scheduled job: {job_name}")
