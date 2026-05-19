"""OpenAI implementation for the provider-agnostic LLM interface."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None  # type: ignore[assignment,misc]

from app.clients.llm.base import (
    BaseLLMProvider,
    LLMProviderConfigurationError,
    LLMProviderError,
    LLMProviderValidationError,
    LLMRequest,
    LLMResponse,
    LLMValidationError,
    ensure_json_dict,
    validate_minimal_schema_contract,
)
from app.services.llm_request_log_sink import (
    LLMLogRecord,
    LLMRequestLogSink,
    hash_text,
    redact_preview,
    safe_invoke_sink,
)


class OpenAIProvider(BaseLLMProvider):
    """Provider adapter that calls OpenAI structured JSON output APIs."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4-turbo",
        timeout: float = 30.0,
        # Legacy kwarg aliases
        timeout_seconds: float | None = None,
        # MH-150 — optional audit sink. Default None preserves prior behaviour.
        request_log_sink: LLMRequestLogSink | None = None,
    ) -> None:
        """Initialize OpenAI provider client state."""
        if not api_key:
            raise ValueError("API key is required")

        self._api_key = api_key
        self.model = model
        self.timeout = timeout if timeout_seconds is None else timeout_seconds
        self._request_log_sink = request_log_sink

        if AsyncOpenAI is not None:
            self.client = AsyncOpenAI(api_key=api_key, timeout=self.timeout)
        else:
            self.client = None

    @staticmethod
    def _check_type(value: Any, expected_type: str) -> bool:
        """Check if a value matches the expected JSON Schema type string."""
        if expected_type == "string":
            return isinstance(value, str)
        if expected_type == "number":
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        if expected_type == "integer":
            return isinstance(value, int) and not isinstance(value, bool)
        if expected_type == "boolean":
            return isinstance(value, bool)
        if expected_type == "object":
            return isinstance(value, dict)
        if expected_type == "array":
            return isinstance(value, list)
        # Unknown type — skip validation
        return True

    async def generate_structured(self, request: LLMRequest) -> LLMResponse:
        """Generate structured output and return validated JSON dictionary."""
        if not request.system_prompt.strip():
            raise LLMProviderValidationError("system_prompt must not be empty")
        user_text = request.user_prompt or request.user_message
        if not user_text.strip():
            raise LLMProviderValidationError("user_prompt must not be empty")
        if not request.model_name.strip():
            raise LLMProviderValidationError("model_name must not be empty")

        if AsyncOpenAI is None or self.client is None:
            raise LLMProviderConfigurationError(
                "OpenAI SDK is not installed. Add dependency: openai"
            )

        schema = dict(request.schema)
        if "type" not in schema:
            schema["type"] = "object"

        # MH-150 — capture trace fields for audit sink (no-op if sink unset).
        _started_at = datetime.now(timezone.utc)
        _t0 = time.monotonic()
        _system_hash = hash_text(request.system_prompt)
        _user_hash = hash_text(user_text)

        try:
            response = await self.client.chat.completions.create(
                model=request.model_name,
                messages=[
                    {"role": "system", "content": request.system_prompt},
                    {"role": "user", "content": user_text},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "structured_payload",
                        "strict": True,
                        "schema": schema,
                    },
                },
                temperature=request.temperature,
            )
        except TimeoutError as exc:
            self._emit_log_failure(
                request, user_text, _system_hash, _user_hash, _started_at, _t0, exc
            )
            raise LLMValidationError(f"Request timed out: {exc}") from exc
        except Exception as exc:
            self._emit_log_failure(
                request, user_text, _system_hash, _user_hash, _started_at, _t0, exc
            )
            raise LLMProviderError(f"OpenAI request failed: {exc}") from exc

        raw_content = ""
        stop_reason = ""
        if response.choices:
            raw_content = response.choices[0].message.content or ""
            stop_reason = getattr(response.choices[0], "finish_reason", "") or ""
        if not raw_content:
            raise LLMProviderError("Empty response from OpenAI")

        try:
            parsed: Any = json.loads(raw_content)
        except json.JSONDecodeError as exc:
            raise LLMValidationError("Response is not valid JSON") from exc

        payload = ensure_json_dict(parsed)

        # Schema validation
        try:
            validate_minimal_schema_contract(payload, schema)
        except (LLMProviderValidationError, LLMValidationError) as exc:
            raise LLMValidationError(str(exc)) from exc

        # Type validation using schema properties
        properties = schema.get("properties", {})
        for field_name, field_schema in properties.items():
            if field_name in payload:
                expected = field_schema.get("type", "")
                if expected and not self._check_type(payload[field_name], expected):
                    raise LLMValidationError(
                        f"Field '{field_name}' has wrong type: expected {expected}"
                    )

        model_name = getattr(response, "model", request.model_name) or request.model_name
        usage = getattr(response, "usage", None)
        usage_tokens: dict[str, int] = {}
        if usage is not None:
            usage_tokens = {
                "prompt": getattr(usage, "prompt_tokens", 0) or 0,
                "completion": getattr(usage, "completion_tokens", 0) or 0,
                "total": getattr(usage, "total_tokens", 0) or 0,
            }

        # MH-150 — emit success record (no-op if sink unset).
        safe_invoke_sink(
            self._request_log_sink,
            LLMLogRecord(
                provider="openai",
                model_requested=request.model_name,
                model_returned=model_name,
                system_prompt_hash=_system_hash,
                user_prompt_hash=_user_hash,
                system_prompt_preview=redact_preview(request.system_prompt),
                user_prompt_preview=redact_preview(user_text),
                response_payload_json=payload,
                stop_reason=stop_reason or None,
                prompt_tokens=usage_tokens.get("prompt"),
                completion_tokens=usage_tokens.get("completion"),
                total_tokens=usage_tokens.get("total"),
                latency_ms=int((time.monotonic() - _t0) * 1000),
                started_at=_started_at,
            ),
        )

        return LLMResponse(
            content=payload,
            model=model_name,
            stop_reason=stop_reason,
            usage_tokens=usage_tokens,
        )

    def _emit_log_failure(
        self,
        request: LLMRequest,
        user_text: str,
        system_hash: str,
        user_hash: str,
        started_at,
        t0: float,
        exc: BaseException,
    ) -> None:
        """MH-150 — emit failure record (no-op if sink unset)."""
        safe_invoke_sink(
            self._request_log_sink,
            LLMLogRecord(
                provider="openai",
                model_requested=request.model_name,
                system_prompt_hash=system_hash,
                user_prompt_hash=user_hash,
                system_prompt_preview=redact_preview(request.system_prompt),
                user_prompt_preview=redact_preview(user_text),
                latency_ms=int((time.monotonic() - t0) * 1000),
                started_at=started_at,
                error_class=exc.__class__.__name__,
                error_message=str(exc)[:1000],
            ),
        )

    async def health_check(self) -> bool:
        """Return True if the provider is reachable."""
        if AsyncOpenAI is None or self.client is None:
            return False
        try:
            await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
            )
            return True
        except Exception:
            return False
