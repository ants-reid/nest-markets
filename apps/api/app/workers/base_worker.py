"""Base worker scaffold for Phase 7 background infrastructure."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class WorkerResult:
    """Standard result envelope for worker run invocations."""

    worker_name: str
    status: str
    started_at: datetime
    finished_at: datetime
    message: str


class BaseWorker:
    """Minimal worker scaffold with overridable execute hook."""

    worker_name = "base_worker"

    def run(self) -> WorkerResult:
        """Run the worker's execute hook and return a result envelope."""
        started_at = datetime.now(UTC)
        message = self.execute()
        finished_at = datetime.now(UTC)
        return WorkerResult(
            worker_name=self.worker_name,
            status="ok",
            started_at=started_at,
            finished_at=finished_at,
            message=message,
        )

    def execute(self) -> str:
        """Execute worker logic.

        Subclasses should override this method with real task behavior.
        """
        return "base worker scaffold executed"
