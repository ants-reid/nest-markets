"""Tests for MH-COCKPIT-13-A auto-paper status card aggregator."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.services.cockpit_auto_paper_status_service import (
    get_auto_paper_status_card,
)
from app.services.cockpit_mode_service import (
    reset_cockpit_mode_for_tests,
    set_cockpit_mode,
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


class _ScalarResult:
    def __init__(self, values):
        self._values = values

    def all(self):
        return list(self._values)

    def first(self):
        return self._values[0] if self._values else None


class _ExecuteResult:
    def __init__(self, values):
        self._values = values

    def scalars(self):
        return _ScalarResult(self._values)


class _FakeSession:
    def __init__(self, *, open_positions=None, latest_order=None):
        self._open_positions = open_positions or []
        self._latest_order = latest_order
        self._calls = 0

    def execute(self, _statement):
        self._calls += 1
        if self._calls == 1:
            return _ExecuteResult(self._open_positions)
        values = [self._latest_order] if self._latest_order is not None else []
        return _ExecuteResult(values)


class _FakeOrder:
    def __init__(
        self,
        *,
        submitted_at: datetime,
        qty: float = 1.5,
        notional: float = 2500.0,
        status: str = "accepted",
        ibkr_status: str | None = None,
    ):
        self.order_type = "auto_paper"
        self.status = status
        self.side = "buy"
        self.direction = "long"
        self.qty = qty
        self.quantity = None
        self.notional = notional
        self.submitted_at = submitted_at
        self.timestamp = None
        self.signal_id = None
        self.asset_id = None
        self.broker_order_id = None
        self.ibkr_status = ibkr_status


@pytest.fixture(autouse=True)
def reset_cockpit_mode_state():
    reset_cockpit_mode_for_tests()
    yield
    reset_cockpit_mode_for_tests()


@pytest.fixture()
def isolated_service(tmp_path: Path) -> WorkerRunLogService:
    return WorkerRunLogService(log_path=tmp_path / "worker_run_log.jsonl")


def test_card_shape_with_no_runs(isolated_service):
    session = _FakeSession()
    card = get_auto_paper_status_card(
        trading_control_state=_paper_armed_state(),
        run_log_service=isolated_service,
        session=session,
    )
    for key in (
        "advisory",
        "mode",
        "auto_paper_selectable",
        "auto_paper_active",
        "auto_paper_armed",
        "live_trading_locked",
        "auto_live_locked",
        "posture",
        "headline",
        "subline",
        "last_check_at",
        "last_action_at",
        "last_decision",
        "last_block_reason",
        "open_paper_positions_count",
        "max_open_paper_positions",
        "risk_gate_summary",
        "safety_notes",
        "operator_next_action",
        "enforcement",
        "trading_control",
        "latest_run",
        "latest_paper_order",
        "candidate_queue",
        "queue_hygiene",
        "run_log_summary",
        "links",
    ):
        assert key in card, f"missing key: {key}"
    assert "controlled_gate" in card
    assert "decision" in card["controlled_gate"]
    assert "snapshot" in card["controlled_gate"]
    for snap_key in (
        "auto_paper_enabled",
        "broker_provider",
        "broker_mode",
        "tws_enabled",
        "live_execution_enabled",
        "max_orders_per_run",
        "max_orders_per_day",
        "max_notional_usd",
        "symbol_allowlist",
        "order_type",
        "limit_price",
        "require_tws",
        "orders_today",
        "kill_switch_active",
    ):
        assert snap_key in card["controlled_gate"]["snapshot"], f"missing snapshot key: {snap_key}"
    assert card["mode"] == "learning"
    assert card["auto_paper_selectable"] is True
    assert card["auto_paper_active"] is False
    assert card["auto_paper_armed"] is False
    assert card["live_trading_locked"] is True
    assert card["auto_live_locked"] is True
    assert card["latest_run"] is None
    assert card["latest_paper_order"] is None
    assert card["last_decision"] == "unknown"
    assert card["enforcement"]["auto_paper_enforcement_enabled"] is False
    assert card["enforcement"]["auto_trading_enabled"] is False
    assert card["trading_control"]["paper_order_submission_allowed"] is True
    assert card["safety_notes"]
    assert "simulate trades only" in " ".join(card["safety_notes"]).lower()
    assert "eligible_count" in card["candidate_queue"]
    assert "top_candidates" in card["candidate_queue"]
    assert "selection_explanation" in card["candidate_queue"]
    assert "stale_manual_seed_count" in card["queue_hygiene"]
    assert "duplicate_symbol_candidate_count" in card["queue_hygiene"]
    assert "cleanup_recommendations" in card["queue_hygiene"]


def test_card_posture_ok_when_paper_clean(isolated_service):
    set_cockpit_mode("auto_paper", trading_control_state=_paper_armed_state())
    isolated_service.append(
        WorkerRunEntry(
            worker_name="auto_paper_test",
            status="ok",
            message="auto_paper_trader: 1 positions opened",
            started_at=datetime.now(timezone.utc).isoformat(),
            finished_at=datetime.now(timezone.utc).isoformat(),
            source="manual",
            outcome_counts={
                "accepted_count": 1,
                "rejected_count": 0,
                "cancelled_count": 0,
                "blocked_count": 0,
                "risk_blocked_count": 0,
                "gate_blocked_count": 0,
                "skipped_cap_count": 0,
                "legacy_broker_rejected_count": 0,
            },
        )
    )
    submitted_at = datetime(2025, 1, 2, 3, 4, tzinfo=timezone.utc)
    card = get_auto_paper_status_card(
        trading_control_state=_paper_armed_state(),
        run_log_service=isolated_service,
        session=_FakeSession(latest_order=_FakeOrder(submitted_at=submitted_at)),
    )
    assert card["posture"] == "ok"
    assert card["mode"] == "auto_paper"
    assert card["auto_paper_active"] is True
    assert card["auto_paper_armed"] is True
    assert card["latest_run"] is not None
    assert card["latest_run"]["status"] == "ok"
    assert card["last_decision"] == "accepted"
    assert card["last_action_at"] == submitted_at.isoformat()
    assert card["latest_paper_order"]["qty"] == pytest.approx(1.5)
    assert any(item["label"] == "Open paper position cap" for item in card["risk_gate_summary"])


def test_card_posture_warning_when_latest_errored(isolated_service):
    isolated_service.append(_entry(status="error"))
    card = get_auto_paper_status_card(
        trading_control_state=_paper_armed_state(),
        run_log_service=isolated_service,
        session=_FakeSession(),
    )
    assert card["posture"] == "warning"
    assert "errored" in card["headline"].lower()
    assert card["last_decision"] == "errored"
    assert "inspect the latest auto paper worker run" in card["operator_next_action"].lower()


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
        session=_FakeSession(),
    )
    assert card["posture"] == "blocked"
    assert "emergency" in card["headline"].lower()
    assert card["last_block_reason"] == "Emergency stop is active."
    assert "clear the emergency stop" in card["operator_next_action"].lower()


def test_card_links_present(isolated_service):
    card = get_auto_paper_status_card(
        trading_control_state=_paper_armed_state(),
        run_log_service=isolated_service,
        session=_FakeSession(),
    )
    for key in ("readiness", "scheduler", "worker_run_log", "broker_control", "broker_health"):
        assert key in card["links"]
        assert card["links"][key].startswith("/")


def test_card_reports_cap_block_and_latest_order(isolated_service):
    set_cockpit_mode("auto_paper", trading_control_state=_paper_armed_state())
    isolated_service.append(
        WorkerRunEntry(
            worker_name="auto_paper_test",
            status="ok",
            message="auto_paper_trader: 0 positions opened, 2 skipped (cap)",
            started_at=datetime.now(timezone.utc).isoformat(),
            finished_at=datetime.now(timezone.utc).isoformat(),
            source="scheduled",
            outcome_counts={
                "accepted_count": 0,
                "rejected_count": 0,
                "cancelled_count": 0,
                "blocked_count": 0,
                "risk_blocked_count": 0,
                "gate_blocked_count": 0,
                "skipped_cap_count": 2,
                "legacy_broker_rejected_count": 0,
            },
        )
    )
    submitted_at = datetime(2025, 1, 2, 4, 5, tzinfo=timezone.utc)
    card = get_auto_paper_status_card(
        trading_control_state=_paper_armed_state(),
        run_log_service=isolated_service,
        session=_FakeSession(
            open_positions=[object(), object(), object(), object(), object()],
            latest_order=_FakeOrder(submitted_at=submitted_at, qty=0.75, notional=950.0, status="queued"),
        ),
    )
    assert card["last_decision"] == "skipped"
    assert card["last_block_reason"] == "Auto Paper position cap reached."
    assert card["open_paper_positions_count"] == 5
    assert card["last_action_at"] == submitted_at.isoformat()
    assert card["latest_paper_order"]["status"] == "queued"
    assert "position cap reached" in card["operator_next_action"].lower()


def test_latest_paper_order_exposes_ibkr_status(isolated_service):
    submitted_at = datetime(2025, 1, 2, 5, 6, tzinfo=timezone.utc)
    card = get_auto_paper_status_card(
        trading_control_state=_paper_armed_state(),
        run_log_service=isolated_service,
        session=_FakeSession(
            latest_order=_FakeOrder(submitted_at=submitted_at, ibkr_status="PreSubmitted"),
        ),
    )
    assert card["latest_paper_order"] is not None
    assert card["latest_paper_order"]["ibkr_status"] == "PreSubmitted"


def test_audit_alignment_warns_when_order_exists_but_history_missing(isolated_service):
    submitted_at = datetime(2025, 1, 2, 5, 6, tzinfo=timezone.utc)
    card = get_auto_paper_status_card(
        trading_control_state=_paper_armed_state(),
        run_log_service=isolated_service,
        session=_FakeSession(
            latest_order=_FakeOrder(submitted_at=submitted_at, ibkr_status="PreSubmitted"),
        ),
    )

    assert card["audit_alignment"]["status"] == "warning"
    assert "latest_paper_order_without_run_log" in card["audit_alignment"]["warning_codes"]
    assert card["audit_alignment"]["latest_paper_order_present"] is True
