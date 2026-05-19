from app.indicators.adx import calculate_adx


def test_adx_is_available_for_clear_trend() -> None:
    highs = [float(100 + i) for i in range(60)]
    lows = [float(99 + i) for i in range(60)]
    closes = [float(99.5 + i) for i in range(60)]

    result = calculate_adx(highs, lows, closes, period=14)
    assert result is not None
    assert result.adx >= 0.0
    assert result.di_plus >= 0.0
    assert result.di_minus >= 0.0


def test_adx_returns_none_for_short_series() -> None:
    values = [float(100 + i) for i in range(20)]
    assert calculate_adx(values, values, values, period=14) is None
