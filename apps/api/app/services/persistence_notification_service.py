"""Persistence and query helpers for in-app alert notifications."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.audit_log import AuditLog
from app.services.persistence_alert_service import PersistenceAlertService


@dataclass
class NotificationRecord:
    """One in-app notification derived from one active alert."""

    notification_id: str
    alert_id: str
    rule_id: UUID
    execution_id: UUID
    asset: str
    status: str
    message: str
    level: str
    is_read: bool
    read_at: datetime | None


class PersistenceNotificationService:
    """Derive and persist in-app notification state for active alerts."""

    ENTITY_TYPE_NOTIFICATION = "alert_notification"
    EVENT_NOTIFICATION_READ = "notification_read"

    def __init__(self, session: Session) -> None:
        """Initialize service with an explicit SQLAlchemy session."""
        self._session = session
        self._alert_service = PersistenceAlertService(session)

    def list_notifications(self, *, include_visual_seed: bool = False) -> list[NotificationRecord]:
        """Return in-app notifications derived from active alerts with read state."""
        active_alerts = self._alert_service.list_active_alerts(include_visual_seed=include_visual_seed)
        read_events = self._load_read_events()

        notifications: list[NotificationRecord] = []
        for alert in active_alerts:
            notification_uuid = self._notification_uuid_for_alert(alert.alert_id)
            read_at = read_events.get(notification_uuid)
            notifications.append(
                NotificationRecord(
                    notification_id=str(notification_uuid),
                    alert_id=alert.alert_id,
                    rule_id=alert.rule_id,
                    execution_id=alert.execution_id,
                    asset=alert.asset,
                    status=alert.status,
                    message=alert.message,
                    level=alert.level,
                    is_read=read_at is not None,
                    read_at=read_at,
                )
            )

        return notifications

    def mark_as_read(self, notification_id: str, *, include_visual_seed: bool = False) -> NotificationRecord:
        """Mark one notification as read by writing one audit event."""
        target: NotificationRecord | None = None
        for candidate in self.list_notifications(include_visual_seed=include_visual_seed):
            if candidate.notification_id == notification_id:
                target = candidate
                break

        if target is None:
            raise ValueError(f"Notification '{notification_id}' not found")

        if not target.is_read:
            now = datetime.now(UTC)
            self._session.add(
                AuditLog(
                    entity_type=self.ENTITY_TYPE_NOTIFICATION,
                    entity_id=UUID(notification_id),
                    event_type=self.EVENT_NOTIFICATION_READ,
                    payload_json={
                        "alert_id": target.alert_id,
                        "execution_id": str(target.execution_id),
                        "asset": target.asset,
                        "read_at": now.isoformat(),
                    },
                )
            )
            self._session.flush()

        for refreshed in self.list_notifications(include_visual_seed=include_visual_seed):
            if refreshed.notification_id == notification_id:
                return refreshed

        raise ValueError(f"Notification '{notification_id}' not found")

    def _load_read_events(self) -> dict[UUID, datetime]:
        """Return latest read timestamp per notification id."""
        rows = self._session.execute(
            select(AuditLog)
            .where(AuditLog.entity_type == self.ENTITY_TYPE_NOTIFICATION)
            .where(AuditLog.event_type == self.EVENT_NOTIFICATION_READ)
            .order_by(AuditLog.created_at.asc(), AuditLog.id.asc())
        ).scalars().all()

        read_by_notification: dict[UUID, datetime] = {}
        for row in rows:
            if row.entity_id is None:
                continue
            payload = row.payload_json or {}
            read_at = self._parse_iso(payload.get("read_at")) or row.created_at
            read_by_notification[row.entity_id] = read_at
        return read_by_notification

    def _notification_uuid_for_alert(self, alert_id: str) -> UUID:
        """Build deterministic notification UUID for one active alert id."""
        return uuid5(NAMESPACE_URL, f"market-hunter-alert-notification:{alert_id}")

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