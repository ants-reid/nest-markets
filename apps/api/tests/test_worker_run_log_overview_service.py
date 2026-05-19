"""Tests for MH-158-A worker-run-log overview aggregator service."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.services.worker_run_log_overview_service import (
    WorkerRunLogOverviewError,
    get_worker_run_log_overview,
)
from app.services.worker_run_log_service import (
    WorkerRunEntry,
    WorkerRunLogService,
)


def _make_entry(suffix: str, *, status: str = "ok", source: str = "manual") -> WorkerRunEntry:
    now = datetime.now(timezone.utc).isoformat()
    return WorkerRunEntry(
        worker_name="auto_paper_test",
        status=status,
        message=f"test run {suffix}: 0 positions opened, 0 risk-blocked",
        started_at=now,
        finished_at=now,
        source=source,
    )


@pytest.fixture()
def isolated_service(tmp_path: Path) -> WorkerRunLogService:
    return WorkerRunLogService(log_path=tmp_path / "worker_run_log.jsonl")


def test_empty_overview_shape(isolated_service):
    result = get_worker_run_log_overview(limit=5, service=isolated_service)
    assert "operator-facing only" in result["advisory"]
    assert result["limit"] == 5
    assert result["retention"]["current_entry_count"] == 0
    assert result["retention"]["log_exists"] is False
    assert result["totals"]["returned"] == 0
    assert result["entries"] == []


def test_overview_returns_recent_entries_newest_first(isolated_service):
    for i in range(3):
        isolated_service.append(_make_entry(str(i)))
    result = get_worker_run_log_overview(limit=10, service=isolated_service)
    assert result["totals"]["returned"] == 3
    assert result["retention"]["current_entry_count"] == 3
    # Newest first per WorkerRunLogService.recent()
    assert "test run 2" in result["entries"][0]["message"]


def test_overview_status_and_source_counts(isolated_service):
    isolated_service.append(_make_entry("a", status="ok", source="manual"))
    isolated_service.append(_make_entry("b", status="ok", source="scheduled"))
    isolated_service.append(_make_entry("c", status="error", source="manual"))
    result = get_worker_run_log_overview(limit=10, service=isolated_service)
    assert result["totals"]["by_status"].get("ok") == 2
    assert result["totals"]["by_status"].get("error") == 1
    assert result["totals"]["by_source"].get("manual") == 2
    assert result["totals"]["by_source"].get("scheduled") == 1


def test_limit_clamped(isolated_service):
    for i in range(5):
        isolated_service.append(_make_entry(str(i)))
    result = get_worker_run_log_overview(limit=10_000, service=isolated_service)
    assert result["limit"] == 200
    assert result["totals"]["returned"] <= 200


def test_invalid_limit_rejected(isolated_service):
    with pytest.raises(WorkerRunLogOverviewError):
        get_worker_run_log_overview(limit=0, service=isolated_service)
