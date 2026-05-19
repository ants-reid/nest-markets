"""Read-only prompt versioning route — lists and serves versioned prompt files."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.prompt_version import PromptVersion
from app.db.session import get_db_session
from app.services.prompt_version_service import _infer_role

router = APIRouter(prefix="/prompts", tags=["prompts"])

_PROMPTS_BASE = Path(__file__).resolve().parents[2] / "prompts"
_ALLOWED_SUBDIRS = {"system", "user", "schemas"}


def _collect_prompt_names() -> list[str]:
    """Walk system/ and user/ subdirectories and return relative prompt paths."""
    names: list[str] = []
    for subdir in ("system", "user"):
        target = _PROMPTS_BASE / subdir
        if target.is_dir():
            for f in sorted(target.iterdir()):
                if f.is_file() and f.suffix in {".md", ".txt", ".json"}:
                    names.append(f"{subdir}/{f.name}")
    return names


class PromptListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prompts: list[str]


class PromptDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    content: str


class PromptVersionHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Any
    name: str
    role: str
    version: str
    is_active: bool
    file_hash: str | None
    created_at: datetime


@router.get("", response_model=PromptListResponse)
def list_prompts() -> PromptListResponse:
    """Return the names of all versioned prompt files (system/ and user/)."""
    return PromptListResponse(prompts=_collect_prompt_names())


@router.get("/{subdir}/{filename}/history", response_model=list[PromptVersionHistoryItem])
def get_prompt_history(
    subdir: str,
    filename: str,
    session: Annotated[Session, Depends(get_db_session)],
) -> list[PromptVersionHistoryItem]:
    """Return the version history for a specific prompt file."""
    if subdir not in _ALLOWED_SUBDIRS:
        raise HTTPException(status_code=404, detail="Prompt not found.")

    safe_filename = Path(filename).name
    if safe_filename != filename or ".." in filename:
        raise HTTPException(status_code=404, detail="Prompt not found.")

    role = _infer_role(safe_filename)
    if role is None:
        raise HTTPException(status_code=404, detail="Prompt role unrecognised.")

    rows = (
        session.execute(
            select(PromptVersion)
            .where(PromptVersion.role == role)
            .order_by(PromptVersion.created_at.desc())
        )
        .scalars()
        .all()
    )
    if not rows:
        raise HTTPException(status_code=404, detail="No version history found for this prompt.")

    return [
        PromptVersionHistoryItem(
            id=r.id,
            name=r.name,
            role=r.role.value if hasattr(r.role, "value") else str(r.role),
            version=r.version,
            is_active=r.is_active,
            file_hash=(r.schema_json or {}).get("hash"),
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.get("/{subdir}/{filename}", response_model=PromptDetailResponse)
def get_prompt(subdir: str, filename: str) -> PromptDetailResponse:
    """Return the content of a single prompt file by subdir and filename."""
    if subdir not in _ALLOWED_SUBDIRS:
        raise HTTPException(status_code=404, detail="Prompt not found.")

    safe_filename = Path(filename).name
    if safe_filename != filename or ".." in filename:
        raise HTTPException(status_code=404, detail="Prompt not found.")

    path = _PROMPTS_BASE / subdir / safe_filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Prompt not found.")

    return PromptDetailResponse(
        name=f"{subdir}/{safe_filename}",
        content=path.read_text(encoding="utf-8"),
    )
