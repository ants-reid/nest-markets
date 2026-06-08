"""Tests for AutoPaperTraderWorker — QA-210/211/212/213/214."""

from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.db.enums import AssetClass, SignalStatus
from app.db.models.signal import Signal
from app.schedules.data_sync_scheduler import DataSyncScheduler
from app.clients.broker.broker_interface import OrderResult
from app.services.auto_paper_gate_service import AutoPaperGateDecision
from app.services.trading_control_service import AutoTradingBlockedError
from app.services.opportunity_ranker_service import RankedOpportunity
from app.services.risk_service import RiskOutput
from app.workers.auto_paper_trader_worker import (
    AutoPaperTraderWorker,
    classify_auto_paper_submit_error,
)
from app.workers.base_worker import BaseWorker


@pytest.fixture(autouse=True)
def _bypass_auto_paper_controlled_gate():
    # These tests cover downstream worker behavior (risk, broker, position cap).
    # The controlled-run gate has dedicated coverage in
    # test_auto_paper_gate_service.py and test_auto_paper_worker_gate_integration.py.
    allowed = AutoPaperGateDecision(allowed=True, blocking_gate=None, reason=None, snapshot={})
    with patch(
        "app.services.auto_paper_gate_service.AutoPaperGateService.evaluate_run",
        return_value=allowed,
    ), patch(
        "app.services.auto_paper_gate_service.AutoPaperGateService.evaluate_order",
        return_value=allowed,
    ):
        yield


# ---------------------------------------------------------------------------
# QA-210 — ExecutionModeName AUTO_PAPER enum
# ---------------------------------------------------------------------------


def test_execution_mode_name_has_auto_paper():
    """ExecutionModeName must include AUTO_PAPER value (BP3-04.01)."""
    from app.db.enums import ExecutionModeName

    assert hasattr(ExecutionModeName, "AUTO_PAPER")
    assert ExecutionModeName.AUTO_PAPER.value == "auto_paper"


def test_execution_mode_service_auto_paper_no_approval():
    """ExecutionModeService with auto_paper mode returns requires_approval=False."""
    from app.services.execution_mode_service import ExecutionModeService

    mock_session = MagicMock()
    mock_mode = MagicMock()
    mock_mode.name = "auto_paper"
    mock_mode.id = uuid.uuid4()
    mock_mode.requires_approval = "inactive"
    mock_session.query.return_value.filter.return_value.first.return_value = mock_mode

    service = ExecutionModeService(session=mock_session)
    route = service.get_route()
    assert route.requires_approval is False


# ---------------------------------------------------------------------------
# QA-211 — AutoPaperTraderWorker is a BaseWorker
# ---------------------------------------------------------------------------


def test_auto_paper_trader_worker_is_base_worker():
    """AutoPaperTraderWorker must extend BaseWorker (Gate 9)."""
    assert issubclass(AutoPaperTraderWorker, BaseWorker)


def test_auto_paper_trader_worker_name():
    """worker_name must be 'auto_paper_trader'."""
    assert AutoPaperTraderWorker.worker_name == "auto_paper_trader"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_opportunity(symbol: str = "EURUSD") -> RankedOpportunity:
    return RankedOpportunity(
        signal_id=uuid.uuid4(),
        asset=symbol,
        asset_class=AssetClass.FX,
        direction="long",
        setup_type="trend_pullback",
        confidence=0.80,
        score=82.5,
        regime="trend",
        horizon="intraday",
        entry_low=1.081,
        entry_high=1.082,
        stop_price=1.079,
        target_price=1.085,
    )


def _make_signal(signal_id: uuid.UUID) -> MagicMock:
    s = MagicMock(spec=Signal)
    s.id = signal_id
    s.asset_id = uuid.uuid4()
    s.entry_min = Decimal("1.0815")
    s.stop_price = Decimal("1.0790")
    s.target_price = Decimal("1.0850")
    s.signal_status = SignalStatus.CANDIDATE
    s.confidence = Decimal("0.80")
    s.signal_score = Decimal("82")
    return s


