"""Execution cost model for Strategy Lab research backtests (MH-15A/B/C).

This module provides deterministic cost assumptions and cost calculations used
to derive net performance metrics from gross simulated PnL.

Important:
- Assumptions here are research defaults only.
- They are not broker quotes or live execution guarantees.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.db.enums import AssetClass

COST_MODEL_VERSION = "mh15c_v1"
CostScenario = Literal["low", "base", "high"]
CostProfileName = Literal[
    "optimistic_research",
    "standard_research",
    "conservative_research",
    "stress_research",
]
StressPresetName = Literal[
    "normal_liquidity",
    "wide_spread",
    "high_slippage",
    "volatile_session",
    "news_event_stress",
]

DEFAULT_COST_PROFILE: CostProfileName = "standard_research"
DEFAULT_STRESS_PRESET: StressPresetName = "normal_liquidity"


@dataclass(frozen=True)
class ExecutionCostAssumptions:
    """Per-asset-class deterministic execution cost assumptions."""

    asset_class: str
    spread_bps: float
    slippage_bps: float
    commission_bps: float
    fixed_fee_per_trade: float

    @property
    def round_trip_cost_bps(self) -> float:
        """Round-trip bps applied over entry and exit notionals."""
        return (self.spread_bps + self.slippage_bps + self.commission_bps) * 2.0

    @property
    def per_side_cost_bps(self) -> float:
        return self.spread_bps + self.slippage_bps + self.commission_bps


@dataclass(frozen=True)
class ExecutionCostEstimate:
    """Calculated trade cost estimate for one closed trade."""

    cost_model_version: str
    asset_class: str
    spread_bps: float
    slippage_bps: float
    commission_bps: float
    fixed_fee_per_trade: float
    round_trip_cost_bps: float
    estimated_entry_cost: float
    estimated_exit_cost: float
    estimated_total_cost: float
    cost_scenario: CostScenario


@dataclass(frozen=True)
class CostProfileMetadata:
    profile_name: CostProfileName
    profile_label: str
    profile_description: str
    profile_multiplier: float
    intended_use: str
    is_broker_calibrated: bool = False
    live_ready: bool = False


@dataclass(frozen=True)
class StressPresetMetadata:
    preset_name: StressPresetName
    preset_label: str
    preset_description: str
    spread_multiplier: float
    slippage_multiplier: float
    commission_multiplier: float
    is_broker_calibrated: bool = False
    live_ready: bool = False


_DEFAULT_ASSUMPTIONS: dict[str, ExecutionCostAssumptions] = {
    "equities_etfs": ExecutionCostAssumptions(
        asset_class="equities_etfs",
        spread_bps=2.0,
        slippage_bps=2.0,
        commission_bps=0.0,
        fixed_fee_per_trade=0.0,
    ),
    "forex": ExecutionCostAssumptions(
        asset_class="forex",
        spread_bps=1.0,
        slippage_bps=1.0,
        commission_bps=0.0,
        fixed_fee_per_trade=0.0,
    ),
    "crypto": ExecutionCostAssumptions(
        asset_class="crypto",
        spread_bps=8.0,
        slippage_bps=8.0,
        commission_bps=10.0,
        fixed_fee_per_trade=0.0,
    ),
    "commodities": ExecutionCostAssumptions(
        asset_class="commodities",
        spread_bps=4.0,
        slippage_bps=4.0,
        commission_bps=0.0,
        fixed_fee_per_trade=0.0,
    ),
    "unknown": ExecutionCostAssumptions(
        asset_class="unknown",
        spread_bps=5.0,
        slippage_bps=5.0,
        commission_bps=0.0,
        fixed_fee_per_trade=0.0,
    ),
}


_KNOWN_FOREX: frozenset[str] = frozenset({
    "AUDUSD",
    "EURUSD",
    "NZDUSD",
    "USDJPY",
    "GBPUSD",
    "USDCAD",
    "USDCHF",
})

_KNOWN_CRYPTO_PREFIXES: tuple[str, ...] = (
    "BTC",
    "ETH",
    "SOL",
)

_KNOWN_COMMODITIES: frozenset[str] = frozenset({
    "XAU",
    "XAUUSD",
    "WTI",
    "BRENT",
    "CL",
    "GC",
})

_KNOWN_ETFS: frozenset[str] = frozenset({"SPY", "QQQ", "DIA", "IWM"})
_SCENARIO_MULTIPLIERS: dict[CostScenario, float] = {
    "low": 0.5,
    "base": 1.0,
    "high": 2.0,
}

_PROFILE_METADATA: dict[CostProfileName, CostProfileMetadata] = {
    "optimistic_research": CostProfileMetadata(
        profile_name="optimistic_research",
        profile_label="Optimistic Research",
        profile_description="Lower friction assumptions for clean/liquid market conditions.",
        profile_multiplier=0.75,
        intended_use="Best-case research sensitivity check.",
    ),
    "standard_research": CostProfileMetadata(
        profile_name="standard_research",
        profile_label="Standard Research",
        profile_description="Default deterministic assumptions used in baseline research.",
        profile_multiplier=1.0,
        intended_use="Primary comparison and ranking baseline.",
    ),
    "conservative_research": CostProfileMetadata(
        profile_name="conservative_research",
        profile_label="Conservative Research",
        profile_description="Higher friction assumptions for cautious planning.",
        profile_multiplier=1.5,
        intended_use="Downside-aware planning and validation.",
    ),
    "stress_research": CostProfileMetadata(
        profile_name="stress_research",
        profile_label="Stress Research",
        profile_description="Severe execution friction assumptions for robustness stress testing.",
        profile_multiplier=3.0,
        intended_use="Adverse-conditions stress testing.",
    ),
}

_STRESS_PRESETS: dict[StressPresetName, StressPresetMetadata] = {
    "normal_liquidity": StressPresetMetadata(
        preset_name="normal_liquidity",
        preset_label="Normal Liquidity",
        preset_description="Baseline spread/slippage behavior.",
        spread_multiplier=1.0,
        slippage_multiplier=1.0,
        commission_multiplier=1.0,
    ),
    "wide_spread": StressPresetMetadata(
        preset_name="wide_spread",
        preset_label="Wide Spread",
        preset_description="Spread widens while slippage remains baseline.",
        spread_multiplier=3.0,
        slippage_multiplier=1.0,
        commission_multiplier=1.0,
    ),
    "high_slippage": StressPresetMetadata(
        preset_name="high_slippage",
        preset_label="High Slippage",
        preset_description="Slippage worsens while spread remains baseline.",
        spread_multiplier=1.0,
        slippage_multiplier=3.0,
        commission_multiplier=1.0,
    ),
    "volatile_session": StressPresetMetadata(
        preset_name="volatile_session",
        preset_label="Volatile Session",
        preset_description="Both spread and slippage elevated in volatile periods.",
        spread_multiplier=2.0,
        slippage_multiplier=2.0,
        commission_multiplier=1.0,
    ),
    "news_event_stress": StressPresetMetadata(
        preset_name="news_event_stress",
        preset_label="News Event Stress",
        preset_description="Severe spread/slippage widening around event shocks.",
        spread_multiplier=4.0,
        slippage_multiplier=4.0,
        commission_multiplier=1.0,
    ),
}


def list_cost_profiles() -> list[dict[str, str | float | bool]]:
    return [
        {
            "profile_name": p.profile_name,
            "profile_label": p.profile_label,
            "profile_description": p.profile_description,
            "profile_multiplier": p.profile_multiplier,
            "intended_use": p.intended_use,
            "is_broker_calibrated": p.is_broker_calibrated,
            "live_ready": p.live_ready,
        }
        for p in _PROFILE_METADATA.values()
    ]


def get_cost_profile(profile_name: str) -> dict[str, str | float | bool] | None:
    profile = _PROFILE_METADATA.get(profile_name)  # type: ignore[arg-type]
    if profile is None:
        return None
    return {
        "profile_name": profile.profile_name,
        "profile_label": profile.profile_label,
        "profile_description": profile.profile_description,
        "profile_multiplier": profile.profile_multiplier,
        "intended_use": profile.intended_use,
        "is_broker_calibrated": profile.is_broker_calibrated,
        "live_ready": profile.live_ready,
    }


def list_stress_presets() -> list[dict[str, str | float | bool]]:
    return [
        {
            "preset_name": s.preset_name,
            "preset_label": s.preset_label,
            "preset_description": s.preset_description,
            "spread_multiplier": s.spread_multiplier,
            "slippage_multiplier": s.slippage_multiplier,
            "commission_multiplier": s.commission_multiplier,
            "is_broker_calibrated": s.is_broker_calibrated,
            "live_ready": s.live_ready,
        }
        for s in _STRESS_PRESETS.values()
    ]


def get_stress_preset(preset_name: str) -> dict[str, str | float | bool] | None:
    preset = _STRESS_PRESETS.get(preset_name)  # type: ignore[arg-type]
    if preset is None:
        return None
    return {
        "preset_name": preset.preset_name,
        "preset_label": preset.preset_label,
        "preset_description": preset.preset_description,
        "spread_multiplier": preset.spread_multiplier,
        "slippage_multiplier": preset.slippage_multiplier,
        "commission_multiplier": preset.commission_multiplier,
        "is_broker_calibrated": preset.is_broker_calibrated,
        "live_ready": preset.live_ready,
    }


def classify_asset_class(symbol: str, asset_class: str | None = None) -> str:
    """Classify symbol into cost-model asset classes using deterministic rules."""
    if asset_class:
        lowered = asset_class.lower()
        if lowered in {AssetClass.EQUITY.value, AssetClass.ETF.value, AssetClass.INDEX_PROXY.value}:
            return "equities_etfs"
        if lowered == AssetClass.FX.value:
            return "forex"
        if lowered == AssetClass.CRYPTO.value:
            return "crypto"
        if lowered == AssetClass.COMMODITY_PROXY.value:
            return "commodities"

    token = symbol.strip().upper().replace("-", "").replace("/", "")

    if any(token.startswith(prefix) for prefix in _KNOWN_CRYPTO_PREFIXES):
        return "crypto"

    if token in _KNOWN_FOREX:
        return "forex"
    if len(token) == 6 and token.isalpha() and (token.startswith("USD") or token.endswith("USD")):
        return "forex"

    if token in _KNOWN_COMMODITIES:
        return "commodities"

    if token in _KNOWN_ETFS:
        return "equities_etfs"

    if 1 <= len(token) <= 5 and token.isalpha():
        return "equities_etfs"

    return "unknown"


def get_default_assumptions(symbol: str, asset_class: str | None = None) -> ExecutionCostAssumptions:
    """Return deterministic execution-cost assumptions for the given symbol."""
    key = classify_asset_class(symbol=symbol, asset_class=asset_class)
    return _DEFAULT_ASSUMPTIONS.get(key, _DEFAULT_ASSUMPTIONS["unknown"])


def _assumptions_for_scenario(
    assumptions: ExecutionCostAssumptions,
    scenario: CostScenario,
) -> ExecutionCostAssumptions:
    multiplier = _SCENARIO_MULTIPLIERS.get(scenario, 1.0)
    return ExecutionCostAssumptions(
        asset_class=assumptions.asset_class,
        spread_bps=assumptions.spread_bps * multiplier,
        slippage_bps=assumptions.slippage_bps * multiplier,
        commission_bps=assumptions.commission_bps * multiplier,
        fixed_fee_per_trade=assumptions.fixed_fee_per_trade,
    )


def _profile_metadata(profile_name: str) -> CostProfileMetadata:
    return _PROFILE_METADATA.get(profile_name, _PROFILE_METADATA[DEFAULT_COST_PROFILE])  # type: ignore[arg-type]


def _stress_metadata(preset_name: str) -> StressPresetMetadata:
    return _STRESS_PRESETS.get(preset_name, _STRESS_PRESETS[DEFAULT_STRESS_PRESET])  # type: ignore[arg-type]


def calculate_cost_for_scenario(
    *,
    symbol: str,
    quantity: float,
    entry_price: float,
    exit_price: float,
    scenario: CostScenario,
    asset_class: str | None = None,
) -> ExecutionCostEstimate:
    """Calculate one scenario-specific estimate using default profile/preset.

    Backward compatibility contract:
    - defaults to standard_research profile
    - defaults to normal_liquidity stress preset
    """
    return calculate_cost_for_profile_and_scenario(
        symbol=symbol,
        quantity=quantity,
        entry_price=entry_price,
        exit_price=exit_price,
        scenario=scenario,
        profile_name=DEFAULT_COST_PROFILE,
        stress_preset=DEFAULT_STRESS_PRESET,
        asset_class=asset_class,
    )


def calculate_cost_for_profile_and_scenario(
    *,
    symbol: str,
    quantity: float,
    entry_price: float,
    exit_price: float,
    scenario: CostScenario,
    profile_name: str = DEFAULT_COST_PROFILE,
    stress_preset: str = DEFAULT_STRESS_PRESET,
    asset_class: str | None = None,
) -> ExecutionCostEstimate:
    """Calculate scenario estimate with research profile and stress preset."""
    base = get_default_assumptions(symbol=symbol, asset_class=asset_class)
    profile = _profile_metadata(profile_name)
    preset = _stress_metadata(stress_preset)

    scenario_multiplier = _SCENARIO_MULTIPLIERS.get(scenario, 1.0)
    assumptions = ExecutionCostAssumptions(
        asset_class=base.asset_class,
        spread_bps=base.spread_bps * profile.profile_multiplier * scenario_multiplier * preset.spread_multiplier,
        slippage_bps=base.slippage_bps * profile.profile_multiplier * scenario_multiplier * preset.slippage_multiplier,
        commission_bps=base.commission_bps * profile.profile_multiplier * scenario_multiplier * preset.commission_multiplier,
        fixed_fee_per_trade=base.fixed_fee_per_trade,
    )

    qty = max(float(quantity), 0.0)
    entry_notional = abs(float(entry_price) * qty)
    exit_notional = abs(float(exit_price) * qty)

    per_side_ratio = assumptions.per_side_cost_bps / 10_000.0
    entry_cost = entry_notional * per_side_ratio + assumptions.fixed_fee_per_trade
    exit_cost = exit_notional * per_side_ratio + assumptions.fixed_fee_per_trade
    total_cost = entry_cost + exit_cost

    return ExecutionCostEstimate(
        cost_model_version=COST_MODEL_VERSION,
        asset_class=assumptions.asset_class,
        spread_bps=assumptions.spread_bps,
        slippage_bps=assumptions.slippage_bps,
        commission_bps=assumptions.commission_bps,
        fixed_fee_per_trade=assumptions.fixed_fee_per_trade,
        round_trip_cost_bps=assumptions.round_trip_cost_bps,
        estimated_entry_cost=round(entry_cost, 6),
        estimated_exit_cost=round(exit_cost, 6),
        estimated_total_cost=round(total_cost, 6),
        cost_scenario=scenario,
    )


def calculate_sensitivity_band(
    *,
    gross_pnl_amount: float,
    low_total_cost_amount: float,
    base_total_cost_amount: float,
    high_total_cost_amount: float,
) -> dict[str, float | str | None]:
    """Compute cost-drag percentages and deterministic sensitivity level."""
    gross = float(gross_pnl_amount)
    if gross <= 0.0:
        return {
            "cost_drag_low_pct": None,
            "cost_drag_base_pct": None,
            "cost_drag_high_pct": None,
            "cost_sensitivity_level": "high",
        }

    drag_low = max(0.0, float(low_total_cost_amount) / gross * 100.0)
    drag_base = max(0.0, float(base_total_cost_amount) / gross * 100.0)
    drag_high = max(0.0, float(high_total_cost_amount) / gross * 100.0)

    if drag_base < 10.0:
        level = "low"
    elif drag_base <= 30.0:
        level = "medium"
    else:
        level = "high"

    return {
        "cost_drag_low_pct": round(drag_low, 6),
        "cost_drag_base_pct": round(drag_base, 6),
        "cost_drag_high_pct": round(drag_high, 6),
        "cost_sensitivity_level": level,
    }


def build_cost_sensitivity_summary(
    *,
    gross_pnl_amount: float,
    low_cost_estimate: ExecutionCostEstimate,
    base_cost_estimate: ExecutionCostEstimate,
    high_cost_estimate: ExecutionCostEstimate,
) -> dict[str, float | str | None]:
    """Build deterministic low/base/high sensitivity summary for one trade."""
    gross = float(gross_pnl_amount)
    low_net = gross - low_cost_estimate.estimated_total_cost
    base_net = gross - base_cost_estimate.estimated_total_cost
    high_net = gross - high_cost_estimate.estimated_total_cost

    band = calculate_sensitivity_band(
        gross_pnl_amount=gross,
        low_total_cost_amount=low_cost_estimate.estimated_total_cost,
        base_total_cost_amount=base_cost_estimate.estimated_total_cost,
        high_total_cost_amount=high_cost_estimate.estimated_total_cost,
    )

    return {
        "gross_pnl_amount": round(gross, 6),
        "low_net_pnl_amount": round(low_net, 6),
        "base_net_pnl_amount": round(base_net, 6),
        "high_net_pnl_amount": round(high_net, 6),
        "low_total_cost_amount": round(low_cost_estimate.estimated_total_cost, 6),
        "base_total_cost_amount": round(base_cost_estimate.estimated_total_cost, 6),
        "high_total_cost_amount": round(high_cost_estimate.estimated_total_cost, 6),
        "cost_drag_low_pct": band["cost_drag_low_pct"],
        "cost_drag_base_pct": band["cost_drag_base_pct"],
        "cost_drag_high_pct": band["cost_drag_high_pct"],
        "cost_sensitivity_level": band["cost_sensitivity_level"],
    }


def build_profile_sensitivity_summary(
    *,
    symbol: str,
    quantity: float,
    entry_price: float,
    exit_price: float,
    gross_pnl_amount: float,
    profile_name: str = DEFAULT_COST_PROFILE,
    stress_preset: str = DEFAULT_STRESS_PRESET,
    asset_class: str | None = None,
) -> dict[str, float | str | None | bool]:
    """Build low/base/high sensitivity summary for a profile/preset context."""
    low = calculate_cost_for_profile_and_scenario(
        symbol=symbol,
        quantity=quantity,
        entry_price=entry_price,
        exit_price=exit_price,
        scenario="low",
        profile_name=profile_name,
        stress_preset=stress_preset,
        asset_class=asset_class,
    )
    base = calculate_cost_for_profile_and_scenario(
        symbol=symbol,
        quantity=quantity,
        entry_price=entry_price,
        exit_price=exit_price,
        scenario="base",
        profile_name=profile_name,
        stress_preset=stress_preset,
        asset_class=asset_class,
    )
    high = calculate_cost_for_profile_and_scenario(
        symbol=symbol,
        quantity=quantity,
        entry_price=entry_price,
        exit_price=exit_price,
        scenario="high",
        profile_name=profile_name,
        stress_preset=stress_preset,
        asset_class=asset_class,
    )
    summary = build_cost_sensitivity_summary(
        gross_pnl_amount=gross_pnl_amount,
        low_cost_estimate=low,
        base_cost_estimate=base,
        high_cost_estimate=high,
    )
    profile = _profile_metadata(profile_name)
    preset = _stress_metadata(stress_preset)
    return {
        **summary,
        "cost_profile_used": profile.profile_name,
        "stress_preset_used": preset.preset_name,
        "broker_calibrated": False,
        "live_ready": False,
    }


def estimate_trade_cost(
    *,
    symbol: str,
    quantity: float,
    entry_price: float,
    exit_price: float,
    asset_class: str | None = None,
) -> ExecutionCostEstimate:
    """Estimate round-trip execution costs for one closed trade (base scenario)."""
    return calculate_cost_for_profile_and_scenario(
        symbol=symbol,
        quantity=quantity,
        entry_price=entry_price,
        exit_price=exit_price,
        asset_class=asset_class,
        scenario="base",
        profile_name=DEFAULT_COST_PROFILE,
        stress_preset=DEFAULT_STRESS_PRESET,
    )