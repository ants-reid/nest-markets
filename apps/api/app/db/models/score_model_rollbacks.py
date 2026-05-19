"""ScoreModelRollback — rollback audit trail."""

from __future__ import annotations

import uuid
from typing import Optional
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.enums import RollbackTrigger
from app.db.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class ScoreModelRollback(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Audit record for every model rollback event."""

    __tablename__ = "score_model_rollbacks"

    from_model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("score_model_registry.id", ondelete="RESTRICT"), nullable=False
    )
    to_model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("score_model_registry.id", ondelete="RESTRICT"), nullable=False
    )
    rollback_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    rollback_trigger: Mapped[RollbackTrigger] = mapped_column(
        Enum(RollbackTrigger, name="rollback_trigger_enum"), nullable=False
    )
    triggered_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    rollback_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