def _make_risk_profile() -> MagicMock:
    from app.db.models.risk_profile import RiskProfile

    p = MagicMock(spec=RiskProfile)
    p.min_confidence = Decimal("0.60")
    p.min_signal_score = Decimal("50")
    p.max_spread_bps_fx = Decimal("5")
    p.max_spread_bps_equity = Decimal("10")
    p.max_daily_drawdown_pct = Decimal("2.0")
    p.cooldown_after_3_losses_min = None
    p.kill_switch_enabled = False
    p.max_open_positions = Decimal("5")
    p.max_correlated_positions = Decimal("3")
    p.max_correlated_bucket_exposure = Decimal("3")
    return p


# ---------------------------------------------------------------------------
# QA-212 — Risk gate always called; approved opportunity opens position
# ---------------------------------------------------------------------------


def test_auto_paper_opens_position_when_risk_approved():
    """Accepted broker outcomes should persist both PaperOrder and Position."""
    mock_session = MagicMock()

    opportunity = _make_opportunity("EURUSD")
    signal = _make_signal(opportunity.signal_id)

    mock_session.execute.return_value.scalar_one.return_value = 0  # 0 open positions
    mock_session.get.return_value = signal

    risk_profile = _make_risk_profile()
    mock_session.query.return_value.filter.return_value.first.return_value = risk_profile

    approved_output = RiskOutput(approved=True, decision="approved")

    with patch("app.workers.auto_paper_trader_worker.OpportunityRankerService") as mock_ranker_cls, \
         patch("app.workers.auto_paper_trader_worker.RiskService") as mock_risk_cls, \
         patch("app.workers.auto_paper_trader_worker.BrokerService.submit_auto_order", new_callable=AsyncMock) as mock_submit_auto_order:

        mock_ranker_cls.return_value.rank.return_value = [opportunity]
        mock_risk_cls.return_value.evaluate.return_value = approved_output
        mock_submit_auto_order.return_value = OrderResult(broker_order_id="AUTO-1", status="SUBMITTED")

        worker = AutoPaperTraderWorker(session=mock_session)
        result = worker.run()

    assert result.status == "ok"
    assert "1 positions opened" in result.message
    # PaperOrder and Position must have been added
    add_calls = mock_session.add.call_args_list
    assert len(add_calls) == 2
    paper_order = add_calls[0].args[0]
    position = add_calls[1].args[0]
    assert paper_order.status == "accepted"
    assert paper_order.ibkr_status == "SUBMITTED"
    assert position.broker_order_id == "AUTO-1"
    assert signal.signal_status == SignalStatus.PAPER_SUBMITTED
    # Risk service was called exactly once (Gate 10)
    mock_risk_cls.return_value.evaluate.assert_called_once()
    mock_submit_auto_order.assert_called_once()


def test_auto_paper_does_not_open_position_when_risk_blocked():
    """When risk is blocked, no PaperOrder or Position must be created."""
    mock_session = MagicMock()

    opportunity = _make_opportunity("GBPUSD")
    signal = _make_signal(opportunity.signal_id)

    mock_session.execute.return_value.scalar_one.return_value = 0
    mock_session.get.return_value = signal

    risk_profile = _make_risk_profile()
    mock_session.query.return_value.filter.return_value.first.return_value = risk_profile

    blocked_output = RiskOutput(
        approved=False, decision="rejected", blocking_rule="signal_score_below_threshold"
    )

    with patch("app.workers.auto_paper_trader_worker.OpportunityRankerService") as mock_ranker_cls, \
         patch("app.workers.auto_paper_trader_worker.RiskService") as mock_risk_cls:

        mock_ranker_cls.return_value.rank.return_value = [opportunity]
        mock_risk_cls.return_value.evaluate.return_value = blocked_output

        worker = AutoPaperTraderWorker(session=mock_session)
        result = worker.run()

    assert result.status == "ok"
    assert "0 positions opened" in result.message
    # Gate 10: risk service still called despite block
    mock_risk_cls.return_value.evaluate.assert_called_once()
    # No DB rows added
    mock_session.add.assert_not_called()


