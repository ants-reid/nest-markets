"""MH-150 — Add llm_request_logs table for durable LLM round-trip audit trail."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "r3s4t5u6v7w8"
down_revision = "q2r3s4t5u6v7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "llm_request_logs",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model_requested", sa.String(length=100), nullable=False),
        sa.Column("model_returned", sa.String(length=100), nullable=True),
        sa.Column("system_prompt_hash", sa.String(length=64), nullable=True),
        sa.Column("user_prompt_hash", sa.String(length=64), nullable=True),
        sa.Column("system_prompt_preview", sa.Text(), nullable=True),
        sa.Column("user_prompt_preview", sa.Text(), nullable=True),
        sa.Column(
            "prompt_version_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("response_payload_json", sa.JSON(), nullable=True),
        sa.Column("stop_reason", sa.String(length=50), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("error_class", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("correlation_id", sa.String(length=100), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_index(
        "ix_llm_request_logs_created_at",
        "llm_request_logs",
        ["created_at"],
    )
    op.create_index(
        "ix_llm_request_logs_correlation_id",
        "llm_request_logs",
        ["correlation_id"],
    )
    op.create_index(
        "ix_llm_request_logs_provider_model",
        "llm_request_logs",
        ["provider", "model_requested"],
    )


def downgrade() -> None:
    op.drop_index("ix_llm_request_logs_provider_model", table_name="llm_request_logs")
    op.drop_index("ix_llm_request_logs_correlation_id", table_name="llm_request_logs")
    op.drop_index("ix_llm_request_logs_created_at", table_name="llm_request_logs")
    op.drop_table("llm_request_logs")
