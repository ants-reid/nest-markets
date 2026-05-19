"""Paper validation event timeline model for MH-16."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import CreatedAtMixin, JSONBType, UUIDPrimaryKeyMixin
from typing import Optional


class PaperValidationEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Immutable event row for plan lifecycle/audit visibility."""

    __tablename__ = "paper_validation_events"

    paper_validation_plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("paper_validation_plans.id"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[Optional[dict]] = mapped_column(JSONBType, nullable=True)
