"""Model registry endpoints.

GET    /models          — List all registered model versions.
GET    /models/active   — Return the currently active model version.
GET    /models/{id}     — Return a specific model version by ID.
POST   /models          — Register a new model version.
PATCH  /models/{id}     — Update mutable metadata on a model version.
DELETE /models/{id}     — Deactivate (soft-delete) a model version.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db_session as get_db
from app.schemas.models import (
    CreateModelVersionRequest,
    ModelGovernanceActionResponse,
    ModelVersionListResponse,
    ModelVersionResponse,
    UpdateModelVersionRequest,
)
from app.services.governance.model_audit_service import ModelAuditService
from app.services.governance.model_registry_service import ModelRegistryService

router = APIRouter(prefix="/models", tags=["models"])


def _registry(db: Session = Depends(get_db)) -> ModelRegistryService:
    return ModelRegistryService(session=db, audit_service=ModelAuditService(db))


@router.get("", response_model=ModelVersionListResponse)
def list_models(registry: ModelRegistryService = Depends(_registry)) -> ModelVersionListResponse:
    """List all registered model versions (newest first)."""
    items = registry.get_all()
    return ModelVersionListResponse(
        items=[ModelVersionResponse.model_validate(v) for v in items],
        total=len(items),
    )


@router.get("/active", response_model=ModelVersionResponse)
def get_active_model(registry: ModelRegistryService = Depends(_registry)) -> ModelVersionResponse:
    """Return the currently active model version."""
    version = registry.get_active()
    if version is None:
        raise HTTPException(status_code=404, detail="No active model version")
    return ModelVersionResponse.model_validate(version)


@router.get("/{model_version_id}", response_model=ModelVersionResponse)
def get_model(
    model_version_id: uuid.UUID,
    registry: ModelRegistryService = Depends(_registry),
) -> ModelVersionResponse:
    """Return a specific model version by ID."""
    version = registry.get_by_id(model_version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Model version not found")
    return ModelVersionResponse.model_validate(version)


@router.post("", response_model=ModelVersionResponse, status_code=201)
def create_model(
    body: CreateModelVersionRequest,
    db: Session = Depends(get_db),
    registry: ModelRegistryService = Depends(_registry),
) -> ModelVersionResponse:
    """Register a new model version (inactive by default)."""
    version = registry.create(
        provider_name=body.provider_name,
        model_name=body.model_name,
        alias_name=body.alias_name,
        temperature=body.temperature,
        top_p=body.top_p,
        max_output_tokens=body.max_output_tokens,
        reasoning_level=body.reasoning_level,
        supports_structured_output=body.supports_structured_output,
        notes=body.notes,
    )
    db.commit()
    return ModelVersionResponse.model_validate(version)


@router.patch("/{model_version_id}", response_model=ModelVersionResponse)
def update_model(
    model_version_id: uuid.UUID,
    body: UpdateModelVersionRequest,
    db: Session = Depends(get_db),
    registry: ModelRegistryService = Depends(_registry),
) -> ModelVersionResponse:
    """Update mutable metadata on a model version."""
    try:
        version = registry.update(
            model_version_id,
            alias_name=body.alias_name,
            notes=body.notes,
            temperature=body.temperature,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.commit()
    return ModelVersionResponse.model_validate(version)


@router.delete("/{model_version_id}", response_model=ModelGovernanceActionResponse)
def deactivate_model(
    model_version_id: uuid.UUID,
    db: Session = Depends(get_db),
    registry: ModelRegistryService = Depends(_registry),
) -> ModelGovernanceActionResponse:
    """Deactivate (soft-delete) a model version."""
    try:
        version = registry.deactivate(model_version_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.commit()
    return ModelGovernanceActionResponse(
        action="deactivate",
        model_version_id=version.id,
        is_active=version.is_active,
        message=f"Model version {version.id} deactivated",
    )
