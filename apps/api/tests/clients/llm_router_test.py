"""Tests for LLM provider router."""

from unittest.mock import MagicMock, patch

import pytest

from app.clients.llm.base import LLMProviderError
from app.clients.llm.router import LLMProviderRouter
from app.config import Settings


@pytest.fixture
def valid_settings():
    """Create valid settings for OpenAI."""
    settings = Settings(
        llm_provider="openai",
        openai_api_key="test-key-123",
        openai_model_name="gpt-4-turbo",
        openai_timeout=30,
    )
    return settings


@pytest.fixture
def router(valid_settings):
    """Create router with valid settings."""
    with patch("app.clients.llm.router.OpenAIProvider"):
        router = LLMProviderRouter(valid_settings)
        return router


class TestLLMProviderRouterInit:
    """Tests for router initialization."""

    def test_init_openai_valid(self, valid_settings):
        """Test initializing with valid OpenAI settings."""
        with patch("app.clients.llm.router.OpenAIProvider") as mock_openai:
            LLMProviderRouter(valid_settings)
            mock_openai.assert_called_once_with(
                api_key="test-key-123",
                model="gpt-4-turbo",
                timeout=30,
            )

    def test_init_openai_missing_key(self):
        """Test initialization fails with missing OpenAI key."""
        settings = Settings(
            llm_provider="openai",
            openai_api_key="",  # Empty key
        )
        with pytest.raises(LLMProviderError, match="API key not configured"):
            LLMProviderRouter(settings)

    def test_init_unsupported_provider(self):
        """Test initialization fails with unsupported provider."""
        settings = Settings(
            llm_provider="anthropic",
            openai_api_key="test-key",
        )
        with pytest.raises(LLMProviderError, match="Unsupported LLM provider"):
            LLMProviderRouter(settings)


class TestLLMProviderRouterGetProvider:
    """Tests for getting provider."""

    def test_get_provider_success(self, router):
        """Test getting provider."""
        provider = router.get_provider()
        assert provider is not None

    def test_get_provider_returns_same_instance(self, router):
        """Test getting provider returns same instance."""
        provider1 = router.get_provider()
        provider2 = router.get_provider()
        assert provider1 is provider2


class TestLLMProviderRouterHealthCheck:
    """Tests for health check."""

    @pytest.mark.asyncio
    async def test_health_check_success(self, router):
        """Test successful health check."""
        router._provider.health_check = MagicMock()

        async def mock_health_check():
            return True

        router._provider.health_check = mock_health_check

        is_healthy = await router.health_check()
        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, router):
        """Test failed health check."""
        async def mock_health_check():
            return False

        router._provider.health_check = mock_health_check

        is_healthy = await router.health_check()
        assert is_healthy is False

    @pytest.mark.asyncio
    async def test_health_check_error(self, router):
        """Test health check with error."""
        async def mock_health_check():
            raise Exception("Connection failed")

        router._provider.health_check = mock_health_check

        is_healthy = await router.health_check()
        assert is_healthy is False
