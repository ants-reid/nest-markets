"""Focused gating tests for advanced order submissions in MH-36B."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.config import get_settings
from app.services.advanced_order_service import AdvancedOrderService, BracketOrderConfig
from app.services.trading_control_service import LiveTradingNotArmedError


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_submit_bracket_order_blocks_in_live_mode(monkeypatch):
    monkeypatch.setenv("LIVE_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("BROKER_MODE", "live")
    monkeypatch.setenv("IBKR_ACCOUNT_TYPE", "live")
    get_settings.cache_clear()

    adapter = AsyncMock()
    service = AdvancedOrderService(adapter)

    config = BracketOrderConfig(
        conid=265598,
        side="BUY",
        quantity=1,
        entry_price=100.0,
        take_profit_price=105.0,
        stop_loss_price=95.0,
    )

    with pytest.raises(LiveTradingNotArmedError):
        await service.submit_bracket_order(config)