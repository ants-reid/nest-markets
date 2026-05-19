"""Tests for volatility indicators."""

import pytest

from app.indicators import calculate_realized_volatility, calculate_parkinson_volatility


class TestVolatility:
    """Volatility calculation tests."""

    def test_realized_volatility_constant(self):
        """Test realized volatility with constant prices."""
        prices = [100.0] * 30
        result = calculate_realized_volatility(prices, 20)
        assert result.value is not None
        assert result.value < 0.01  # Near zero volatility

    def test_realized_volatility_trending(self):
        """Test realized volatility with trending prices."""
        prices = list(range(100, 150))
        result = calculate_realized_volatility(prices, 20)
        assert result.value is not None
        assert result.annualized is not None
        assert result.annualized > result.value  # Annualized should be larger

    def test_realized_volatility_insufficient_data(self):
        """Test realized volatility with insufficient data."""
        prices = [100.0, 101.0, 102.0]
        result = calculate_realized_volatility(prices, 20)
        assert result.value is None
        assert result.annualized is None

    def test_realized_volatility_invalid_period(self):
        """Test realized volatility with invalid period."""
        prices = list(range(100, 150))
        with pytest.raises(ValueError):
            calculate_realized_volatility(prices, 0)

    def test_parkinson_volatility(self):
        """Test Parkinson volatility calculation."""
        bars = []
        price = 100.0
        for i in range(30):
            bars.append(
                {
                    "high": price * 1.01,
                    "low": price * 0.99,
                    "close": price,
                }
            )
            price += 0.1
        result = calculate_parkinson_volatility(bars, 20)
        assert result.value is not None
        assert result.annualized is not None

    def test_parkinson_insufficient_data(self):
        """Test Parkinson volatility with insufficient data."""
        bars = [{"high": 101, "low": 99, "close": 100}]
        result = calculate_parkinson_volatility(bars, 20)
        assert result.value is None
