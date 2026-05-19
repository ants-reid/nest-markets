"""Prompt and schema loading helpers.

Separate from providers. Used by signal services to load prompts/schemas
from database or files.
"""

import json
from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)


class PromptLoader:
    """Loads prompts from database or files.

    Decoupled from database models - accepts any prompt dict.
    """

    @staticmethod
    def validate_prompt(prompt: dict[str, Any]) -> bool:
        """Validate prompt has required fields.

        Args:
            prompt: Prompt dict (from DB or file)

        Returns:
            True if valid

        Raises:
            ValueError: If required fields missing
        """
        required = ["system_prompt", "user_template"]
        for field in required:
            if field not in prompt:
                raise ValueError(f"Missing required prompt field: {field}")
        return True

    @staticmethod
    def render_user_message(user_template: str, context: dict[str, Any]) -> str:
        """Render user template with context.

        Args:
            user_template: Template with {variable} placeholders
            context: Context dict with values

        Returns:
            Rendered user message

        Note:
            Uses simple .format() - no complex template logic.
            Template author is responsible for valid placeholders.
        """
        try:
            return user_template.format(**context)
        except KeyError as e:
            raise ValueError(f"Missing template variable: {e}") from e


class SchemaLoader:
    """Loads and validates JSON schemas.

    Decoupled from database models - accepts any schema dict or JSON string.
    """

    @staticmethod
    def load_schema(schema_input: str | dict[str, Any]) -> dict[str, Any]:
        """Load schema from JSON string or dict.

        Args:
            schema_input: JSON schema as string or dict

        Returns:
            Parsed schema dict

        Raises:
            ValueError: If JSON is invalid
            TypeError: If input is wrong type
        """
        if isinstance(schema_input, dict):
            return schema_input

        if isinstance(schema_input, str):
            try:
                return json.loads(schema_input)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON schema: {e}") from e

        raise TypeError(f"Schema must be dict or JSON string, got {type(schema_input)}")

    @staticmethod
    def validate_schema(schema: dict[str, Any]) -> bool:
        """Validate schema structure.

        Args:
            schema: JSON schema dict

        Returns:
            True if valid

        Raises:
            ValueError: If schema is invalid

        Note:
            Basic validation. Full JSON Schema validation is done by providers.
        """
        if not isinstance(schema, dict):
            raise ValueError("Schema must be a dict")

        # Ensure root has type
        if "type" not in schema:
            logger.warning("schema_missing_type")
            # Still valid, providers may add it

        return True

    @staticmethod
    def extract_required_fields(schema: dict[str, Any]) -> list[str]:
        """Extract required field names from schema.

        Args:
            schema: JSON schema dict

        Returns:
            List of required field names, empty if none specified
        """
        return schema.get("required", [])


class PromptContext:
    """Helper for building consistent prompt context.

    Ensures all prompt templates receive consistent context structure.
    """

    @staticmethod
    def build_signal_context(
        asset_symbol: str,
        current_price: float,
        features: dict[str, Any],
        recent_bars: Optional[list[dict[str, Any]]] = None,
        market_regime: Optional[str] = None,
    ) -> dict[str, Any]:
        """Build context dict for signal generation prompt.

        Args:
            asset_symbol: Ticker symbol (e.g., 'AAPL')
            current_price: Current price
            features: Feature snapshot (from feature service)
            recent_bars: Optional recent OHLCV bars
            market_regime: Optional market regime classification

        Returns:
            Context dict ready for template rendering
        """
        context = {
            "asset_symbol": asset_symbol,
            "current_price": current_price,
            "sma_20": features.get("sma_20"),
            "sma_50": features.get("sma_50"),
            "sma_200": features.get("sma_200"),
            "rsi_14": features.get("rsi_14"),
            "atr_14": features.get("atr_14"),
            "volatility": features.get("volatility"),
            "trend_direction": features.get("trend_direction"),
            "trend_strength": features.get("trend_strength"),
            "market_quality": features.get("market_quality"),
            "spread_bps": features.get("spread_bps"),
        }

        if recent_bars:
            context["recent_bars"] = recent_bars

        if market_regime:
            context["market_regime"] = market_regime

        logger.debug("prompt_context_built", asset=asset_symbol)
        return context
