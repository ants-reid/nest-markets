"""Deterministic ADX implementation."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from app.indicators.atr import calculate_true_range


@dataclass(frozen=True)
class ADXResult:
    """Latest ADX with directional indicators."""

    adx: float | None
    di_plus: float | None
    di_minus: float | None


def calculate_adx(
    highs_or_bars: Sequence[float] | Sequence[dict[str, Any]],
    lows: Sequence[float] | int | None = None,
    closes: Sequence[float] | None = None,
    period: int = 14,
) -> ADXResult | None:
    """Compute ADX using conservative Wilder smoothing steps."""
    # Support calculate_adx(bars, period) where bars are dicts
    if isinstance(lows, int):
        period = lows
        lows = None

    if period <= 0:
        raise ValueError("period must be positive")

    highs: list[float]
    lows_series: list[float]
    closes_series: list[float]

    if lows is None and closes is None:
        bars = highs_or_bars
        highs = [float(bar["high"]) for bar in bars]  # type: ignore[index]
        lows_series = [float(bar["low"]) for bar in bars]  # type: ignore[index]
        closes_series = [float(bar["close"]) for bar in bars]  # type: ignore[index]
    else:
        if lows is None or closes is None:
            raise ValueError("lows and closes must both be provided")
        highs = [float(v) for v in highs_or_bars]  # type: ignore[arg-type]
        lows_series = [float(v) for v in lows]
        closes_series = [float(v) for v in closes]

    if not (len(highs) == len(lows_series) == len(closes_series)):
        raise ValueError("high, low, and close series must have the same length")
    if len(highs) < (period * 2) + 1:
        if lows is None and closes is None:
            return ADXResult(adx=None, di_plus=None, di_minus=None)
        return None

    true_ranges: list[float] = []
    plus_dm: list[float] = []
    minus_dm: list[float] = []

    for idx in range(1, len(highs)):
        up_move = highs[idx] - highs[idx - 1]
        down_move = lows_series[idx - 1] - lows_series[idx]

        plus = up_move if up_move > down_move and up_move > 0.0 else 0.0
        minus = down_move if down_move > up_move and down_move > 0.0 else 0.0

        plus_dm.append(plus)
        minus_dm.append(minus)
        true_ranges.append(
            calculate_true_range(highs[idx], lows_series[idx], closes_series[idx - 1])
        )

    smoothed_tr = sum(true_ranges[:period])
    smoothed_plus = sum(plus_dm[:period])
    smoothed_minus = sum(minus_dm[:period])

    dx_values: list[float] = []
    latest_di_plus = 0.0
    latest_di_minus = 0.0

    def _dx(tr_value: float, plus_value: float, minus_value: float) -> tuple[float, float, float]:
        if tr_value <= 0.0:
            return 0.0, 0.0, 0.0
        di_plus = 100.0 * (plus_value / tr_value)
        di_minus = 100.0 * (minus_value / tr_value)
        denominator = di_plus + di_minus
        if denominator == 0.0:
            return 0.0, di_plus, di_minus
        return 100.0 * abs(di_plus - di_minus) / denominator, di_plus, di_minus

    first_dx, latest_di_plus, latest_di_minus = _dx(smoothed_tr, smoothed_plus, smoothed_minus)
    dx_values.append(first_dx)

    for idx in range(period, len(true_ranges)):
        smoothed_tr = smoothed_tr - (smoothed_tr / period) + true_ranges[idx]
        smoothed_plus = smoothed_plus - (smoothed_plus / period) + plus_dm[idx]
        smoothed_minus = smoothed_minus - (smoothed_minus / period) + minus_dm[idx]
        dx, latest_di_plus, latest_di_minus = _dx(smoothed_tr, smoothed_plus, smoothed_minus)
        dx_values.append(dx)

    if len(dx_values) < period:
        return None

    adx_value = sum(dx_values[:period]) / float(period)
    for dx in dx_values[period:]:
        adx_value = ((adx_value * (period - 1)) + dx) / float(period)

    return ADXResult(adx=adx_value, di_plus=latest_di_plus, di_minus=latest_di_minus)
