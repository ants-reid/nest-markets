"""MH-36 — Add paper_recommendations table for strategy-to-paper drafting."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "m8n9o0p1q2r3"
down_revision = "l7m8n9o0p1q2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "paper_recommendations",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "signal_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("signals.id"),
            nullable=True,
        ),
        sa.Column(
            "model_version_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("model_versions.id"),
            nullable=True,
        ),
        sa.Column("ticker", sa.String(20), nullable=False),
        sa.Column("side", sa.String(20), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 8), nullable=False),
        sa.Column("order_type", sa.String(50), nullable=False),
        sa.Column("limit_price", sa.Numeric(18, 8), nullable=True),
        sa.Column("confidence", sa.Numeric(10, 4), nullable=True),
        sa.Column("risk_score", sa.Numeric(10, 4), nullable=True),
        sa.Column("estimated_notional", sa.Numeric(18, 8), nullable=True),
        sa.Column("rationale", sa.Text, nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft"),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", sa.String(100), nullable=True),
        sa.Column("review_notes", sa.Text, nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paper_order_ids", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("source_metadata", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_index(
        "ix_paper_recommendations_signal",
        "paper_recommendations",
        ["signal_id"],
    )
    op.create_index(
        "ix_paper_recommendations_model",
        "paper_recommendations",
        ["model_version_id"],
    )
    op.create_index(
        "ix_paper_recommendations_status_ts",
        "paper_recommendations",
        ["status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_paper_recommendations_status_ts", "paper_recommendations")
    op.drop_index("ix_paper_recommendations_model", "paper_recommendations")
    op.drop_index("ix_paper_recommendations_signal", "paper_recommendations")
    op.drop_table("paper_recommendations")
