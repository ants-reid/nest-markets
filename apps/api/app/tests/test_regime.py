from app.indicators.regime import classify_regime


def test_regime_high_volatility_wins() -> None:
    regime = classify_regime(trend_score=0.6, volatility=0.04, adx=30.0)
    assert regime == "high_volatility"


def test_regime_range_for_low_trend_strength() -> None:
    regime = classify_regime(trend_score=0.05, volatility=0.012, adx=12.0)
    assert regime == "range"
