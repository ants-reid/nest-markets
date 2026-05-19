"""Prompt adaptations routes — propose and apply AI-driven prompt revisions.

Gate 11: POST /prompt-adaptations/apply creates a NEW PromptVersion row.
It NEVER updates an existing row in-place.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.enums import PromptRole
from app.db.models.prompt_version import PromptVersion
from app.db.session import get_db_session

router = APIRouter(prefix="/prompt-adaptations", tags=["prompt-adaptations"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class PromptAdaptationProposalRequest(BaseModel):
    """Payload sent to apply a prompt adaptation proposal."""

    setup_type: str = Field(..., min_length=1)
    rationale: str = Field(..., min_length=1)
    proposed_prompt_text: str = Field(..., min_length=1)
    current_win_rate: float = Field(..., ge=0.0, le=1.0)
    total_samples: int = Field(..., ge=0)


class PromptVersionCreatedResponse(BaseModel):
    """Response after a new PromptVersion is created from a proposal."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    role: str
    version: str
    is_active: bool


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/apply",
    response_model=PromptVersionCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
def apply_prompt_adaptation(
    body: PromptAdaptationProposalRequest,
    session: Annotated[Session, Depends(get_db_session)],
) -> PromptVersionCreatedResponse:
    """Create a new PromptVersion from an adaptation proposal (Gate 11).

    The new version is stored as inactive; an operator must explicitly promote
    it via the existing prompt-versions promote endpoint.
    """
    # Find the current highest version for the SIGNAL_ENGINE role
    existing = session.execute(
        select(PromptVersion)
        .where(PromptVersion.role == PromptRole.SIGNAL_ENGINE)
        .order_by(PromptVersion.version.desc())
        .limit(1)
    ).scalar_one_or_none()

    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existing SIGNAL_ENGINE PromptVersion found. Seed the database first.",
        )

    # Compute next version string (e.g. "1.0" -> "1.1", "1.9" -> "1.10")
    try:
        major, minor = existing.version.split(".", 1)
        next_version = f"{major}.{int(minor) + 1}"
    except (ValueError, AttributeError):
        # Fallback: append -adapted
        next_version = f"{existing.version}-adapted"

    # Gate 11: create a NEW row — existing row is NOT modified
    new_version = PromptVersion(
        name=f"Adapted: {body.setup_type} ({body.current_win_rate:.1%} win rate)",
        role=PromptRole.SIGNAL_ENGINE,
        version=next_version,
        system_prompt=body.proposed_prompt_text,
        user_template=existing.user_template,  # preserve existing user template
        schema_json=existing.schema_json,  # preserve existing schema
        is_active=False,
        notes=(
            f"Auto-proposed by PromptAdaptationService. "
            f"Setup: {body.setup_type}. "
            f"Win rate: {body.current_win_rate:.1%} / {body.total_samples} samples. "
            f"Rationale: {body.rationale}"
        ),
    )

    session.add(new_version)
    session.commit()
    session.refresh(new_version)

    return PromptVersionCreatedResponse(
        id=new_version.id,
        name=new_version.name,
        role=new_version.role.value,
        version=new_version.version,
        is_active=new_version.is_active,
    )
