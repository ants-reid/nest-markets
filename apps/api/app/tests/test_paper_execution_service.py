import pytest

from app.services.paper_execution_service import PaperExecutionService
from app.services.signal_service import SignalOutput


def _signal() -> SignalOutput:
    return SignalOutput(
        asset="EURUSD",
        timeframe="1h",
        direction="long",
        regime="trend",
        setup_type="trend_pullback",
        entry_zone=(1.081, 1.082),
        stop_price=1.078,
        target_price=1.088,
        confidence=0.74,
        horizon_label="1_3_days",
        catalyst_type="macro",
        catalyst_score=0.6,
        catalyst_summary="Macro context supportive",
        thesis="Trend continuation",
        invalidators=["Break below 1.078"],
        signal_score=75.0,
        should_trade=True,
    )


def test_paper_execution_happy_path() -> None:
    service = PaperExecutionService()
    signal = _signal()

    submitted = service.submit_order(signal=signal, allowed_risk_amount=100.0, latest_price=1.0815)
    filled = service.fill_order(submitted)
    closed = service.close_order(filled, close_price=1.0870)

    assert submitted.status == "submitted"
    assert submitted.qty > 0
    assert submitted.notional > 0
    assert submitted.side == "buy"
    assert filled.status == "filled"
    assert closed.status == "closed"


def test_paper_execution_blocked_on_invalid_stop_distance() -> None:
    service = PaperExecutionService()
    signal = _signal()
    signal = SignalOutput(**{**signal.__dict__, "stop_price": 1.0825})

    result = service.submit_order(signal=signal, allowed_risk_amount=100.0, latest_price=1.0815)

    assert result.status == "blocked"
    assert result.reason == "invalid_stop_distance"
    assert result.qty == 0.0


def test_fill_order_raises_when_status_is_not_submitted() -> None:
    service = PaperExecutionService()
    signal = _signal()

    submitted = service.submit_order(signal=signal, allowed_risk_amount=100.0, latest_price=1.0815)
    filled = service.fill_order(submitted)

    with pytest.raises(ValueError):
        service.fill_order(filled)


def test_close_order_raises_when_status_is_not_filled() -> None:
    service = PaperExecutionService()
    signal = _signal()

    submitted = service.submit_order(signal=signal, allowed_risk_amount=100.0, latest_price=1.0815)

    with pytest.raises(ValueError):
        service.close_order(submitted, close_price=1.0870)
