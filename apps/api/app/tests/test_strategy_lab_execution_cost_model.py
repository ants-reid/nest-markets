"""MH-15B tests for deterministic cost scenarios and sensitivity analysis."""

from __future__ import annotations

import pytest

from app.services.execution_cost_model import (
    COST_MODEL_VERSION,
    build_cost_sensitivity_summary,
    build_profile_sensitivity_summary,
    calculate_cost_for_scenario,
    calculate_cost_for_profile_and_scenario,
    classify_asset_class,
    estimate_trade_cost,
    get_cost_profile,
    get_default_assumptions,
    get_stress_preset,
    list_cost_profiles,
    list_stress_presets,
)


def test_default_assumptions_equities_etfs() -> None:
    assumptions = get_default_assumptions("AAPL", "equity")
    assert assumptions.asset_class == "equities_etfs"
    assert assumptions.spread_bps == 2.0
    assert assumptions.slippage_bps == 2.0
    assert assumptions.commission_bps == 0.0
    assert assumptions.fixed_fee_per_trade == 0.0


def test_default_assumptions_forex() -> None:
    assumptions = get_default_assumptions("EURUSD", "fx")
    assert assumptions.asset_class == "forex"
    assert assumptions.spread_bps == 1.0
    assert assumptions.slippage_bps == 1.0


def test_default_assumptions_crypto() -> None:
    assumptions = get_default_assumptions("BTC-USD", "crypto")
    assert assumptions.asset_class == "crypto"
    assert assumptions.spread_bps == 8.0
    assert assumptions.slippage_bps == 8.0
    assert assumptions.commission_bps == 10.0


def test_default_assumptions_commodities() -> None:
    assumptions = get_default_assumptions("XAUUSD", "commodity_proxy")
    assert assumptions.asset_class == "commodities"
    assert assumptions.spread_bps == 4.0
    assert assumptions.slippage_bps == 4.0


def test_default_assumptions_unknown() -> None:
    assumptions = get_default_assumptions("UNKNOWN!", None)
    assert assumptions.asset_class == "unknown"
    assert assumptions.spread_bps == 5.0
    assert assumptions.slippage_bps == 5.0


def test_classify_forex_symbol_rule() -> None:
    assert classify_asset_class("EURUSD", None) == "forex"
    assert classify_asset_class("USDJPY", None) == "forex"


def test_classify_equities_and_etf_rule() -> None:
    assert classify_asset_class("SPY", None) == "equities_etfs"
    assert classify_asset_class("AAPL", None) == "equities_etfs"


def test_classify_crypto_rule() -> None:
    assert classify_asset_class("BTC-USD", None) == "crypto"
    assert classify_asset_class("ETHUSD", None) == "crypto"


def test_classify_commodity_rule() -> None:
    assert classify_asset_class("XAU", None) == "commodities"
    assert classify_asset_class("BRENT", None) == "commodities"


def test_estimate_trade_cost_calculation() -> None:
    estimate = estimate_trade_cost(
        symbol="AAPL",
        quantity=10,
        entry_price=100.0,
        exit_price=110.0,
        asset_class="equity",
    )

    # Equities assumptions: 2 + 2 + 0 = 4 bps per side
    # Entry cost = 1000 * 0.0004 = 0.4
    # Exit cost  = 1100 * 0.0004 = 0.44
    assert estimate.cost_model_version == COST_MODEL_VERSION
    assert estimate.asset_class == "equities_etfs"
    assert estimate.round_trip_cost_bps == pytest.approx(8.0)
    assert estimate.estimated_entry_cost == pytest.approx(0.4)
    assert estimate.estimated_exit_cost == pytest.approx(0.44)
    assert estimate.estimated_total_cost == pytest.approx(0.84)


def test_cost_scenarios_low_base_high_for_same_trade() -> None:
    low = calculate_cost_for_scenario(
        symbol="AAPL",
        quantity=10,
        entry_price=100.0,
        exit_price=110.0,
        asset_class="equity",
        scenario="low",
    )
    base = calculate_cost_for_scenario(
        symbol="AAPL",
        quantity=10,
        entry_price=100.0,
        exit_price=110.0,
        asset_class="equity",
        scenario="base",
    )
    high = calculate_cost_for_scenario(
        symbol="AAPL",
        quantity=10,
        entry_price=100.0,
        exit_price=110.0,
        asset_class="equity",
        scenario="high",
    )

    assert low.estimated_total_cost < base.estimated_total_cost < high.estimated_total_cost
    assert base.round_trip_cost_bps == pytest.approx(8.0)
    assert low.round_trip_cost_bps == pytest.approx(4.0)
    assert high.round_trip_cost_bps == pytest.approx(16.0)


