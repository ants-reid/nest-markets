"""MH-162 post-lock simulation regression suite.

This suite is additive and test-only. It verifies that simulator paper,
broker-paper, and live-locked execution surfaces remain separated and that
post-lock submit safety remains fail-closed and auditable.
"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.clients.broker.broker_interface import OrderRequest, OrderResult
from app.config import get_settings
from app.db.models.broker_submit_decision import BrokerSubmitDecision
from app.db.session import SessionLocal
from app.services.broker_preflight_decision_service import BrokerPreflightDecisionService
from app.services.broker_service import BrokerService
from app.services.paper_source_contract import (
    CANONICAL_PAPER_ROUTE,
    SERIOUS_PAPER_SOURCE,
    SOURCE_BROKER_DRY_RUN,
    SOURCE_IBKR_PAPER,
    SOURCE_INTERNAL_MOCK_SIMULATOR,
    broker_dry_run_sources,
    broker_sources_from_mode,
    live_locked_execution_sources,
    simulator_execution_sources,
)
from app.services.trading_control_service import LiveTradingNotArmedError
from app.workers.async_bridge import run_async
from app.workers.auto_paper_trader_worker import AutoPaperTraderWorker


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _clear_submit_decisions():
    with SessionLocal() as session:
        session.query(BrokerSubmitDecision).delete(synchronize_session=False)
        session.commit()
    yield
    with SessionLocal() as session:
        session.query(BrokerSubmitDecision).delete(synchronize_session=False)
        session.commit()


def test_simulator_sources_are_isolated_from_broker_paper_path():
    simulator = simulator_execution_sources()

    assert simulator["execution_source"] == SOURCE_INTERNAL_MOCK_SIMULATOR
    assert simulator["balance_source"] == "app_simulated"
    assert simulator["positions_source"] == "app_db_simulated"
    assert simulator["serious_paper_source"] == SOURCE_IBKR_PAPER
    assert simulator["is_canonical_paper"] is False
    assert simulator["canonical_paper_route"] == CANONICAL_PAPER_ROUTE
    assert simulator["broker_account_mode"] == "simulator"
    assert simulator["live_state"] == "ibkr_live_locked"
    assert "not the canonical IBKR paper" in simulator["simulator_warning"]


def test_broker_paper_sources_remain_canonical_path():
    broker_paper = broker_sources_from_mode({"mode": "paper"})

    assert broker_paper["execution_source"] == SOURCE_IBKR_PAPER
    assert broker_paper["balance_source"] == SOURCE_IBKR_PAPER
    assert broker_paper["fills_source"] == SOURCE_IBKR_PAPER
    assert broker_paper["positions_source"] == SOURCE_IBKR_PAPER
    assert broker_paper["is_canonical_paper"] is True
    assert broker_paper["canonical_paper_route"] == CANONICAL_PAPER_ROUTE
    assert broker_paper["broker_account_mode"] == "paper"
    assert broker_paper["live_state"] == "ibkr_live_locked"


def test_broker_dry_run_sources_mark_canonical_paper_without_simulator_drift():
    broker_dry_run = broker_dry_run_sources({"mode": "paper"})

    assert broker_dry_run["execution_source"] == SOURCE_BROKER_DRY_RUN
    assert broker_dry_run["balance_source"] == SOURCE_IBKR_PAPER
    assert broker_dry_run["fills_source"] == "pending_broker_fill"
    assert broker_dry_run["fees_source"] == "pending_broker_report"
    assert broker_dry_run["is_canonical_paper"] is True
    assert broker_dry_run["canonical_paper_route"] == CANONICAL_PAPER_ROUTE
    assert broker_dry_run["broker_account_mode"] == "paper"


def test_submit_decision_persistence_keeps_source_and_sanitizes_warning_payload():
    decision_service = BrokerPreflightDecisionService()
    long_secretish_message = "x" * 400
    warnings = [
        {
            "code": "max_order_notional_exceeded",
            "message": long_secretish_message,
            "severity": "warning",
            "source": "risk_limits",
            "enforcement_enabled": False,
            "api_key": "SHOULD_NOT_PERSIST",
            "token": "SHOULD_NOT_PERSIST",
        }
    ]
    preflight_decision = decision_service.build_preflight_decision(issues=[], warnings=warnings)

    decision_service.persist_submit_decision(
        intent="manual",
        preflight_decision=preflight_decision,
        warnings=warnings,
        source="submit_preflight",
        submit_gate="blocked",
    )

    with SessionLocal() as session:
        row = session.query(BrokerSubmitDecision).one()
        payload = row.preflight_json
        persisted_warning = payload["warnings"][0]

    assert payload["source"] == "submit_preflight"
    assert payload["execution_mode"] == "ibkr_paper"
    assert payload["account_mode"] == "paper"
    assert payload["execution_source"] == "ibkr_paper"
    assert payload["canonical_paper_route"] == CANONICAL_PAPER_ROUTE
    assert payload["broker_account_mode"] == "paper"
    assert persisted_warning["code"] == "max_order_notional_exceeded"
    assert len(persisted_warning["message"]) == 240
    assert "api_key" not in persisted_warning
    assert "token" not in persisted_warning


@pytest.mark.parametrize(
    ("decision", "expected"),
    [
        ({"decision_status": "allowed", "blocking_count": 0, "would_block_count": 0}, False),
        ({"decision_status": "advisory", "blocking_count": 0, "would_block_count": 0}, False),
        ({"decision_status": "would_block", "blocking_count": 0, "would_block_count": 1}, True),
        ({"decision_status": "blocked", "blocking_count": 1, "would_block_count": 0}, True),
        ({"decision_status": "unknown", "blocking_count": 0, "would_block_count": 0}, True),
        ({"decision_status": "error", "blocking_count": 0, "would_block_count": 0}, True),
    ],
)
def test_preflight_blocking_is_fail_closed(decision, expected):
    decision_service = BrokerPreflightDecisionService()
    assert decision_service.is_submit_blocked_by_preflight(decision) is expected


@pytest.mark.asyncio
async def test_live_mode_submit_stays_blocked_and_writes_auditable_decision(monkeypatch):
    monkeypatch.setenv("LIVE_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("BROKER_MODE", "live")
    monkeypatch.setenv("IBKR_ACCOUNT_TYPE", "live")
    get_settings.cache_clear()

    mock_broker = AsyncMock()
    service = BrokerService(broker=mock_broker)

    request = OrderRequest(
        ticker="AAPL",
        side="BUY",
        quantity=Decimal("1"),
        order_type="MARKET",
    )

    with pytest.raises(LiveTradingNotArmedError):
        await service.submit_order(request)

    mock_broker.submit_order.assert_not_called()

    with SessionLocal() as session:
        row = session.query(BrokerSubmitDecision).one()
        payload = row.preflight_json

    assert row.would_block is True
    assert row.blocked_reason_code == "mode_guard_blocked"
    assert payload["submit_gate"] == "blocked"
    assert payload["source"] == "submit_attempt"
    assert payload["execution_mode"] == "ibkr_live_locked"
    assert payload["account_mode"] == "live"


@pytest.mark.asyncio
async def test_async_bridge_runs_inside_an_existing_event_loop():
    async def _payload() -> str:
        return "ok"

    value = run_async(lambda: _payload())
    assert value == "ok"


def test_auto_paper_worker_submission_path_uses_auto_submit_gate_only():
    worker = AutoPaperTraderWorker(session=MagicMock())
    opportunity = SimpleNamespace(asset="AAPL", direction="long")
    signal = SimpleNamespace(entry_min=101.5)
    fake_service = SimpleNamespace(
        submit_auto_order=AsyncMock(
            return_value=OrderResult(broker_order_id="AUTO-1", status="SUBMITTED")
        ),
        submit_order=AsyncMock(),
    )

    with patch.object(worker, "_get_broker_service", return_value=fake_service):
        result = worker._submit_via_broker_gate(opportunity, signal)

    assert result.status == "SUBMITTED"
    fake_service.submit_auto_order.assert_awaited_once()
    fake_service.submit_order.assert_not_called()


def test_canonical_paper_contract_is_consistent_across_source_helpers():
    simulator = simulator_execution_sources()
    broker_paper = broker_sources_from_mode({"mode": "paper"})
    live_locked = live_locked_execution_sources()

    assert SERIOUS_PAPER_SOURCE == SOURCE_IBKR_PAPER
    assert simulator["serious_paper_source"] == SERIOUS_PAPER_SOURCE
    assert broker_paper["serious_paper_source"] == SERIOUS_PAPER_SOURCE
    assert live_locked["serious_paper_source"] == SERIOUS_PAPER_SOURCE

    assert broker_paper["is_canonical_paper"] is True
    assert simulator["is_canonical_paper"] is False
    assert live_locked["is_canonical_paper"] is False

    assert simulator["execution_source"] != broker_paper["execution_source"]
    assert live_locked["execution_source"] != broker_paper["execution_source"]
