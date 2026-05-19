from app.indicators.atr import calculate_atr


def test_atr_constant_range_is_constant() -> None:
    highs = [11.0] * 30
    lows = [10.0] * 30
    closes = [10.5] * 30

    atr = calculate_atr(highs, lows, closes, period=14)
    assert atr is not None
    assert round(atr, 8) == 1.0


def test_atr_returns_none_for_short_input() -> None:
    assert calculate_atr([11.0, 12.0], [10.0, 11.0], [10.5, 11.5], period=14) is None
