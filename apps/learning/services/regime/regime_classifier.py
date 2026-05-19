"""RegimeClassifier — classify the current market regime.

Regime is one of: risk_on, risk_off, high_vol, low_vol, chop, trend.
The classifier uses a rules-based heuristic that combines VIX level,
price momentum, and breadth metrics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class RegimeInput:
    """Snapshot of market indicators used for regime classification."""

    vix: float
    spy_roc_21: float  # 21-day rate-of-change for SPY
    advance_decline_ratio: float  # >1 = more advancers
    yield_curve_slope: float  # 10Y - 2Y spread in percent


@dataclass(frozen=True)
class RegimeOutput:
    """Classified market regime."""

    regime: str  # one of MarketRegimeType values
    confidence: float  # 0–1 rule-based confidence
    reason: str


class RegimeClassifier:
    """Rules-based market regime classifier."""

    def classify(self, inputs: RegimeInput) -> RegimeOutput:
        """Return the current regime given market indicator snapshot."""
        if inputs.vix >= 30:
            return RegimeOutput(
                regime="high_vol",
                confidence=0.85,
                reason=f"VIX={inputs.vix:.1f} above 30 threshold",
            )

        if inputs.vix <= 14:
            if inputs.spy_roc_21 > 0 and inputs.advance_decline_ratio > 1.1:
                return RegimeOutput(
                    regime="risk_on",
                    confidence=0.80,
                    reason="Low VIX + positive momentum + broad advance",
                )
            return RegimeOutput(
                regime="low_vol",
                confidence=0.70,
                reason=f"VIX={inputs.vix:.1f} below 14, mixed breadth",
            )

        if inputs.spy_roc_21 > 0.03:
            return RegimeOutput(
                regime="trend",
                confidence=0.75,
                reason=f"Strong SPY 21-day momentum ({inputs.spy_roc_21:.1%})",
            )

        if abs(inputs.spy_roc_21) < 0.01:
            return RegimeOutput(
                regime="chop",
                confidence=0.65,
                reason="Low momentum, sideways price action",
            )

        if inputs.advance_decline_ratio < 0.9 or inputs.yield_curve_slope < 0:
            return RegimeOutput(
                regime="risk_off",
                confidence=0.72,
                reason="Negative breadth or inverted curve",
            )

        return RegimeOutput(
            regime="chop",
            confidence=0.50,
            reason="No dominant regime signal",
        )
