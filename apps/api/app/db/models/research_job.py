"""ResearchJob — persisted lifecycle for Data Centre import and quality jobs."""

from __future__ import annotations

import uuid
from typing import Optional
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import JSONBType, TimestampMixin, UUIDPrimaryKeyMixin


class ResearchJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Tracks one orchestrated research job execution."""

    __tablename__ = "research_jobs"

    job_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="queued", index=True)
    requested_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    request_payload: Mapped[dict] = mapped_column(JSONBType, nullable=False)
    result_payload: Mapped[Optional[dict]] = mapped_column(JSONBType, nullable=True)
    progress_current: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    progress_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    progress_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_of_job_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
