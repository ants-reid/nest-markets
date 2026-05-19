"""Tests for momentum indicator."""


from app.indicators import calculate_momentum, calculate_roc, calculate_momentum_score


class TestMomentum:
    """Momentum calculation tests."""

    def test_momentum_positive(self):
        """Test positive momentum."""
        momentum = calculate_momentum(current_price=105.0, price_n_bars_ago=100.0)
        assert momentum > 0
        assert abs(momentum - 5.0) < 0.1  # Should be ~5%

    def test_momentum_negative(self):
        """Test negative momentum."""
        momentum = calculate_momentum(current_price=95.0, price_n_bars_ago=100.0)
        assert momentum < 0
        assert abs(momentum - (-5.0)) < 0.1  # Should be ~-5%

    def test_momentum_zero(self):
        """Test zero momentum."""
        momentum = calculate_momentum(current_price=100.0, price_n_bars_ago=100.0)
        assert abs(momentum) < 0.01

    def test_roc_bullish(self):
        """Test ROC with bullish momentum."""
        prices = list(range(100, 150))
        result = calculate_roc(prices, 12)
        assert result.value is not None
        assert result.direction == "bullish"
        assert result.strength > 0

    def test_roc_bearish(self):
        """Test ROC with bearish momentum."""
        prices = list(range(150, 100, -1))
        result = calculate_roc(prices, 12)
        assert result.value is not None
        assert result.direction == "bearish"
        assert result.strength > 0

    def test_roc_neutral(self):
        """Test ROC with neutral momentum."""
        prices = [100.0] * 30
        result = calculate_roc(prices, 12)
        assert result.value is not None
        assert abs(result.value) < 1.0
        assert result.direction == "neutral"

    def test_momentum_score(self):
        """Test composite momentum score."""
        result = calculate_momentum_score(rsi=75, roc=10.0, adx=35)
        assert result.value is not None
        assert result.direction == "bullish"
        assert 0 <= result.strength <= 1
