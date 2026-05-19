"""ModelRollbackService — revert the active model to the previous version.

Rollback reads the audit log for the most recent ``model_governance.promote``
event, extracts the ``previous_active_id``, and re-promotes that version.
This gives a one-step undo for problematic model promotions.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.audit_log import AuditLog
from app.db.models.model_version import ModelVersion
from app.services.governance.model_audit_service import ModelAuditService


class ModelRollbackService:
    """Rolls back the active model to the previous version."""

    def __init__(
        self,
        session: Session,
        audit_service: ModelAuditService | None = None,
    ) -> None:
        self._session = session
        self._audit = audit_service or ModelAuditService(session)

    def rollback(self) -> ModelVersion:
        """Revert to the model version active before the last promotion.

        Raises:
            ValueError: If no active version exists, no previous version
                can be found in the audit log, or the previous version ID
                is not in the registry.
        """
        # Find current active version
        current_active = (
            self._session.execute(
                select(ModelVersion).where(ModelVersion.is_active == True)  # noqa: E712
            )
            .scalars()
            .first()
        )
        if current_active is None:
            raise ValueError("No active model version to roll back from")

        # Find the most recent promote event for the current active version
        promote_log = (
            self._session.execute(
                select(AuditLog)
                .where(AuditLog.entity_type == "model_version")
                .where(AuditLog.event_type == "model_governance.promote")
                .where(AuditLog.entity_id == current_active.id)
                .order_by(AuditLog.created_at.desc())
            )
            .scalars()
            .first()
        )

        if promote_log is None or not promote_log.payload_json:
            raise ValueError(
                f"No promotion audit record found for active version {current_active.id}"
            )

        previous_id_str = promote_log.payload_json.get("previous_active_id")
        if not previous_id_str:
            raise ValueError("Promote audit log has no previous_active_id; cannot roll back")

        try:
            previous_id = uuid.UUID(previous_id_str)
        except (ValueError, AttributeError) as exc:
            raise ValueError(f"Invalid previous_active_id in audit log: {previous_id_str}") from exc

        previous_version = self._session.get(ModelVersion, previous_id)
        if previous_version is None:
            raise ValueError(f"Previous ModelVersion {previous_id} not found in registry")

        rolled_back_from_id = str(current_active.id)

        # Deactivate current, promote previous
        current_active.is_active = False
        previous_version.is_active = True
        self._session.flush()

        self._audit.log_rollback(previous_version, rolled_back_from_id=rolled_back_from_id)
        return previous_version
