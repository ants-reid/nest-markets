"""NewsItem — news articles from market data providers."""

from __future__ import annotations

from typing import Optional
from datetime import datetime

from sqlalchemy import DateTime, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import CreatedAtMixin, JSONBType, UUIDPrimaryKeyMixin


class NewsItem(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """News headline and article from a data provider."""

    __tablename__ = "news_items"
    __table_args__ = (
        UniqueConstraint("external_id", "source", name="uq_news_items_external_source"),
        Index("ix_news_items_published_at", "published_at"),
    )

    external_id: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    headline: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    full_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ingested_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sentiment_score: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    urgency_score: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    extra_metadata: Mapped[Optional[dict]] = mapped_column(JSONBType, nullable=True)
