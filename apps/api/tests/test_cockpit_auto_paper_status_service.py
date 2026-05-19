"""Tests for MH-COCKPIT-13-A auto-paper status card aggregator."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.services.cockpit_auto_paper_status_service import (
    get_auto_paper_status_card,
)
from app.services.trading_control_service import TradingControlState
from app.services.worker_run_log_service import (
    WorkerRunEntry,
    WorkerRunLogService,
)


def _paper_armed_state() -> TradingControlState:
    return TradingControlState(
        trading_mode="paper",
        execution_control="manual",
        arming_state="armed",
        live_order_submission_allowed=False,
        paper_order_submission_allowed=True,
        auto_trading_allowed=False,
        emergency_stop_active=False,
        reasons=(),
    )


def _entry(status: str = "ok", source: str = "manual") -> WorkerRunEntry:
    now = datetime.now(timezone.utc).isoformat()
    return WorkerRunEntry(
        worker_name="auto_paper_test",
        status=status,
        message="card test entry",
        started_at=now,
        finished_at=now,
        source=source,
    )


@pytest.fixture()
def isolated_service(tmp_path: Path) -> WorkerRunLogService:
    return WorkerRunLogService(log_path=tmp_path / "worker_run_log.jsonl")


def test_card_shape_with_no_runs(isolated_service):
    card = get_auto_paper_status_card(
        trading_control_state=_paper_armed_state(),
        run_log_service=isolated_service,
    )
    for key in (
        "advisory",
        "posture",
        "headline",
        "subline",
        "enforcement",
        "trading_control",
        "latest_run",
        "run_log_summary",
        "links",
    ):
        assert key in card, f"missing key: {key}"
    assert card["latest_run"] is None
    assert card["enforcement"]["auto_paper_enforcement_enabled"] is False
    assert card["enforcement"]["auto_trading_enabled"] is False
    assert card["trading_control"]["paper_order_submission_allowed"] is True


def test_card_posture_ok_when_paper_clean(isolated_service):
    isolated_service.append(_entry(status="ok"))
    card = get_auto_paper_status_card(
        trading_control_state=_paper_armed_state(),
        run_log_service=isolated_service,
    )
    assert card["posture"] == "ok"
    assert card["latest_run"] is not None
    assert card["latest_run"]["status"] == "ok"


def test_card_posture_warning_when_latest_errored(isolated_service):
    isolated_service.append(_entry(status="error"))
    card = get_auto_paper_status_card(
        trading_control_state=_paper_armed_state(),
        run_log_service=isolated_service,
    )
    assert card["posture"] == "warning"
    assert "errored" in card["headline"].lower()


def test_card_posture_blocked_on_emergency_stop(isolated_service):
    state = TradingControlState(
        trading_mode="paper",
        execution_control="manual",
        arming_state="emergency_stopped",
        live_order_submission_allowed=False,
        paper_order_submission_allowed=False,
        auto_trading_allowed=False,
        emergency_stop_active=True,
        reasons=("emergency_stop",),
    )
    card = get_auto_paper_status_card(
        trading_control_state=state,
        run_log_service=isolated_service,
    )
    assert card["posture"] == "blocked"
    assert "emergency" in card["headline"].lower()


def test_card_links_present(isolated_service):
    card = get_auto_paper_status_card(
        trading_control_state=_paper_armed_state(),
        run_log_service=isolated_service,
    )
    for key in ("readiness", "scheduler", "worker_run_log", "broker_control", "broker_health"):
        assert key in card["links"]
        assert card["links"][key].startswith("/")
