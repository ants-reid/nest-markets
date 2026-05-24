"""Broker preflight decision helper service.

This module centralizes decision classification and persistence used by
``BrokerService`` submit and dry-run paths. It is internal orchestration only;
it never submits broker orders and never alters trading control outcomes.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from app.db.session import SessionLocal
from app.services.broker_mode_guard import get_broker_mode_metadata
from app.services.paper_source_contract import broker_dry_run_sources, broker_sources_from_mode
from app.services.broker_submit_decision_service import (
    BrokerSubmitDecisionRecord,
    BrokerSubmitDecisionService,
)

_logger = logging.getLogger(__name__)

_CORRELATION_ID_HARD_CAP = 160
_REFERENCE_HARD_CAP = 240


def _optional_str(value: Any, *, max_len: int | None = None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    value = value.strip()
    if not value:
        return None
    if max_len is None or len(value) <= max_len:
        return value
    return value[:max_len]


def _optional_uuid(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError):
        return None


def _optional_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


class BrokerPreflightDecisionService:
    """Classify and persist broker preflight decisions."""

    def build_preflight_decision(
        self,
        *,
        issues: list[dict[str, Any]],
        warnings: list[dict[str, Any]],
    ) -> dict[str, Any]:
        blocking_items: list[dict[str, Any]] = []
        advisory_items: list[dict[str, Any]] = []
        would_block_items: list[dict[str, Any]] = []

        for issue in issues:
            blocking_items.append(
                {
                    "code": issue["code"],
                    "message": issue["message"],
                    "severity": issue.get("severity"),
                    "source": issue.get("source") or "request_validation",
                    "enforcement_enabled": True,
                    "classification": "blocking",
                }
            )

        blocking_warning_codes = {
            "emergency_stop_active",
        }

        would_block_codes = {
            "max_order_notional_exceeded",
            "max_total_exposure_exceeded",
            "max_symbol_exposure_exceeded",
            "max_open_positions_exceeded",
            "max_trades_per_day_exceeded",
            "min_cash_buffer_breached",
        }

        for warning in warnings:
            warning_code = warning.get("code")
            if warning_code in blocking_warning_codes:
                classification = "blocking"
                target = blocking_items
            elif warning_code in would_block_codes:
                classification = "would_block"
                target = would_block_items
            else:
                classification = "advisory"
                target = advisory_items
            target.append(
                {
                    "code": warning["code"],
                    "message": warning["message"],
                    "severity": warning.get("severity"),
                    "source": warning.get("source"),
                    "enforcement_enabled": bool(warning.get("enforcement_enabled", False)),
                    "classification": classification,
                }
            )

        if blocking_items:
            decision_status = "blocked"
        elif would_block_items:
            decision_status = "would_block"
        elif advisory_items:
            decision_status = "advisory"
        else:
            decision_status = "allowed"

        return {
            "decision_status": decision_status,
            "submit_gate": "not_applied",
            "advisory_count": len(advisory_items),
            "would_block_count": len(would_block_items),
            "blocking_count": len(blocking_items),
            "advisory_items": advisory_items,
            "would_block_items": would_block_items,
            "blocking_items": blocking_items,
        }

    def is_submit_blocked_by_preflight(self, decision: dict[str, Any]) -> bool:
        decision_status = str(decision.get("decision_status") or "unknown").strip().lower()
        blocking_count = int(decision.get("blocking_count") or 0)
        would_block_count = int(decision.get("would_block_count") or 0)

        if blocking_count > 0 or would_block_count > 0:
            return True
        if decision_status in {"blocked", "would_block", "error", "unknown", "invalid"}:
            return True
        return decision_status not in {"allowed", "advisory"}

    def build_blocked_error_decision(self, *, code: str, message: str) -> dict[str, Any]:
        return {
            "decision_status": "error",
            "submit_gate": "blocked",
            "advisory_count": 0,
            "would_block_count": 1,
            "blocking_count": 0,
            "advisory_items": [],
            "would_block_items": [
                {
                    "code": code,
                    "message": message,
                    "source": "preflight",
                    "classification": "would_block",
                    "severity": "critical",
                }
            ],
            "blocking_items": [],
        }

    def decision_reason_fields(
        self, preflight_decision: dict[str, Any], warnings: list[dict[str, Any]]
    ) -> tuple[str | None, str | None, str | None, list[dict[str, Any]]]:
        del warnings
        blocked_reasons = list(preflight_decision.get("blocking_items") or []) + list(
            preflight_decision.get("would_block_items") or []
        )
        primary = blocked_reasons[0] if blocked_reasons else None
        reason_code = primary.get("code") if primary else None
        reason_text = primary.get("message") if primary else None

        decision_status = str(preflight_decision.get("decision_status") or "unknown").strip().lower()
        if reason_text:
            decision_reason = reason_text
        elif decision_status == "allowed":
            decision_reason = "preflight_allowed"
        elif decision_status == "advisory":
            decision_reason = "advisory_only"
        elif decision_status == "would_block":
            decision_reason = "would_block_findings"
        elif decision_status == "blocked":
            decision_reason = "blocking_findings"
        else:
            decision_reason = "preflight_unknown"

        return decision_reason, reason_code, reason_text, blocked_reasons

    def execution_mode_metadata(self) -> tuple[str, str]:
        mode_meta = get_broker_mode_metadata()
        broker_mode = str(mode_meta.get("mode") or "paper").lower()
        execution_mode = "ibkr_paper"
        if broker_mode == "live":
            execution_mode = "ibkr_live_locked"
        return execution_mode, broker_mode

    def source_metadata(self, *, source: str) -> dict[str, Any]:
        mode_meta = get_broker_mode_metadata()
        if source == "dry_run":
            return broker_dry_run_sources(mode_meta)
        return broker_sources_from_mode(mode_meta)

    def decision_metadata(self, metadata: dict[str, Any] | None) -> tuple[str | None, dict[str, Any]]:
        sanitized: dict[str, Any] = {}
        if not metadata:
            return None, sanitized

        correlation_id = _optional_str(
            metadata.get("correlation_id"), max_len=_CORRELATION_ID_HARD_CAP
        )
        recommendation_id = _optional_uuid(metadata.get("recommendation_id"))
        route_check_reference = _optional_str(
            metadata.get("route_check_reference"), max_len=_REFERENCE_HARD_CAP
        )
        dry_run_reference = _optional_str(
            metadata.get("dry_run_reference"), max_len=_REFERENCE_HARD_CAP
        )
        ticker = _optional_str(metadata.get("ticker"), max_len=32)
        side = _optional_str(metadata.get("side"), max_len=16)
        order_type = _optional_str(metadata.get("order_type"), max_len=32)
        quantity = _optional_number(metadata.get("quantity"))
        limit_price = _optional_number(metadata.get("limit_price"))
        stop_price = _optional_number(metadata.get("stop_price"))

        if recommendation_id is not None:
            sanitized["recommendation_id"] = recommendation_id
        if route_check_reference is not None:
            sanitized["route_check_reference"] = route_check_reference
        if dry_run_reference is not None:
            sanitized["dry_run_reference"] = dry_run_reference

        request_summary = {
            "ticker": ticker,
            "side": side,
            "quantity": quantity,
            "order_type": order_type,
            "limit_price": limit_price,
            "stop_price": stop_price,
        }
        if any(value is not None for value in request_summary.values()):
            sanitized["request_summary"] = request_summary

        return correlation_id, sanitized

    def persist_submit_decision(
        self,
        *,
        intent: str,
        preflight_decision: dict[str, Any],
        warnings: list[dict[str, Any]],
        source: str,
        submit_gate: str,
        broker_order_id: str | None = None,
        decision_metadata: dict[str, Any] | None = None,
    ) -> None:
        try:
            decision_status = str(preflight_decision.get("decision_status") or "unknown").strip().lower()
            blocked = self.is_submit_blocked_by_preflight(preflight_decision)
            decision_reason, reason_code, reason_text, blocked_reasons = self.decision_reason_fields(
                preflight_decision, warnings
            )
            execution_mode, account_mode = self.execution_mode_metadata()
            correlation_id, extra_metadata = self.decision_metadata(decision_metadata)

            record = BrokerSubmitDecisionRecord(
                intent=intent,
                would_block=blocked,
                decision_status=decision_status,
                allowed_to_submit=not blocked,
                decision_reason=decision_reason,
                blocked_reason_code=reason_code,
                blocked_reason_text=reason_text,
                blocked_reasons=blocked_reasons,
                warnings=warnings,
                execution_mode=execution_mode,
                account_mode=account_mode,
                source=source,
                submit_gate=submit_gate,
                broker_order_id=broker_order_id,
                correlation_id=correlation_id,
            )
            with SessionLocal() as session:
                writer = BrokerSubmitDecisionService(session)
                writer.persist(
                    record,
                    source_metadata={
                        **self.source_metadata(source=source),
                        **extra_metadata,
                    },
                )
                session.commit()
        except Exception:
            _logger.exception(
                "Failed to persist broker submit decision intent=%s source=%s",
                intent,
                source,
            )

    def persist_submit_decision_from_result(
        self,
        *,
        result: dict[str, Any],
        intent: str,
        source: str,
        decision_metadata: dict[str, Any] | None = None,
    ) -> None:
        preflight_decision = dict(result.get("preflight_decision") or {})
        warnings = list(result.get("warnings") or [])
        submit_gate = str(preflight_decision.get("submit_gate") or "not_applied")
        self.persist_submit_decision(
            intent=intent,
            preflight_decision=preflight_decision,
            warnings=warnings,
            source=source,
            submit_gate=submit_gate,
            decision_metadata=decision_metadata,
        )