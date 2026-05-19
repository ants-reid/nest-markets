"""Tests for EMA indicator."""

import pytest

from app.indicators import calculate_ema, calculate_multiple_emas


class TestEMA:
    """EMA calculation tests."""

    def test_ema_insufficient_data(self):
        """Test EMA with insufficient data."""
        result = calculate_ema([100.0, 101.0, 102.0], 10)
        assert result.value is None
        assert result.period == 10

    def test_ema_exact_period(self):
        """Test EMA with exactly period data points."""
        prices = [100.0 + i for i in range(20)]
        result = calculate_ema(prices, 20)
        assert result.value is not None
        assert result.period == 20

    def test_ema_simple_constant(self):
        """Test EMA with constant prices."""
        prices = [100.0] * 30
        result = calculate_ema(prices, 10)
        assert result.value is not None
        assert abs(result.value - 100.0) < 0.01

    def test_ema_uptrend(self):
        """Test EMA with uptrending prices."""
        prices = list(range(100, 150))
        result = calculate_ema(prices, 10)
        assert result.value is not None
        assert result.value > 100  # Should be above start price

    def test_ema_downtrend(self):
        """Test EMA with downtrending prices."""
        prices = list(range(150, 100, -1))
        result = calculate_ema(prices, 10)
        assert result.value is not None
        assert result.value < 150  # Should be below start price

    def test_ema_invalid_period(self):
        """Test EMA with invalid period."""
        with pytest.raises(ValueError):
            calculate_ema([100.0, 101.0], -1)

    def test_multiple_emas(self):
        """Test calculating multiple EMAs at once."""
        prices = list(range(100, 300))
        periods = [10, 20, 50]
        results = calculate_multiple_emas(prices, periods)

        assert len(results) == 3
        assert 10 in results
        assert 20 in results
        assert 50 in results
        assert all(r.value is not None for r in results.values())
