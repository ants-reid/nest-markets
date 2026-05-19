"""Tests for RSI indicator."""

import pytest

from app.indicators import calculate_rsi, calculate_smoothed_rsi


class TestRSI:
    """RSI calculation tests."""

    def test_rsi_insufficient_data(self):
        """Test RSI with insufficient data."""
        result = calculate_rsi([100.0, 101.0, 102.0], 14)
        assert result.value is None
        assert result.period == 14

    def test_rsi_constant_prices(self):
        """Test RSI with constant prices (no momentum)."""
        prices = [100.0] * 30
        result = calculate_rsi(prices, 14)
        assert result.value is not None
        assert abs(result.value - 50.0) < 1.0  # Should be around 50 (neutral)

    def test_rsi_uptrend(self):
        """Test RSI during uptrend."""
        prices = list(range(100, 150))  # Steady uptrend
        result = calculate_rsi(prices, 14)
        assert result.value is not None
        assert result.value > 60  # Should be elevated (overbought tendency)

    def test_rsi_downtrend(self):
        """Test RSI during downtrend."""
        prices = list(range(150, 100, -1))  # Steady downtrend
        result = calculate_rsi(prices, 14)
        assert result.value is not None
        assert result.value < 40  # Should be depressed (oversold tendency)

    def test_rsi_bounds(self):
        """Test RSI is always between 0 and 100."""
        prices = list(range(100, 200))
        result = calculate_rsi(prices, 14)
        assert result.value is not None
        assert 0 <= result.value <= 100

    def test_rsi_invalid_period(self):
        """Test RSI with invalid period."""
        with pytest.raises(ValueError):
            calculate_rsi([100.0, 101.0], 0)

    def test_smoothed_rsi(self):
        """Test Wilder's smoothed RSI."""
        prices = list(range(100, 150))
        result = calculate_smoothed_rsi(prices, 14)
        assert result.value is not None
        assert 0 <= result.value <= 100
