# Strategy Lab — Research Risk Notes

**Status**: Research-only. Not suitable for live trading decisions.  
**Phase**: MH-18 — Rolling-Window / Multi-Fold Walk-Forward Validation  
**Last updated**: 2026-04-28

---

## 1. Results Include Deterministic Scenario Costs

Strategy Lab now computes both **gross** and **net** metrics. Net metrics model execution
friction using deterministic research assumptions (not broker quotes).

| Cost component | Status |
|---|---|
| Bid-ask spread | ✅ Modelled (research assumption) |
| Slippage / market impact | ✅ Modelled (research assumption) |
| Commission / fees | ✅ Modelled (research assumption) |
| Financing / borrow cost | ❌ Not modelled |
| Tax / settlement | ❌ Not modelled |

### Base assumptions by asset class

| Asset class | Base spread bps | Base slippage bps | Base commission bps | Fixed fee / trade |
|---|---:|---:|---:|---:|
| US equities / ETFs | 2 | 2 | 0 | 0 |
| Forex majors | 1 | 1 | 0 | 0 |
| Crypto | 8 | 8 | 10 | 0 |
| Commodities | 4 | 4 | 0 | 0 |
| Unknown | 5 | 5 | 0 | 0 |

These are deterministic research defaults and should not be interpreted as executable
live pricing.

### Scenario multipliers

MH-15B added sensitivity scenarios around base assumptions:

| Scenario | Multiplier on spread/slippage/commission |
|---|---:|
| `low` | 0.5x |
| `base` | 1.0x |
| `high` | 2.0x |

Fixed per-trade fees remain unchanged across scenarios.

### MH-15C research calibration profiles

Profiles are deterministic multipliers applied to scenario assumptions:

| Profile | Multiplier |
|---|---:|
| `optimistic_research` | 0.75x |
| `standard_research` | 1.0x |
| `conservative_research` | 1.5x |
| `stress_research` | 3.0x |

### MH-15C stress presets

Presets independently stress spread/slippage/commission components:

| Preset | Spread | Slippage | Commission |
|---|---:|---:|---:|
| `normal_liquidity` | 1.0x | 1.0x | 1.0x |
| `wide_spread` | 3.0x | 1.0x | 1.0x |
| `high_slippage` | 1.0x | 3.0x | 1.0x |
| `volatile_session` | 2.0x | 2.0x | 1.0x |
| `news_event_stress` | 4.0x | 4.0x | 1.0x |

Current defaults remain deterministic and backward-compatible:
- profile: `standard_research`
- stress preset: `normal_liquidity`

Every `BacktestRunResponse`, `BacktestReplayResponse`, `StrategyResultResponse`,
`StrategyComparisonResponse`, and `AIBacktestReportResponse` carries a
`research_warnings` block that makes this explicit at the API level:

```json
{
  "research_only": true,
  "execution_costs_modelled": true,
  "spread_modelled": true,
  "slippage_modelled": true,
  "fees_modelled": true,
  "live_ready": false,
  "cost_model_version": "mh15c_v1",
  "cost_model_status": "modelled",
  "warning": "Execution costs are modelled using research assumptions, not broker-confirmed live execution costs. Results remain research-only."
}
```

---

## 2. No Live-Trading Readiness

`live_ready: false` remains a hard-coded gate. Execution costs being modelled does **not**
mean the system is ready for live deployment. No automated process should read this field
as a trigger for live order placement.

---

## 3. Sensitivity Rules

Strategy Lab now computes gross, low-cost net, base-cost net, and high-cost net metrics.

Sensitivity level rules are deterministic:
- low: base cost drag < 10% of gross profit
- medium: base cost drag 10% to 30% of gross profit
- high: base cost drag > 30% of gross profit
- non-positive gross profit: treated as high sensitivity to avoid divide-by-zero

Where cost drag is:
- cost_drag = base_total_cost_amount / gross_pnl_amount

## 4. Metrics Still Missing

| Metric | Status |
|---|---|
| Risk-free rate / Sharpe ratio | Not calculated |
| Annualised return | Not calculated |
| Calmar ratio | Not calculated |
| Rolling drawdown | Not calculated |
| Commission-adjusted P&L | Calculated (net metrics) |
| Slippage-adjusted P&L | Calculated (net metrics) |

---

## 5. Deterministic Result Quality Scoring (MH-16)

Strategy results now include deterministic, research-only quality metadata in
`StrategyResult.metrics`:

- `result_quality_version` (`mh16_v1`)
- `sample_size_score`
- `profitability_score`
- `drawdown_score`
- `cost_sensitivity_score`
- `consistency_score` (nullable when monthly data is unavailable)
- `robustness_score`
- `overfitting_risk_score`
- `research_confidence_score`
- `quality_grade` (`A|B|C|D|F`)
- `quality_warnings`
- `paper_trade_ready=false`
- `live_ready=false`

These scores are deterministic guidance only and are **not** permission to paper trade
or live trade.

---

## 6. Quality Summary Endpoint

New read-only endpoint:
- `GET /strategy-lab/backtests/{backtest_id}/quality-summary`

Returns aggregate research quality information:
- average confidence
- grade distribution
- highest overfitting risk
- aggregate warnings

This endpoint is read-only and does not trigger replay/recalculation.

---

## 7. Walk-Forward / Out-of-Sample Validation (MH-17)

Strategy Lab now supports deterministic walk-forward validation with a default split:

