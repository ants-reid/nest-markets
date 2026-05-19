"""Persistence and query helpers for MVP alert rules and active alerts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.audit_log import AuditLog
from app.services.persistence_paper_execution_service import PersistencePaperExecutionService


@dataclass
class AlertRuleState:
    """Materialized state for one persisted alert rule."""

    rule_id: UUID
    asset: str
    condition: str
    status: str
    created_at: datetime
    updated_at: datetime
    snoozed_until: datetime | None


@dataclass
class ActiveAlertRecord:
    """One active alert generated from a rule and execution state."""

    alert_id: str
    rule_id: UUID
    execution_id: UUID
    asset: str
    status: str
    message: str
    level: str


class PersistenceAlertService:
    """Persist alert rule events and derive current rule/alert views."""

    EVENT_RULE_CREATED = "rule_created"
    EVENT_RULE_ACKNOWLEDGED = "rule_acknowledged"
    EVENT_RULE_SNOOZED = "rule_snoozed"

    def __init__(self, session: Session) -> None:
        """Initialize service with an explicit SQLAlchemy session."""
        self._session = session

    def create_rule(self, *, asset: str, condition: str) -> AlertRuleState:
        """Create one alert rule by writing a creation event."""
        now = datetime.now(UTC)
        rule_id = uuid4()
        payload = {
            "asset": asset.strip().upper(),
            "condition": condition.strip(),
            "status": "active",
            "snoozed_until": None,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

        self._session.add(
            AuditLog(
                entity_type="alert_rule",
                entity_id=rule_id,
                event_type=self.EVENT_RULE_CREATED,
                payload_json=payload,
            )
        )
        self._session.flush()
        return AlertRuleState(
            rule_id=rule_id,
            asset=payload["asset"],
            condition=payload["condition"],
            status="active",
            created_at=now,
            updated_at=now,
            snoozed_until=None,
        )

    def list_rules(self) -> list[AlertRuleState]:
        """Return the current materialized state for all alert rules."""
        rows = self._session.execute(
            select(AuditLog)
            .where(AuditLog.entity_type == "alert_rule")
            .order_by(AuditLog.created_at.asc(), AuditLog.id.asc())
        ).scalars().all()

        materialized: dict[UUID, AlertRuleState] = {}

        # First pass: create baseline rules.
        for row in rows:
            if row.entity_id is None:
                continue
            payload = row.payload_json or {}
            if row.event_type == self.EVENT_RULE_CREATED:
                asset = str(payload.get("asset") or "").strip().upper()
                condition = str(payload.get("condition") or "").strip()
                status = str(payload.get("status") or "active").strip().lower()
                if not asset or not condition:
                    continue
                materialized[row.entity_id] = AlertRuleState(
                    rule_id=row.entity_id,
                    asset=asset,
                    condition=condition,
                    status=status,
                    created_at=row.created_at,
                    updated_at=row.created_at,
                    snoozed_until=self._parse_iso(payload.get("snoozed_until")),
                )
        # Second pass: apply lifecycle transitions.
        updates = [row for row in rows if row.entity_id is not None and row.event_type != self.EVENT_RULE_CREATED]
        updates.sort(key=self._event_updated_at)

        for row in updates:
            payload = row.payload_json or {}
            current = materialized.get(row.entity_id)
            if current is None:
                continue

            if row.event_type == self.EVENT_RULE_ACKNOWLEDGED:
                current.status = "acknowledged"
                current.updated_at = self._event_updated_at(row)
                current.snoozed_until = None
                continue

            if row.event_type == self.EVENT_RULE_SNOOZED:
                current.status = "snoozed"
                current.updated_at = self._event_updated_at(row)
                current.snoozed_until = self._parse_iso(payload.get("snoozed_until"))

        return sorted(materialized.values(), key=lambda item: (item.created_at, str(item.rule_id)))

    def acknowledge_rule(self, rule_id: UUID) -> AlertRuleState:
        """Acknowledge one rule by writing an acknowledgment event."""
        self._get_rule_or_raise(rule_id)
        self._session.add(
            AuditLog(
                entity_type="alert_rule",
                entity_id=rule_id,
                event_type=self.EVENT_RULE_ACKNOWLEDGED,
                payload_json={"updated_at": datetime.now(UTC).isoformat()},
            )
        )
        self._session.flush()

        refreshed = self._get_rule_or_raise(rule_id)
        return refreshed

    def snooze_rule(self, rule_id: UUID, minutes: int) -> AlertRuleState:
        """Snooze one rule for the requested number of minutes."""
        if minutes <= 0:
            raise ValueError("Snooze minutes must be > 0")

        _ = self._get_rule_or_raise(rule_id)
        snoozed_until = datetime.now(UTC) + timedelta(minutes=minutes)
        self._session.add(
            AuditLog(
                entity_type="alert_rule",
                entity_id=rule_id,
                event_type=self.EVENT_RULE_SNOOZED,
                payload_json={
                    "minutes": minutes,
                    "snoozed_until": snoozed_until.isoformat(),
                    "updated_at": datetime.now(UTC).isoformat(),
                },
            )
        )
        self._session.flush()

        refreshed = self._get_rule_or_raise(rule_id)
        return refreshed

    def list_active_alerts(self, *, include_visual_seed: bool = False) -> list[ActiveAlertRecord]:
        """Return active alerts generated from persisted rules and paper executions."""
        now = datetime.now(UTC)
        rules = self.list_rules()
        available_rules = [
            rule
            for rule in rules
            if rule.status == "active" or (rule.status == "snoozed" and (rule.snoozed_until is None or rule.snoozed_until <= now))
        ]

        if not available_rules:
            return []

        paper_persistence = PersistencePaperExecutionService(self._session)
        orders = paper_persistence.list_paper_orders(
            limit=50,
            offset=0,
            status=None,
            include_visual_seed=include_visual_seed,
        )

        alerts: list[ActiveAlertRecord] = []
        for row in orders:
            try:
                execution = paper_persistence.build_service_result(row)
            except ValueError:
                continue

            execution_status = execution.status.lower()
            execution_asset = execution.asset.upper()

            for rule in available_rules:
                if execution_asset != rule.asset:
                    continue
                if not self._matches_condition(rule.condition, execution_status):
                    continue

                alert_id = f"{rule.rule_id}:{execution.execution_id}:{execution_status}"
                message = f"{rule.asset} matched rule '{rule.condition}' on execution status '{execution.status}'."
                level = "warning" if execution_status in {"blocked", "rejected"} else "info"
                alerts.append(
                    ActiveAlertRecord(
                        alert_id=alert_id,
                        rule_id=rule.rule_id,
                        execution_id=execution.execution_id,
                        asset=execution.asset,
                        status=execution.status,
                        message=message,
                        level=level,
                    )
                )

        return alerts

    def _get_rule_or_raise(self, rule_id: UUID) -> AlertRuleState:
        """Return one materialized rule or raise if it does not exist."""
        for rule in self.list_rules():
            if rule.rule_id == rule_id:
                return rule
        raise ValueError(f"Alert rule '{rule_id}' not found")

    def _matches_condition(self, condition: str, execution_status: str) -> bool:
        """Evaluate minimal MVP rule syntax against one execution status."""
        normalized = condition.strip().lower()

        if "!=" in normalized:
            left, right = normalized.split("!=", 1)
            if left.strip() == "status":
                return execution_status != right.strip()

        if "=" in normalized:
            left, right = normalized.split("=", 1)
            if left.strip() == "status":
                return execution_status == right.strip()

        # Unsupported condition syntax is ignored by design in MVP.
        return False

    def _event_updated_at(self, row: AuditLog) -> datetime:
        """Return deterministic update timestamp for one lifecycle event row."""
        payload = row.payload_json or {}
        parsed = self._parse_iso(payload.get("updated_at"))
        return parsed or row.created_at

    def _parse_iso(self, value: object) -> datetime | None:
        """Parse one ISO datetime string payload field when present."""
        if value is None:
            return None
        if not isinstance(value, str):
            return None

        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None

        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed
