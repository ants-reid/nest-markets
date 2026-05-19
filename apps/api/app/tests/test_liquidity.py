from app.indicators.liquidity import assess_liquidity_from_quote, calculate_liquidity_score


def test_liquidity_score_prefers_tight_spreads() -> None:
    tight = calculate_liquidity_score([1.0, 1.5, 2.0])
    wide = calculate_liquidity_score([25.0, 30.0, 35.0])
    assert tight is not None
    assert wide is not None
    assert tight > wide


def test_liquidity_assessment_contains_quality() -> None:
    result = assess_liquidity_from_quote(100.0, 100.02, bid_size=1500, ask_size=1400)
    assert result is not None
    assert result.score > 0.0
    assert result.quality in {"excellent", "good", "fair", "poor"}
