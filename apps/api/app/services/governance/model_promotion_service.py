"""ModelPromotionService — promote a candidate model version to active.

Promotion sets exactly one ``ModelVersion.is_active = True`` and clears all
others.  The previous active version ID is recorded in the audit log so that
``ModelRollbackService`` can identify the prior state.

Invariant: at most one ModelVersion has ``is_active = True`` after any
promotion.  This is enforced in application logic (not a DB constraint in
Phase 3; a partial-unique index can be added in Phase 4).
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.model_version import ModelVersion
from app.services.governance.model_audit_service import ModelAuditService


class ModelPromotionService:
    """Promotes a candidate model version to the active slot."""

    def __init__(
        self,
        session: Session,
        audit_service: ModelAuditService | None = None,
    ) -> None:
        self._session = session
        self._audit = audit_service or ModelAuditService(session)

    def promote(self, model_version_id: uuid.UUID) -> ModelVersion:
        """Set ``model_version_id`` as the active model.

        All currently active versions are deactivated first.  The newly
        promoted version is returned with ``is_active = True``.

        Raises:
            ValueError: If the target version does not exist.
        """
        candidate = self._session.get(ModelVersion, model_version_id)
        if candidate is None:
            raise ValueError(f"ModelVersion {model_version_id} not found")

        # Find the current active version (may be None)
        current_active = (
            self._session.execute(
                select(ModelVersion).where(ModelVersion.is_active == True)  # noqa: E712
            )
            .scalars()
            .first()
        )
        previous_id = str(current_active.id) if current_active else None

        # Deactivate all existing active versions
        if current_active and current_active.id != candidate.id:
            current_active.is_active = False

        # Promote the candidate
        candidate.is_active = True
        self._session.flush()

        self._audit.log_promote(candidate, previous_id=previous_id)
        return candidate
