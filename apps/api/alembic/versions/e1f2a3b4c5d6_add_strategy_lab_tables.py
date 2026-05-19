"""add_strategy_lab_tables

Revision ID: e1f2a3b4c5d6
Revises: a1b2c3d4e5f6, d5e6f7a8b9c0, e7f8g9h0i1j2
Create Date: 2026-04-27 00:00:00.000000

MH-06: Strategy Lab Data Contracts
- Adds strategy_configs, backtest_runs, mock_trades, strategy_results,
  equity_curve_points, and drawdown_periods tables.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "e1f2a3b4c5d6"
down_revision = ("a1b2c3d4e5f6", "d5e6f7a8b9c0", "e7f8g9h0i1j2")
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # strategy_configs
    # ------------------------------------------------------------------
    op.create_table(
        "strategy_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("strategy_type", sa.String(length=100), nullable=False),
        sa.Column("asset", sa.String(length=50), nullable=False),
        sa.Column("timeframe", sa.String(length=10), nullable=False),
        sa.Column("parameters", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("risk_settings", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_strategy_configs_asset", "strategy_configs", ["asset"])
    op.create_index("ix_strategy_configs_timeframe", "strategy_configs", ["timeframe"])

    # ------------------------------------------------------------------
    # backtest_runs
    # ------------------------------------------------------------------
    op.create_table(
        "backtest_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="queued"),
        sa.Column("date_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("date_to", sa.DateTime(timezone=True), nullable=False),
        sa.Column("requested_assets", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("requested_timeframes", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("strategy_config_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("starting_capital", sa.Numeric(20, 4), nullable=False, server_default="10000"),
        sa.Column("result_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_backtest_runs_status", "backtest_runs", ["status"])

    # ------------------------------------------------------------------
    # mock_trades
    # ------------------------------------------------------------------
    op.create_table(
        "mock_trades",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("backtest_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("strategy_config_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("asset", sa.String(length=50), nullable=False),
        sa.Column("timeframe", sa.String(length=10), nullable=False),
        sa.Column("side", sa.String(length=10), nullable=False),
        sa.Column("entry_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("entry_price", sa.Numeric(20, 8), nullable=False),
        sa.Column("stop_price", sa.Numeric(20, 8), nullable=True),
        sa.Column("target_price", sa.Numeric(20, 8), nullable=True),
        sa.Column("exit_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("exit_price", sa.Numeric(20, 8), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),
        sa.Column("result", sa.String(length=20), nullable=True),
        sa.Column("pnl_amount", sa.Numeric(20, 4), nullable=True),
        sa.Column("pnl_pct", sa.Numeric(10, 6), nullable=True),
        sa.Column("r_multiple", sa.Numeric(10, 4), nullable=True),
        sa.Column("reason_for_entry", sa.Text(), nullable=True),
        sa.Column("reason_for_exit", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_mock_trades_backtest_run_id", "mock_trades", ["backtest_run_id"])
    op.create_index("ix_mock_trades_strategy_config_id", "mock_trades", ["strategy_config_id"])
    op.create_index("ix_mock_trades_asset", "mock_trades", ["asset"])
    op.create_index("ix_mock_trades_timeframe", "mock_trades", ["timeframe"])

    # ------------------------------------------------------------------
    # strategy_results
    # ------------------------------------------------------------------
    op.create_table(
        "strategy_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("backtest_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("strategy_config_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("asset", sa.String(length=50), nullable=True),
        sa.Column("timeframe", sa.String(length=10), nullable=True),
        sa.Column("total_trades", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("wins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("losses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("breakeven", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("win_rate", sa.Numeric(10, 6), nullable=True),
        sa.Column("average_win", sa.Numeric(20, 4), nullable=True),
        sa.Column("average_loss", sa.Numeric(20, 4), nullable=True),
        sa.Column("profit_factor", sa.Numeric(10, 4), nullable=True),
        sa.Column("expectancy", sa.Numeric(10, 4), nullable=True),
        sa.Column("total_return_pct", sa.Numeric(10, 4), nullable=True),
        sa.Column("max_drawdown_pct", sa.Numeric(10, 4), nullable=True),
        sa.Column("score", sa.Numeric(10, 4), nullable=True),
        sa.Column("metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_strategy_results_backtest_run_id", "strategy_results", ["backtest_run_id"])
    op.create_index("ix_strategy_results_strategy_config_id", "strategy_results", ["strategy_config_id"])
    op.create_index("ix_strategy_results_asset", "strategy_results", ["asset"])

    # ------------------------------------------------------------------
    # equity_curve_points
    # ------------------------------------------------------------------
    op.create_table(
        "equity_curve_points",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("backtest_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("equity", sa.Numeric(20, 4), nullable=False),
        sa.Column("cash", sa.Numeric(20, 4), nullable=True),
        sa.Column("open_pnl", sa.Numeric(20, 4), nullable=True),
        sa.Column("drawdown_pct", sa.Numeric(10, 6), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_equity_curve_points_backtest_run_id", "equity_curve_points", ["backtest_run_id"])
    op.create_index("ix_equity_curve_points_timestamp", "equity_curve_points", ["timestamp"])

    # ------------------------------------------------------------------
    # drawdown_periods
    # ------------------------------------------------------------------
    op.create_table(
        "drawdown_periods",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("backtest_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("trough_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("max_drawdown_pct", sa.Numeric(10, 4), nullable=False),
        sa.Column("duration_candles", sa.Integer(), nullable=True),
        sa.Column("recovered", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_drawdown_periods_backtest_run_id", "drawdown_periods", ["backtest_run_id"])


def downgrade() -> None:
    op.drop_index("ix_drawdown_periods_backtest_run_id", table_name="drawdown_periods")
    op.drop_table("drawdown_periods")

    op.drop_index("ix_equity_curve_points_timestamp", table_name="equity_curve_points")
    op.drop_index("ix_equity_curve_points_backtest_run_id", table_name="equity_curve_points")
    op.drop_table("equity_curve_points")

    op.drop_index("ix_strategy_results_asset", table_name="strategy_results")
    op.drop_index("ix_strategy_results_strategy_config_id", table_name="strategy_results")
    op.drop_index("ix_strategy_results_backtest_run_id", table_name="strategy_results")
    op.drop_table("strategy_results")

    op.drop_index("ix_mock_trades_timeframe", table_name="mock_trades")
    op.drop_index("ix_mock_trades_asset", table_name="mock_trades")
    op.drop_index("ix_mock_trades_strategy_config_id", table_name="mock_trades")
    op.drop_index("ix_mock_trades_backtest_run_id", table_name="mock_trades")
    op.drop_table("mock_trades")

    op.drop_index("ix_backtest_runs_status", table_name="backtest_runs")
    op.drop_table("backtest_runs")

    op.drop_index("ix_strategy_configs_timeframe", table_name="strategy_configs")
    op.drop_index("ix_strategy_configs_asset", table_name="strategy_configs")
    op.drop_table("strategy_configs")
