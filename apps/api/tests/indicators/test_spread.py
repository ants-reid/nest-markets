"""Tests for spread quality."""

import pytest

from app.indicators import calculate_spread_quality, assess_quote_liquidity


class TestSpread:
    """Spread quality tests."""

    def test_spread_quality_tight(self):
        """Test tight spread assessment."""
        result = calculate_spread_quality(bid_price=100.0, ask_price=100.01, mid_price=100.005)
        assert result.quality == "tight"
        assert result.spread_bps < 1.5

    def test_spread_quality_normal(self):
        """Test normal spread assessment."""
        result = calculate_spread_quality(bid_price=100.0, ask_price=100.03, mid_price=100.015)
        assert result.quality == "normal"
        assert 1.0 < result.spread_bps < 6.0

    def test_spread_quality_wide(self):
        """Test wide spread assessment."""
        result = calculate_spread_quality(bid_price=100.0, ask_price=100.1, mid_price=100.05)
        assert result.quality == "wide"
        assert 5.0 < result.spread_bps < 30.0

    def test_spread_quality_extreme(self):
        """Test extreme spread assessment."""
        result = calculate_spread_quality(bid_price=100.0, ask_price=101.0, mid_price=100.5)
        assert result.quality == "extreme"
        assert result.spread_bps > 25.0

    def test_spread_quality_invalid(self):
        """Test invalid spread (bid >= ask)."""
        with pytest.raises(ValueError):
            calculate_spread_quality(bid_price=100.0, ask_price=100.0, mid_price=100.0)

    def test_liquidity_high(self):
        """Test high liquidity assessment."""
        quality = assess_quote_liquidity(bid_size=2000, ask_size=1500)
        assert quality == "high"

    def test_liquidity_medium(self):
        """Test medium liquidity assessment."""
        quality = assess_quote_liquidity(bid_size=200, ask_size=150)
        assert quality == "medium"

    def test_liquidity_low(self):
        """Test low liquidity assessment."""
        quality = assess_quote_liquidity(bid_size=50, ask_size=25)
        assert quality == "low"
