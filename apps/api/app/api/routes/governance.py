"""Model governance endpoints — promotion and rollback.

POST /governance/promote   — Promote a candidate model version to active.
POST /governance/rollback  — Rollback to the previous active model version.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db_session as get_db
from app.schemas.models import ModelGovernanceActionResponse, PromoteModelVersionRequest
from app.services.governance.model_audit_service import ModelAuditService
from app.services.governance.model_promotion_service import ModelPromotionService
from app.services.governance.model_rollback_service import ModelRollbackService

router = APIRouter(prefix="/governance", tags=["governance"])


@router.post("/promote", response_model=ModelGovernanceActionResponse)
def promote_model(
    body: PromoteModelVersionRequest,
    db: Session = Depends(get_db),
) -> ModelGovernanceActionResponse:
    """Promote a candidate model version to the active slot."""
    audit = ModelAuditService(db)
    promotion_service = ModelPromotionService(db, audit_service=audit)
    try:
        version = promotion_service.promote(body.model_version_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.commit()
    return ModelGovernanceActionResponse(
        action="promote",
        model_version_id=version.id,
        is_active=version.is_active,
        message=f"Model version {version.id} is now active",
    )


@router.post("/rollback", response_model=ModelGovernanceActionResponse)
def rollback_model(db: Session = Depends(get_db)) -> ModelGovernanceActionResponse:
    """Roll back the active model to the previously active version."""
    audit = ModelAuditService(db)
    rollback_service = ModelRollbackService(db, audit_service=audit)
    try:
        version = rollback_service.rollback()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    return ModelGovernanceActionResponse(
        action="rollback",
        model_version_id=version.id,
        is_active=version.is_active,
        message=f"Rolled back to model version {version.id}",
    )