def test_auto_paper_does_not_open_position_when_broker_gate_blocks():
    """Worker automation must not create rows when the broker auto-submit seam is blocked."""
    mock_session = MagicMock()

    opportunity = _make_opportunity("USDJPY")
    signal = _make_signal(opportunity.signal_id)

    mock_session.execute.return_value.scalar_one.return_value = 0
    mock_session.get.return_value = signal

    risk_profile = _make_risk_profile()
    mock_session.query.return_value.filter.return_value.first.return_value = risk_profile

    approved_output = RiskOutput(approved=True, decision="approved")

    with patch("app.workers.auto_paper_trader_worker.OpportunityRankerService") as mock_ranker_cls, \
         patch("app.workers.auto_paper_trader_worker.RiskService") as mock_risk_cls, \
         patch(
             "app.workers.auto_paper_trader_worker.BrokerService.submit_auto_order",
             new_callable=AsyncMock,
             side_effect=AutoTradingBlockedError("Auto trading is not enabled in MH-36B. Manual trading only."),
         ) as mock_submit_auto_order:

        mock_ranker_cls.return_value.rank.return_value = [opportunity]
        mock_risk_cls.return_value.evaluate.return_value = approved_output

        worker = AutoPaperTraderWorker(session=mock_session)
        result = worker.run()

    assert result.status == "ok"
    assert "0 positions opened" in result.message
    assert "1 gate-blocked" in result.message
    mock_risk_cls.return_value.evaluate.assert_called_once()
    mock_submit_auto_order.assert_called_once()
    mock_session.add.assert_not_called()
    assert signal.signal_status == SignalStatus.CANDIDATE


def test_auto_paper_records_rejected_broker_outcome_without_opening_position():
    """Rejected broker outcomes should persist only an order-level outcome, not a position."""
    mock_session = MagicMock()

    opportunity = _make_opportunity("AUDUSD")
    signal = _make_signal(opportunity.signal_id)

    mock_session.execute.return_value.scalar_one.return_value = 0
    mock_session.get.return_value = signal

    risk_profile = _make_risk_profile()
    mock_session.query.return_value.filter.return_value.first.return_value = risk_profile

    approved_output = RiskOutput(approved=True, decision="approved")

    with patch("app.workers.auto_paper_trader_worker.OpportunityRankerService") as mock_ranker_cls, \
         patch("app.workers.auto_paper_trader_worker.RiskService") as mock_risk_cls, \
         patch("app.workers.auto_paper_trader_worker.BrokerService.submit_auto_order", new_callable=AsyncMock) as mock_submit_auto_order:

        mock_ranker_cls.return_value.rank.return_value = [opportunity]
        mock_risk_cls.return_value.evaluate.return_value = approved_output
        mock_submit_auto_order.return_value = OrderResult(
            broker_order_id="AUTO-2",
            status="REJECTED",
            error_message="Order rejected by broker",
        )

        worker = AutoPaperTraderWorker(session=mock_session)
        result = worker.run()

    assert result.status == "ok"
    assert "0 positions opened" in result.message
    assert "1 rejected" in result.message
    add_calls = mock_session.add.call_args_list
    assert len(add_calls) == 1
    paper_order = add_calls[0].args[0]
    assert paper_order.status == "rejected"
    assert paper_order.ibkr_status == "REJECTED"
    assert signal.signal_status == SignalStatus.CANDIDATE


def test_auto_paper_records_cancelled_broker_outcome_without_opening_position():
    """Cancelled broker outcomes should persist only order state and skip position open."""
    mock_session = MagicMock()

    opportunity = _make_opportunity("NZDUSD")
    signal = _make_signal(opportunity.signal_id)

    mock_session.execute.return_value.scalar_one.return_value = 0
    mock_session.get.return_value = signal

    risk_profile = _make_risk_profile()
    mock_session.query.return_value.filter.return_value.first.return_value = risk_profile

    approved_output = RiskOutput(approved=True, decision="approved")

    with patch("app.workers.auto_paper_trader_worker.OpportunityRankerService") as mock_ranker_cls, \
         patch("app.workers.auto_paper_trader_worker.RiskService") as mock_risk_cls, \
         patch("app.workers.auto_paper_trader_worker.BrokerService.submit_auto_order", new_callable=AsyncMock) as mock_submit_auto_order:

        mock_ranker_cls.return_value.rank.return_value = [opportunity]
        mock_risk_cls.return_value.evaluate.return_value = approved_output
        mock_submit_auto_order.return_value = OrderResult(
            broker_order_id="AUTO-3",
            status="CANCELLED",
        )

        worker = AutoPaperTraderWorker(session=mock_session)
        result = worker.run()

    assert result.status == "ok"
    assert "0 positions opened" in result.message
    assert "1 cancelled" in result.message
    add_calls = mock_session.add.call_args_list
    assert len(add_calls) == 1
    paper_order = add_calls[0].args[0]
    assert paper_order.status == "canceled"
    assert paper_order.ibkr_status == "CANCELLED"
    assert signal.signal_status == SignalStatus.CANDIDATE


