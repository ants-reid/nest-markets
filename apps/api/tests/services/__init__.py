"""Tests for signal service."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.clients.llm import LLMResponse
from app.db.models import PromptVersion, Signal
from app.services.signal_service import SignalInput, SignalOutput, SignalService


@pytest.fixture
def mock_router():
    """Create mock LLM router."""
    return MagicMock()


@pytest.fixture
def mock_session():
    """Create mock database session."""
    return MagicMock(spec=Session)


@pytest.fixture
def signal_service(mock_router, mock_session):
    """Create signal service with mocks."""
    return SignalService(router=mock_router, session=mock_session)


@pytest.fixture
def mock_prompt_version():
    """Create mock prompt version."""
    prompt = MagicMock(spec=PromptVersion)
    prompt.id = uuid4()
    prompt.role = "signal_engine"
    prompt.version = "1.0"
    prompt.system_prompt = "You are a trading analyst."
    prompt.user_template = "Analyze {asset_symbol} at {current_price}"
    prompt.schema_json = """{
        "type": "object",
        "properties": {
            "direction": {"type": "string", "enum": ["long", "short", "flat"]},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "catalyst": {"type": "string"},
            "reasoning": {"type": "string"}
        },
        "required": ["direction", "confidence"]
    }"""
    return prompt


@pytest.fixture
def signal_input():
    """Create signal input."""
    return SignalInput(
        asset_id=uuid4(),
        asset_symbol="AAPL",
        current_price=150.0,
        features={
            "sma_20": 148.0,
            "sma_50": 147.0,
            "sma_200": 145.0,
            "rsi_14": 65.0,
            "atr_14": 2.5,
            "volatility": 0.015,
            "trend_direction": "up",
            "trend_strength": 0.8,
            "market_quality": "good",
            "spread_bps": 1.0,
        },
        timestamp=datetime.utcnow(),
    )


@pytest.fixture
def llm_response():
    """Create mock LLM response."""
    return LLMResponse(
        content={
            "direction": "long",
            "confidence": 0.85,
            "catalyst": "Bullish breakout above 200-day MA",
            "reasoning": "Strong uptrend with positive momentum",
        },
        raw_text='{"direction": "long", "confidence": 0.85, ...}',
        model="gpt-4-turbo",
        stop_reason="stop",
        usage_tokens={"prompt": 100, "completion": 50, "total": 150},
    )


@pytest.fixture
def mock_signal():
    """Create mock persisted signal."""
    signal = MagicMock(spec=Signal)
    signal.id = uuid4()
    signal.asset_id = uuid4()
    signal.direction = "long"
    signal.confidence = 0.85
    signal.catalyst = "Bullish breakout"
    signal.reasoning = "Strong uptrend"
    return signal


class TestSignalServiceInit:
    """Tests for service initialization."""

    def test_service_init(self, mock_router, mock_session):
        """Test service initialization."""
        service = SignalService(router=mock_router, session=mock_session)
        assert service.router == mock_router
        assert service.session == mock_session


class TestLoadActivePrompt:
    """Tests for loading active prompt."""

    def test_load_active_prompt_success(self, signal_service, mock_session, mock_prompt_version):
        """Test loading active prompt succeeds."""
        mock_session.query.return_value.filter.return_value.first.return_value = (
            mock_prompt_version
        )

        prompt = signal_service._load_active_prompt()

        assert prompt == mock_prompt_version
        mock_session.query.assert_called_once()

    def test_load_active_prompt_not_found(self, signal_service, mock_session):
        """Test loading prompt fails when not found."""
        mock_session.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="No active signal_engine prompt found"):
            signal_service._load_active_prompt()


class TestAssembleContext:
    """Tests for context assembly."""

    def test_assemble_context_basic(self, signal_service, signal_input):
        """Test assembling basic context."""
        context = signal_service._assemble_context(signal_input)

        assert context["asset_symbol"] == "AAPL"
        assert context["current_price"] == 150.0
        assert context["sma_20"] == 148.0
        assert context["rsi_14"] == 65.0
        assert context["trend_direction"] == "up"

    def test_assemble_context_with_macro(self, signal_service, signal_input):
        """Test assembling context with macro data."""
        signal_input.macro_context = {
            "fed_rate": 5.5,
            "market_sentiment": "bullish",
        }

        context = signal_service._assemble_context(signal_input)

        assert context["fed_rate"] == 5.5
        assert context["market_sentiment"] == "bullish"

    def test_assemble_context_with_news(self, signal_service, signal_input):
        """Test assembling context with news."""
        signal_input.recent_news = [
            {
                "headline": "Strong earnings beat",
                "sentiment": "positive",
            },
            {
                "headline": "Guidance raised",
                "sentiment": "positive",
            },
        ]

        context = signal_service._assemble_context(signal_input)

        assert "news_summary" in context
        assert "Strong earnings beat" in context["news_summary"]
        assert "positive" in context["news_summary"]


class TestSummarizeNews:
    """Tests for news summarization."""

    def test_summarize_empty_news(self, signal_service):
        """Test summarizing empty news list."""
        summary = signal_service._summarize_news([])
        assert summary == "No recent news"

    def test_summarize_single_news(self, signal_service):
        """Test summarizing single news."""
        news = [
            {
                "headline": "Strong earnings",
                "sentiment": "positive",
            }
        ]
        summary = signal_service._summarize_news(news)
        assert "Strong earnings" in summary
        assert "positive" in summary

    def test_summarize_multiple_news(self, signal_service):
        """Test summarizing multiple news."""
        news = [
            {"headline": f"News {i}", "sentiment": "positive"} for i in range(10)
        ]
        summary = signal_service._summarize_news(news)
        # Should limit to 5 most recent
        for i in range(5):
            assert f"News {i}" in summary


class TestValidateSignalOutput:
    """Tests for output validation."""

    def test_validate_output_valid(self, signal_service, llm_response):
        """Test validating valid output."""
        schema = {
            "type": "object",
            "properties": {
                "direction": {"type": "string"},
                "confidence": {"type": "number"},
            },
            "required": ["direction", "confidence"],
        }

        # Should not raise
        signal_service._validate_signal_output(llm_response.content, schema)

    def test_validate_output_missing_required(self, signal_service):
        """Test validation fails for missing required field."""
        output = {
            "direction": "long",
            # Missing required confidence
        }
        schema = {
            "type": "object",
            "required": ["direction", "confidence"],
        }

        with pytest.raises(Exception, match="Missing required fields"):
            signal_service._validate_signal_output(output, schema)

    def test_validate_output_invalid_direction(self, signal_service):
        """Test validation fails for invalid direction."""
        output = {
            "direction": "invalid",
            "confidence": 0.85,
        }
        schema = {
            "type": "object",
            "required": ["direction", "confidence"],
        }

        with pytest.raises(Exception, match="Invalid direction"):
            signal_service._validate_signal_output(output, schema)

    def test_validate_output_invalid_confidence(self, signal_service):
        """Test validation fails for invalid confidence."""
        output = {
            "direction": "long",
            "confidence": 1.5,  # Out of bounds
        }
        schema = {
            "type": "object",
            "required": ["direction", "confidence"],
        }

        with pytest.raises(Exception, match="Invalid confidence"):
            signal_service._validate_signal_output(output, schema)


class TestCalculateSignalScore:
    """Tests for signal score calculation."""

    def test_calculate_score_high_confidence(self, signal_service):
        """Test score calculation with high confidence."""
        output = {"confidence": 0.9}
        score = signal_service._calculate_signal_score(output)
        assert score == 0.9

    def test_calculate_score_low_confidence(self, signal_service):
        """Test score calculation with low confidence."""
        output = {"confidence": 0.3}
        score = signal_service._calculate_signal_score(output)
        assert score == 0.3

    def test_calculate_score_bounds(self, signal_service):
        """Test score is bounded 0-1."""
        # Test clamping
        output = {"confidence": 1.5}
        score = signal_service._calculate_signal_score(output)
        assert score == 1.0

        output = {"confidence": -0.5}
        score = signal_service._calculate_signal_score(output)
        assert score == 0.0


class TestPersistSignal:
    """Tests for signal persistence."""

    def test_persist_signal_success(
        self, signal_service, mock_session, signal_input, mock_prompt_version, llm_response
    ):
        """Test persisting signal to database."""
        mock_session.add = MagicMock()
        mock_session.commit = MagicMock()
        mock_session.refresh = MagicMock()

        signal_service._persist_signal(
            signal_input=signal_input,
            prompt_version=mock_prompt_version,
            llm_output=llm_response.content,
        )

        # Check that session.add was called
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()


class TestBuildOutput:
    """Tests for output building."""

    def test_build_output(self, signal_service, mock_signal, llm_response, mock_prompt_version):
        """Test building signal output."""
        output = signal_service._build_output(
            signal=mock_signal,
            llm_output=llm_response.content,
            prompt_version=mock_prompt_version,
        )

        assert isinstance(output, SignalOutput)
        assert output.signal_id == mock_signal.id
        assert output.asset_id == mock_signal.asset_id
        assert output.direction == "long"
        assert output.confidence == 0.85
        assert output.prompt_version_id == mock_prompt_version.id


class TestGenerateSignal:
    """Tests for main generate_signal method."""

    @pytest.mark.asyncio
    async def test_generate_signal_success(
        self,
        signal_service,
        mock_session,
        mock_router,
        signal_input,
        mock_prompt_version,
        llm_response,
        mock_signal,
    ):
        """Test successful signal generation."""
        # Setup mocks
        mock_session.query.return_value.filter.return_value.first.return_value = (
            mock_prompt_version
        )
        mock_session.add = MagicMock()
        mock_session.commit = MagicMock()
        mock_session.refresh = MagicMock()

        mock_provider = AsyncMock()
        mock_provider.generate_structured = AsyncMock(return_value=llm_response)
        mock_router.get_provider.return_value = mock_provider

        # Generate signal
        result = await signal_service.generate_signal(signal_input)

        # Verify result
        assert isinstance(result, SignalOutput)
        assert result.direction == "long"
        assert result.confidence == 0.85

        # Verify LLM was called
        mock_provider.generate_structured.assert_called_once()

        # Verify persistence happened
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_signal_no_prompt(
        self, signal_service, mock_session, signal_input
    ):
        """Test signal generation fails without active prompt."""
        mock_session.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="No active signal_engine prompt found"):
            await signal_service.generate_signal(signal_input)

    @pytest.mark.asyncio
    async def test_generate_signal_llm_error(
        self, signal_service, mock_session, mock_router, signal_input, mock_prompt_version
    ):
        """Test signal generation handles LLM error."""
        mock_session.query.return_value.filter.return_value.first.return_value = (
            mock_prompt_version
        )

        mock_provider = AsyncMock()
        mock_provider.generate_structured = AsyncMock(side_effect=Exception("API error"))
        mock_router.get_provider.return_value = mock_provider

        with pytest.raises(Exception, match="API error"):
            await signal_service.generate_signal(signal_input)

    @pytest.mark.asyncio
    async def test_generate_signal_validation_error(
        self,
        signal_service,
        mock_session,
        mock_router,
        signal_input,
        mock_prompt_version,
    ):
        """Test signal generation with invalid LLM output."""
        mock_session.query.return_value.filter.return_value.first.return_value = (
            mock_prompt_version
        )

        # LLM returns invalid output (missing required field)
        invalid_response = LLMResponse(
            content={"confidence": 0.85},  # Missing required direction
            raw_text="{}",
            model="gpt-4",
            stop_reason="stop",
        )

        mock_provider = AsyncMock()
        mock_provider.generate_structured = AsyncMock(return_value=invalid_response)
        mock_router.get_provider.return_value = mock_provider

        with pytest.raises(Exception, match="Missing required fields"):
            await signal_service.generate_signal(signal_input)
