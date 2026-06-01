"""Worker-level tests for Auto Paper v1 controlled-run gate integration."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.services.auto_paper_gate_service import AutoPaperGateDecision
from app.workers.auto_paper_trader_worker import AutoPaperTraderWorker


@pytest.fixture
def mock_session():
    return MagicMock()


def _settings_obj():
    return SimpleNamespace(
        auto_paper_enabled=True,
        auto_paper_max_orders_per_run=1,
        auto_paper_max_orders_per_day=1,
        auto_paper_max_notional_usd=100.0,
        auto_paper_symbol_allowlist="AAPL",
        auto_paper_order_type="LIMIT",
        auto_paper_limit_price=50.0,
        auto_paper_require_tws=True,
        auto_paper_max_open_positions=5,
        broker_provider="tws",
        broker_mode="paper",
        tws_enabled=True,
        live_execution_enabled=False,
    )


def test_worker_execute_returns_early_when_gate_blocks(mock_session):
    worker = AutoPaperTraderWorker(session=mock_session)

    with (
        patch(
            "app.workers.auto_paper_trader_worker.get_settings",
            return_value=_settings_obj(),
        ),
        patch(
            "app.workers.auto_paper_trader_worker.AutoPaperGateService"
        ) as mock_gate_cls,
    ):
        mock_gate = mock_gate_cls.return_value
        mock_gate.evaluate_run.return_value = AutoPaperGateDecision(
            allowed=False,
            blocking_gate="auto_paper_enabled",
            reason="AUTO_PAPER_ENABLED is false",
        )
        result = worker.execute()

    assert "controlled-run gate blocked" in result
    assert "auto_paper_enabled" in result


def test_worker_build_order_uses_settings_limit_price():
    worker = AutoPaperTraderWorker()
    signal = SimpleNamespace(entry_min=None, stop_price=None, asset_id=None)
    opportunity = SimpleNamespace(asset="AAPL", direction="long")

    with patch(
        "app.workers.auto_paper_trader_worker.get_settings",
        return_value=_settings_obj(),
    ):
        order = worker._build_broker_order_request(opportunity, signal)

    assert order.order_type == "LIMIT"
    assert float(order.limit_price) == pytest.approx(50.0)
    assert order.ticker == "AAPL"
