"""add_mh13_quality_review_polish

Revision ID: h3i4j5k6l7m8
Revises: g2h3i4j5k6l7
Create Date: 2026-04-28 00:00:00.000000

MH-13: Data Quality Review Workflow Polish
- Adds reviewed_by (VARCHAR 255) and reviewed_at (TIMESTAMPTZ) to market_data_quality_reports
- Creates quality_review_audits table (append-only audit trail)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "h3i4j5k6l7m8"
down_revision = "g2h3i4j5k6l7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Extend quality reports with reviewer metadata
    op.add_column(
        "market_data_quality_reports",
        sa.Column("reviewed_by", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "market_data_quality_reports",
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Audit trail table
    op.create_table(
        "quality_review_audits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("report_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("asset_symbol", sa.String(length=50), nullable=False),
        sa.Column("timeframe", sa.String(length=10), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=True),
        sa.Column("previous_status", sa.String(length=50), nullable=True),
        sa.Column("new_status", sa.String(length=50), nullable=False),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_by", sa.String(length=255), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["report_id"],
            ["market_data_quality_reports.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_quality_review_audits_report_id",
        "quality_review_audits",
        ["report_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_quality_review_audits_report_id", table_name="quality_review_audits")
    op.drop_table("quality_review_audits")
    op.drop_column("market_data_quality_reports", "reviewed_at")
    op.drop_column("market_data_quality_reports", "reviewed_by")
