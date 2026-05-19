"""MH-NEWS-08-A — ``NewsInDecisionLog`` ORM model (audit-only, no writer yet).

A durable record of one consumed news item per (decision, news_item) pair.
Lock to ``evidence_class = 'research_only'`` is enforced at the database
layer by a CHECK constraint installed in the matching Alembic migration —
news may add caution but must never silently escalate into a trading-decision
evidence class without an explicit unlock phase.

**No production code path writes to this table in this phase.** A future
suffix (MH-NEWS-08-B, paired with MH-NEWS-04 advisory-flag wiring + MH-150
LLMRequestLog correlation) will populate it.

Drift-lock guarantee: read-only model in the current cycle. Worker
behaviour, ``BrokerService.submit_auto_order``, and
``assert_auto_trading_allowed()`` are all unchanged.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import CreatedAtMixin, JSONBType, UUIDPrimaryKeyMixin


class NewsInDecisionLog(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One row per news item consumed by a future decision pipeline.

    All correlation columns are nullable so the future writer can persist
    whatever subset of context is available without forcing schema-level
    coupling to any particular decision pipeline. Snapshot columns capture
    the news item fields verbatim at the moment of consumption so historical
    rows survive upstream deletions.
    """

    __tablename__ = "news_in_decision_log"

    decision_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    decision_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    signal_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    llm_request_log_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    news_article_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    news_item_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    evidence_class: Mapped[str] = mapped_column(
        String(32), nullable=False, default="research_only"
    )
    headline_snapshot: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )
    source_snapshot: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    url_snapshot: Mapped[Optional[str]] = mapped_column(
        String(1000), nullable=True
    )
    published_at_snapshot: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    context_json: Mapped[Optional[dict]] = mapped_column(
        JSONBType, nullable=True
    )
