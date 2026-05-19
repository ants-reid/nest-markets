"""MH-158-A — Worker-run-log overview aggregator.

Read-only consolidator that combines retention metadata and the most-recent
auto-paper worker run entries into a single cockpit-friendly payload. Wraps
the existing :class:`WorkerRunLogService` (file-backed JSONL store) without
introducing new persistence or new write paths.

Drift-lock guarantees:
- Pure read; no writes anywhere.
- Wraps an existing service; no broker/LLM/trading-control code is touched.
- Worker execution behaviour is unchanged.
- Output is operator-facing only and never feeds the trading path.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List

from app.services.worker_run_log_service import (
    WorkerRunEntry,
    WorkerRunLogService,
)

_DEFAULT_LIMIT = 20
_MAX_LIMIT = 200
_MIN_LIMIT = 1


class WorkerRunLogOverviewError(ValueError):
    """Raised when the caller passes invalid overview parameters."""


def _entry_payload(entry: WorkerRunEntry) -> Dict[str, Any]:
    return asdict(entry)


def _aggregate_status_counts(entries: List[WorkerRunEntry]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for e in entries:
        key = (e.status or "unknown").lower()
        counts[key] = counts.get(key, 0) + 1
    return counts


def _aggregate_source_counts(entries: List[WorkerRunEntry]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for e in entries:
        key = (e.source or "unknown").lower()
        counts[key] = counts.get(key, 0) + 1
    return counts


def get_worker_run_log_overview(
    *,
    limit: int = _DEFAULT_LIMIT,
    service: WorkerRunLogService | None = None,
) -> Dict[str, Any]:
    """Return retention metadata + recent run entries.

    Parameters
    ----------
    limit:
        Number of recent entries to include. Clamped to ``[1, 200]``.
    service:
        Optional injected service (test hook).
    """
    if not isinstance(limit, int) or limit < _MIN_LIMIT:
        raise WorkerRunLogOverviewError("limit must be a positive integer")
    capped = max(_MIN_LIMIT, min(int(limit), _MAX_LIMIT))

    svc = service or WorkerRunLogService()
    retention = svc.get_retention_metadata()
    entries = svc.recent(limit=capped)

    return {
        "advisory": (
            "Worker-run-log overview is derived from the file-backed "
            "auto-paper run log and is operator-facing only. It never "
            "feeds the trading path."
        ),
        "limit": capped,
        "retention": retention,
        "totals": {
            "returned": len(entries),
            "by_status": _aggregate_status_counts(entries),
            "by_source": _aggregate_source_counts(entries),
        },
        "entries": [_entry_payload(e) for e in entries],
    }
