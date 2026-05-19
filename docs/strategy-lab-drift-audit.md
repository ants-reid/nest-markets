# Strategy Lab Drift Audit Report

**Date**: 28 April 2026
**Scope**: All Strategy Lab API routes, services, models, test files, and live database state
**Method**: Read-only — no code created or modified, no records altered, no migrations run

---

## A. Executive Summary

No unauthorized drift found. All Strategy Lab capabilities present in the codebase are explicitly accounted for in the build ledger (`docs/build-ledger.md`) as phases MH-06 through MH-14. The 314 strategy configs and 16 backtest runs in the live database were created by the `StrategyComparisonService` during developer testing of MH-10; this is a documented known limitation of that service (no deduplication across comparison calls). The 7 failed backtest runs are a correct system artefact: they pre-date MH-10B, which recalculated AAPL's quality score from 85.39 to 98.17, allowing subsequent runs to pass the `approved_for_backtest` gate. All 71 Strategy Lab tests pass. The codebase is safe, correctly wired, and ready to advance to MH-19 once that phase is deliberately scoped.

---

## B. Strategy Lab Endpoints Found

**File**: `apps/api/app/api/routes/strategy_lab.py`

| # | Method | Path | Handler | Phase | Purpose |
|---|--------|------|---------|-------|---------|
| 1 | POST | `/strategy-lab/configs` | `create_config` | MH-06 | Create a new strategy config |
| 2 | GET | `/strategy-lab/configs` | `list_configs` | MH-06 | Paginated list of configs |
| 3 | GET | `/strategy-lab/configs/{config_id}` | `get_config` | MH-06 | Fetch one config by UUID |
| 4 | POST | `/strategy-lab/backtests` | `create_backtest_run` | MH-06 | Create a queued backtest stub |
| 5 | GET | `/strategy-lab/backtests` | `list_backtest_runs` | MH-06 | List backtest runs |
| 6 | GET | `/strategy-lab/backtests/{backtest_id}` | `get_backtest_run` | MH-06 | Fetch one run by UUID |
| 7 | GET | `/strategy-lab/backtests/{backtest_id}/trades` | `list_trades` | MH-06 | Paginated mock trades for a run |
| 8 | GET | `/strategy-lab/backtests/{backtest_id}/results` | `list_results` | MH-06 | Strategy results for a run |
| 9 | GET | `/strategy-lab/backtests/{backtest_id}/equity-curve` | `list_equity_curve` | MH-06 | Equity curve points |
| 10 | GET | `/strategy-lab/backtests/{backtest_id}/drawdowns` | `list_drawdowns` | MH-06 | Drawdown periods |
| 11 | POST | `/strategy-lab/backtests/{backtest_id}/replay` | `replay_backtest` | MH-07 | Trigger deterministic replay engine |
| 12 | POST | `/strategy-lab/comparisons/run` | `run_comparison` | MH-10 | Multi-config Cartesian grid runner |
| 13 | GET | `/strategy-lab/comparisons` | `list_comparisons` | MH-11 | Comparison history |
| 14 | GET | `/strategy-lab/comparisons/{backtest_run_id}` | `get_comparison_detail` | MH-11 | Detail for one comparison run |
| 15 | POST | `/strategy-lab/comparisons/{backtest_run_id}/label` | `set_label` | MH-11 | Set research label on a comparison |
| 16 | POST | `/strategy-lab/backtests/{backtest_id}/ai-report` | `create_ai_report` | MH-14 | Trigger LLM-powered research report |
| 17 | GET | `/strategy-lab/backtests/{backtest_id}/ai-reports` | `list_ai_reports` | MH-14 | List AI reports for a run |
| 18 | GET | `/strategy-lab/ai-reports/{report_id}` | `get_ai_report` | MH-14 | Fetch one AI report by UUID |

**Total: 18 endpoints** — all accounted for in the build ledger.

---

## C. Strategy Lab Services and Files Found

| File | Phase | Role |
|------|-------|------|
| `apps/api/app/services/strategy_lab_service.py` | MH-06, MH-11 | CRUD for configs, backtest runs, trades, results, equity curve, drawdowns; comparison history/label |
| `apps/api/app/services/historical_replay_service.py` | MH-07 | Deterministic candle replay; reads `bars` table; enforces quality gate; orchestrates simulation |
| `apps/api/app/services/mock_trade_simulator_service.py` | MH-08 | `ma_momentum` trade simulation; entry/exit/stop/target; equity curve; drawdowns; metrics |
| `apps/api/app/services/strategy_comparison_service.py` | MH-10 | Cartesian parameter grid; scoring formula; creates `StrategyConfig` + `BacktestRun` rows per call |
| `apps/api/app/services/ai_backtest_report_service.py` | MH-14 | LLM-powered research report; calls `LLMProviderRouter`; persists `AIBacktestReport` |
| `apps/api/app/api/routes/strategy_lab.py` | MH-06–14 | All 18 route handlers |
| `apps/api/app/tests/test_strategy_lab.py` | MH-06 | 18 tests |
| `apps/api/app/tests/test_strategy_lab_replay.py` | MH-07 | 15 tests |
| `apps/api/app/tests/test_strategy_lab_mock_trades.py` | MH-08 | 17 tests |
| `apps/api/app/tests/test_strategy_lab_comparison.py` | MH-10 | 17 tests |
| `apps/api/app/tests/test_strategy_lab_history.py` | MH-11 | 4 tests |

