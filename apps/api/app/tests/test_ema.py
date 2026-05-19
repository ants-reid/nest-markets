from app.indicators.ema import calculate_ema


def test_calculate_ema_known_sequence() -> None:
    prices = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    assert calculate_ema(prices, period=3) == 9.0


def test_calculate_ema_insufficient_data() -> None:
    assert calculate_ema([1.0, 2.0], period=3) is None
