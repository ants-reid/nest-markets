"""Provider-agnostic LLM interfaces for structured generation."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, TypeAlias

JSONPrimitive: TypeAlias = str | int | float | bool | None
JSONValue: TypeAlias = JSONPrimitive | dict[str, "JSONValue"] | list["JSONValue"]
JSONDict: TypeAlias = dict[str, JSONValue]


@dataclass
class LLMRequest:
    """Input contract for structured generation across providers."""

    system_prompt: str
    schema: dict[str, Any]
    model_name: str = "gpt-4-turbo"
    user_prompt: str = ""
    user_message: str = ""
    temperature: float = 0.0
    max_tokens: int = 0

    def __post_init__(self) -> None:
        """Normalise user_message / user_prompt aliases."""
        if self.user_message and not self.user_prompt:
            object.__setattr__(self, "user_prompt", self.user_message)
        elif self.user_prompt and not self.user_message:
            object.__setattr__(self, "user_message", self.user_prompt)


@dataclass(frozen=True)
class LLMResponse:
    """Response container for structured LLM output."""

    content: JSONDict
    model: str = ""
    stop_reason: str = ""
    usage_tokens: dict[str, int] = None  # type: ignore[assignment]
    # Legacy alias
    model_name: str = ""

    def __post_init__(self) -> None:
        if self.usage_tokens is None:
            object.__setattr__(self, "usage_tokens", {})
        if not self.model_name and self.model:
            object.__setattr__(self, "model_name", self.model)
        elif not self.model and self.model_name:
            object.__setattr__(self, "model", self.model_name)


class LLMProviderError(Exception):
    """Base error for LLM provider operations."""


class LLMProviderConfigurationError(LLMProviderError):
    """Raised when provider configuration is invalid."""


class LLMProviderValidationError(LLMProviderError):
    """Raised when provider output is not valid for expected structure."""


class LLMValidationError(LLMProviderValidationError):
    """Backward-compatible alias for validation errors."""


class LLMTimeoutError(LLMProviderError):
    """Raised when provider request exceeds timeout."""


class BaseLLMProvider(ABC):
    """Abstract provider contract for async structured LLM calls."""

    @abstractmethod
    async def generate_structured(self, request: LLMRequest) -> JSONDict:
        """Generate schema-constrained output and return JSON-compatible dict."""


def ensure_json_dict(value: Any) -> JSONDict:
    """Validate that a value is a JSON-compatible dictionary."""
    if not isinstance(value, dict):
        raise LLMProviderValidationError("Structured response must be a dictionary")

    try:
        serialized = json.dumps(value)
    except (TypeError, ValueError) as exc:
        raise LLMProviderValidationError("Structured response is not JSON-compatible") from exc

    parsed = json.loads(serialized)
    if not isinstance(parsed, dict):
        raise LLMProviderValidationError("Structured response must decode to a dictionary")
    return parsed


def validate_minimal_schema_contract(payload: JSONDict, schema: dict[str, Any]) -> None:
    """Run minimal schema checks for required fields and root object type."""
    schema_type = schema.get("type")
    if schema_type is not None and schema_type != "object":
        raise LLMProviderValidationError("Top-level schema type must be 'object'")

    required_fields = schema.get("required", [])
    if not isinstance(required_fields, list):
        raise LLMProviderValidationError("Schema 'required' must be a list")

    for field_name in required_fields:
        if field_name not in payload:
            raise LLMProviderValidationError(f"Missing required field: {field_name}")
