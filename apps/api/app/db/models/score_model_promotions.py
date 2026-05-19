"""ScoreModelPromotion — promotion audit trail."""

from __future__ import annotations

import uuid
from typing import Optional
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.enums import PromotionType
from app.db.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class ScoreModelPromotion(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Audit record for every model promotion event."""

    __tablename__ = "score_model_promotions"

    from_model_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("score_model_registry.id", ondelete="SET NULL"), nullable=True
    )
    to_model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("score_model_registry.id", ondelete="RESTRICT"), nullable=False
    )
    promotion_type: Mapped[PromotionType] = mapped_column(
        Enum(PromotionType, name="promotion_type_enum"), nullable=False
    )
    promoted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    promoted_by: Mapped[Optional[str]] = mapped_column(nullable=True)
    approval_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rollback_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
