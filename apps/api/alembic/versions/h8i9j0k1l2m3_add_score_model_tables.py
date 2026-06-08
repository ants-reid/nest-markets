"""add_score_model_tables

Revision ID: h8i9j0k1l2m3
Revises: g7h8i9j0k1l2
Create Date: 2026-06-08 18:10:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "h8i9j0k1l2m3"
down_revision = "g7h8i9j0k1l2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    model_registry_status_enum = postgresql.ENUM(
        "candidate",
        "active",
        "archived",
        "failed",
        name="model_registry_status_enum",
        create_type=False,
    )
    promotion_type_enum = postgresql.ENUM(
        "candidate_to_active",
        "active_to_active",
        name="promotion_type_enum",
        create_type=False,
    )
    rollback_trigger_enum = postgresql.ENUM(
        "automatic",
        "manual",
        "performance_degradation",
        name="rollback_trigger_enum",
        create_type=False,
    )

    bind = op.get_bind()
    model_registry_status_enum.create(bind, checkfirst=True)
    promotion_type_enum.create(bind, checkfirst=True)
    rollback_trigger_enum.create(bind, checkfirst=True)

    op.create_table(
        "score_model_registry",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("strategy_bucket", sa.String(length=100), nullable=False),
        sa.Column("asset_class", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("training_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("trained_by", sa.String(length=255), nullable=True),
        sa.Column("status", model_registry_status_enum, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("promoted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("promoted_by", sa.String(length=255), nullable=True),
        sa.UniqueConstraint(
            "strategy_bucket",
            "asset_class",
            "version_number",
            name="uq_smr_bucket_asset_version",
        ),
    )
    op.create_index("ix_smr_status", "score_model_registry", ["status"])
    op.create_index("ix_smr_is_active", "score_model_registry", ["is_active"])

    op.create_table(
        "score_model_evaluations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("model_registry_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evaluation_run_id", sa.String(length=255), nullable=False),
        sa.Column("evaluation_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("validation_strategy", sa.String(length=100), nullable=True),
        sa.Column("metric_name", sa.String(length=100), nullable=True),
        sa.Column("metric_value", sa.Numeric(18, 8), nullable=True),
        sa.Column("metric_details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("passed_gates", sa.Boolean(), nullable=True),
        sa.Column("gate_failures", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("evaluated_by", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["model_registry_id"], ["score_model_registry.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("model_registry_id", "evaluation_run_id", "metric_name", name="uq_sme_model_run_metric"),
    )

    op.create_table(
        "score_model_parameters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("model_registry_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parameter_name", sa.String(length=255), nullable=False),
        sa.Column("parameter_value", sa.Numeric(18, 8), nullable=True),
        sa.Column("min_value", sa.Numeric(18, 8), nullable=True),
        sa.Column("max_value", sa.Numeric(18, 8), nullable=True),
        sa.Column("parameter_type", sa.String(length=50), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("regime_tag", sa.String(length=100), nullable=True),
        sa.Column("effective_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deprecated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["model_registry_id"], ["score_model_registry.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("model_registry_id", "parameter_name", "regime_tag", name="uq_smp_model_param_regime"),
    )

    op.create_table(
        "score_model_promotions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("from_model_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("to_model_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("promotion_type", promotion_type_enum, nullable=False),
        sa.Column("promoted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("promoted_by", sa.String(length=255), nullable=True),
        sa.Column("approval_notes", sa.Text(), nullable=True),
        sa.Column("rollback_eligible", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.ForeignKeyConstraint(["from_model_id"], ["score_model_registry.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["to_model_id"], ["score_model_registry.id"], ondelete="RESTRICT"),
    )

    op.create_table(
        "score_model_rollbacks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("from_model_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("to_model_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rollback_reason", sa.String(length=255), nullable=True),
        sa.Column("rollback_trigger", rollback_trigger_enum, nullable=False),
        sa.Column("triggered_by", sa.String(length=255), nullable=True),
        sa.Column("rollback_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["from_model_id"], ["score_model_registry.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["to_model_id"], ["score_model_registry.id"], ondelete="RESTRICT"),
    )


def downgrade() -> None:
    op.drop_table("score_model_rollbacks")
    op.drop_table("score_model_promotions")
    op.drop_table("score_model_parameters")
    op.drop_table("score_model_evaluations")

    op.drop_index("ix_smr_is_active", table_name="score_model_registry")
    op.drop_index("ix_smr_status", table_name="score_model_registry")
    op.drop_table("score_model_registry")

    bind = op.get_bind()
    postgresql.ENUM(name="rollback_trigger_enum").drop(bind, checkfirst=True)
    postgresql.ENUM(name="promotion_type_enum").drop(bind, checkfirst=True)
    postgresql.ENUM(name="model_registry_status_enum").drop(bind, checkfirst=True)
