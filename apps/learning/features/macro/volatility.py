"""Macro volatility features — VIX regime classification."""

from __future__ import annotations

from typing import Sequence


def vix_regime(vix: float) -> str:
    """Classify the VIX into broad volatility regimes."""
    if vix < 15:
        return "low_vol"
    if vix < 25:
        return "normal"
    if vix < 35:
        return "elevated"
    return "crisis"


def vix_percentile(vix: float, history: Sequence[float]) -> float | None:
    """Return the percentile rank of the current VIX reading vs historical values."""
    if not history:
        return None
    below = sum(1 for v in history if v < vix)
    return 100 * below / len(history)
