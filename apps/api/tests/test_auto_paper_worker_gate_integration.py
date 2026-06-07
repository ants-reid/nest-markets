"""Worker-level tests for Auto Paper v1 controlled-run gate integration."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.clients.broker.broker_interface import OrderResult
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
        auto_paper_kill_on_error_count=3,
        auto_paper_kill_on_reject_rate=0.5,
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

    def test_worker_reuses_route_broker_service_singleton():
        worker = AutoPaperTraderWorker()
        shared = MagicMock()

        with patch("app.api.routes.broker.get_broker_service", return_value=shared) as getter:
            first = worker._get_broker_service()
            second = worker._get_broker_service()

        assert first is shared
        assert second is shared
        assert getter.call_count == 2


def test_worker_watchdog_blocks_after_reject_rate_threshold(mock_session):
    worker = AutoPaperTraderWorker(session=mock_session)

    opportunities = [
        SimpleNamespace(signal_id="sig-1", asset="AAPL", direction="long", asset_class=SimpleNamespace(value="equity")),
        SimpleNamespace(signal_id="sig-2", asset="AAPL", direction="long", asset_class=SimpleNamespace(value="equity")),
    ]

    signal = SimpleNamespace(
        asset_id="asset-1",
        entry_min=50.0,
        stop_price=49.0,
        target_price=55.0,
        confidence=0.9,
        signal_score=0.8,
        signal_status=None,
    )

    broker = MagicMock()
    broker.submit_auto_order = AsyncMock(return_value=OrderResult(
        broker_order_id="rej-1",
        status="REJECTED",
        error_message="simulated reject",
    ))

    with (
        patch(
            "app.workers.auto_paper_trader_worker.get_settings",
            return_value=_settings_obj(),
        ),
        patch("app.workers.auto_paper_trader_worker.AutoPaperGateService") as mock_gate_cls,
        patch("app.workers.auto_paper_trader_worker.OpportunityRankerService") as mock_ranker_cls,
        patch("app.workers.auto_paper_trader_worker.RiskService") as mock_risk_cls,
        patch.object(AutoPaperTraderWorker, "_load_risk_profile", return_value=SimpleNamespace(kill_switch_enabled=False)),
        patch.object(AutoPaperTraderWorker, "_count_open_auto_paper_positions", return_value=0),
        patch.object(AutoPaperTraderWorker, "_get_broker_service", return_value=broker),
    ):
        mock_gate = mock_gate_cls.return_value
        mock_gate.evaluate_run.return_value = AutoPaperGateDecision(
            allowed=True,
            blocking_gate=None,
            reason=None,
        )
        mock_gate.evaluate_order.return_value = AutoPaperGateDecision(
            allowed=True,
            blocking_gate=None,
            reason=None,
        )

        mock_ranker_cls.return_value.rank.return_value = opportunities

        risk_service = mock_risk_cls.return_value
        risk_service.evaluate.return_value = SimpleNamespace(approved=True, blocking_rule=None)

        mock_session.get.return_value = signal

        result = worker.execute()

    assert "watchdog blocked further submits" in result
    assert broker.submit_auto_order.call_count == 1