- in-sample: 60%
- validation: 20%
- out-of-sample: 20%

Custom split percentages are accepted when they total 100 and each split remains
positive duration.

Read-only endpoints:
- `POST /strategy-lab/backtests/{backtest_id}/walk-forward`
- `GET /strategy-lab/backtests/{backtest_id}/walk-forward`

Validation outputs include:
- period metrics (trade count, win rate, net PF, net return, max drawdown,
  confidence, quality grade)
- degradation metrics (return/profit-factor/confidence degradation)
- `validation_stability_score` and stability grade (`stable|mixed|unstable`)
- warnings for poor out-of-sample behavior
- `paper_trade_ready=false`
- `live_ready=false`

Out-of-sample validation is deterministic research guidance, not approval for
paper or live trading.

---

## 8. Strategy Comparison Warnings

The comparison runner (`POST /strategy-lab/comparisons/run`) creates new
`StrategyConfig` rows for every Cartesian-product combination on each call.
It does **not** deduplicate equivalent parameter sets across calls.

- This is acceptable for research use.
- Operators running large grids frequently may accumulate storage over time.
- A deduplication / config-reuse phase is recommended before production scale-up.

Comparison scoring remains based on base net metrics. Comparison responses now also
surface high-cost scenario metrics and sensitivity levels, and warn when high-cost
assumptions turn a strategy unprofitable. They also include deterministic research
metadata for `cost_profile_used`, `stress_preset_used`, and `broker_calibrated=false`.
Comparison rows now also include `quality_grade`, `research_confidence_score`,
`overfitting_risk_score`, and `quality_warnings`.
When available, rows also surface walk-forward metadata
(`validation_stability_score`, `validation_stability_grade`, `out_of_sample_pass`,
`walk_forward_warnings`).

---

## 9. Rolling-Window / Multi-Fold Validation (MH-18)

Strategy Lab now supports repeated rolling-window validation through the existing
walk-forward endpoint by supplying `fold_count > 1`.

Example request shape:
- `POST /strategy-lab/backtests/{backtest_id}/walk-forward`
- body: `{ "fold_count": 3 }`

Multi-fold responses now include:
- per-fold split windows and period metrics
- aggregate rolling summary metrics:
  - `fold_count`
  - `stable_fold_ratio`
  - `average_validation_stability_score`
  - `stability_dispersion`
  - `average_return_degradation_pct`
  - `average_confidence_degradation_pct`
  - `rolling_validation_grade`
  - `rolling_out_of_sample_pass`

Persisted strategy result metrics now store:
- `walk_forward_validation_version = mh18_v1` when `fold_count > 1`
- `walk_forward_fold_count`
- `walk_forward_folds`
- `rolling_window_summary`

Single-fold behavior remains backward-compatible:
- `fold_count = 1` preserves MH-17 semantics
- aggregate comparison fields still map to a single deterministic stability score,
  grade, pass/fail flag, and warnings

All rolling validation output remains research-only:
- `paper_trade_ready=false`
- `live_ready=false`
- no paper-trading unlock
- no live-trading approval

---

## 10. Gross vs Low/Base/High Interpretation

- Top-level historical fields remain backward-compatible and may reflect gross-style values.
- Scenario net values are available in strategy result metrics:
  `low_net_total_return_pct`, `base_net_total_return_pct`, `high_net_total_return_pct`,
  `low_net_profit_factor`, `base_net_profit_factor`, `high_net_profit_factor`,
  and scenario cost totals.
- Compatibility fields (`net_total_return_pct`, `net_profit_factor`, `total_cost_amount`)
  remain equal to base scenario values.
- Comparison scoring now prefers net metrics when available and warns when forced to
  fall back to gross metrics.

---

## 11. Strategy Lab Research Review UI (MH-19)

The `/strategy-lab` frontend route is now a research review cockpit for existing
outputs only. It surfaces:

- backtest runs
- comparison runs
- strategy result metrics
- deterministic cost profile and stress preset metadata
- quality summaries
- walk-forward / rolling-fold validation summaries
- optional AI research reports

The UI does **not** include:

- live approval
- live trading
- paper-trading controls
- broker execution
- baseline manager controls
- signal generation from Strategy Lab outputs

Optional buttons on the page are explicitly marked as research actions and state
that they do not execute trades.

---

## 12. Do Not Use Strategy Lab Output Directly for Live Trading

Strategy Lab outputs (comparison reports, AI backtest reports, strategy results) are
intended for **research and analyst review only**. The workflow for progression toward
live trading is:

1. Research → Strategy Lab backtest (current phase)
2. Cost/scenario/profile stress review (MH-15A/B/C)
3. Result quality scoring review (MH-16)
4. Walk-forward/out-of-sample stability review (MH-17)
5. Rolling-window or multi-fold walk-forward validation (MH-18)
6. **Future**: broker-calibrated and venue-specific execution model refinement
7. **Future**: live approval gate with multi-party sign-off

No system in phases 1-6 should be interpreted as granting live-trading permission.

Overfitting warnings in MH-16 are conservative deterministic v1 rules and should be
treated as screening signals, not as definitive statistical proof.

Walk-forward stability in MH-17/MH-18 is deterministic rule-based guidance and should
be interpreted as conservative screening, not formal statistical validation.

---

## 13. Next Recommended Phase

→ **Broker-Calibrated Execution Model Refinement (Research-Only)**: improve venue-
specific cost realism without changing `paper_trade_ready=false` or
`live_ready=false`.