def test_auto_paper_skips_when_no_opportunities():
    """When ranker returns empty list, worker short-circuits cleanly."""
    mock_session = MagicMock()

    with patch("app.workers.auto_paper_trader_worker.OpportunityRankerService") as mock_ranker_cls:
        mock_ranker_cls.return_value.rank.return_value = []

        worker = AutoPaperTraderWorker(session=mock_session)
        result = worker.run()

    assert result.status == "ok"
    assert "skipped" in result.message
    mock_session.add.assert_not_called()


# ---------------------------------------------------------------------------
# QA-213 — Scheduler registration
# ---------------------------------------------------------------------------


def test_auto_paper_trader_registered_in_scheduler():
    """auto_paper_trader job must be registered in DataSyncScheduler."""
    scheduler = DataSyncScheduler()
    names = {j.name for j in scheduler.list_jobs()}
    assert "auto_paper_trader" in names


def test_auto_paper_trader_scheduler_returns_correct_worker():
    """get_worker('auto_paper_trader') must return AutoPaperTraderWorker."""
    scheduler = DataSyncScheduler()
    worker = scheduler.get_worker("auto_paper_trader")
    assert isinstance(worker, AutoPaperTraderWorker)


# ---------------------------------------------------------------------------
# QA-214 — Position cap (5 open max)
# ---------------------------------------------------------------------------


def test_auto_paper_respects_position_cap():
    """Worker must not open trade #6 when 5 auto-paper positions are already open."""
    mock_session = MagicMock()

    opportunities = [_make_opportunity(f"ASSET{i}") for i in range(3)]
    signals = {op.signal_id: _make_signal(op.signal_id) for op in opportunities}

    # Already at cap
    mock_session.execute.return_value.scalar_one.return_value = 5
    mock_session.get.side_effect = lambda model, id_: signals.get(id_)

    risk_profile = _make_risk_profile()
    mock_session.query.return_value.filter.return_value.first.return_value = risk_profile

    approved_output = RiskOutput(approved=True, decision="approved")

    with patch("app.workers.auto_paper_trader_worker.OpportunityRankerService") as mock_ranker_cls, \
         patch("app.workers.auto_paper_trader_worker.RiskService") as mock_risk_cls:

        mock_ranker_cls.return_value.rank.return_value = opportunities
        mock_risk_cls.return_value.evaluate.return_value = approved_output

        worker = AutoPaperTraderWorker(session=mock_session)
        result = worker.run()

    assert result.status == "ok"
    assert "0 positions opened" in result.message
    assert "skipped (cap)" in result.message
    # Risk gate never called because cap check fires first
    mock_risk_cls.return_value.evaluate.assert_not_called()
    mock_session.add.assert_not_called()


# ---------------------------------------------------------------------------
# IBKR working-status acceptance (PreSubmitted / PendingSubmit / ApiPending)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "broker_status",
    ["PreSubmitted", "PendingSubmit", "ApiPending"],
)
def test_auto_paper_treats_ibkr_working_status_as_accepted(broker_status):
    """IBKR working statuses must persist a PaperOrder and open a Position."""
    mock_session = MagicMock()

    opportunity = _make_opportunity("AAPL")
    signal = _make_signal(opportunity.signal_id)

    mock_session.execute.return_value.scalar_one.return_value = 0
    mock_session.get.return_value = signal

    risk_profile = _make_risk_profile()
    mock_session.query.return_value.filter.return_value.first.return_value = risk_profile

    approved_output = RiskOutput(approved=True, decision="approved")

    with patch("app.workers.auto_paper_trader_worker.OpportunityRankerService") as mock_ranker_cls, \
         patch("app.workers.auto_paper_trader_worker.RiskService") as mock_risk_cls, \
         patch("app.workers.auto_paper_trader_worker.BrokerService.submit_auto_order", new_callable=AsyncMock) as mock_submit_auto_order:

        mock_ranker_cls.return_value.rank.return_value = [opportunity]
        mock_risk_cls.return_value.evaluate.return_value = approved_output
        mock_submit_auto_order.return_value = OrderResult(
            broker_order_id="12", status=broker_status
        )

        worker = AutoPaperTraderWorker(session=mock_session)
        result = worker.run()

    assert result.status == "ok"
    assert "1 positions opened" in result.message
    assert "unsupported" not in result.message

    add_calls = mock_session.add.call_args_list
    assert len(add_calls) == 2  # PaperOrder + Position
    paper_order = add_calls[0].args[0]
    position = add_calls[1].args[0]
    assert paper_order.status == "accepted"
    # Preserve the raw broker status for the timeline / audit surface.
    assert paper_order.ibkr_status == broker_status
    assert position.broker_order_id == "12"
    assert signal.signal_status == SignalStatus.PAPER_SUBMITTED


