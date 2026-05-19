"""add_mh15_baseline_candidates

Revision ID: j5k6l7m8n9o0
Revises: i4j5k6l7m8n9
Create Date: 2026-04-28 07:45:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "j5k6l7m8n9o0"
down_revision = "i4j5k6l7m8n9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "baseline_candidates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("backtest_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("strategy_config_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ai_backtest_report_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("asset", sa.String(50), nullable=False),
        sa.Column("timeframe", sa.String(10), nullable=False),
        sa.Column("strategy_type", sa.String(100), nullable=False),
        sa.Column("parameters", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("metrics", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(50), nullable=False, server_default="watchlist_candidate"),
        sa.Column("review_notes", sa.Text, nullable=True),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("reviewed_by", sa.String(255), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_baseline_candidates_backtest_run_id", "baseline_candidates", ["backtest_run_id"])
    op.create_index("ix_baseline_candidates_strategy_config_id", "baseline_candidates", ["strategy_config_id"])
    op.create_index("ix_baseline_candidates_ai_backtest_report_id", "baseline_candidates", ["ai_backtest_report_id"])
    op.create_index("ix_baseline_candidates_asset", "baseline_candidates", ["asset"])
    op.create_index("ix_baseline_candidates_timeframe", "baseline_candidates", ["timeframe"])
    op.create_index("ix_baseline_candidates_strategy_type", "baseline_candidates", ["strategy_type"])
    op.create_index("ix_baseline_candidates_status", "baseline_candidates", ["status"])


def downgrade() -> None:
    op.drop_index("ix_baseline_candidates_status", table_name="baseline_candidates")
    op.drop_index("ix_baseline_candidates_strategy_type", table_name="baseline_candidates")
    op.drop_index("ix_baseline_candidates_timeframe", table_name="baseline_candidates")
    op.drop_index("ix_baseline_candidates_asset", table_name="baseline_candidates")
    op.drop_index("ix_baseline_candidates_ai_backtest_report_id", table_name="baseline_candidates")
    op.drop_index("ix_baseline_candidates_strategy_config_id", table_name="baseline_candidates")
    op.drop_index("ix_baseline_candidates_backtest_run_id", table_name="baseline_candidates")
    op.drop_table("baseline_candidates")
