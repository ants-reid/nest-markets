"""add_mh14_ai_backtest_reports

Revision ID: i4j5k6l7m8n9
Revises: h3i4j5k6l7m8
Create Date: 2026-04-28

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "i4j5k6l7m8n9"
down_revision = "h3i4j5k6l7m8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_backtest_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("backtest_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("report_type", sa.String(50), nullable=False, server_default="comparison_review"),
        sa.Column("focus", sa.String(50), nullable=False, server_default="balanced"),
        sa.Column("status", sa.String(50), nullable=False, server_default="completed"),
        sa.Column("model_name", sa.String(100), nullable=True),
        sa.Column("input_summary", postgresql.JSONB, nullable=True),
        sa.Column("report_json", postgresql.JSONB, nullable=True),
        sa.Column("plain_english_summary", sa.Text, nullable=True),
        sa.Column("confidence_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
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
    op.create_index("ix_ai_backtest_reports_backtest_run_id", "ai_backtest_reports", ["backtest_run_id"])
    op.create_index("ix_ai_backtest_reports_status", "ai_backtest_reports", ["status"])


def downgrade() -> None:
    op.drop_index("ix_ai_backtest_reports_status", table_name="ai_backtest_reports")
    op.drop_index("ix_ai_backtest_reports_backtest_run_id", table_name="ai_backtest_reports")
    op.drop_table("ai_backtest_reports")
