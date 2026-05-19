"""MH-NEWS-06 — Add ``evidence_class`` column with CHECK constraint.

Pure additive migration:

* Adds ``evidence_class VARCHAR(32) NOT NULL DEFAULT 'research_only'`` to
  ``news_articles``. Existing rows are backfilled to ``'research_only'``
  by the server default during the ``ADD COLUMN`` itself.
* Installs a CHECK constraint ``ck_news_articles_evidence_class_research_only``
  that pins the value to ``'research_only'``.

This locks the drift-lock invariant at the database layer: news rows can
never silently escalate into a trading-decision evidence class without an
explicit migration to relax this constraint AND a paired unlock phase.

No production code path consumes this column for trading decisions yet —
MH-NEWS-04 / MH-NEWS-08 will surface it for paper-only advisory + audit.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "v7w8x9y0z1a2"
down_revision = "u6v7w8x9y0z1"
branch_labels = None
depends_on = None


CONSTRAINT_NAME = "ck_news_articles_evidence_class_research_only"


def upgrade() -> None:
    op.add_column(
        "news_articles",
        sa.Column(
            "evidence_class",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'research_only'"),
        ),
    )
    op.create_check_constraint(
        CONSTRAINT_NAME,
        "news_articles",
        "evidence_class = 'research_only'",
    )


def downgrade() -> None:
    op.drop_constraint(CONSTRAINT_NAME, "news_articles", type_="check")
    op.drop_column("news_articles", "evidence_class")
