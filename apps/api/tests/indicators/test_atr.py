"""Tests for ATR indicator."""

import pytest

from app.indicators import calculate_atr


class TestATR:
    """ATR calculation tests."""

    def test_atr_insufficient_data(self):
        """Test ATR with insufficient data."""
        bars = [
            {"high": 101, "low": 99, "close": 100},
            {"high": 102, "low": 98, "close": 101},
        ]
        result = calculate_atr(bars, 14)
        assert result.value is None

    def test_atr_low_volatility(self):
        """Test ATR with low volatility (narrow ranges)."""
        bars = []
        price = 100.0
        for _ in range(30):
            bars.append(
                {
                    "high": price * 1.001,
                    "low": price * 0.999,
                    "close": price,
                }
            )
        result = calculate_atr(bars, 14)
        assert result.value is not None
        assert result.value < 0.5  # Should be small

    def test_atr_high_volatility(self):
        """Test ATR with high volatility (wide ranges)."""
        bars = []
        price = 100.0
        for i in range(30):
            bars.append(
                {
                    "high": price * 1.05,
                    "low": price * 0.95,
                    "close": price,
                }
            )
            price += 0.1 * (1 if i % 2 == 0 else -1)
        result = calculate_atr(bars, 14)
        assert result.value is not None
        assert result.value > 1.0  # Should be larger

    def test_atr_invalid_period(self):
        """Test ATR with invalid period."""
        bars = [{"high": 101, "low": 99, "close": 100}]
        with pytest.raises(ValueError):
            calculate_atr(bars, 0)
