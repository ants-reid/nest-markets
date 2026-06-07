"""Tests for auto-paper audit reconciliation persistence behavior."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.db.models.broker_submit_decision import BrokerSubmitDecision
from app.db.models.paper_order import PaperOrder
from app.db.session import SessionLocal
from app.services.auto_paper_audit_reconciliation_service import (
    AutoPaperAuditReconciliationService,
)
from app.services.cockpit_auto_paper_status_service import get_auto_paper_status_card
from app.services.trading_control_service import TradingControlState
from app.services.worker_run_log_service import WorkerRunLogService


@pytest.fixture
def cleanup_rows():
    created_order_ids: list[uuid.UUID] = []
    created_decision_ids: list[uuid.UUID] = []
    yield created_order_ids, created_decision_ids
    with SessionLocal() as session:
        if created_decision_ids:
            session.query(BrokerSubmitDecision).filter(
                BrokerSubmitDecision.id.in_(created_decision_ids)
            ).delete(synchronize_session=False)
        if created_order_ids:
            session.query(PaperOrder).filter(
                PaperOrder.id.in_(created_order_ids)
            ).delete(synchronize_session=False)
        session.commit()


@pytest.fixture
def isolated_run_log(tmp_path: Path) -> WorkerRunLogService:
    return WorkerRunLogService(log_path=tmp_path / "worker_run_log.jsonl")


def _paper_armed_state() -> TradingControlState:
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


def _insert_auto_paper_order(*, broker_order_id: int, status: str = "accepted") -> uuid.UUID:
    with SessionLocal() as session:
        order = PaperOrder(
            signal_id=None,
            order_type="auto_paper",
            side="long",
            qty=1,
            quantity=1,
            status=status,
            submitted_at=datetime.now(timezone.utc),
            broker_order_id=broker_order_id,
            ibkr_status="PendingSubmit",
        )
        session.add(order)
        session.commit()
        session.refresh(order)
        return order.id


def _insert_non_auto_order(*, broker_order_id: int) -> uuid.UUID:
    with SessionLocal() as session:
        order = PaperOrder(
            signal_id=None,
            order_type="manual",
            side="long",
            qty=1,
            quantity=1,
            status="accepted",
            submitted_at=datetime.now(timezone.utc),
            broker_order_id=broker_order_id,
        )
        session.add(order)
        session.commit()
        session.refresh(order)
        return order.id


def _collect_decision_ids_for_broker_order(
    *,
    broker_order_id: int,
    created_decisions: list[uuid.UUID],
) -> None:
    with SessionLocal() as session:
        rows = session.query(BrokerSubmitDecision).all()
        for row in rows:
            payload = row.preflight_json if isinstance(row.preflight_json, dict) else {}
            if str(payload.get("broker_order_id")) == str(broker_order_id):
                created_decisions.append(row.id)


def test_reconciliation_creates_missing_run_log_and_submit_decision(cleanup_rows, isolated_run_log):
    created_orders, created_decisions = cleanup_rows
    order_id = _insert_auto_paper_order(broker_order_id=27001)
    created_orders.append(order_id)

    with SessionLocal() as session:
        order = session.get(PaperOrder, order_id)
        assert order is not None
        original_status = order.status

        service = AutoPaperAuditReconciliationService(run_log_service=isolated_run_log)
        result = service.reconcile_for_paper_order(session=session, paper_order=order)
        session.commit()

        assert result.run_log_reconciled is True
        assert result.submit_decision_reconciled is True
        assert result.warnings == []

        reloaded = session.get(PaperOrder, order_id)
        assert reloaded is not None
        assert reloaded.status == original_status

        rows = session.query(BrokerSubmitDecision).filter(
            BrokerSubmitDecision.intent == "auto"
        ).all()
        assert len(rows) >= 1
        matching = [
            row
            for row in rows
            if isinstance(row.preflight_json, dict)
            and str(row.preflight_json.get("broker_order_id")) == "27001"
        ]
        assert len(matching) == 1
        created_decisions.extend([matching[0].id])
        assert matching[0].would_block is False

    entries = isolated_run_log.recent(limit=20)
    assert len(entries) == 1
    assert "audit reconciliation" in entries[0].message
    assert "broker_order_id=27001" in entries[0].message


def test_reconciliation_is_idempotent(cleanup_rows, isolated_run_log):
    created_orders, created_decisions = cleanup_rows
    order_id = _insert_auto_paper_order(broker_order_id=27002)
    created_orders.append(order_id)

    with SessionLocal() as session:
        order = session.get(PaperOrder, order_id)
        assert order is not None
        service = AutoPaperAuditReconciliationService(run_log_service=isolated_run_log)

        first = service.reconcile_for_paper_order(session=session, paper_order=order)
        session.commit()
        second = service.reconcile_for_paper_order(session=session, paper_order=order)
        session.commit()

        assert first.run_log_reconciled is True
        assert first.submit_decision_reconciled is True
        assert second.run_log_reconciled is False
        assert second.submit_decision_reconciled is False

        rows = session.query(BrokerSubmitDecision).filter(
            BrokerSubmitDecision.intent == "auto"
        ).all()
        matching = [
            row
            for row in rows
            if isinstance(row.preflight_json, dict)
            and str(row.preflight_json.get("broker_order_id")) == "27002"
        ]
        assert len(matching) == 1
        created_decisions.extend([matching[0].id])

    entries = [e for e in isolated_run_log.recent(limit=20) if "broker_order_id=27002" in e.message]
    assert len(entries) == 1


def test_reconciliation_skips_non_auto_or_non_accepted_orders(cleanup_rows, isolated_run_log):
    created_orders, created_decisions = cleanup_rows
    manual_order_id = _insert_non_auto_order(broker_order_id=27003)
    rejected_order_id = _insert_auto_paper_order(broker_order_id=27004, status="rejected")
    created_orders.extend([manual_order_id, rejected_order_id])

    with SessionLocal() as session:
        manual_order = session.get(PaperOrder, manual_order_id)
        rejected_order = session.get(PaperOrder, rejected_order_id)
        assert manual_order is not None
        assert rejected_order is not None

        service = AutoPaperAuditReconciliationService(run_log_service=isolated_run_log)
        manual_result = service.reconcile_for_paper_order(session=session, paper_order=manual_order)
        rejected_result = service.reconcile_for_paper_order(session=session, paper_order=rejected_order)
        session.commit()

        assert manual_result.run_log_reconciled is False
        assert manual_result.submit_decision_reconciled is False
        assert rejected_result.run_log_reconciled is False
        assert rejected_result.submit_decision_reconciled is False

        rows = session.query(BrokerSubmitDecision).filter(
            BrokerSubmitDecision.intent == "auto"
        ).all()
        matching = [
            row
            for row in rows
            if isinstance(row.preflight_json, dict)
            and str(row.preflight_json.get("broker_order_id")) in {"27003", "27004"}
        ]
        assert matching == []

    assert isolated_run_log.recent(limit=20) == []


def test_reconciliation_surfaces_run_log_write_warning(monkeypatch, cleanup_rows, isolated_run_log):
    created_orders, created_decisions = cleanup_rows
    order_id = _insert_auto_paper_order(broker_order_id=27005)
    created_orders.append(order_id)

    service = AutoPaperAuditReconciliationService(run_log_service=isolated_run_log)

    def _boom(_entry):
        raise RuntimeError("run log unavailable")

    monkeypatch.setattr(isolated_run_log, "append", _boom)

    with SessionLocal() as session:
        order = session.get(PaperOrder, order_id)
        assert order is not None
        result = service.reconcile_for_paper_order(session=session, paper_order=order)
        session.commit()

        assert any("run_log_reconciliation_failed" in warning for warning in result.warnings)

    _collect_decision_ids_for_broker_order(
        broker_order_id=27005,
        created_decisions=created_decisions,
    )


def test_cockpit_alignment_warning_before_and_ok_after(cleanup_rows, isolated_run_log):
    created_orders, created_decisions = cleanup_rows
    order_id = _insert_auto_paper_order(broker_order_id=27006)
    created_orders.append(order_id)

    with SessionLocal() as session:
        order = session.get(PaperOrder, order_id)
        assert order is not None

        before = get_auto_paper_status_card(
            trading_control_state=_paper_armed_state(),
            run_log_service=isolated_run_log,
            session=session,
        )
        assert before["audit_alignment"]["status"] == "warning"

        service = AutoPaperAuditReconciliationService(run_log_service=isolated_run_log)
        _ = service.reconcile_for_paper_order(session=session, paper_order=order)
        session.commit()

        rows = session.query(BrokerSubmitDecision).filter(
            BrokerSubmitDecision.intent == "auto"
        ).all()
        for row in rows:
            payload = row.preflight_json if isinstance(row.preflight_json, dict) else {}
            if str(payload.get("broker_order_id")) == "27006":
                created_decisions.append(row.id)

        after = get_auto_paper_status_card(
            trading_control_state=_paper_armed_state(),
            run_log_service=isolated_run_log,
            session=session,
        )
        assert after["audit_alignment"]["status"] == "ok"
