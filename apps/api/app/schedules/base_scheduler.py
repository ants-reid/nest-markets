"""Base scheduler scaffold for Phase 7 scheduled jobs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScheduledJob:
    """Immutable scheduled job definition."""

    name: str
    cron: str
    enabled: bool = True


class BaseScheduler:
    """Minimal scheduler scaffold with in-memory job registry."""

    def __init__(self) -> None:
        self._jobs: dict[str, ScheduledJob] = {}

    def register_job(self, job: ScheduledJob) -> None:
        """Register or replace a job definition by name."""
        self._jobs[job.name] = job

    def list_jobs(self) -> list[ScheduledJob]:
        """Return all registered jobs sorted by name for deterministic behavior."""
        return [self._jobs[name] for name in sorted(self._jobs.keys())]
