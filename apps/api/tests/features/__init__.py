"""Tests for feature service."""

import pytest

from app.features import calculate_features


class TestFeatureService:
    """Feature service tests."""

    def test_calculate_features_minimum_bars(self, sample_bars):
        """Test feature calculation with minimum bars."""
        features = calculate_features(bars=sample_bars[:20])
        assert features is not None
        assert "sma_20" in features
        assert "rsi_14" in features
        assert "volatility" in features
        assert "trend_direction" in features

    def test_calculate_features_insufficient_bars(self):
        """Test feature calculation with insufficient bars."""
        bars = [
            {"open": 100, "high": 101, "low": 99, "close": 100, "volume": 1000}
        ] * 10
        with pytest.raises(ValueError):
            calculate_features(bars=bars)

    def test_calculate_features_with_quotes(self, sample_bars, sample_quotes):
        """Test feature calculation with quotes."""
        features = calculate_features(
            bars=sample_bars[:50], quotes=sample_quotes[:50]
        )
        assert features is not None
        assert "spread_bps" in features
        assert features["spread_bps"] is not None

    def test_feature_values_reasonable(self, sample_bars):
        """Test that calculated features are within reasonable bounds."""
        features = calculate_features(bars=sample_bars[:50])

        # RSI should be 0-100
        if features["rsi_14"] is not None:
            assert 0 <= features["rsi_14"] <= 100

        # Volatility should be positive
        if features["volatility"] is not None:
            assert features["volatility"] >= 0

        # Trend strength 0-1
        assert 0 <= features["trend_strength"] <= 1

        # Volume ratio should be positive
        assert features["volume_ratio"] > 0

    def test_feature_trend_consistency(self, sample_bars):
        """Test trend calculation is consistent."""
        features = calculate_features(bars=sample_bars[-100:])
        assert features["trend_direction"] in ["up", "down", "neutral"]
