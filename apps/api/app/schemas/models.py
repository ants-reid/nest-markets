"""Pydantic schemas for model registry and governance endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ModelVersionResponse(BaseModel):
    """Public representation of a ModelVersion row."""

    id: uuid.UUID
    provider_name: str
    model_name: str
    alias_name: str | None = None
    temperature: float | None = None
    top_p: float | None = None
    max_output_tokens: int | None = None
    reasoning_level: str | None = None
    supports_structured_output: bool
    is_active: bool
    notes: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ModelVersionListResponse(BaseModel):
    items: list[ModelVersionResponse]
    total: int


class CreateModelVersionRequest(BaseModel):
    provider_name: str = Field(..., min_length=1, max_length=100)
    model_name: str = Field(..., min_length=1, max_length=255)
    alias_name: str | None = Field(None, max_length=255)
    temperature: float | None = Field(None, ge=0.0, le=2.0)
    top_p: float | None = Field(None, ge=0.0, le=1.0)
    max_output_tokens: int | None = Field(None, ge=1)
    reasoning_level: str | None = Field(None, max_length=50)
    supports_structured_output: bool = True
    notes: str | None = Field(None, max_length=1000)


class UpdateModelVersionRequest(BaseModel):
    alias_name: str | None = Field(None, max_length=255)
    temperature: float | None = Field(None, ge=0.0, le=2.0)
    notes: str | None = Field(None, max_length=1000)


class PromoteModelVersionRequest(BaseModel):
    model_version_id: uuid.UUID


class ModelGovernanceActionResponse(BaseModel):
    """Generic response for promote/rollback/deactivate operations."""

    action: str
    model_version_id: uuid.UUID
    is_active: bool
    message: str
