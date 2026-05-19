from typing import Optional
from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import JSONBType, CreatedAtMixin, UUIDPrimaryKeyMixin


class NewsArticle(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Normalized news article store."""

    __tablename__ = "news_articles"
    __table_args__ = (
        Index("ix_news_articles_published_at", "published_at"),
    )

    provider_article_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    headline: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    body_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    authors_json: Mapped[Optional[list]] = mapped_column(JSONBType, nullable=True)
    tickers_json: Mapped[Optional[list]] = mapped_column(JSONBType, nullable=True)
    sector_tags_json: Mapped[Optional[list]] = mapped_column(JSONBType, nullable=True)
    sentiment_provider: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    raw_json: Mapped[Optional[dict]] = mapped_column(JSONBType, nullable=True)
    # MH-NEWS-02 — provider-supplied supporting citations (research-only).
    citations_json: Mapped[Optional[list]] = mapped_column(JSONBType, nullable=True)
    # MH-NEWS-06 — locked at the DB layer via CHECK constraint to ``research_only``.
    # Drift-lock invariant: news must never escalate to a trading-decision input
    # without an explicit unlock phase. The CHECK constraint is defined in the
    # migration ``v7w8x9y0z1a2_add_mh_news_06_evidence_class``.
    evidence_class: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default="research_only",
        default="research_only",
    )
