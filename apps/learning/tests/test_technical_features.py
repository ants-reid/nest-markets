"""Phase 7 — technical feature tests."""

from __future__ import annotations

from apps.learning.features.technical.momentum import rate_of_change, momentum_score
from apps.learning.features.technical.volatility import average_true_range, realised_volatility
from apps.learning.features.technical.levels import vwap, distance_from_high, pivot_high, pivot_low
from apps.learning.features.technical.patterns import is_range_compressed, is_breakout
from apps.learning.features.technical.volume import relative_volume, volume_trend


class TestMomentum:
    def test_roc_basic(self):
        prices = [100.0] * 21 + [105.0]
        assert rate_of_change(prices, 21) == pytest.approx(0.05)

    def test_roc_insufficient_data(self):
        assert rate_of_change([100.0], 5) is None

    def test_momentum_score_keys(self):
        prices = [float(i + 100) for i in range(70)]
        result = momentum_score(prices)
        assert set(result.keys()) == {"roc_5", "roc_21", "roc_63"}


class TestVolatility:
    def test_atr_basic(self):
        highs = [101.0] * 15
        lows = [99.0] * 15
        closes = [100.0] * 15
        result = average_true_range(highs, lows, closes, period=14)
        assert result == pytest.approx(2.0)

    def test_atr_insufficient(self):
        assert average_true_range([101], [99], [100], period=14) is None

    def test_realised_vol_positive(self):
        import math
        prices = [100.0 * (1.01 ** i) for i in range(25)]
        vol = realised_volatility(prices, period=21, annualise=False)
        assert vol is not None
        assert vol > 0


class TestLevels:
    def test_vwap_basic(self):
        closes = [100.0, 102.0, 98.0]
        volumes = [1000.0, 2000.0, 500.0]
        expected = (100 * 1000 + 102 * 2000 + 98 * 500) / 3500
        assert vwap(closes, volumes) == pytest.approx(expected)

    def test_vwap_empty(self):
        assert vwap([], []) is None

    def test_distance_from_high(self):
        highs = [110.0] * 52
        result = distance_from_high(100.0, highs, window=52)
        assert result == pytest.approx(-10 / 110)


class TestPatterns:
    def test_compression_detected(self):
        highs = [100.5] * 10
        lows = [99.5] * 10
        assert is_range_compressed(highs, lows, period=10, threshold=0.02) is True

    def test_breakout_detected(self):
        closes = [100.0] * 20 + [110.0]
        highs = [101.0] * 20 + [111.0]
        assert is_breakout(closes, highs, lookback=20) is True


class TestVolume:
    def test_relative_volume_above_average(self):
        volumes = [1000.0] * 21
        volumes[-1] = 3000.0
        result = relative_volume(volumes, period=20)
        assert result == pytest.approx(3.0)

    def test_relative_volume_insufficient(self):
        assert relative_volume([1000.0] * 5, period=20) is None


import pytest
