"""NewsSymbolLink — many-to-many: news items to asset symbols."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin
from typing import Optional


class NewsSymbolLink(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Association between a news item and an asset symbol."""

    __tablename__ = "news_symbol_links"
    __table_args__ = (
        UniqueConstraint("news_item_id", "asset_id", name="uq_news_symbol_links_item_asset"),
    )

    news_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("news_items.id", ondelete="CASCADE"), nullable=False
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    relevance_score: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    mention_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
