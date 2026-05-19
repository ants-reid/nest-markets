"""MH-150 — LLMRequestLog: durable audit trail for every LLM round-trip.

Pure additive table. Provider hooks an *optional* sink that writes one row per
call (success or failure). Default behaviour: no logging emitted unless a sink
is explicitly wired by the caller (this phase ships the model + migration +
sink contract; no global wiring).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import CreatedAtMixin, JSONBType, UUIDPrimaryKeyMixin


class LLMRequestLog(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One row per LLM request/response (or per error)."""

    __tablename__ = "llm_request_logs"

    # --- Provider / model identity ---
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model_requested: Mapped[str] = mapped_column(String(100), nullable=False)
    model_returned: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # --- Prompt provenance ---
    # Hashes of the full prompts (so we can prove identity without storing PII).
    system_prompt_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_prompt_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    # Length-capped previews for human review.
    system_prompt_preview: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_prompt_preview: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    prompt_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    # --- Response / outcome ---
    response_payload_json: Mapped[Optional[dict]] = mapped_column(JSONBType, nullable=True)
    stop_reason: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    prompt_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # --- Error state ---
    error_class: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # --- Trace ---
    correlation_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
