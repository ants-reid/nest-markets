"""LLM provider router for MVP provider selection from config."""

from __future__ import annotations

from app.clients.llm.base import BaseLLMProvider, LLMProviderError
from app.clients.llm.openai_provider import OpenAIProvider
from app.config import Settings


class LLMProviderRouter:
    """Selects and returns the active LLM provider implementation."""

    def __init__(self, settings: Settings) -> None:
        """Initialize router using typed app settings — creates provider eagerly."""
        provider_name = str(getattr(settings, "llm_provider", "openai")).lower()

        if provider_name != "openai":
            raise LLMProviderError(
                f"Unsupported LLM provider '{provider_name}'. MVP supports 'openai' only."
            )

        api_key = str(getattr(settings, "openai_api_key", "") or "")
        if not api_key:
            raise LLMProviderError("API key not configured for OpenAI provider")

        model = str(getattr(settings, "openai_model", "gpt-4-turbo") or "gpt-4-turbo")
        timeout = float(getattr(settings, "openai_timeout", 30.0) or 30.0)

        self._provider: BaseLLMProvider = OpenAIProvider(
            api_key=api_key,
            model=model,
            timeout=timeout,
        )

    def get_provider(self) -> BaseLLMProvider:
        """Return the configured provider singleton."""
        return self._provider

    async def health_check(self) -> bool:
        """Delegate health check to the configured provider."""
        try:
            return await self._provider.health_check()
        except Exception:
            return False
