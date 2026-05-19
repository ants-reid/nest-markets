from app.services.live_execution_service import LiveExecutionRequest, LiveExecutionService


def test_live_execution_returns_disabled_result() -> None:
    service = LiveExecutionService()
    request = LiveExecutionRequest(
        asset="EURUSD",
        side="buy",
        qty=1000.0,
        notional=1081.0,
        stop_price=1.078,
        target_price=1.088,
    )

    result = service.submit(request)

    assert result.accepted is False
    assert result.status == "disabled"
    assert result.reason == "live_execution_disabled_in_mvp"
