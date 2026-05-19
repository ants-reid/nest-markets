from app.indicators.volatility import calculate_realized_volatility


def test_realized_volatility_zero_for_flat_prices() -> None:
    prices = [100.0] * 25
    vol = calculate_realized_volatility(prices, period=20)
    assert vol == 0.0


def test_realized_volatility_positive_for_moving_prices() -> None:
    prices = [100.0, 101.0, 100.5, 101.5, 102.0, 101.2, 102.2, 103.0, 102.4, 103.4, 104.0, 103.3, 104.3, 105.1, 104.6, 105.6, 106.0, 105.2, 106.2, 107.0, 106.3]
    vol = calculate_realized_volatility(prices, period=20)
    assert vol is not None
    assert vol > 0.0
