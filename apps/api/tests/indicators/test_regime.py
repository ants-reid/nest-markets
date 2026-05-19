"""Tests for regime classification."""


from app.indicators import classify_regime, assess_market_quality


class TestRegime:
    """Regime classification tests."""

    def test_regime_trending_up(self):
        """Test regime classification for uptrend."""
        result = classify_regime(
            adx=40, rsi=65, volatility=0.015, trend_direction="up", trend_strength=0.8
        )
        assert result.regime == "trending_up"
        assert result.confidence > 0.3

    def test_regime_trending_down(self):
        """Test regime classification for downtrend."""
        result = classify_regime(
            adx=45, rsi=35, volatility=0.015, trend_direction="down", trend_strength=0.85
        )
        assert result.regime == "trending_down"
        assert result.confidence > 0.3

    def test_regime_mean_reversion(self):
        """Test regime classification for mean reversion."""
        result = classify_regime(
            adx=15, rsi=80, volatility=0.01, trend_direction="neutral", trend_strength=0.2
        )
        assert result.regime == "mean_reversion"

    def test_regime_high_vol(self):
        """Test regime classification for high volatility."""
        result = classify_regime(
            adx=25, rsi=50, volatility=0.05, trend_direction="neutral", trend_strength=0.5
        )
        assert result.regime == "high_vol"

    def test_regime_low_vol(self):
        """Test regime classification for low volatility."""
        result = classify_regime(
            adx=10, rsi=50, volatility=0.005, trend_direction="neutral", trend_strength=0.1
        )
        assert result.regime == "low_vol"

    def test_market_quality_good(self):
        """Test market quality assessment - good."""
        quality = assess_market_quality(
            spread_bps=0.5, volatility=0.02, volume_ratio=1.2
        )
        assert quality == "good"

    def test_market_quality_fair(self):
        """Test market quality assessment - fair."""
        quality = assess_market_quality(
            spread_bps=3.0, volatility=0.02, volume_ratio=1.0
        )
        assert quality == "fair"

    def test_market_quality_poor(self):
        """Test market quality assessment - poor."""
        quality = assess_market_quality(
            spread_bps=50.0, volatility=0.1, volume_ratio=0.5
        )
        assert quality == "poor"
