"""add_mh16_paper_validation_plans

Revision ID: k6l7m8n9o0p1
Revises: j5k6l7m8n9o0
Create Date: 2026-04-28 10:10:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "k6l7m8n9o0p1"
down_revision = "j5k6l7m8n9o0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "paper_validation_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("baseline_candidate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("backtest_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("strategy_config_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("required_trades", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("minimum_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("target_profit_factor", sa.Numeric(12, 6), nullable=True),
        sa.Column("max_drawdown_pct", sa.Numeric(12, 6), nullable=True),
        sa.Column("max_daily_loss_pct", sa.Numeric(12, 6), nullable=True),
        sa.Column("starting_paper_capital", sa.Numeric(18, 4), nullable=False, server_default="200000"),
        sa.Column("backtest_metrics", postgresql.JSONB, nullable=True),
        sa.Column("paper_metrics", postgresql.JSONB, nullable=True),
        sa.Column("progress", postgresql.JSONB, nullable=True),
        sa.Column("pass_fail_reasons", postgresql.JSONB, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("reviewed_by", sa.String(255), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_index("ix_paper_validation_plans_baseline_candidate_id", "paper_validation_plans", ["baseline_candidate_id"])
    op.create_index("ix_paper_validation_plans_backtest_run_id", "paper_validation_plans", ["backtest_run_id"])
    op.create_index("ix_paper_validation_plans_strategy_config_id", "paper_validation_plans", ["strategy_config_id"])
    op.create_index("ix_paper_validation_plans_status", "paper_validation_plans", ["status"])

    op.create_table(
        "paper_validation_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("paper_validation_plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["paper_validation_plan_id"], ["paper_validation_plans.id"]),
    )
    op.create_index("ix_paper_validation_events_paper_validation_plan_id", "paper_validation_events", ["paper_validation_plan_id"])


def downgrade() -> None:
    op.drop_index("ix_paper_validation_events_paper_validation_plan_id", table_name="paper_validation_events")
    op.drop_table("paper_validation_events")

    op.drop_index("ix_paper_validation_plans_status", table_name="paper_validation_plans")
    op.drop_index("ix_paper_validation_plans_strategy_config_id", table_name="paper_validation_plans")
    op.drop_index("ix_paper_validation_plans_backtest_run_id", table_name="paper_validation_plans")
    op.drop_index("ix_paper_validation_plans_baseline_candidate_id", table_name="paper_validation_plans")
    op.drop_table("paper_validation_plans")
