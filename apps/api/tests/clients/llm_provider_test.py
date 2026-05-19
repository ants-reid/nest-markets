"""Tests for OpenAI provider."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai.types.chat import ChatCompletion
from openai.types.chat.chat_completion import Choice
from openai.types.completion_usage import CompletionUsage

from app.clients.llm.base import LLMProviderError, LLMRequest, LLMValidationError
from app.clients.llm.openai_provider import OpenAIProvider


@pytest.fixture
def openai_provider():
    """Create OpenAI provider with mock config."""
    with patch("app.clients.llm.openai_provider.AsyncOpenAI"):
        provider = OpenAIProvider(api_key="test-key-123", model="gpt-4-turbo", timeout=30)
        return provider


@pytest.fixture
def valid_request():
    """Create valid LLM request."""
    return LLMRequest(
        system_prompt="You are a trading assistant.",
        user_message="Generate a signal for AAPL",
        schema={
            "type": "object",
            "properties": {"signal": {"type": "string"}, "confidence": {"type": "number"}},
            "required": ["signal"],
        },
        temperature=0.5,
        max_tokens=200,
    )


class TestOpenAIProviderInit:
    """Tests for OpenAI provider initialization."""

    def test_init_valid(self, openai_provider):
        """Test initializing with valid config."""
        assert openai_provider.model == "gpt-4-turbo"
        assert openai_provider.timeout == 30

    def test_init_missing_api_key(self):
        """Test initialization fails with missing API key."""
        with pytest.raises(ValueError, match="API key is required"):
            OpenAIProvider(api_key="", model="gpt-4-turbo")

    def test_init_custom_model(self):
        """Test initialization with custom model."""
        with patch("app.clients.llm.openai_provider.AsyncOpenAI"):
            provider = OpenAIProvider(api_key="key", model="custom-model")
            assert provider.model == "custom-model"


class TestOpenAIProviderGenerate:
    """Tests for structured generation."""

    @pytest.mark.asyncio
    async def test_generate_structured_success(self, openai_provider, valid_request):
        """Test successful structured generation."""
        # Mock OpenAI response
        mock_response = MagicMock(spec=ChatCompletion)
        mock_response.choices = [
            MagicMock(
                spec=Choice,
                message=MagicMock(content='{"signal": "buy", "confidence": 0.85}'),
                finish_reason="stop",
            )
        ]
        mock_response.model = "gpt-4-turbo"
        mock_response.usage = MagicMock(
            spec=CompletionUsage,
            prompt_tokens=50,
            completion_tokens=30,
            total_tokens=80,
        )

        openai_provider.client.chat.completions.create = AsyncMock(
            return_value=mock_response
        )

        response = await openai_provider.generate_structured(valid_request)

        assert response.content == {"signal": "buy", "confidence": 0.85}
        assert response.model == "gpt-4-turbo"
        assert response.stop_reason == "stop"
        assert response.usage_tokens["total"] == 80

    @pytest.mark.asyncio
    async def test_generate_structured_invalid_json(self, openai_provider, valid_request):
        """Test handling of invalid JSON response."""
        mock_response = MagicMock(spec=ChatCompletion)
        mock_response.choices = [
            MagicMock(
                message=MagicMock(content="{invalid json}"),
                finish_reason="stop",
            )
        ]

        openai_provider.client.chat.completions.create = AsyncMock(
            return_value=mock_response
        )

        with pytest.raises(LLMValidationError, match="not valid JSON"):
            await openai_provider.generate_structured(valid_request)

    @pytest.mark.asyncio
    async def test_generate_structured_empty_response(self, openai_provider, valid_request):
        """Test handling of empty response."""
        mock_response = MagicMock(spec=ChatCompletion)
        mock_response.choices = [
            MagicMock(
                message=MagicMock(content=None),
                finish_reason="stop",
            )
        ]

        openai_provider.client.chat.completions.create = AsyncMock(
            return_value=mock_response
        )

        with pytest.raises(LLMProviderError, match="Empty response"):
            await openai_provider.generate_structured(valid_request)

    @pytest.mark.asyncio
    async def test_generate_structured_schema_validation_missing_required(
        self, openai_provider, valid_request
    ):
        """Test schema validation for missing required field."""
        mock_response = MagicMock(spec=ChatCompletion)
        # Missing required 'signal' field
        mock_response.choices = [
            MagicMock(
                message=MagicMock(content='{"confidence": 0.85}'),
                finish_reason="stop",
            )
        ]

        openai_provider.client.chat.completions.create = AsyncMock(
            return_value=mock_response
        )

        with pytest.raises(LLMValidationError, match="Missing required"):
            await openai_provider.generate_structured(valid_request)

    @pytest.mark.asyncio
    async def test_generate_structured_schema_validation_wrong_type(
        self, openai_provider, valid_request
    ):
        """Test schema validation for wrong type."""
        mock_response = MagicMock(spec=ChatCompletion)
        # confidence should be number, not string
        mock_response.choices = [
            MagicMock(
                message=MagicMock(content='{"signal": "buy", "confidence": "high"}'),
                finish_reason="stop",
            )
        ]

        openai_provider.client.chat.completions.create = AsyncMock(
            return_value=mock_response
        )

        with pytest.raises(LLMValidationError, match="wrong type"):
            await openai_provider.generate_structured(valid_request)

    @pytest.mark.asyncio
    async def test_generate_structured_timeout(self, openai_provider, valid_request):
        """Test timeout handling."""
        openai_provider.client.chat.completions.create = AsyncMock(side_effect=TimeoutError())

        with pytest.raises(LLMValidationError):  # Gets wrapped in LLMProviderError
            await openai_provider.generate_structured(valid_request)


class TestOpenAIProviderSchema:
    """Tests for schema handling."""

    def test_check_type_string(self):
        """Test type checking for string."""
        assert OpenAIProvider._check_type("hello", "string") is True
        assert OpenAIProvider._check_type(123, "string") is False

    def test_check_type_number(self):
        """Test type checking for number."""
        assert OpenAIProvider._check_type(123, "number") is True
        assert OpenAIProvider._check_type(123.45, "number") is True
        assert OpenAIProvider._check_type("123", "number") is False

    def test_check_type_integer(self):
        """Test type checking for integer."""
        assert OpenAIProvider._check_type(123, "integer") is True
        assert OpenAIProvider._check_type(123.45, "integer") is False

    def test_check_type_boolean(self):
        """Test type checking for boolean."""
        assert OpenAIProvider._check_type(True, "boolean") is True
        assert OpenAIProvider._check_type(False, "boolean") is True
        assert OpenAIProvider._check_type(1, "boolean") is False

    def test_check_type_object(self):
        """Test type checking for object."""
        assert OpenAIProvider._check_type({}, "object") is True
        assert OpenAIProvider._check_type({"key": "value"}, "object") is True
        assert OpenAIProvider._check_type([], "object") is False

    def test_check_type_array(self):
        """Test type checking for array."""
        assert OpenAIProvider._check_type([], "array") is True
        assert OpenAIProvider._check_type([1, 2, 3], "array") is True
        assert OpenAIProvider._check_type({}, "array") is False

    def test_check_type_unknown(self):
        """Test type checking for unknown type."""
        # Unknown type should return True (skip validation)
        assert OpenAIProvider._check_type("anything", "unknown_type") is True


@pytest.mark.asyncio
async def test_health_check(openai_provider):
    """Test health check implementation."""
    mock_response = MagicMock(spec=ChatCompletion)
    mock_response.choices = [
        MagicMock(
            message=MagicMock(content='{"status": "ok"}'),
            finish_reason="stop",
        )
    ]

    openai_provider.client.chat.completions.create = AsyncMock(
        return_value=mock_response
    )

    is_healthy = await openai_provider.health_check()
    assert is_healthy is True