**No Strategy Lab files found outside the above list.** No orphan service, orphan route file, or shadow import detected.

---

## D. Matrix Phase Mapping

| Build Ledger Phase | Capability | Status |
|---|---|---|
| MH-06 | Strategy Lab data contracts: DB models, schemas, CRUD routes, 6 Strategy Lab tables | PASS — Ledger entry present, 18/18 tests pass |
| MH-07 | Historical Replay Service: `queued→running→completed/failed`, reads `bars` table | PASS — Ledger entry present, 15/15 tests pass |
| MH-08 | Mock Trade Simulator: `ma_momentum`, entry/exit/stop/target, equity curve, drawdowns | PASS — Ledger entry present, 17/17 tests pass |
| MH-09 | Data quality integration: `approved_for_backtest` gate wired into replay | PASS — Ledger entry present (quality gate confirmed in code at lines 158, 272–281 of replay service) |
| MH-10 | Strategy Comparison Service: Cartesian grid, scoring, ranked results | PASS — Ledger entry present, 17/17 tests pass |
| MH-10B | Quality score recalculation (AAPL: 85.39 → 98.17) | PASS — Ledger entry present |
| MH-10C | Comparison scoring formula refinements | PASS — Ledger entry present |
| MH-11 | Comparison history, detail, research label endpoints | PASS — Ledger entry present, 4/4 tests pass |
| MH-12 | Not in Strategy Lab scope | — |
| MH-13 | Not in Strategy Lab scope | — |
| MH-14 | AI Backtest Report Service: LLM-powered research reports with structured JSON output | PASS — Ledger entry present |
| MH-14 Polish | AI report refinements | PASS — Ledger entry present |

**No Strategy Lab phase found in code that is absent from the build ledger.**

---

## E. Safety Checks

| Check | Result | Evidence |
|---|---|---|
| Lookahead bias prevention | PASS | Simulation iterates `for i in range(slow_window, len(candles))` sequentially; entry/exit decisions use only indices <= `i`; no access to `i+n` bars |
| One trade at a time per (asset, timeframe) | PASS | `open_trade is None` guard prevents concurrent position entry |
| Live trading / broker execution | PASS | No `ibkr`, `broker`, `execute_order`, `place_order`, or `submit` calls found in any Strategy Lab service |
| Spread / slippage modelling | NOT MODELLED | No spread or slippage applied. Entries and exits use bar close prices directly. Known limitation — acceptable for research-phase backtesting; must be noted before production promotion. |
| Commission / fee modelling | NOT MODELLED | No transaction cost deduction. Same caveat applies. |
| Zero-risk-distance guard | PASS | `if risk_dist <= 0.0: warnings.append(...); continue` — skips degenerate entries |
| End-of-data open trade closure | PASS | `if open_trade is not None: _close_trade(... "end_of_data" ...)` at loop end |

---

## F. Data Quality Enforcement Status

| Check | Result | Evidence |
|---|---|---|
| `approved_for_backtest` gate enforced by default | YES | `_check_approval()` at line 260 of replay service queries `MarketDataQualityReport`; returns `(False, msg)` unless `approved_for_backtest = True` |
| Behaviour when gate fails (default) | Correct — skips asset | Run status transitions to `failed` for that (asset, timeframe) combo |
| Bypass flag available | YES — `allow_unapproved_data=True` | Emits warning but proceeds. Flag is not exposed via the public API route — it is backend-only with a hardcoded default of `False` in the route handler |
| Quality score threshold | Score >= 90 enforced by the quality report itself (not re-checked in replay) | AAPL was 85.39 pre-MH-10B, causing 7 run failures; raised to 98.17 by MH-10B |

---

## G. Metrics Calculation Status

| Metric | Calculated | Where |
|---|---|---|
| Total trades | YES | `_compute_metrics()` in `mock_trade_simulator_service.py` |
| Win rate | YES | `wins / total` |
| Average win / average loss | YES | Mean of win/loss `pnl_amount` lists |
| Profit factor | YES | `gross_profit / gross_loss` |
| Expectancy | YES | `win_rate x avg_win - (1 - win_rate) x avg_loss` |
| Total return % | YES | `(final_equity - starting_capital) / starting_capital x 100` |
| Max drawdown % | YES | Max `drawdown_pct` across all equity curve points |
| Equity curve | YES | `EquityCurvePoint` rows written per closed trade |
| Drawdown periods | YES | `_detect_drawdown_periods()` — peak-to-trough periods with recovery flag |
| Comparison score | YES | `min(pf,5)x30 + returnx2 + wrx20 - ddx3`, clamped [0,100] |
| R-multiple per trade | YES | `(exit - entry) / risk_distance` |
| Spread / slippage | NOT IMPLEMENTED | — |
| Fees / commission | NOT IMPLEMENTED | — |
| Sharpe ratio | NOT IMPLEMENTED | — |
| Annualised return | NOT IMPLEMENTED | — |

