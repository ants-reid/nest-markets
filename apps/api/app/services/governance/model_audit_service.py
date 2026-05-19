"""ModelAuditService — audit trail logging for model governance events.

Every governance action (create, promote, rollback, deactivate, update)
is recorded in the ``AuditLog`` table with entity_type ``model_version``.
This provides a tamper-evident trail required for Gate 11 compliance.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models.audit_log import AuditLog
from app.db.models.model_version import ModelVersion


class ModelAuditService:
    """Records governance events for model versions."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def log_create(self, version: ModelVersion) -> None:
        self._log("create", version, {})

    def log_update(self, version: ModelVersion) -> None:
        self._log("update", version, {
            "alias_name": version.alias_name,
            "notes": version.notes,
            "temperature": version.temperature,
        })

    def log_promote(self, version: ModelVersion, previous_id: str | None) -> None:
        self._log("promote", version, {"previous_active_id": previous_id})

    def log_rollback(self, version: ModelVersion, rolled_back_from_id: str | None) -> None:
        self._log("rollback", version, {"rolled_back_from_id": rolled_back_from_id})

    def log_deactivate(self, version: ModelVersion) -> None:
        self._log("deactivate", version, {})

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _log(self, event_type: str, version: ModelVersion, payload: dict) -> None:
        entry = AuditLog(
            entity_type="model_version",
            entity_id=version.id,
            event_type=f"model_governance.{event_type}",
            payload_json={
                "provider_name": version.provider_name,
                "model_name": version.model_name,
                "is_active": version.is_active,
                **payload,
            },
        )
        self._session.add(entry)
        self._session.flush()
