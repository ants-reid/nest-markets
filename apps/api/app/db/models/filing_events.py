"""FilingEvent — SEC filings and earnings events."""

from __future__ import annotations

import uuid
from typing import Optional
from datetime import date

from sqlalchemy import Date, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.enums import FilingEventType
from app.db.models.mixins import CreatedAtMixin, JSONBType, UUIDPrimaryKeyMixin


class FilingEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """SEC filing or earnings event associated with an asset."""

    __tablename__ = "filing_events"
    __table_args__ = (
        UniqueConstraint("asset_id", "event_type", "event_date",
                         name="uq_filing_events_asset_type_date"),
    )

    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[FilingEventType] = mapped_column(
        Enum(FilingEventType, name="filing_event_type_enum"), nullable=False
    )
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    filing_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    extra_metadata: Mapped[Optional[dict]] = mapped_column(JSONBType, nullable=True)
