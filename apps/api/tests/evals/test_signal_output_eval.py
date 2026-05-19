"""Eval harness: structural validation of SignalService.generate_signal output.

Evals differ from unit tests — they verify that the service contract (schema,
field types, value ranges) holds for a known canonical input when the LLM call
is replaced by a deterministic mock. These tests are intentionally kept
separate from the main test suite to allow independent extension and scoring.

Pattern: mock the LLM provider, run the full service pipeline, assert that
the returned SignalOutput satisfies all structural invariants.

To run evals only:
    cd apps/api && PYTHONPATH=$PWD .venv/bin/python -m pytest tests/evals/ -v
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from app.services.signal_service import SignalInput, SignalOutput, SignalService

# ---------------------------------------------------------------------------
# Canonical eval input (deterministic, repeatable)
# ---------------------------------------------------------------------------

CANONICAL_INPUT = SignalInput(
    asset="EURUSD",
    timeframe="1h",
    latest_price=1.0815,
    feature_snapshot={
        "regime_preclassification": "trend",
        "rsi_14": 58.2,
        "atr_14": 0.0031,
        "sma_20": 1.0798,
        "sma_50": 1.0775,
    },
    catalyst_context={
        "event": "ECB rate decision",
        "sentiment_score": 0.65,
        "macro_surprise": "hawkish",
    },
    risk_notes="max_risk_per_trade_pct=1.0",
)

# Deterministic mock LLM payload matching signal_schema_v1.json
_MOCK_PAYLOAD: dict[str, Any] = {
    "asset": "EURUSD",
    "timeframe": "1h",
    "direction": "long",
    "regime": "trend",
    "setup_type": "trend_pullback",
    "entry_zone": [1.0810, 1.0820],
    "stop_price": 1.0790,
    "target_price": 1.0850,
    "confidence": 0.75,
    "horizon_label": "1_3_days",
    "catalyst_type": "macro",
    "catalyst_score": 0.65,
    "catalyst_summary": "ECB hawkish surprise supports EUR strength near-term.",
    "thesis": "Trend pullback entry after ECB catalyst with defined R:R.",
    "invalidators": ["price_closes_below_1.076", "risk_off_spike"],
    "signal_score": 78.5,
    "should_trade": True,
}


def _make_service_with_mock_provider(payload: dict[str, Any]) -> SignalService:
    """Build a SignalService wired to a mock provider returning a fixed payload."""
    mock_provider = MagicMock()
    mock_provider.generate_structured = AsyncMock(return_value=payload)

    mock_router = MagicMock()
    mock_router.get_provider.return_value = mock_provider

    return SignalService(router=mock_router)


# ---------------------------------------------------------------------------
# QA-082: Structural invariants eval
# ---------------------------------------------------------------------------


class TestSignalOutputStructuralInvariants:
    """QA-082: SignalService.generate_signal returns a structurally valid SignalOutput."""

    def setup_method(self) -> None:
        service = _make_service_with_mock_provider(_MOCK_PAYLOAD)
        self.result: SignalOutput = asyncio.run(
            service.generate_signal(CANONICAL_INPUT)
        )

    def test_returns_signal_output_type(self) -> None:
        assert isinstance(self.result, SignalOutput)

    def test_asset_matches_input(self) -> None:
        assert self.result.asset == CANONICAL_INPUT.asset

    def test_timeframe_matches_input(self) -> None:
        assert self.result.timeframe == CANONICAL_INPUT.timeframe

    def test_direction_is_valid(self) -> None:
        assert self.result.direction in {"long", "short", "flat"}

    def test_confidence_in_range(self) -> None:
        assert 0.0 <= self.result.confidence <= 1.0

    def test_signal_score_in_range(self) -> None:
        assert 0.0 <= self.result.signal_score <= 100.0

    def test_entry_zone_is_ordered_tuple(self) -> None:
        low, high = self.result.entry_zone
        assert isinstance(low, float)
        assert isinstance(high, float)
        assert low <= high

    def test_stop_price_is_positive(self) -> None:
        assert self.result.stop_price > 0.0

    def test_target_price_is_positive(self) -> None:
        assert self.result.target_price > 0.0

    def test_invalidators_is_non_empty_list(self) -> None:
        assert isinstance(self.result.invalidators, list)
        assert len(self.result.invalidators) > 0

    def test_should_trade_is_bool(self) -> None:
        assert isinstance(self.result.should_trade, bool)

    def test_thesis_is_non_empty_string(self) -> None:
        assert isinstance(self.result.thesis, str)
        assert len(self.result.thesis) > 0

    def test_catalyst_score_in_range(self) -> None:
        assert 0.0 <= self.result.catalyst_score <= 1.0
