"""Tests for SignalService performance context injection — QA-220."""

from __future__ import annotations

from unittest.mock import MagicMock


from app.services.performance_stats_service import DimensionWinRate, PerformanceStats


def _make_signal_service(stats: PerformanceStats | None = None):
    """Create a minimal SignalService with a mock performance_stats_service."""
    # Import lazily to avoid triggering config loading
    from app.services.signal_service import SignalService
    from app.clients.llm.router import LLMProviderRouter

    mock_router = MagicMock(spec=LLMProviderRouter)
    mock_perf = None
    if stats is not None:
        mock_perf = MagicMock()
        mock_perf.overall_stats.return_value = stats

    service = SignalService(router=mock_router, performance_stats_service=mock_perf)
    return service


def _stats_with_trades(n: int) -> PerformanceStats:
    return PerformanceStats(
        total_trades=n,
        total_wins=int(n * 0.55),
        overall_win_rate=0.55,
        by_setup=[
            DimensionWinRate(key="TREND_PULLBACK", total=n, wins=int(n * 0.55), win_rate=0.55)
        ],
        by_regime=[],
    )


# ---------------------------------------------------------------------------
# QA-220
# ---------------------------------------------------------------------------


def test_performance_context_block_absent_when_no_service():
    service = _make_signal_service(stats=None)
    block = service._build_performance_context_block(min_samples=10)
    assert block == ""


def test_performance_context_block_absent_below_min_samples():
    service = _make_signal_service(stats=_stats_with_trades(5))
    block = service._build_performance_context_block(min_samples=10)
    assert block == ""


def test_performance_context_block_present_above_min_samples():
    service = _make_signal_service(stats=_stats_with_trades(20))
    block = service._build_performance_context_block(min_samples=10)
    assert "## Historical Performance Context" in block
    assert "Overall win rate" in block


def test_performance_context_block_contains_setup_info():
    service = _make_signal_service(stats=_stats_with_trades(20))
    block = service._build_performance_context_block(min_samples=10)
    assert "TREND_PULLBACK" in block


def test_render_user_prompt_appends_context_when_stats_available():
    """render_user_prompt must include the context block when stats meet threshold."""
    service = _make_signal_service(stats=_stats_with_trades(20))
    template = (
        "Asset: {asset}\nTimeframe: {timeframe}\nRegime: {regime_hint}\n"
        "Price: {latest_price}\nSnapshot: {feature_snapshot_json}\n"
        "Catalyst: {catalyst_context_json}\nRisk: {risk_notes}"
    )
    from app.services.signal_service import SignalInput

    signal_input = SignalInput(
        asset="EUR/USD",
        timeframe="1h",
        latest_price=1.0850,
        feature_snapshot={"regime_preclassification": "trend"},
        catalyst_context={},
    )
    rendered = service.render_user_prompt(template, signal_input)
    assert "## Historical Performance Context" in rendered
