from app.services.execution_mode_service import ExecutionModeService


def test_execution_mode_routes_when_approved() -> None:
    service = ExecutionModeService()

    decision = service.route(approved=True, requested_mode="confirm_live")

    assert decision.proceed_to_execution is True
    assert decision.selected_execution_mode == "confirm_live"


def test_execution_mode_blocks_when_not_approved() -> None:
    service = ExecutionModeService()

    decision = service.route(approved=False, requested_mode="auto_live")

    assert decision.proceed_to_execution is False
    assert decision.selected_execution_mode == "blocked"