---

## H. Database Record Counts (Live, as of this audit)

| Table | Count | Notes |
|---|---|---|
| `strategy_configs` | 314 | All `ma_momentum`. Created by `StrategyComparisonService` — 224 AAPL, 30 NVDA, 30 SPY, 30 QQQ |
| `backtest_runs` | 16 | 9 completed, 7 failed |
| `mock_trades` | 39,697 | Only in 9 completed runs; 7 failed runs have 0 trades |
| `strategy_results` | 270 | 30 per completed run x 9 runs |
| `equity_curve_points` | 39,967 | Includes starting-capital anchor point per run |
| `drawdown_periods` | 2,329 | Across all 9 completed runs |

**Source of 314 configs**: Each call to `POST /strategy-lab/comparisons/run` creates new `StrategyConfig` rows — no deduplication. The comparison service has this documented as a known limitation.

**Source of 7 failed runs**: AAPL's `approved_for_backtest` quality score was 85.39 (below 90 threshold) during early MH-10 development testing. These runs correctly failed. MH-10B raised AAPL's score to 98.17; all 9 subsequent runs completed successfully.

---

## I. What Is Safe to Keep

Everything. Specifically:

- All 18 API route handlers — correctly implementing MH-06 through MH-14, no overreach
- `HistoricalReplayService` — reads-only from `bars`; no live execution path
- `MockTradeSimulatorService` — deterministic, sequential, no lookahead, no broker wiring
- `StrategyComparisonService` — parameter search only; creates research artefacts, nothing executable
- `AIBacktestReportService` — LLM report generation; read-only input; writes only `AIBacktestReport` rows
- All 6 Strategy Lab DB tables (`strategy_configs`, `backtest_runs`, `mock_trades`, `strategy_results`, `equity_curve_points`, `drawdown_periods`)
- All 314 `strategy_configs` rows and 9 completed `backtest_runs` — valid research data
- The 7 failed runs — valid system history; evidence that the quality gate worked before MH-10B

---

## J. What Looks Like Drift or Is Unsafe

| Item | Assessment | Severity |
|---|---|---|
| 314 config rows — no deduplication | Not drift; documented known limitation of `StrategyComparisonService`. Will grow unboundedly with each comparison call. | Low — research-phase acceptable; needs a dedup or cleanup mechanism before production |
| No spread/slippage/fee modelling | Not drift — never scoped. Results are optimistic relative to live trading. Must be disclosed before any live promotion. | Medium — acceptable for research; blocking for any live signal use |
| `allow_unapproved_data` bypass flag | Not drift — intentional escape hatch for dev. Not exposed via public API. Low risk as-is. | Low |
| MH-14 AI reports have 0 dedicated tests | The endpoint is implemented and in the ledger, but no `test_ai_report*.py` file exists. All other MH phases have test files. | Medium — gap in coverage, not drift |
| 4 tests for MH-11 history | Thin coverage for comparison history/label compared to other phases (15–18 tests). | Low |
| No MH-19 defined | No definition of the next phase exists in the build ledger. Next build could accidentally extend Strategy Lab or start live wiring without a formal scope. | Medium — process risk, not code risk |

**No live broker wiring detected. No MH-19 code detected. No emergency stop / live approval code detected.** The prior accidental MH-19 build was confirmed fully rolled back.

---

## K. Recommendation

**Keep everything. Relabel current position as MH-18 complete. Define MH-19 deliberately before any new build.**

Specific actions, in priority order:

1. **Keep all 314 configs and 9 completed runs** — valid research artefacts. Do not delete.
2. **Add MH-14 AI report tests** — the only phase with a route implementation but no test file. Create `test_strategy_lab_ai_report.py` to cover: report creation, list, get-by-id, LLM mock, malformed response handling.
3. **Document spread/slippage gap** — add a note to `SIGNAL_SERVICE.md` or `INDICATORS.md` explicitly stating that mock simulations do not model execution costs, and that this must be addressed before any live signal promotion.
4. **Define MH-19 in the build ledger before writing any code** — the natural next phases are: (a) signal generation service consuming backtest output, or (b) paper trading mode, or (c) config deduplication + comparison pruning. Choose one, write the scope, then build.
5. **Do not manually clean the DB** — the 314 configs and 7 failed runs are coherent history. A future cleanup migration can be scoped as part of MH-19 or a separate maintenance ticket if storage becomes a concern.

The Strategy Lab is legitimately and correctly built. Proceed with confidence.
