"""Focused tests for the env-backed MH-36B trading control service."""
from __future__ import annotations

import pytest

from app.config import get_settings
from app.services.trading_control_service import (
    AutoTradingBlockedError,
    LiveTradingNotArmedError,
    TradingControlMisconfiguredError,
    assert_auto_trading_allowed,
    assert_mode_configuration_consistent,
    assert_order_submission_allowed,
    get_trading_mode,
)


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_get_trading_mode_defaults_to_armed_paper_manual():
    state = get_trading_mode()
    assert state.trading_mode == "paper"
    assert state.execution_control == "manual"
    assert state.arming_state == "armed"
    assert state.paper_order_submission_allowed is True
    assert state.live_order_submission_allowed is False


def test_get_trading_mode_live_visible_but_disarmed(monkeypatch):
    monkeypatch.setenv("LIVE_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("BROKER_MODE", "live")
    monkeypatch.setenv("IBKR_ACCOUNT_TYPE", "live")
    get_settings.cache_clear()

    state = get_trading_mode()
    assert state.trading_mode == "live"
    assert state.execution_control == "manual"
    assert state.arming_state == "disarmed"
    assert state.live_order_submission_allowed is False
    assert state.reasons


def test_assert_order_submission_allowed_allows_manual_paper_submit():
    assert_order_submission_allowed(intent="manual")


def test_assert_order_submission_allowed_blocks_live_submit(monkeypatch):
    monkeypatch.setenv("LIVE_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("BROKER_MODE", "live")
    monkeypatch.setenv("IBKR_ACCOUNT_TYPE", "live")
    get_settings.cache_clear()

    with pytest.raises(LiveTradingNotArmedError):
        assert_order_submission_allowed(intent="manual")


def test_assert_order_submission_allowed_allows_live_dry_run(monkeypatch):
    monkeypatch.setenv("LIVE_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("BROKER_MODE", "live")
    monkeypatch.setenv("IBKR_ACCOUNT_TYPE", "live")
    get_settings.cache_clear()

    assert_order_submission_allowed(intent="manual", dry_run=True)


def test_assert_auto_trading_allowed_is_blocked():
    with pytest.raises(AutoTradingBlockedError):
        assert_auto_trading_allowed()


def test_assert_order_submission_allowed_blocks_auto_intent():
    with pytest.raises(AutoTradingBlockedError):
        assert_order_submission_allowed(intent="auto")


def test_assert_mode_configuration_consistent_rejects_partial_live(monkeypatch):
    monkeypatch.setenv("LIVE_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("BROKER_MODE", "paper")
    get_settings.cache_clear()

    with pytest.raises(TradingControlMisconfiguredError):
        assert_mode_configuration_consistent()
