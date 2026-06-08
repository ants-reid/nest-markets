"""Auto-paper audit reconciliation helpers.

This module backfills missing audit artifacts for persisted auto-paper orders
without modifying execution behavior, trading gates, or order state.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models.broker_submit_decision import BrokerSubmitDecision
from app.db.models.paper_order import PaperOrder
from app.services.broker_submit_decision_service import (
    BrokerSubmitDecisionRecord,
    BrokerSubmitDecisionService,
)
from app.services.worker_run_log_service import WorkerRunEntry, WorkerRunLogService

_logger = logging.getLogger(__name__)

_RECONCILED_REASON = "audit_reconciled_missing_submit_decision"
_RECONCILED_SOURCE = "audit_reconciliation"
_MAX_RECENT_DECISIONS = 300
_RECONCILED_GATE = "reconciled_allowed"
_RECONCILE_TAG = "audit_reconcile"
_RUN_LOG_MESSAGE = (
    "audit reconciliation: paper order accepted without matching worker run log"
)


@dataclass
class AutoPaperAuditReconciliationResult:
    run_log_reconciled: bool = False
    submit_decision_reconciled: bool = False
    warnings: list[str] = field(default_factory=list)


class AutoPaperAuditReconciliationService:
    """Backfill missing audit evidence for accepted auto-paper orders."""

    def __init__(self, run_log_service: WorkerRunLogService | None = None) -> None:
        self._run_log_service = run_log_service or WorkerRunLogService()

    def reconcile_for_paper_order(
        self,
        *,
        session: Session,
        paper_order: PaperOrder,
    ) -> AutoPaperAuditReconciliationResult:
        result = AutoPaperAuditReconciliationResult()

        if not self._eligible_for_reconciliation(paper_order):
            return result

        broker_order_id = self._coerce_broker_order_id(paper_order.broker_order_id)
        if broker_order_id is None:
            return result

        run_log_tag = self._run_log_tag(broker_order_id)

        try:
            if not self._has_run_log_evidence(run_log_tag):
                self._append_run_log_reconciliation_entry(paper_order, run_log_tag)
                result.run_log_reconciled = True
        except Exception as exc:  # noqa: BLE001
            msg = f"run_log_reconciliation_failed:{exc}"
            result.warnings.append(msg)
            _logger.warning("Auto-paper audit reconciliation run-log failed: %s", exc)

        try:
            if not self._has_submit_decision_evidence(
                session=session,
                broker_order_id=broker_order_id,
                signal_id=paper_order.signal_id,
            ):
                self._persist_reconciled_submit_decision(
                    session=session,
                    paper_order=paper_order,
                    broker_order_id=broker_order_id,
                )
                result.submit_decision_reconciled = True
        except Exception as exc:  # noqa: BLE001
            msg = f"submit_decision_reconciliation_failed:{exc}"
            result.warnings.append(msg)
            _logger.warning("Auto-paper audit reconciliation decision write failed: %s", exc)

        return result

    def _eligible_for_reconciliation(self, paper_order: PaperOrder) -> bool:
        if self._normalize_text(paper_order.order_type) != "auto_paper":
            return False
        normalized_status = self._normalize_text(paper_order.status)
        return normalized_status in {"accepted", "filled"}

    def _normalize_text(self, value: Any) -> str:
        if value is None:
            return ""
        if hasattr(value, "value"):
            value = value.value
        return str(value).strip().lower()

    def _coerce_broker_order_id(self, broker_order_id: Any) -> str | None:
        if broker_order_id is None:
            return None
        value = str(broker_order_id).strip()
        return value or None

    def _run_log_tag(self, broker_order_id: str) -> str:
        return f"{_RECONCILE_TAG}:broker_order_id={broker_order_id}"

    def _has_run_log_evidence(self, run_log_tag: str) -> bool:
        for entry in self._run_log_service.recent(limit=200):
            if run_log_tag in str(entry.message):
                return True
        return False

    def _append_run_log_reconciliation_entry(self, paper_order: PaperOrder, run_log_tag: str) -> None:
        submitted_at = self._serialize_timestamp(paper_order)
        message = (
            f"{_RUN_LOG_MESSAGE}; {run_log_tag}; "
            f"signal_id={paper_order.signal_id}; ibkr_status={paper_order.ibkr_status}; "
            f"status={paper_order.status}; submitted_at={submitted_at}"
        )
        now = datetime.now(UTC).isoformat()
        self._run_log_service.append(
            WorkerRunEntry(
                worker_name="auto_paper_audit_reconciliation",
                status="ok",
                message=message,
                started_at=now,
                finished_at=now,
                source="manual",
                outcome_counts={
                    "accepted_count": 1,
                    "rejected_count": 0,
                    "cancelled_count": 0,
                    "blocked_count": 0,
                    "risk_blocked_count": 0,
                    "gate_blocked_count": 0,
                    "skipped_cap_count": 0,
                    "legacy_broker_rejected_count": 0,
                },
            )
        )

    def _has_submit_decision_evidence(
        self,
        *,
        session: Session,
        broker_order_id: str,
        signal_id,
    ) -> bool:
        rows = session.execute(
            select(BrokerSubmitDecision)
            .where(BrokerSubmitDecision.intent == "auto")
            .order_by(desc(BrokerSubmitDecision.created_at))
            .limit(_MAX_RECENT_DECISIONS)
        ).scalars().all()

        for row in rows:
            payload = row.preflight_json if isinstance(row.preflight_json, dict) else {}
            payload_broker_order_id = str(payload.get("broker_order_id") or "").strip()
            if payload_broker_order_id != broker_order_id:
                continue
            if signal_id is None or row.signal_id == signal_id:
                return True
        return False

    def _persist_reconciled_submit_decision(
        self,
        *,
        session: Session,
        paper_order: PaperOrder,
        broker_order_id: str,
    ) -> None:
        writer = BrokerSubmitDecisionService(session)
        record = BrokerSubmitDecisionRecord(
            intent="auto",
            would_block=False,
            decision_status="allowed",
            allowed_to_submit=True,
            decision_reason=_RECONCILED_REASON,
            blocked_reason_code=None,
            blocked_reason_text=None,
            blocked_reasons=[],
            warnings=[],
            execution_mode="ibkr_paper",
            account_mode="paper",
            source=_RECONCILED_SOURCE,
            submit_gate=_RECONCILED_GATE,
            broker_order_id=broker_order_id,
            correlation_id=f"audit-reconcile:{paper_order.id}",
            signal_id=paper_order.signal_id,
        )
        writer.persist(
            record,
            source_metadata={
                "reconciled_from": "paper_order",
                "paper_order_id": str(paper_order.id),
                "paper_order_status": self._normalize_text(paper_order.status),
                "paper_order_ibkr_status": paper_order.ibkr_status,
                "paper_order_submitted_at": self._serialize_timestamp(paper_order),
            },
        )

    def _serialize_timestamp(self, paper_order: PaperOrder) -> str | None:
        submitted_at = paper_order.submitted_at or paper_order.timestamp
        if submitted_at is None:
            return None
        return submitted_at.isoformat()