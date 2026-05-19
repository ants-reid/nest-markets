"""Tests for ADX indicator."""

import pytest

from app.indicators import calculate_adx


class TestADX:
    """ADX calculation tests."""

    def test_adx_insufficient_data(self):
        """Test ADX with insufficient data."""
        bars = [
            {"high": 101, "low": 99, "close": 100},
            {"high": 102, "low": 98, "close": 101},
        ]
        result = calculate_adx(bars, 14)
        assert result.adx is None
        assert result.di_plus is None
        assert result.di_minus is None

    def test_adx_uptrend(self):
        """Test ADX during clear uptrend."""
        bars = []
        price = 100.0
        for _ in range(50):
            bars.append(
                {
                    "high": price + 2,
                    "low": price - 1,
                    "close": price + 0.5,
                }
            )
            price += 0.5
        result = calculate_adx(bars, 14)
        assert result.adx is not None
        assert result.di_plus is not None
        assert result.di_minus is not None
        # In uptrend, DI+ > DI-
        assert result.di_plus > result.di_minus

    def test_adx_downtrend(self):
        """Test ADX during clear downtrend."""
        bars = []
        price = 150.0
        for _ in range(50):
            bars.append(
                {
                    "high": price + 1,
                    "low": price - 2,
                    "close": price - 0.5,
                }
            )
            price -= 0.5
        result = calculate_adx(bars, 14)
        assert result.adx is not None
        assert result.di_plus is not None
        assert result.di_minus is not None
        # In downtrend, DI- > DI+
        assert result.di_minus > result.di_plus

    def test_adx_bounds(self):
        """Test ADX values are bounded 0-100."""
        bars = []
        for i in range(50):
            price = 100 + (i * 0.5)
            bars.append(
                {
                    "high": price * 1.01,
                    "low": price * 0.99,
                    "close": price,
                }
            )
        result = calculate_adx(bars, 14)
        assert result.adx is not None
        assert 0 <= result.adx <= 100
        assert 0 <= result.di_plus <= 100
        assert 0 <= result.di_minus <= 100

    def test_adx_invalid_period(self):
        """Test ADX with invalid period."""
        bars = [{"high": 101, "low": 99, "close": 100}]
        with pytest.raises(ValueError):
            calculate_adx(bars, 0)
