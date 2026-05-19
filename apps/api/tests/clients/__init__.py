"""Tests for LLM provider base interface."""

import pytest

from app.clients.llm.base import (
    BaseLLMProvider,
    LLMProviderError,
    LLMRequest,
    LLMResponse,
    LLMValidationError,
)


class MockProvider(BaseLLMProvider):
    """Mock provider for testing base interface."""

    async def generate_structured(self, request: LLMRequest) -> LLMResponse:
        """Mock implementation."""
        return LLMResponse(
            content={"status": "ok"},
            raw_text='{"status": "ok"}',
            model="mock-model",
            stop_reason="stop",
        )


@pytest.fixture
def mock_provider():
    """Create mock provider."""
    return MockProvider(model="mock-model", timeout=30)


@pytest.fixture
def valid_request():
    """Create valid LLM request."""
    return LLMRequest(
        system_prompt="You are a helpful assistant.",
        user_message="Hello, how are you?",
        schema={"type": "object", "properties": {"response": {"type": "string"}}},
        temperature=0.7,
        max_tokens=100,
    )


class TestLLMRequest:
    """Tests for LLMRequest dataclass."""

    def test_request_creation(self, valid_request):
        """Test creating valid request."""
        assert valid_request.system_prompt == "You are a helpful assistant."
        assert valid_request.user_message == "Hello, how are you?"
        assert valid_request.temperature == 0.7
        assert valid_request.max_tokens == 100

    def test_request_defaults(self):
        """Test request defaults."""
        request = LLMRequest(
            system_prompt="sys",
            user_message="user",
            schema={},
        )
        assert request.temperature == 0.7
        assert request.max_tokens is None
        assert request.timeout is None

    def test_request_temperature_bounds(self):
        """Test temperature can be set to valid values."""
        # Temperature 0 = deterministic
        request = LLMRequest(
            system_prompt="sys",
            user_message="user",
            schema={},
            temperature=0,
        )
        assert request.temperature == 0

        # Temperature 1 = creative
        request = LLMRequest(
            system_prompt="sys",
            user_message="user",
            schema={},
            temperature=1.0,
        )
        assert request.temperature == 1.0


class TestLLMResponse:
    """Tests for LLMResponse dataclass."""

    def test_response_creation(self):
        """Test creating response."""
        response = LLMResponse(
            content={"key": "value"},
            raw_text='{"key": "value"}',
            model="gpt-4",
            stop_reason="stop",
        )
        assert response.content == {"key": "value"}
        assert response.model == "gpt-4"

    def test_response_with_usage(self):
        """Test response with token usage."""
        usage = {"prompt": 10, "completion": 20, "total": 30}
        response = LLMResponse(
            content={},
            raw_text="",
            model="gpt-4",
            stop_reason="stop",
            usage_tokens=usage,
        )
        assert response.usage_tokens == usage
        assert response.usage_tokens["total"] == 30


class TestBaseLLMProvider:
    """Tests for BaseLLMProvider base class."""

    def test_provider_initialization(self, mock_provider):
        """Test provider can be initialized."""
        assert mock_provider.model == "mock-model"
        assert mock_provider.timeout == 30

    def test_provider_is_abstract(self):
        """Test BaseLLMProvider cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseLLMProvider(model="test", timeout=30)

    @pytest.mark.asyncio
    async def test_mock_provider_generate(self, mock_provider, valid_request):
        """Test mock provider implementation."""
        response = await mock_provider.generate_structured(valid_request)
        assert response.content == {"status": "ok"}
        assert response.model == "mock-model"

    @pytest.mark.asyncio
    async def test_health_check(self, mock_provider):
        """Test health check works."""
        is_healthy = await mock_provider.health_check()
        assert is_healthy is True


class TestLLMExceptions:
    """Tests for LLM exception hierarchy."""

    def test_provider_error(self):
        """Test LLMProviderError."""
        error = LLMProviderError("test error")
        assert str(error) == "test error"

    def test_validation_error(self):
        """Test LLMValidationError."""
        error = LLMValidationError("schema mismatch")
        assert str(error) == "schema mismatch"
        assert isinstance(error, LLMProviderError)

    def test_timeout_error(self):
        """Test LLMTimeoutError."""
        error = LLMProviderError("request timed out")
        assert str(error) == "request timed out"
        assert isinstance(error, LLMProviderError)
