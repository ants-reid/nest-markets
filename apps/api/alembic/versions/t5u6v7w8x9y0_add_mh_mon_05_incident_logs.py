"""MH-MON-05 — Add incident_logs table (append-only operational incident log)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "t5u6v7w8x9y0"
down_revision = "s4t5u6v7w8x9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "incident_logs",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("extra_json", sa.JSON(), nullable=True),
        sa.Column("correlation_id", sa.String(length=100), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "severity IN ('info', 'warn', 'error', 'critical')",
            name="ck_incident_logs_severity",
        ),
    )
    op.create_index(
        "ix_incident_logs_created_at",
        "incident_logs",
        ["created_at"],
    )
    op.create_index(
        "ix_incident_logs_severity_created_at",
        "incident_logs",
        ["severity", "created_at"],
    )
    op.create_index(
        "ix_incident_logs_source_created_at",
        "incident_logs",
        ["source", "created_at"],
    )
    op.create_index(
        "ix_incident_logs_code",
        "incident_logs",
        ["code"],
    )


def downgrade() -> None:
    op.drop_index("ix_incident_logs_code", table_name="incident_logs")
    op.drop_index("ix_incident_logs_source_created_at", table_name="incident_logs")
    op.drop_index("ix_incident_logs_severity_created_at", table_name="incident_logs")
    op.drop_index("ix_incident_logs_created_at", table_name="incident_logs")
    op.drop_table("incident_logs")
