from app.indicators.rsi import calculate_rsi


def test_rsi_strong_uptrend_reaches_high_values() -> None:
    prices = [float(i) for i in range(1, 40)]
    rsi = calculate_rsi(prices, period=14)
    assert rsi is not None
    assert rsi > 90.0


def test_rsi_flat_series_is_neutral() -> None:
    prices = [100.0] * 30
    rsi = calculate_rsi(prices, period=14)
    assert rsi == 50.0
