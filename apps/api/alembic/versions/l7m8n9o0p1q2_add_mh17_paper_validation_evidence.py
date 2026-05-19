"""MH-17 — Add paper_validation_evidence table."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "l7m8n9o0p1q2"
down_revision = "k6l7m8n9o0p1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "paper_validation_evidence",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "paper_validation_plan_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("paper_validation_plans.id"),
            nullable=False,
        ),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("source_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("confidence", sa.String(20), nullable=False, server_default="manual"),
        sa.Column("asset", sa.String(50), nullable=True),
        sa.Column("timeframe", sa.String(10), nullable=True),
        sa.Column("side", sa.String(20), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("entry_price", sa.Numeric(18, 8), nullable=True),
        sa.Column("exit_price", sa.Numeric(18, 8), nullable=True),
        sa.Column("pnl_amount", sa.Numeric(18, 8), nullable=True),
        sa.Column("pnl_pct", sa.Numeric(12, 6), nullable=True),
        sa.Column("r_multiple", sa.Numeric(10, 4), nullable=True),
        sa.Column("result", sa.String(20), nullable=False, server_default="unknown"),
        sa.Column("payload", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "included_in_metrics",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_index(
        "ix_paper_validation_evidence_plan_id",
        "paper_validation_evidence",
        ["paper_validation_plan_id"],
    )
    op.create_index(
        "ix_paper_validation_evidence_source",
        "paper_validation_evidence",
        ["source_type", "source_id"],
    )
    op.create_index(
        "ix_paper_validation_evidence_included",
        "paper_validation_evidence",
        ["paper_validation_plan_id", "included_in_metrics"],
    )


def downgrade() -> None:
    op.drop_index("ix_paper_validation_evidence_included", "paper_validation_evidence")
    op.drop_index("ix_paper_validation_evidence_source", "paper_validation_evidence")
    op.drop_index("ix_paper_validation_evidence_plan_id", "paper_validation_evidence")
    op.drop_table("paper_validation_evidence")