def test_base_scenario_matches_mh15a_estimate_trade_cost() -> None:
    legacy_base = estimate_trade_cost(
        symbol="EURUSD",
        quantity=10000,
        entry_price=1.10,
        exit_price=1.11,
        asset_class="fx",
    )
    scenario_base = calculate_cost_for_scenario(
        symbol="EURUSD",
        quantity=10000,
        entry_price=1.10,
        exit_price=1.11,
        asset_class="fx",
        scenario="base",
    )

    assert legacy_base.estimated_total_cost == pytest.approx(scenario_base.estimated_total_cost)
    assert legacy_base.round_trip_cost_bps == pytest.approx(scenario_base.round_trip_cost_bps)


def test_sensitivity_summary_handles_winning_trade() -> None:
    low = calculate_cost_for_scenario(
        symbol="AAPL",
        quantity=10,
        entry_price=100,
        exit_price=110,
        asset_class="equity",
        scenario="low",
    )
    base = calculate_cost_for_scenario(
        symbol="AAPL",
        quantity=10,
        entry_price=100,
        exit_price=110,
        asset_class="equity",
        scenario="base",
    )
    high = calculate_cost_for_scenario(
        symbol="AAPL",
        quantity=10,
        entry_price=100,
        exit_price=110,
        asset_class="equity",
        scenario="high",
    )

    summary = build_cost_sensitivity_summary(
        gross_pnl_amount=100.0,
        low_cost_estimate=low,
        base_cost_estimate=base,
        high_cost_estimate=high,
    )

    assert summary["low_net_pnl_amount"] > summary["base_net_pnl_amount"] > summary["high_net_pnl_amount"]
    assert summary["cost_drag_base_pct"] is not None
    assert summary["cost_sensitivity_level"] in {"low", "medium", "high"}


def test_sensitivity_summary_handles_non_positive_gross_without_divide_by_zero() -> None:
    low = calculate_cost_for_scenario(
        symbol="AAPL",
        quantity=10,
        entry_price=100,
        exit_price=95,
        asset_class="equity",
        scenario="low",
    )
    base = calculate_cost_for_scenario(
        symbol="AAPL",
        quantity=10,
        entry_price=100,
        exit_price=95,
        asset_class="equity",
        scenario="base",
    )
    high = calculate_cost_for_scenario(
        symbol="AAPL",
        quantity=10,
        entry_price=100,
        exit_price=95,
        asset_class="equity",
        scenario="high",
    )

    summary = build_cost_sensitivity_summary(
        gross_pnl_amount=0.0,
        low_cost_estimate=low,
        base_cost_estimate=base,
        high_cost_estimate=high,
    )

    assert summary["cost_drag_low_pct"] is None
    assert summary["cost_drag_base_pct"] is None
    assert summary["cost_drag_high_pct"] is None
    assert summary["cost_sensitivity_level"] in {"high", "loss_sensitive"}


def test_list_profiles_returns_all_named_profiles() -> None:
    items = list_cost_profiles()
    names = {item["profile_name"] for item in items}
    assert names == {
        "optimistic_research",
        "standard_research",
        "conservative_research",
        "stress_research",
    }


def test_standard_profile_matches_existing_base_assumptions() -> None:
    standard = calculate_cost_for_profile_and_scenario(
        symbol="AAPL",
        quantity=10,
        entry_price=100,
        exit_price=110,
        scenario="base",
        profile_name="standard_research",
        stress_preset="normal_liquidity",
        asset_class="equity",
    )
    legacy = calculate_cost_for_scenario(
        symbol="AAPL",
        quantity=10,
        entry_price=100,
        exit_price=110,
        scenario="base",
        asset_class="equity",
    )
    assert standard.estimated_total_cost == pytest.approx(legacy.estimated_total_cost)


