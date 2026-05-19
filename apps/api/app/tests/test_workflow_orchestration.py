from __future__ import annotations

from dataclasses import dataclass

from app.services.approval_service import ApprovalRequest, ApprovalService
from app.services.execution_mode_service import ExecutionModeService
from app.services.live_execution_service import LiveExecutionRequest, LiveExecutionResult, LiveExecutionService
from app.services.paper_execution_service import PaperExecutionResult, PaperExecutionService
from app.services.risk_profile_service import RiskProfile
from app.services.risk_service import RiskContext, RiskDecision, RiskService
from app.services.signal_service import SignalOutput


@dataclass(frozen=True)
class WorkflowServices:
    """Bundle of existing MVP services used by orchestration tests."""

    risk: RiskService
    paper: PaperExecutionService
    approval: ApprovalService
    live: LiveExecutionService


def _signal() -> SignalOutput:
    return SignalOutput(
        asset="EURUSD",
        timeframe="1h",
        direction="long",
        regime="trend",
        setup_type="trend_pullback",
        entry_zone=(1.0810, 1.0820),
        stop_price=1.0780,
        target_price=1.0880,
        confidence=0.75,
        horizon_label="1_3_days",
        catalyst_type="macro",
        catalyst_score=0.60,
        catalyst_summary="Macro backdrop remains supportive.",
        thesis="Price structure supports continuation from pullback.",
        invalidators=["1h close below 1.0780"],
        signal_score=76.0,
        should_trade=True,
    )


def _risk_context(requested_execution_mode: str) -> RiskContext:
    return RiskContext(
        spread_bps=10.0,
        daily_drawdown_pct=1.0,
        consecutive_losses=1,
        minutes_since_last_loss=240,
        correlated_exposure_count=1,
        market_quality_flag=True,
        account_equity=50000.0,
        requested_execution_mode=requested_execution_mode,
    )


def _services() -> WorkflowServices:
    execution_mode_service = ExecutionModeService()
    risk_service = RiskService(
        profile=RiskProfile(),
        execution_mode_service=execution_mode_service,
    )
    return WorkflowServices(
        risk=risk_service,
        paper=PaperExecutionService(),
        approval=ApprovalService(),
        live=LiveExecutionService(),
    )


def _build_live_request(
    signal: SignalOutput,
    allowed_risk_amount: float,
    latest_price: float,
) -> LiveExecutionRequest:
    """Build a future live request deterministically for scaffold-only testing."""
    low, high = sorted(signal.entry_zone)
    if low <= latest_price <= high:
        entry_price = latest_price
    elif latest_price < low:
        entry_price = low
    else:
        entry_price = high

    stop_distance = entry_price - signal.stop_price
    qty = 0.0 if stop_distance <= 0.0 else allowed_risk_amount / stop_distance

    return LiveExecutionRequest(
        asset=signal.asset,
        side="buy" if signal.direction == "long" else "sell",
        qty=qty,
        notional=qty * entry_price,
        stop_price=signal.stop_price,
        target_price=signal.target_price,
    )


def test_approved_paper_mode_routes_to_paper_execution() -> None:
    services = _services()
    signal = _signal()
    decision = services.risk.evaluate(signal, _risk_context("paper"))

    assert decision.approved is True
    assert decision.selected_execution_mode == "paper"

    result = services.paper.submit_order(
        signal=signal,
        allowed_risk_amount=decision.allowed_risk_amount,
        latest_price=1.0815,
    )

    assert result.status in {"submitted", "blocked"}
    assert result.asset == signal.asset


def test_approved_confirm_live_mode_creates_pending_approval_request() -> None:
    services = _services()
    signal = _signal()
    decision = services.risk.evaluate(signal, _risk_context("confirm_live"))

    assert decision.approved is True
    assert decision.selected_execution_mode == "confirm_live"

    request = services.approval.create_request(
        signal=signal,
        execution_mode="confirm_live",
        risk_approved=decision.approved,
    )

    assert isinstance(request, ApprovalRequest)
    assert request.status == "pending"
    assert request.asset == signal.asset


def test_approved_auto_live_mode_returns_disabled_live_execution_result() -> None:
    services = _services()
    signal = _signal()
    decision = services.risk.evaluate(signal, _risk_context("auto_live"))

    assert decision.approved is True
    assert decision.selected_execution_mode == "auto_live"

    live_request = _build_live_request(
        signal=signal,
        allowed_risk_amount=decision.allowed_risk_amount,
        latest_price=1.0815,
    )
    result = services.live.submit(live_request)

    assert isinstance(result, LiveExecutionResult)
    assert result.accepted is False
    assert result.status == "disabled"
    assert result.reason == "live_execution_disabled_in_mvp"


def test_blocked_risk_decision_stops_execution_paths() -> None:
    services = _services()
    signal = _signal()
    blocked_context = RiskContext(
        spread_bps=10.0,
        daily_drawdown_pct=1.0,
        consecutive_losses=1,
        minutes_since_last_loss=240,
        correlated_exposure_count=1,
        market_quality_flag=True,
        account_equity=50000.0,
        requested_execution_mode="paper",
    )
    blocked_signal = SignalOutput(**{**signal.__dict__, "confidence": 0.20})

    decision = services.risk.evaluate(blocked_signal, blocked_context)

    assert isinstance(decision, RiskDecision)
    assert decision.approved is False
    assert decision.selected_execution_mode == "blocked"
    assert decision.allowed_risk_amount == 0.0


def test_end_to_end_happy_path_signal_to_paper_close() -> None:
    services = _services()
    signal = _signal()
    decision = services.risk.evaluate(signal, _risk_context("paper"))

    assert decision.approved is True

    submitted = services.paper.submit_order(
        signal=signal,
        allowed_risk_amount=decision.allowed_risk_amount,
        latest_price=1.0815,
    )
    filled = services.paper.fill_order(submitted)
    closed = services.paper.close_order(filled, close_price=1.0870)

    assert isinstance(submitted, PaperExecutionResult)
    assert submitted.status == "submitted"
    assert filled.status == "filled"
    assert closed.status == "closed"
    assert closed.fill_price == 1.0870
