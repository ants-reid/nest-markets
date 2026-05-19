"""Deterministic ATR implementation."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ATRResult:
    """ATR computation result."""

    value: float | None


def calculate_true_range(high: float, low: float, previous_close: float | None) -> float:
    """Compute true range for one bar."""
    intrabar_range = high - low
    if previous_close is None:
        return intrabar_range
    return max(
        intrabar_range,
        abs(high - previous_close),
        abs(low - previous_close),
    )


def calculate_atr(
    highs_or_bars: Sequence[float] | Sequence[dict[str, Any]],
    lows_or_period: Sequence[float] | int | None = None,
    closes: Sequence[float] | None = None,
    period: int = 14,
) -> ATRResult:
    """Compute average true range using Wilder smoothing.

    Accepts either:
    - Bar dicts: calculate_atr(bars, period)
    - Separate sequences: calculate_atr(highs, lows, closes, period=14)
    """
    if isinstance(lows_or_period, int):
        # calculate_atr(bars, period) — bar dict path
        bars = highs_or_bars
        _period = lows_or_period
        return _atr_from_bars(bars, _period)  # type: ignore[arg-type]
    elif lows_or_period is None and closes is None:
        # calculate_atr(bars) — bar dict path with default period
        return _atr_from_bars(highs_or_bars, period)  # type: ignore[arg-type]
    else:
        # calculate_atr(highs, lows, closes, period=14) — legacy 3-series path
        if lows_or_period is None or closes is None:
            raise ValueError("lows and closes must both be provided")
        return _atr_from_series(highs_or_bars, lows_or_period, closes, period)  # type: ignore[arg-type]


def _atr_from_bars(bars: Sequence[dict[str, Any]], period: int) -> ATRResult:
    if period <= 0:
        raise ValueError("period must be positive")
    highs = [float(bar["high"]) for bar in bars]
    lows_series = [float(bar["low"]) for bar in bars]
    closes_series = [float(bar["close"]) for bar in bars]
    return _compute_atr(highs, lows_series, closes_series, period)


def _atr_from_series(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    period: int,
) -> ATRResult:
    if period <= 0:
        raise ValueError("period must be positive")
    return _compute_atr(
        [float(v) for v in highs],
        [float(v) for v in lows],
        [float(v) for v in closes],
        period,
    )


def _compute_atr(
    highs: list[float],
    lows_series: list[float],
    closes_series: list[float],
    period: int,
) -> ATRResult:
    if not (len(highs) == len(lows_series) == len(closes_series)):
        raise ValueError("high, low, and close series must have the same length")
    if len(highs) < period + 1:
        return ATRResult(value=None)

    true_ranges: list[float] = []
    for idx in range(1, len(highs)):
        true_ranges.append(
            calculate_true_range(highs[idx], lows_series[idx], closes_series[idx - 1])
        )

    atr_value = sum(true_ranges[:period]) / float(period)
    for tr_value in true_ranges[period:]:
        atr_value = ((atr_value * (period - 1)) + tr_value) / float(period)

    return ATRResult(value=atr_value)
    for idx in range(1, len(highs)):
        true_ranges.append(
            calculate_true_range(highs[idx], lows_series[idx], closes_series[idx - 1])
        )

    atr_value = sum(true_ranges[:period]) / float(period)
    for tr_value in true_ranges[period:]:
        atr_value = ((atr_value * (period - 1)) + tr_value) / float(period)

    return atr_value
