"""MH-NEWS-02 — Add citations_json column to news_articles.

Pure additive nullable JSONB column. Backfill is unnecessary because the
column accepts NULL and existing rows have no provider-supplied citations.
The column is consumption-only; no production code path queries it yet
(MH-NEWS-04 / MH-NEWS-08 will).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "u6v7w8x9y0z1"
down_revision = "t5u6v7w8x9y0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "news_articles",
        sa.Column(
            "citations_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("news_articles", "citations_json")
