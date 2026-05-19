"""MH-150 — Sink contract for ``OpenAIProvider`` to emit redacted LLM round-trip records.

The provider takes an *optional* ``request_log_sink: Callable[[LLMLogRecord], None]``.
If ``None`` (default), no logging occurs and provider behaviour is identical
to pre-MH-150. If supplied, the provider invokes the sink with a fully
redacted record after every call (success or failure). Sink errors are
swallowed so logging can never break the trading-decision path.

This module ships:
    * ``LLMLogRecord``                — typed log payload
    * ``hash_text(s)``                — stable sha256 hex digest used for prompt provenance
    * ``redact_preview(s, n=500)``    — length-capped, control-stripped human preview
    * ``build_db_sink(session_factory)`` — sink that writes one ``LLMRequestLog`` row

No call site is wired in this phase; we only ship the audit table and the
sink contract for future MH-159/MH-160/MH-AI-* phases to consume.
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# Reuse the sanitizer's control-stripping behaviour for human previews.
_CONTROL_STRIP = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")


@dataclass
class LLMLogRecord:
    """Redacted record describing one LLM round-trip."""

    provider: str
    model_requested: str
    model_returned: Optional[str] = None
    system_prompt_hash: Optional[str] = None
    user_prompt_hash: Optional[str] = None
    system_prompt_preview: Optional[str] = None
    user_prompt_preview: Optional[str] = None
    prompt_version_id: Optional[Any] = None
    response_payload_json: Optional[dict] = None
    stop_reason: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    latency_ms: Optional[int] = None
    error_class: Optional[str] = None
    error_message: Optional[str] = None
    correlation_id: Optional[str] = None
    started_at: Optional[Any] = None
    extra: dict[str, Any] = field(default_factory=dict)


LLMRequestLogSink = Callable[[LLMLogRecord], None]


def hash_text(text: str) -> str:
    """Return a stable sha256 hex digest of the input text."""
    if text is None:
        return ""
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def redact_preview(text: str, max_len: int = 500) -> str:
    """Return a control-stripped, length-capped preview safe for storage."""
    if text is None:
        return ""
    cleaned = _CONTROL_STRIP.sub("", text)
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len] + "...[truncated]"
    return cleaned


def safe_invoke_sink(sink: Optional[LLMRequestLogSink], record: LLMLogRecord) -> None:
    """Invoke a sink swallowing all exceptions (audit must never break callers)."""
    if sink is None:
        return
    try:
        sink(record)
    except Exception:  # pragma: no cover - defensive
        logger.exception("LLM request-log sink raised; swallowing.")


def build_db_sink(session_factory: Callable[[], Any]) -> LLMRequestLogSink:
    """Return a sink that writes one ``LLMRequestLog`` row per record.

    ``session_factory`` is a zero-arg callable returning a SQLAlchemy session.
    The sink owns the session lifecycle (opens, commits, closes).
    """

    def _sink(record: LLMLogRecord) -> None:
        from app.db.models.llm_request_log import LLMRequestLog

        session = session_factory()
        try:
            row = LLMRequestLog(
                provider=record.provider,
                model_requested=record.model_requested,
                model_returned=record.model_returned,
                system_prompt_hash=record.system_prompt_hash,
                user_prompt_hash=record.user_prompt_hash,
                system_prompt_preview=record.system_prompt_preview,
                user_prompt_preview=record.user_prompt_preview,
                prompt_version_id=record.prompt_version_id,
                response_payload_json=record.response_payload_json,
                stop_reason=record.stop_reason,
                prompt_tokens=record.prompt_tokens,
                completion_tokens=record.completion_tokens,
                total_tokens=record.total_tokens,
                latency_ms=record.latency_ms,
                error_class=record.error_class,
                error_message=record.error_message,
                correlation_id=record.correlation_id,
                started_at=record.started_at,
            )
            session.add(row)
            session.commit()
        except Exception:
            try:
                session.rollback()
            except Exception:
                pass
            raise
        finally:
            try:
                session.close()
            except Exception:
                pass

    return _sink
