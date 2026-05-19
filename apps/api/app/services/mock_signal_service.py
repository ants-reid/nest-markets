"""Deterministic mock signal service for MVP development and testing.

Used by the workflow route when ``use_mock_signal=True`` to avoid LLM calls
during development, smoke tests, and UI-driven workflow runs.

This lives in services/ so the route file stays thin.
"""

from __future__ import annotations

from app.services.signal_service import SignalInput, SignalOutput


class MockSignalService:
    """Return a deterministic flat/no-trade signal without calling the LLM."""

    async def generate_signal(self, signal_input: SignalInput) -> SignalOutput:
        """Return a safe flat/no-trade signal for all mock-mode requests."""
        return SignalOutput(
            asset=signal_input.asset,
            timeframe=signal_input.timeframe,
            direction="flat",
            regime="range",
            setup_type="none",
            entry_zone=(0.0, 0.0),
            stop_price=0.0,
            target_price=0.0,
            confidence=0.0,
            horizon_label="intraday",
            catalyst_type="none",
            catalyst_score=0.0,
            catalyst_summary="Mock signal — no LLM called.",
            thesis="Mock-safe no-trade response.",
            invalidators=["mock mode active"],
            signal_score=0.0,
            should_trade=False,
        )
