"""Tests for trend indicator."""


from app.indicators import (
    calculate_trend_direction,
    calculate_trend_strength,
    calculate_trend_score,
)


class TestTrend:
    """Trend calculation tests."""

    def test_trend_direction_uptrend(self):
        """Test trend direction in uptrend."""
        direction = calculate_trend_direction(
            sma_short=105, sma_medium=103, sma_long=100, current_price=107
        )
        assert direction == "up"

    def test_trend_direction_downtrend(self):
        """Test trend direction in downtrend."""
        direction = calculate_trend_direction(
            sma_short=95, sma_medium=97, sma_long=100, current_price=93
        )
        assert direction == "down"

    def test_trend_direction_neutral(self):
        """Test trend direction when neutral."""
        direction = calculate_trend_direction(
            sma_short=100, sma_medium=101, sma_long=102, current_price=101
        )
        assert direction == "neutral"

    def test_trend_strength(self):
        """Test trend strength calculation."""
        # Strong trend
        strength = calculate_trend_strength(
            sma_short=110, sma_medium=105, sma_long=100
        )
        assert 0 <= strength <= 1
        assert strength > 0.5

        # Weak trend
        strength_weak = calculate_trend_strength(
            sma_short=101, sma_medium=100.5, sma_long=100
        )
        assert strength_weak < strength

    def test_trend_score(self):
        """Test comprehensive trend score."""
        result = calculate_trend_score(
            sma_short=105,
            sma_medium=103,
            sma_long=100,
            current_price=107,
            bars_up=10,
            bars_down=2,
        )
        assert result.direction == "up"
        assert result.strength > 0.5
        assert result.duration_bars == 10
