"""Tests for helpers."""

import pytest

from app.clients.llm.helpers import PromptContext, PromptLoader, SchemaLoader


class TestPromptLoader:
    """Tests for PromptLoader."""

    def test_validate_prompt_valid(self):
        """Test validating valid prompt."""
        prompt = {
            "system_prompt": "You are helpful.",
            "user_template": "Answer {question}",
            "schema_json": "{}",
        }
        assert PromptLoader.validate_prompt(prompt) is True

    def test_validate_prompt_missing_system(self):
        """Test validation fails for missing system_prompt."""
        prompt = {"user_template": "Hello"}
        with pytest.raises(ValueError, match="system_prompt"):
            PromptLoader.validate_prompt(prompt)

    def test_validate_prompt_missing_template(self):
        """Test validation fails for missing user_template."""
        prompt = {"system_prompt": "Hello"}
        with pytest.raises(ValueError, match="user_template"):
            PromptLoader.validate_prompt(prompt)

    def test_render_user_message_simple(self):
        """Test rendering user message with simple variables."""
        template = "Analyze {symbol} at {price}"
        context = {"symbol": "AAPL", "price": 150.25}
        result = PromptLoader.render_user_message(template, context)
        assert result == "Analyze AAPL at 150.25"

    def test_render_user_message_missing_variable(self):
        """Test rendering fails with missing variable."""
        template = "Analyze {symbol} at {price}"
        context = {"symbol": "AAPL"}
        with pytest.raises(ValueError, match="price"):
            PromptLoader.render_user_message(template, context)

    def test_render_user_message_no_vars(self):
        """Test rendering template without variables."""
        template = "Analyze the market"
        context = {}
        result = PromptLoader.render_user_message(template, context)
        assert result == "Analyze the market"


class TestSchemaLoader:
    """Tests for SchemaLoader."""

    def test_load_schema_from_dict(self):
        """Test loading schema from dict."""
        schema = {"type": "object", "properties": {"key": {"type": "string"}}}
        result = SchemaLoader.load_schema(schema)
        assert result == schema

    def test_load_schema_from_json_string(self):
        """Test loading schema from JSON string."""
        schema_str = '{"type": "object", "properties": {"key": {"type": "string"}}}'
        result = SchemaLoader.load_schema(schema_str)
        assert result["type"] == "object"
        assert "properties" in result

    def test_load_schema_invalid_json(self):
        """Test loading invalid JSON string fails."""
        schema_str = "{invalid json}"
        with pytest.raises(ValueError, match="Invalid JSON"):
            SchemaLoader.load_schema(schema_str)

    def test_load_schema_wrong_type(self):
        """Test loading wrong type fails."""
        with pytest.raises(TypeError, match="must be dict or JSON string"):
            SchemaLoader.load_schema(123)

    def test_validate_schema_valid(self):
        """Test validating valid schema."""
        schema = {"type": "object", "properties": {}}
        assert SchemaLoader.validate_schema(schema) is True

    def test_validate_schema_not_dict(self):
        """Test validating non-dict fails."""
        with pytest.raises(ValueError, match="must be a dict"):
            SchemaLoader.validate_schema([])

    def test_extract_required_fields(self):
        """Test extracting required fields."""
        schema = {
            "type": "object",
            "properties": {"id": {}, "name": {}},
            "required": ["id", "name"],
        }
        required = SchemaLoader.extract_required_fields(schema)
        assert required == ["id", "name"]

    def test_extract_required_fields_empty(self):
        """Test extracting when no required fields."""
        schema = {"type": "object", "properties": {}}
        required = SchemaLoader.extract_required_fields(schema)
        assert required == []


class TestPromptContext:
    """Tests for PromptContext helper."""

    def test_build_signal_context_minimal(self):
        """Test building context with minimal fields."""
        features = {
            "sma_20": 150.0,
            "rsi_14": 65.0,
            "trend_direction": "up",
        }
        context = PromptContext.build_signal_context(
            asset_symbol="AAPL",
            current_price=155.0,
            features=features,
        )
        assert context["asset_symbol"] == "AAPL"
        assert context["current_price"] == 155.0
        assert context["sma_20"] == 150.0
        assert context["rsi_14"] == 65.0
        assert context["trend_direction"] == "up"

    def test_build_signal_context_with_bars(self):
        """Test building context with recent bars."""
        features = {}
        bars = [
            {"open": 150, "high": 155, "low": 149, "close": 154, "volume": 1000000},
        ]
        context = PromptContext.build_signal_context(
            asset_symbol="AAPL",
            current_price=154.0,
            features=features,
            recent_bars=bars,
        )
        assert context["recent_bars"] == bars

    def test_build_signal_context_with_regime(self):
        """Test building context with market regime."""
        features = {}
        context = PromptContext.build_signal_context(
            asset_symbol="AAPL",
            current_price=155.0,
            features=features,
            market_regime="trending_up",
        )
        assert context["market_regime"] == "trending_up"

    def test_build_signal_context_all_fields(self):
        """Test building context with all fields."""
        features = {
            "sma_20": 150.0,
            "sma_50": 148.0,
            "sma_200": 145.0,
            "rsi_14": 65.0,
            "atr_14": 2.5,
            "volatility": 0.015,
            "trend_direction": "up",
            "trend_strength": 0.8,
            "market_quality": "good",
            "spread_bps": 1.0,
        }
        bars = [{"close": 155, "volume": 1000000}]
        context = PromptContext.build_signal_context(
            asset_symbol="AAPL",
            current_price=155.0,
            features=features,
            recent_bars=bars,
            market_regime="trending_up",
        )
        assert context["asset_symbol"] == "AAPL"
        assert context["sma_200"] == 145.0
        assert context["market_regime"] == "trending_up"
        assert context["recent_bars"] == bars
