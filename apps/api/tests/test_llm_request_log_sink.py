"""Tests for MH-150 LLM request log sink + provider integration."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.clients.llm.base import LLMRequest
from app.clients.llm.openai_provider import OpenAIProvider
from app.services.llm_request_log_sink import (
    LLMLogRecord,
    hash_text,
    redact_preview,
    safe_invoke_sink,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_schema() -> dict:
    return {
        "type": "object",
        "required": ["ok"],
        "properties": {"ok": {"type": "boolean"}},
    }


def _make_fake_openai_response(content: str = '{"ok": true}', model: str = "gpt-4-turbo"):
    """Return an object shaped like the OpenAI SDK response."""
    fake = MagicMock()
    fake.model = model
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    choice.finish_reason = "stop"
    fake.choices = [choice]
    usage = MagicMock()
    usage.prompt_tokens = 11
    usage.completion_tokens = 7
    usage.total_tokens = 18
    fake.usage = usage
    return fake


# ---------------------------------------------------------------------------
# Sink helpers
# ---------------------------------------------------------------------------


def test_hash_text_is_stable_and_hex():
    h1 = hash_text("hello world")
    h2 = hash_text("hello world")
    assert h1 == h2
    assert len(h1) == 64
    assert all(c in "0123456789abcdef" for c in h1)


def test_hash_text_changes_with_input():
    assert hash_text("a") != hash_text("b")


def test_redact_preview_strips_controls_and_caps():
    out = redact_preview("hi\x00there\x01\x02", max_len=20)
    assert "\x00" not in out
    assert "\x01" not in out

    big = "x" * 800
    out2 = redact_preview(big, max_len=500)
    assert out2.endswith("...[truncated]")
    assert len(out2) <= 500 + len("...[truncated]")


def test_safe_invoke_sink_swallows_exceptions():
    def bad_sink(_record):
        raise RuntimeError("boom")

    # Must not raise.
    safe_invoke_sink(bad_sink, LLMLogRecord(provider="openai", model_requested="m"))


def test_safe_invoke_sink_noop_when_none():
    safe_invoke_sink(None, LLMLogRecord(provider="openai", model_requested="m"))


# ---------------------------------------------------------------------------
# Provider integration
# ---------------------------------------------------------------------------


def test_provider_default_sink_is_none_no_behaviour_change():
    """Sink defaults to None so existing call sites are unchanged."""
    p = OpenAIProvider(api_key="k", model="m")
    assert p._request_log_sink is None


def test_provider_emits_record_on_success():
    captured: list[LLMLogRecord] = []
    p = OpenAIProvider(
        api_key="k",
        model="gpt-4-turbo",
        request_log_sink=captured.append,
    )
    # Replace the SDK client with a stub.
    p.client = MagicMock()
    p.client.chat.completions.create = AsyncMock(return_value=_make_fake_openai_response())

    request = LLMRequest(
        system_prompt="You are a tester.",
        user_prompt="Return ok=true.",
        schema=_make_schema(),
        model_name="gpt-4-turbo",
    )
    asyncio.run(p.generate_structured(request))

    assert len(captured) == 1
    rec = captured[0]
    assert rec.provider == "openai"
    assert rec.model_requested == "gpt-4-turbo"
    assert rec.model_returned == "gpt-4-turbo"
    assert rec.response_payload_json == {"ok": True}
    assert rec.prompt_tokens == 11
    assert rec.completion_tokens == 7
    assert rec.total_tokens == 18
    assert rec.error_class is None
    assert rec.system_prompt_hash == hash_text("You are a tester.")
    assert rec.user_prompt_hash == hash_text("Return ok=true.")
    assert rec.system_prompt_preview == "You are a tester."
    assert rec.user_prompt_preview == "Return ok=true."
    assert rec.latency_ms is not None and rec.latency_ms >= 0


def test_provider_emits_record_on_failure():
    captured: list[LLMLogRecord] = []
    p = OpenAIProvider(api_key="k", request_log_sink=captured.append)
    p.client = MagicMock()
    p.client.chat.completions.create = AsyncMock(side_effect=RuntimeError("upstream 500"))

    request = LLMRequest(
        system_prompt="sys",
        user_prompt="usr",
        schema=_make_schema(),
        model_name="gpt-4-turbo",
    )
    with pytest.raises(Exception):
        asyncio.run(p.generate_structured(request))

    assert len(captured) == 1
    rec = captured[0]
    assert rec.error_class == "RuntimeError"
    assert "upstream 500" in (rec.error_message or "")
    assert rec.response_payload_json is None
    assert rec.model_returned is None


def test_provider_swallows_sink_failure_does_not_break_call():
    def bad_sink(_record):
        raise RuntimeError("sink down")

    p = OpenAIProvider(api_key="k", request_log_sink=bad_sink)
    p.client = MagicMock()
    p.client.chat.completions.create = AsyncMock(return_value=_make_fake_openai_response())

    request = LLMRequest(
        system_prompt="sys",
        user_prompt="usr",
        schema=_make_schema(),
        model_name="gpt-4-turbo",
    )
    # Must not raise even though sink raises.
    result = asyncio.run(p.generate_structured(request))
    assert result.content == {"ok": True}


def test_provider_no_sink_makes_no_extra_calls():
    """When no sink is configured, the provider must behave exactly as before."""
    p = OpenAIProvider(api_key="k")
    assert p._request_log_sink is None
    p.client = MagicMock()
    p.client.chat.completions.create = AsyncMock(return_value=_make_fake_openai_response())

    request = LLMRequest(
        system_prompt="sys",
        user_prompt="usr",
        schema=_make_schema(),
        model_name="gpt-4-turbo",
    )
    result = asyncio.run(p.generate_structured(request))
    assert result.content == {"ok": True}


# ---------------------------------------------------------------------------
# Model import smoke test
# ---------------------------------------------------------------------------


def test_llm_request_log_model_imports_and_has_expected_columns():
    from app.db.models.llm_request_log import LLMRequestLog

    cols = {c.name for c in LLMRequestLog.__table__.columns}
    assert {
        "id",
        "provider",
        "model_requested",
        "model_returned",
        "system_prompt_hash",
        "user_prompt_hash",
        "system_prompt_preview",
        "user_prompt_preview",
        "prompt_version_id",
        "response_payload_json",
        "stop_reason",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "latency_ms",
        "error_class",
        "error_message",
        "correlation_id",
        "started_at",
        "created_at",
    }.issubset(cols)
