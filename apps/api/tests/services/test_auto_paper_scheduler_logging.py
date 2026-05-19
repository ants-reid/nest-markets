"""MH-84 tests for scheduled auto-paper logging parity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.main import _run_scheduled_auto_paper_job
from app.services.worker_run_log_service import WorkerRunLogService
from app.workers.base_worker import WorkerResult


@dataclass
class _StubWorker:
    result: WorkerResult

    def run(self) -> WorkerResult:
        return self.result


class _StubRunLog(WorkerRunLogService):
    def __init__(self) -> None:
        self.entries = []

    def append(self, entry) -> None:
        self.entries.append(entry)


def test_run_scheduled_auto_paper_job_persists_structured_outcome_counts() -> None:
    worker = _StubWorker(
        WorkerResult(
            worker_name="auto_paper_trader",
            status="ok",
            started_at=datetime(2026, 4, 30, 12, 0, 0, tzinfo=timezone.utc),
            finished_at=datetime(2026, 4, 30, 12, 0, 2, tzinfo=timezone.utc),
            message="auto_paper_trader: 1 positions opened, 2 rejected, 1 cancelled, 1 risk-blocked, 1 gate-blocked",
        )
    )
    run_log = _StubRunLog()

    _run_scheduled_auto_paper_job(worker, run_log)

    assert len(run_log.entries) == 1
    entry = run_log.entries[0]
    assert entry.source == "scheduled"
    assert entry.outcome_counts == {
        "accepted_count": 1,
        "rejected_count": 2,
        "cancelled_count": 1,
        "blocked_count": 2,
        "risk_blocked_count": 1,
        "gate_blocked_count": 1,
        "skipped_cap_count": 0,
        "legacy_broker_rejected_count": 0,
    }