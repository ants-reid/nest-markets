"""Lightweight file-backed log of auto-paper worker run results.

Each entry is written after a POST /market-data/auto-paper/run call (manual or
scheduled).  The log is stored as a JSON-lines file in the data directory so no
DB migration is required.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from app.workers.base_worker import WorkerResult

_logger = logging.getLogger(__name__)

# Default path; override via WORKER_RUN_LOG_PATH env var
_DEFAULT_LOG_PATH = Path(__file__).resolve().parent.parent / "data" / "worker_run_log.jsonl"
_MAX_ENTRIES = 200
_RETENTION_WARNING_THRESHOLD_PCT = 80.0
_AUTO_DIAG_MARKER = " || auto_diag="


@dataclass
class WorkerRunEntry:
    """One persisted auto-paper run record."""

    worker_name: str
    status: str
    message: str
    started_at: str
    finished_at: str
    source: str = "manual"  # "manual" | "scheduled"
    outcome_counts: dict[str, int] | None = None
    watchdog_summary: dict[str, Any] | None = None
    attempt_outcomes: list[dict[str, Any]] | None = None


def _split_summary_and_diag(message: str) -> tuple[str, dict[str, Any] | None]:
    if _AUTO_DIAG_MARKER not in message:
        return message, None

    summary, raw_diag = message.split(_AUTO_DIAG_MARKER, 1)
    summary = summary.strip()
    try:
        parsed = json.loads(raw_diag)
    except json.JSONDecodeError:
        return summary, None

    if not isinstance(parsed, dict):
        return summary, None
    return summary, parsed


def extract_auto_paper_watchdog_summary(message: str) -> dict[str, Any] | None:
    _, diag = _split_summary_and_diag(message)
    if not isinstance(diag, dict):
        return None
    watchdog_summary = diag.get("watchdog_summary")
    if not isinstance(watchdog_summary, dict):
        return None
    return watchdog_summary


def extract_auto_paper_attempt_outcomes(message: str) -> list[dict[str, Any]]:
    _, diag = _split_summary_and_diag(message)
    if not isinstance(diag, dict):
        return []
    outcomes = diag.get("attempt_outcomes")
    if not isinstance(outcomes, list):
        return []
    return [item for item in outcomes if isinstance(item, dict)]


def extract_auto_paper_outcome_counts(message: str) -> dict[str, int]:
    """Parse structured outcome counts from an auto-paper worker summary message."""

    summary_message, _ = _split_summary_and_diag(message)

    def _count(pattern: str) -> int:
        match = re.search(pattern, summary_message)
        return int(match.group(1)) if match else 0

    accepted_count = _count(r"(\d+) positions opened")
    risk_blocked_count = _count(r"(\d+) risk-blocked")
    gate_blocked_count = _count(r"(\d+) gate-blocked")
    rejected_count = _count(r"(\d+) rejected")
    cancelled_count = _count(r"(\d+) cancelled")
    skipped_cap_count = _count(r"(\d+) skipped \(cap\)")
    legacy_broker_rejected_count = _count(r"(\d+) broker-rejected")
    if legacy_broker_rejected_count and rejected_count == 0:
        rejected_count = legacy_broker_rejected_count

    return {
        "accepted_count": accepted_count,
        "rejected_count": rejected_count,
        "cancelled_count": cancelled_count,
        "blocked_count": risk_blocked_count + gate_blocked_count,
        "risk_blocked_count": risk_blocked_count,
        "gate_blocked_count": gate_blocked_count,
        "skipped_cap_count": skipped_cap_count,
        "legacy_broker_rejected_count": legacy_broker_rejected_count,
    }


def build_auto_paper_run_entry(result: WorkerResult, *, source: str) -> WorkerRunEntry:
    """Build a persisted run-log entry for one auto-paper worker execution."""
    normalized_source = source if source in {"manual", "scheduled"} else "manual"
    return WorkerRunEntry(
        worker_name=result.worker_name,
        status=result.status,
        message=result.message,
        started_at=result.started_at.isoformat(),
        finished_at=result.finished_at.isoformat(),
        source=normalized_source,
        outcome_counts=extract_auto_paper_outcome_counts(result.message),
        watchdog_summary=extract_auto_paper_watchdog_summary(result.message),
        attempt_outcomes=extract_auto_paper_attempt_outcomes(result.message),
    )


class WorkerRunLogService:
    """Read and write the worker run log."""

    def __init__(self, log_path: Path | None = None) -> None:
        self._path: Path = (
            log_path
            or Path(os.getenv("WORKER_RUN_LOG_PATH", str(_DEFAULT_LOG_PATH)))
        )

    # ------------------------------------------------------------------ #
    # Write                                                                #
    # ------------------------------------------------------------------ #

    def append(self, entry: WorkerRunEntry) -> None:
        """Append one entry; prune to _MAX_ENTRIES to keep size bounded."""
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            existing = self._read_raw()
            existing.append(asdict(entry))
            # Truncate oldest entries
            if len(existing) > _MAX_ENTRIES:
                existing = existing[-_MAX_ENTRIES:]
            self._write_raw(existing)
        except Exception as exc:  # noqa: BLE001
            _logger.warning("WorkerRunLogService: write failed: %s", exc)

    # ------------------------------------------------------------------ #
    # Read                                                                 #
    # ------------------------------------------------------------------ #

    def recent(self, limit: int = 20) -> list[WorkerRunEntry]:
        """Return up to *limit* most-recent entries, newest first."""
        raw = self._read_raw()
        tail = raw[-limit:][::-1]
        entries: list[WorkerRunEntry] = []
        for item in tail:
            try:
                entries.append(WorkerRunEntry(**item))
            except Exception:  # noqa: BLE001
                pass
        return entries

    def get_retention_metadata(self) -> dict[str, str | int | bool | None]:
        """Return read-only retention details for the file-backed run log."""
        raw = self._read_raw()
        oldest_started_at = None
        newest_started_at = None

        if raw:
            oldest_started_at = raw[0].get("started_at")
            newest_started_at = raw[-1].get("started_at")

        current_entry_count = len(raw)
        entries_remaining = max(_MAX_ENTRIES - current_entry_count, 0)
        utilization_pct = round((current_entry_count / _MAX_ENTRIES) * 100, 2) if _MAX_ENTRIES > 0 else 0.0
        near_capacity = utilization_pct >= _RETENTION_WARNING_THRESHOLD_PCT
        retention_status = "near_capacity" if near_capacity else "ok"
        retention_warning = (
            f"Auto-paper history retention is at {utilization_pct:.2f}% of the { _MAX_ENTRIES } entry cap."
            if near_capacity
            else None
        )
        retained_span_hours = None
        average_entries_per_day = None
        estimated_days_until_capacity = None
        retention_trend_status = "insufficient_data"

        if oldest_started_at and newest_started_at and current_entry_count > 1:
            try:
                oldest_dt = datetime.fromisoformat(oldest_started_at)
                newest_dt = datetime.fromisoformat(newest_started_at)
                retained_span_seconds = max((newest_dt - oldest_dt).total_seconds(), 0.0)
                retained_span_hours = round(retained_span_seconds / 3600, 2)
                if retained_span_seconds > 0:
                    average_entries_per_day = round(current_entry_count / (retained_span_seconds / 86400), 2)
                    if average_entries_per_day > 0:
                        estimated_days_until_capacity = round(entries_remaining / average_entries_per_day, 2)
                        retention_trend_status = "growing"
            except ValueError:
                retained_span_hours = None
                average_entries_per_day = None
                estimated_days_until_capacity = None
                retention_trend_status = "insufficient_data"

        return {
            "storage_backend": "file_jsonl",
            "trim_on_append": True,
            "max_entries": _MAX_ENTRIES,
            "current_entry_count": current_entry_count,
            "entries_remaining": entries_remaining,
            "utilization_pct": utilization_pct,
            "warning_threshold_pct": _RETENTION_WARNING_THRESHOLD_PCT,
            "near_capacity": near_capacity,
            "retention_status": retention_status,
            "retention_warning": retention_warning,
            "retained_span_hours": retained_span_hours,
            "average_entries_per_day": average_entries_per_day,
            "estimated_days_until_capacity": estimated_days_until_capacity,
            "retention_trend_status": retention_trend_status,
            "log_exists": self._path.exists(),
            "oldest_started_at": oldest_started_at,
            "latest_started_at": newest_started_at,
        }

    # ------------------------------------------------------------------ #
    # Internals                                                            #
    # ------------------------------------------------------------------ #

    def _read_raw(self) -> list[dict]:
        if not self._path.exists():
            return []
        try:
            return [json.loads(line) for line in self._path.read_text().splitlines() if line.strip()]
        except Exception as exc:  # noqa: BLE001
            _logger.warning("WorkerRunLogService: read failed: %s", exc)
            return []

    def _write_raw(self, entries: list[dict]) -> None:
        self._path.write_text("\n".join(json.dumps(e) for e in entries) + "\n")
