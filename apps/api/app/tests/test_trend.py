from app.indicators.trend import calculate_trend_score


def test_trend_score_positive_for_uptrend() -> None:
    prices = [float(100 + i * 0.5) for i in range(80)]
    score = calculate_trend_score(prices, fast_period=20, slow_period=50, slope_lookback=5)
    assert score is not None
    assert score > 0.0


def test_trend_score_near_neutral_for_flat_market() -> None:
    prices = [100.0 for _ in range(80)]
    score = calculate_trend_score(prices, fast_period=20, slow_period=50, slope_lookback=5)
    assert score is not None
    assert abs(score) < 0.1
