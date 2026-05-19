"""Cross-sectional relative rank features."""

from __future__ import annotations

from typing import Mapping


def percentile_rank(
    symbol: str,
    universe_returns: Mapping[str, float],
) -> float | None:
    """Return the symbol's percentile rank within the universe (0–100).

    Returns None if the symbol is not in the universe.
    """
    if symbol not in universe_returns:
        return None
    sorted_returns = sorted(universe_returns.values())
    value = universe_returns[symbol]
    rank = sorted_returns.index(value)
    return 100 * rank / max(len(sorted_returns) - 1, 1)


def z_score_rank(
    symbol: str,
    universe_returns: Mapping[str, float],
) -> float | None:
    """Return the z-score of the symbol's return vs the universe."""
    if symbol not in universe_returns or len(universe_returns) < 2:
        return None
    values = list(universe_returns.values())
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    import math
    std = math.sqrt(variance)
    if std == 0:
        return 0.0
    return (universe_returns[symbol] - mean) / std
