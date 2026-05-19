from app.services.feature_service import BarInput, FeatureInput, QuoteInput, build_feature_snapshot


def _make_bars(count: int) -> list[BarInput]:
    bars: list[BarInput] = []
    for i in range(count):
        close = 100.0 + (i * 0.4)
        bars.append(
            BarInput(
                open=close - 0.2,
                high=close + 0.5,
                low=close - 0.6,
                close=close,
                volume=1000.0 + (i * 5.0),
            )
        )
    return bars


def test_build_feature_snapshot_returns_structured_payload() -> None:
    payload = FeatureInput(
        bars=_make_bars(90),
        quotes=[QuoteInput(bid=135.1, ask=135.12, bid_size=1200, ask_size=1300)],
        context={"timeframe": "1h"},
    )

    snapshot = build_feature_snapshot(payload)

    assert snapshot.ema_fast is not None
    assert snapshot.ema_slow is not None
    assert snapshot.rsi is not None
    assert snapshot.atr is not None
    assert snapshot.adx is not None
    assert snapshot.regime_preclassification in {
        "trend",
        "range",
        "breakout",
        "high_volatility",
        "low_volatility",
    }


def test_build_feature_snapshot_requires_enough_bars() -> None:
    payload = FeatureInput(bars=_make_bars(10))

    try:
        build_feature_snapshot(payload)
    except ValueError as exc:
        assert "insufficient bars" in str(exc)
    else:
        raise AssertionError("expected ValueError for short bar input")