def test_profile_cost_ordering_optimistic_standard_conservative_stress() -> None:
    optimistic = calculate_cost_for_profile_and_scenario(
        symbol="AAPL",
        quantity=10,
        entry_price=100,
        exit_price=110,
        scenario="base",
        profile_name="optimistic_research",
        stress_preset="normal_liquidity",
        asset_class="equity",
    )
    standard = calculate_cost_for_profile_and_scenario(
        symbol="AAPL",
        quantity=10,
        entry_price=100,
        exit_price=110,
        scenario="base",
        profile_name="standard_research",
        stress_preset="normal_liquidity",
        asset_class="equity",
    )
    conservative = calculate_cost_for_profile_and_scenario(
        symbol="AAPL",
        quantity=10,
        entry_price=100,
        exit_price=110,
        scenario="base",
        profile_name="conservative_research",
        stress_preset="normal_liquidity",
        asset_class="equity",
    )
    stress = calculate_cost_for_profile_and_scenario(
        symbol="AAPL",
        quantity=10,
        entry_price=100,
        exit_price=110,
        scenario="base",
        profile_name="stress_research",
        stress_preset="normal_liquidity",
        asset_class="equity",
    )
    assert optimistic.estimated_total_cost < standard.estimated_total_cost
    assert conservative.estimated_total_cost > standard.estimated_total_cost
    assert stress.estimated_total_cost > conservative.estimated_total_cost


def test_list_stress_presets_returns_all_named_presets() -> None:
    items = list_stress_presets()
    names = {item["preset_name"] for item in items}
    assert names == {
        "normal_liquidity",
        "wide_spread",
        "high_slippage",
        "volatile_session",
        "news_event_stress",
    }


def test_wide_spread_preset_changes_spread_not_slippage() -> None:
    baseline = calculate_cost_for_profile_and_scenario(
        symbol="AAPL",
        quantity=10,
        entry_price=100,
        exit_price=110,
        scenario="base",
        profile_name="standard_research",
        stress_preset="normal_liquidity",
        asset_class="equity",
    )
    wide = calculate_cost_for_profile_and_scenario(
        symbol="AAPL",
        quantity=10,
        entry_price=100,
        exit_price=110,
        scenario="base",
        profile_name="standard_research",
        stress_preset="wide_spread",
        asset_class="equity",
    )
    assert wide.spread_bps == pytest.approx(baseline.spread_bps * 3.0)
    assert wide.slippage_bps == pytest.approx(baseline.slippage_bps)


def test_high_slippage_preset_changes_slippage_not_spread() -> None:
    baseline = calculate_cost_for_profile_and_scenario(
        symbol="AAPL",
        quantity=10,
        entry_price=100,
        exit_price=110,
        scenario="base",
        profile_name="standard_research",
        stress_preset="normal_liquidity",
        asset_class="equity",
    )
    stressed = calculate_cost_for_profile_and_scenario(
        symbol="AAPL",
        quantity=10,
        entry_price=100,
        exit_price=110,
        scenario="base",
        profile_name="standard_research",
        stress_preset="high_slippage",
        asset_class="equity",
    )
    assert stressed.spread_bps == pytest.approx(baseline.spread_bps)
    assert stressed.slippage_bps == pytest.approx(baseline.slippage_bps * 3.0)


def test_news_event_stress_strongly_increases_spread_and_slippage() -> None:
    baseline = calculate_cost_for_profile_and_scenario(
        symbol="AAPL",
        quantity=10,
        entry_price=100,
        exit_price=110,
        scenario="base",
        profile_name="standard_research",
        stress_preset="normal_liquidity",
        asset_class="equity",
    )
    news = calculate_cost_for_profile_and_scenario(
        symbol="AAPL",
        quantity=10,
        entry_price=100,
        exit_price=110,
        scenario="base",
        profile_name="standard_research",
        stress_preset="news_event_stress",
        asset_class="equity",
    )
    assert news.spread_bps == pytest.approx(baseline.spread_bps * 4.0)
    assert news.slippage_bps == pytest.approx(baseline.slippage_bps * 4.0)


def test_build_profile_sensitivity_summary_includes_profile_context() -> None:
    summary = build_profile_sensitivity_summary(
        symbol="AAPL",
        quantity=10,
        entry_price=100,
        exit_price=110,
        gross_pnl_amount=100,
        profile_name="conservative_research",
        stress_preset="volatile_session",
        asset_class="equity",
    )
    assert summary["cost_profile_used"] == "conservative_research"
    assert summary["stress_preset_used"] == "volatile_session"
    assert summary["broker_calibrated"] is False


def test_profile_and_preset_getters_return_metadata() -> None:
    profile = get_cost_profile("standard_research")
    preset = get_stress_preset("normal_liquidity")
    assert profile is not None
    assert preset is not None
    assert profile["is_broker_calibrated"] is False
    assert preset["live_ready"] is False
