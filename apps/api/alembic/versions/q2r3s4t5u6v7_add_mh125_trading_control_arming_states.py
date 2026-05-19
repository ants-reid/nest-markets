"""MH-125 — Add trading_control_arming_states table for durable auto-paper arming state."""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "q2r3s4t5u6v7"
down_revision = "p1q2r3s4t5u6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "trading_control_arming_states",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scope", sa.String(length=50), nullable=False),
        sa.Column("trading_mode", sa.String(length=20), nullable=False),
        sa.Column("state", sa.String(length=20), nullable=False, server_default="disarmed"),
        sa.Column("armed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("armed_by", sa.String(length=100), nullable=True),
        sa.Column("arm_reason", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_enablement_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_enablement_status", sa.String(length=20), nullable=True),
        sa.Column("last_enablement_blockers", sa.JSON(), nullable=True),
        sa.Column("last_enablement_warnings", sa.JSON(), nullable=True),
        sa.Column("client_request_id", sa.String(length=100), nullable=True),
        sa.Column("disarmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("disarmed_by", sa.String(length=100), nullable=True),
        sa.Column("disarm_reason", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("scope", "trading_mode", name="uq_trading_control_arming_states_scope_mode"),
        sa.CheckConstraint("state IN ('armed', 'disarmed')", name="ck_trading_control_arming_states_state"),
        sa.CheckConstraint(
            "last_enablement_status IS NULL OR last_enablement_status IN ('ready', 'blocked', 'warning')",
            name="ck_trading_control_arming_states_enablement_status",
        ),
        sa.CheckConstraint(
            "state <> 'armed' OR (armed_at IS NOT NULL AND armed_by IS NOT NULL AND expires_at IS NOT NULL)",
            name="ck_trading_control_arming_states_armed_fields",
        ),
        sa.CheckConstraint(
            "state <> 'disarmed' OR expires_at IS NULL",
            name="ck_trading_control_arming_states_disarmed_expiry",
        ),
    )

    op.create_index(
        "ix_trading_control_arming_states_state_expires_at",
        "trading_control_arming_states",
        ["state", "expires_at"],
    )
    op.create_index(
        "ix_trading_control_arming_states_updated_at",
        "trading_control_arming_states",
        ["updated_at"],
    )

    op.execute(
        sa.text(
            """
            INSERT INTO trading_control_arming_states (
                id, scope, trading_mode, state, arm_reason
            ) VALUES (
                :id, 'auto_paper', 'paper', 'disarmed',
                'MH-125 default durable arming-state seed row; runtime auto enforcement remains disabled.'
            )
            """
        ).bindparams(id=uuid.uuid4())
    )


def downgrade() -> None:
    op.drop_index("ix_trading_control_arming_states_updated_at", table_name="trading_control_arming_states")
    op.drop_index("ix_trading_control_arming_states_state_expires_at", table_name="trading_control_arming_states")
    op.drop_table("trading_control_arming_states")