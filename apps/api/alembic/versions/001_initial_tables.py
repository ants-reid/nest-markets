"""Initial migration - create all Phase 2 tables."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "001_initial_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all Phase 2 database tables."""
    
    # Create assets table
    op.create_table(
        "assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("asset_type", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol", name="uq_assets_symbol"),
        sa.UniqueConstraint("symbol", "asset_type", name="uq_symbol_type"),
    )
    op.create_index("ix_assets_is_active", "assets", ["is_active"])
    op.create_index("ix_assets_symbol", "assets", ["symbol"])

    # Create bars table
    op.create_table(
        "bars",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("timeframe", sa.String(10), nullable=False),
        sa.Column("open_price", sa.Float(), nullable=False),
        sa.Column("high_price", sa.Float(), nullable=False),
        sa.Column("low_price", sa.Float(), nullable=False),
        sa.Column("close_price", sa.Float(), nullable=False),
        sa.Column("volume", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_id", "timestamp", "timeframe", name="uq_asset_bar"),
    )
    op.create_index("ix_bars_asset_id", "bars", ["asset_id"])
    op.create_index("ix_bars_timestamp", "bars", ["timestamp"])
    op.create_index("ix_bars_timeframe", "bars", ["timeframe"])

    # Create quotes table
    op.create_table(
        "quotes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("bid_price", sa.Float(), nullable=False),
        sa.Column("bid_size", sa.Float(), nullable=False),
        sa.Column("ask_price", sa.Float(), nullable=False),
        sa.Column("ask_size", sa.Float(), nullable=False),
        sa.Column("spread_bps", sa.Float(), nullable=True),
        sa.Column("mid_price", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_quotes_asset_id", "quotes", ["asset_id"])
    op.create_index("ix_quotes_timestamp", "quotes", ["timestamp"])

    # Create news_articles table
    op.create_table(
        "news_articles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("headline", sa.String(500), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column("url", sa.String(500), nullable=True),
        sa.Column("sentiment", sa.String(20), nullable=True),
        sa.Column("relevance_score", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_news_articles_asset_id", "news_articles", ["asset_id"])
    op.create_index("ix_news_articles_published_at", "news_articles", ["published_at"])

    # Create feature_snapshots table
    op.create_table(
        "feature_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rsi_14", sa.Float(), nullable=True),
        sa.Column("sma_20", sa.Float(), nullable=True),
        sa.Column("sma_50", sa.Float(), nullable=True),
        sa.Column("sma_200", sa.Float(), nullable=True),
        sa.Column("atr_14", sa.Float(), nullable=True),
        sa.Column("bb_upper", sa.Float(), nullable=True),
        sa.Column("bb_lower", sa.Float(), nullable=True),
        sa.Column("bb_middle", sa.Float(), nullable=True),
        sa.Column("volatility", sa.Float(), nullable=True),
        sa.Column("trend_direction", sa.String(20), nullable=True),
        sa.Column("trend_strength", sa.Float(), nullable=True),
        sa.Column("market_quality", sa.String(20), nullable=True),
        sa.Column("volume_ratio", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_feature_snapshots_asset_id", "feature_snapshots", ["asset_id"])
    op.create_index("ix_feature_snapshots_timestamp", "feature_snapshots", ["timestamp"])

    # Create prompt_versions table
    op.create_table(
        "prompt_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("version", sa.String(20), nullable=False),
        sa.Column("is_active", sa.String(20), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("user_template", sa.Text(), nullable=False),
        sa.Column("schema_json", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_prompt_versions_is_active", "prompt_versions", ["is_active"])
    op.create_index("ix_prompt_versions_name", "prompt_versions", ["name"])
    op.create_index("ix_prompt_versions_role", "prompt_versions", ["role"])

    # Create model_versions table
    op.create_table(
        "model_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("model_type", sa.String(50), nullable=False),
        sa.Column("version", sa.String(20), nullable=False),
        sa.Column("is_active", sa.String(20), nullable=False),
        sa.Column("model_path", sa.String(500), nullable=True),
        sa.Column("model_hash", sa.String(64), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_model_versions_is_active", "model_versions", ["is_active"])
    op.create_index("ix_model_versions_name", "model_versions", ["name"])

    # Create execution_modes table
    op.create_table(
        "execution_modes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.String(20), nullable=False),
        sa.Column("requires_approval", sa.String(20), nullable=False),
        sa.Column("allows_live_orders", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_execution_modes_name"),
    )
    op.create_index("ix_execution_modes_is_active", "execution_modes", ["is_active"])

    # Create risk_profiles table
    op.create_table(
        "risk_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.String(20), nullable=False),
        sa.Column("max_open_positions", sa.Float(), nullable=False),
        sa.Column("max_correlated_bucket_exposure", sa.Float(), nullable=False),
        sa.Column("max_risk_per_trade_pct", sa.Float(), nullable=False),
        sa.Column("max_daily_drawdown_pct", sa.Float(), nullable=False),
        sa.Column("min_confidence", sa.Float(), nullable=False),
        sa.Column("min_signal_score", sa.Float(), nullable=False),
        sa.Column("max_spread_bps_fx", sa.Float(), nullable=False),
        sa.Column("max_spread_bps_equity", sa.Float(), nullable=False),
        sa.Column("cooldown_after_3_losses_min", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_risk_profiles_name"),
    )
    op.create_index("ix_risk_profiles_is_active", "risk_profiles", ["is_active"])

    # Create execution_policies table
    op.create_table(
        "execution_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.String(20), nullable=False),
        sa.Column("execution_mode_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("risk_profile_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("routing_logic", sa.Text(), nullable=True),
        sa.Column("conditions", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["execution_mode_id"], ["execution_modes.id"], ),
        sa.ForeignKeyConstraint(["risk_profile_id"], ["risk_profiles.id"], ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_execution_policies_name"),
    )
    op.create_index("ix_execution_policies_is_active", "execution_policies", ["is_active"])

    # Create signals table
    op.create_table(
        "signals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("prompt_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("direction", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("signal_score", sa.Float(), nullable=False),
        sa.Column("catalyst", sa.String(100), nullable=True),
        sa.Column("catalyst_strength", sa.String(20), nullable=True),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("structured_output", sa.Text(), nullable=True),
        sa.Column("is_actionable", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ),
        sa.ForeignKeyConstraint(["prompt_version_id"], ["prompt_versions.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_signals_asset_id", "signals", ["asset_id"])
    op.create_index("ix_signals_timestamp", "signals", ["timestamp"])

    # Create risk_decisions table
    op.create_table(
        "risk_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("signal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("risk_profile_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved", sa.String(20), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("capital_available", sa.Float(), nullable=True),
        sa.Column("position_limit", sa.Float(), nullable=True),
        sa.Column("drawdown_limit", sa.Float(), nullable=True),
        sa.Column("spread_check", sa.String(20), nullable=True),
        sa.Column("market_quality_check", sa.String(20), nullable=True),
        sa.Column("correlation_check", sa.String(20), nullable=True),
        sa.Column("blocking_rule", sa.String(100), nullable=True),
        sa.Column("cooldown_active", sa.String(20), nullable=False),
        sa.Column("kill_switch_active", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["risk_profile_id"], ["risk_profiles.id"], ),
        sa.ForeignKeyConstraint(["signal_id"], ["signals.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_risk_decisions_signal_id", "risk_decisions", ["signal_id"])
    op.create_index("ix_risk_decisions_timestamp", "risk_decisions", ["timestamp"])

    # Create paper_orders table
    op.create_table(
        "paper_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("risk_decision_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("direction", sa.String(20), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("limit_price", sa.Float(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("filled_quantity", sa.Float(), nullable=False),
        sa.Column("filled_price", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("filled_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ),
        sa.ForeignKeyConstraint(["risk_decision_id"], ["risk_decisions.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_paper_orders_asset_id", "paper_orders", ["asset_id"])
    op.create_index("ix_paper_orders_risk_decision_id", "paper_orders", ["risk_decision_id"])
    op.create_index("ix_paper_orders_timestamp", "paper_orders", ["timestamp"])

    # Create paper_fills table
    op.create_table(
        "paper_fills",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("paper_order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("commission", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["paper_order_id"], ["paper_orders.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_paper_fills_paper_order_id", "paper_fills", ["paper_order_id"])
    op.create_index("ix_paper_fills_timestamp", "paper_fills", ["timestamp"])

    # Create positions table
    op.create_table(
        "positions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("execution_mode", sa.String(20), nullable=False),
        sa.Column("direction", sa.String(20), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("avg_entry_price", sa.Float(), nullable=False),
        sa.Column("current_price", sa.Float(), nullable=True),
        sa.Column("unrealized_pnl", sa.Float(), nullable=True),
        sa.Column("unrealized_pnl_pct", sa.Float(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_positions_asset_id", "positions", ["asset_id"])
    op.create_index("ix_positions_timestamp", "positions", ["timestamp"])

    # Create pnl_snapshots table
    op.create_table(
        "pnl_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("execution_mode", sa.String(20), nullable=False),
        sa.Column("total_pnl", sa.Float(), nullable=False),
        sa.Column("realized_pnl", sa.Float(), nullable=False),
        sa.Column("unrealized_pnl", sa.Float(), nullable=False),
        sa.Column("daily_pnl", sa.Float(), nullable=False),
        sa.Column("daily_return_pct", sa.Float(), nullable=False),
        sa.Column("account_value", sa.Float(), nullable=False),
        sa.Column("cash_available", sa.Float(), nullable=False),
        sa.Column("max_drawdown_pct", sa.Float(), nullable=False),
        sa.Column("num_open_positions", sa.Float(), nullable=False),
        sa.Column("num_trades_today", sa.Float(), nullable=False),
        sa.Column("num_winning_trades", sa.Float(), nullable=False),
        sa.Column("num_losing_trades", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("timestamp", name="uq_pnl_snapshots_timestamp"),
    )
    op.create_index("ix_pnl_snapshots_execution_mode", "pnl_snapshots", ["execution_mode"])
    op.create_index("ix_pnl_snapshots_timestamp", "pnl_snapshots", ["timestamp"])

    # Create eval_cases table
    op.create_table(
        "eval_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("assets", sa.Text(), nullable=True),
        sa.Column("parameters", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_eval_cases_name"),
    )

    # Create eval_runs table
    op.create_table(
        "eval_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("eval_case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("prompt_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("model_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("total_return_pct", sa.Float(), nullable=False),
        sa.Column("sharpe_ratio", sa.Float(), nullable=True),
        sa.Column("max_drawdown_pct", sa.Float(), nullable=False),
        sa.Column("win_rate", sa.Float(), nullable=True),
        sa.Column("num_trades", sa.Float(), nullable=False),
        sa.Column("results", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["eval_case_id"], ["eval_cases.id"], ),
        sa.ForeignKeyConstraint(["model_version_id"], ["model_versions.id"], ),
        sa.ForeignKeyConstraint(["prompt_version_id"], ["prompt_versions.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_eval_runs_eval_case_id", "eval_runs", ["eval_case_id"])

    # Create approval_requests table
    op.create_table(
        "approval_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("risk_decision_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("approved_by", sa.String(100), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["risk_decision_id"], ["risk_decisions.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_approval_requests_risk_decision_id", "approval_requests", ["risk_decision_id"])
    op.create_index("ix_approval_requests_timestamp", "approval_requests", ["timestamp"])

    # Create audit_logs table
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("actor", sa.String(50), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("risk_level", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_entity_id", "audit_logs", ["entity_id"])
    op.create_index("ix_audit_logs_event_type", "audit_logs", ["event_type"])
    op.create_index("ix_audit_logs_timestamp", "audit_logs", ["timestamp"])


def downgrade() -> None:
    """Downgrade migration - drop all tables."""
    op.drop_index("ix_audit_logs_timestamp", table_name="audit_logs")
    op.drop_index("ix_audit_logs_event_type", table_name="audit_logs")
    op.drop_index("ix_audit_logs_entity_id", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("ix_approval_requests_timestamp", table_name="approval_requests")
    op.drop_index("ix_approval_requests_risk_decision_id", table_name="approval_requests")
    op.drop_table("approval_requests")

    op.drop_index("ix_eval_runs_eval_case_id", table_name="eval_runs")
    op.drop_table("eval_runs")
    op.drop_table("eval_cases")

    op.drop_index("ix_pnl_snapshots_timestamp", table_name="pnl_snapshots")
    op.drop_index("ix_pnl_snapshots_execution_mode", table_name="pnl_snapshots")
    op.drop_table("pnl_snapshots")

    op.drop_index("ix_positions_timestamp", table_name="positions")
    op.drop_index("ix_positions_asset_id", table_name="positions")
    op.drop_table("positions")

    op.drop_index("ix_paper_fills_timestamp", table_name="paper_fills")
    op.drop_index("ix_paper_fills_paper_order_id", table_name="paper_fills")
    op.drop_table("paper_fills")

    op.drop_index("ix_paper_orders_timestamp", table_name="paper_orders")
    op.drop_index("ix_paper_orders_risk_decision_id", table_name="paper_orders")
    op.drop_index("ix_paper_orders_asset_id", table_name="paper_orders")
    op.drop_table("paper_orders")

    op.drop_index("ix_risk_decisions_timestamp", table_name="risk_decisions")
    op.drop_index("ix_risk_decisions_signal_id", table_name="risk_decisions")
    op.drop_table("risk_decisions")

    op.drop_index("ix_signals_timestamp", table_name="signals")
    op.drop_index("ix_signals_asset_id", table_name="signals")
    op.drop_table("signals")

    op.drop_index("ix_execution_policies_is_active", table_name="execution_policies")
    op.drop_table("execution_policies")

    op.drop_index("ix_risk_profiles_is_active", table_name="risk_profiles")
    op.drop_table("risk_profiles")

    op.drop_index("ix_execution_modes_is_active", table_name="execution_modes")
    op.drop_table("execution_modes")

    op.drop_index("ix_model_versions_name", table_name="model_versions")
    op.drop_index("ix_model_versions_is_active", table_name="model_versions")
    op.drop_table("model_versions")

    op.drop_index("ix_prompt_versions_role", table_name="prompt_versions")
    op.drop_index("ix_prompt_versions_name", table_name="prompt_versions")
    op.drop_index("ix_prompt_versions_is_active", table_name="prompt_versions")
    op.drop_table("prompt_versions")

    op.drop_index("ix_feature_snapshots_timestamp", table_name="feature_snapshots")
    op.drop_index("ix_feature_snapshots_asset_id", table_name="feature_snapshots")
    op.drop_table("feature_snapshots")

    op.drop_index("ix_news_articles_published_at", table_name="news_articles")
    op.drop_index("ix_news_articles_asset_id", table_name="news_articles")
    op.drop_table("news_articles")

    op.drop_index("ix_quotes_timestamp", table_name="quotes")
    op.drop_index("ix_quotes_asset_id", table_name="quotes")
    op.drop_table("quotes")

    op.drop_index("ix_bars_timeframe", table_name="bars")
    op.drop_index("ix_bars_timestamp", table_name="bars")
    op.drop_index("ix_bars_asset_id", table_name="bars")
    op.drop_table("bars")

    op.drop_index("ix_assets_symbol", table_name="assets")
    op.drop_index("ix_assets_is_active", table_name="assets")
    op.drop_table("assets")