@pytest.mark.parametrize(
    ("value", "expected_category", "expected_code", "message_fragment"),
    [
        (Exception(), "empty_exception", "empty_exception", "Exception"),
        (
            RuntimeError("Error 326: client id is already in use"),
            "tws_client_id_in_use",
            "error_326",
            "Error 326",
        ),
        (
            AutoTradingBlockedError("Auto trading is not enabled in MH-36B. Manual trading only."),
            "mode_guard_blocked",
            "mh36b_auto_trading_blocked",
            "MH-36B",
        ),
        (TimeoutError(), "broker_timeout", "broker_timeout", "TimeoutError"),
        (
            RuntimeError("TWS gateway unavailable"),
            "tws_unavailable",
            "tws_unavailable",
            "unavailable",
        ),
    ],
)
def test_classify_auto_paper_submit_error_maps_expected_categories(
    value,
    expected_category,
    expected_code,
    message_fragment,
):
    classified = classify_auto_paper_submit_error(value)
    assert classified["error_category"] == expected_category
    assert classified["error_code"] == expected_code
    assert classified["error_message"]
    assert message_fragment.lower() in classified["error_message"].lower()
    assert "traceback" not in classified["error_message"].lower()


def test_classify_auto_paper_submit_error_redacts_secret_like_tokens():
    classified = classify_auto_paper_submit_error(
        RuntimeError("token=abcd123 api_key=my-secret-key bearer abc.xyz")
    )
    assert "abcd123" not in classified["error_message"]
    assert "my-secret-key" not in classified["error_message"]
    assert "abc.xyz" not in classified["error_message"]
    assert "[redacted]" in classified["error_message"]


def test_auto_paper_submit_exception_includes_structured_non_empty_error_fields():
    mock_session = MagicMock()

    opportunity = _make_opportunity("EURUSD")
    signal = _make_signal(opportunity.signal_id)

    mock_session.execute.return_value.scalar_one.return_value = 0
    mock_session.get.return_value = signal

    risk_profile = _make_risk_profile()
    mock_session.query.return_value.filter.return_value.first.return_value = risk_profile

    approved_output = RiskOutput(approved=True, decision="approved")

    with patch("app.workers.auto_paper_trader_worker.OpportunityRankerService") as mock_ranker_cls, \
         patch("app.workers.auto_paper_trader_worker.RiskService") as mock_risk_cls, \
         patch(
             "app.workers.auto_paper_trader_worker.BrokerService.submit_auto_order",
             new_callable=AsyncMock,
             side_effect=TimeoutError(),
         ):
        mock_ranker_cls.return_value.rank.return_value = [opportunity]
        mock_risk_cls.return_value.evaluate.return_value = approved_output

        worker = AutoPaperTraderWorker(session=mock_session)
        result = worker.run()

    assert result.status == "ok"
    assert "submit-error" in result.message
    auto_diag_start = result.message.find("auto_diag=")
    assert auto_diag_start > -1
    auto_diag_json = result.message[auto_diag_start + len("auto_diag=") :]

    import json

    parsed = json.loads(auto_diag_json)
    outcomes = parsed.get("attempt_outcomes") or []
    assert len(outcomes) == 1
    outcome = outcomes[0]
    assert outcome["outcome"] == "submit_error"
    assert outcome["reason_category"] == "submit_exception"
    assert outcome["error_category"] == "broker_timeout"
    assert outcome["error_code"] == "broker_timeout"
    assert outcome["error_message"]
    assert outcome["exception_type"] == "TimeoutError"
    assert outcome["attempt_index"] == 1
    assert outcome["source"] == "auto_paper_trader"
