from app.indicators.momentum import calculate_momentum_score


def test_momentum_score_positive_when_prices_rise() -> None:
    prices = [float(100 + i) for i in range(30)]
    score = calculate_momentum_score(prices, lookback=10)
    assert score is not None
    assert score > 0.0


def test_momentum_score_negative_when_prices_fall() -> None:
    prices = [float(200 - i) for i in range(30)]
    score = calculate_momentum_score(prices, lookback=10)
    assert score is not None
    assert score < 0.0
