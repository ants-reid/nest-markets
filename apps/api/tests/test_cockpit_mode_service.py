"""Tests for MH-COCKPIT-03 cockpit mode service."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.services.cockpit_mode_service import (
    get_cockpit_mode_state,
    reset_cockpit_mode_for_tests,
    set_cockpit_mode,
)
from app.services.trading_control_service import TradingControlState


def _paper_state() -> TradingControlState:
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


def setup_function() -> None:
    reset_cockpit_mode_for_tests()


def test_get_cockpit_mode_state_returns_selectable_and_locked_modes() -> None:
    payload = get_cockpit_mode_state(trading_control_state=_paper_state())

    assert payload.current_mode == "learning"
    assert payload.selectable_modes == ["learning", "manual", "auto_paper"]
    assert payload.locked_modes == ["assisted_live", "live", "auto_live"]
    assert payload.live_trading_enabled is False
    assert payload.auto_live_enabled is False
    assert payload.real_money_enabled is False

    by_id = {mode.id: mode for mode in payload.modes}
    assert by_id["manual"].selectable is True
    assert by_id["auto_paper"].selectable is True
    assert by_id["live"].locked is True
    assert by_id["auto_live"].selectable is False


def test_set_cockpit_mode_accepts_selectable_mode() -> None:
    payload = set_cockpit_mode("auto_paper", trading_control_state=_paper_state())

    assert payload.current_mode == "auto_paper"
    assert payload.global_safety_state.live_trading_enabled is False
    assert payload.global_safety_state.auto_trading_allowed is False


@pytest.mark.parametrize("requested_mode", ["assisted_live", "live", "auto_live"])
def test_set_cockpit_mode_rejects_locked_modes(requested_mode: str) -> None:
    with pytest.raises(HTTPException) as exc_info:
        set_cockpit_mode(requested_mode, trading_control_state=_paper_state())

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == "cockpit_mode_locked"
    assert exc_info.value.detail["requested_mode"] == requested_mode