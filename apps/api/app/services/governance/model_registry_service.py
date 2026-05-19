"""ModelRegistryService — CRUD operations on the ModelVersion registry.

The model registry tracks every LLM provider/model configuration that has
been used or is being considered.  Only one ModelVersion can have
``is_active=True`` at a time; all others are inactive.

All write operations audit themselves via ``ModelAuditService``.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.model_version import ModelVersion

if TYPE_CHECKING:
    from app.services.governance.model_audit_service import ModelAuditService


class ModelRegistryService:
    """CRUD service for ``ModelVersion`` registry entries."""

    def __init__(
        self,
        session: Session,
        audit_service: "ModelAuditService | None" = None,
    ) -> None:
        self._session = session
        self._audit = audit_service

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_all(self) -> list[ModelVersion]:
        """Return all model versions ordered by creation time (newest first)."""
        return list(
            self._session.execute(
                select(ModelVersion).order_by(ModelVersion.created_at.desc())
            )
            .scalars()
            .all()
        )

    def get_active(self) -> ModelVersion | None:
        """Return the currently active model version, or None."""
        return (
            self._session.execute(
                select(ModelVersion).where(ModelVersion.is_active == True)  # noqa: E712
            )
            .scalars()
            .first()
        )

    def get_by_id(self, model_version_id: uuid.UUID) -> ModelVersion | None:
        """Return a specific model version by ID."""
        return self._session.get(ModelVersion, model_version_id)

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    def create(
        self,
        *,
        provider_name: str,
        model_name: str,
        alias_name: str | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        max_output_tokens: int | None = None,
        reasoning_level: str | None = None,
        supports_structured_output: bool = True,
        notes: str | None = None,
    ) -> ModelVersion:
        """Register a new model version (inactive by default)."""
        version = ModelVersion(
            provider_name=provider_name,
            provider=provider_name,
            model_name=model_name,
            alias_name=alias_name,
            temperature=temperature,
            top_p=top_p,
            max_output_tokens=max_output_tokens,
            reasoning_level=reasoning_level,
            supports_structured_output=supports_structured_output,
            is_active=False,
            notes=notes,
        )
        self._session.add(version)
        self._session.flush()
        self._session.refresh(version)
        if self._audit:
            self._audit.log_create(version)
        return version

    def update(
        self,
        model_version_id: uuid.UUID,
        *,
        alias_name: str | None = None,
        notes: str | None = None,
        temperature: float | None = None,
    ) -> ModelVersion:
        """Update mutable metadata fields on a model version."""
        version = self._session.get(ModelVersion, model_version_id)
        if version is None:
            raise ValueError(f"ModelVersion {model_version_id} not found")
        if alias_name is not None:
            version.alias_name = alias_name
        if notes is not None:
            version.notes = notes
        if temperature is not None:
            version.temperature = temperature
        self._session.flush()
        if self._audit:
            self._audit.log_update(version)
        return version

    def deactivate(self, model_version_id: uuid.UUID) -> ModelVersion:
        """Mark a model version as inactive without deleting it."""
        version = self._session.get(ModelVersion, model_version_id)
        if version is None:
            raise ValueError(f"ModelVersion {model_version_id} not found")
        version.is_active = False
        self._session.flush()
        if self._audit:
            self._audit.log_deactivate(version)
        return version
