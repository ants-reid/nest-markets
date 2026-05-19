"""MH-NEWS-08-A — Add ``news_in_decision_log`` audit table.

Pure additive migration. Creates a new ``news_in_decision_log`` table to
durably record every news item consumed by a (future) decision pipeline.
**No code path writes to this table in this migration.** A future suffix
(MH-NEWS-08-B, paired with MH-NEWS-04 advisory-flag wiring + MH-150
LLMRequestLog correlation) will populate it; until then the table sits
idle (always empty).

Drift-lock guarantee:
* Adds a new table only — does not modify any existing table.
* No FK declared into ``news_articles`` / ``news_items`` on purpose: the
  audit row records the news item snapshot fields directly so historical
  rows survive provider-side or upstream deletions.
* Does not change worker behaviour, broker submit semantics, or any gate.
* Auto-paper enforcement, auto trading, and live trading remain OFF.
* ``assert_auto_trading_allowed()`` is unchanged and still blocks auto intent.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "f6a7b8c9d0e1"
down_revision = "z0a1b2c3d4e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "news_in_decision_log",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "decision_kind",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "decision_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "signal_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "llm_request_log_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "news_article_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "news_item_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "evidence_class",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'research_only'"),
        ),
        sa.Column(
            "headline_snapshot",
            sa.String(length=500),
            nullable=True,
        ),
        sa.Column(
            "source_snapshot",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "url_snapshot",
            sa.String(length=1000),
            nullable=True,
        ),
        sa.Column(
            "published_at_snapshot",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "context_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.create_check_constraint(
        "ck_news_in_decision_log_evidence_class_research_only",
        "news_in_decision_log",
        "evidence_class = 'research_only'",
    )
    op.create_index(
        "ix_news_in_decision_log_created_at",
        "news_in_decision_log",
        ["created_at"],
    )
    op.create_index(
        "ix_news_in_decision_log_decision_kind",
        "news_in_decision_log",
        ["decision_kind"],
    )
    op.create_index(
        "ix_news_in_decision_log_signal_id",
        "news_in_decision_log",
        ["signal_id"],
    )
    op.create_index(
        "ix_news_in_decision_log_news_article_id",
        "news_in_decision_log",
        ["news_article_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_news_in_decision_log_news_article_id",
        table_name="news_in_decision_log",
    )
    op.drop_index(
        "ix_news_in_decision_log_signal_id",
        table_name="news_in_decision_log",
    )
    op.drop_index(
        "ix_news_in_decision_log_decision_kind",
        table_name="news_in_decision_log",
    )
    op.drop_index(
        "ix_news_in_decision_log_created_at",
        table_name="news_in_decision_log",
    )
    op.drop_constraint(
        "ck_news_in_decision_log_evidence_class_research_only",
        "news_in_decision_log",
        type_="check",
    )
    op.drop_table("news_in_decision_log")
