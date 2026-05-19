"""Sector relative-strength feature."""

from __future__ import annotations

from typing import Mapping


def sector_relative_strength(
    symbol_returns: Mapping[str, float],
    sector_members: Mapping[str, list[str]],
) -> dict[str, float]:
    """Return per-sector mean return.

    Args:
        symbol_returns: mapping of symbol → period return (as decimal).
        sector_members: mapping of sector_name → list of symbols.

    Returns:
        Mapping of sector_name → mean return for that sector.
    """
    result: dict[str, float] = {}
    for sector, symbols in sector_members.items():
        returns = [symbol_returns[s] for s in symbols if s in symbol_returns]
        if returns:
            result[sector] = sum(returns) / len(returns)
    return result
