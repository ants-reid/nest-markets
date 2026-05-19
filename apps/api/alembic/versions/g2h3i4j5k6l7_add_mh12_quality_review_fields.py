"""add_mh12_quality_review_fields

Revision ID: g2h3i4j5k6l7
Revises: f1a2b3c4d5e6
Create Date: 2026-04-27 00:00:00.000000

MH-12: Data Quality Review Dashboard
- Adds review_status and review_notes to market_data_quality_reports
  so analysts can triage flagged outliers directly from the UI.
"""

from alembic import op
import sqlalchemy as sa

revision = "g2h3i4j5k6l7"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "market_data_quality_reports",
        sa.Column(
            "review_status",
            sa.String(length=50),
            nullable=False,
            server_default="unreviewed",
        ),
    )
    op.add_column(
        "market_data_quality_reports",
        sa.Column("review_notes", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("market_data_quality_reports", "review_notes")
    op.drop_column("market_data_quality_reports", "review_status")
