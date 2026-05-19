"""Macro liquidity condition features."""

from __future__ import annotations


def fed_funds_regime(rate: float) -> str:
    """Classify the Fed Funds rate environment."""
    if rate < 1.0:
        return "ultra_loose"
    if rate < 2.5:
        return "loose"
    if rate < 4.5:
        return "neutral"
    return "tight"


def real_rate(nominal_rate: float, inflation_rate: float) -> float:
    """Return the approximate real interest rate."""
    return nominal_rate - inflation_rate
