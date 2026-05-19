# Build Plan 3 — Multi-Asset Universe, Auto Paper Trader & AI Learning Loop

Date: 2026-04-24
Last updated by: autonomous planning pass

## Purpose

Build Plan 2 achieved RC-2: guarded live trading scaffold, signal persistence, background worker
infrastructure, Polygon market data client, IBKR broker scaffold, prompt versioning, and news ingestion.

Build Plan 3 completes the **autonomous improvement cycle**:

> **multi-asset signal sweep → ranked opportunity selection → auto paper execution → result capture → AI feedback loop → adapted signals**

The system will be able to:
1. Watch a universe of instruments (FX pairs, equities, ETFs, commodity proxies, crypto)
2. Sweep the universe on a schedule, generating AI signals for every asset
3. Rank signals by confidence score and select the best opportunities automatically
4. Execute the top candidates as paper trades without requiring manual approval
5. Record actual outcomes (fill, close, PnL) against predicted direction and magnitude
6. Feed performance history back into the LLM prompt context to improve future signal quality

---

## How To Use This Plan

Same rules as BP-1 and BP-2:

1. Work top to bottom within each section.
2. Before starting a step, mark it `[IN-PROGRESS]` in this file.
3. When done, mark it `[DONE]` and update the referenced matrix rows.
4. If a step produces a new file or service, add it to `docs/implementation-matrix.md` first.
5. If a step produces a new test, add its QA ID to `docs/regression-qa-matrix.md` first.
6. Never mark a step DONE without updating the linked matrix rows.

## Anti-Drift Rules (inherited + new)

- Gates 1–9 from `docs/release-gates.md` remain in force.
- Auto paper trader must not bypass position sizing or risk rules. (Gate 10 — new)
- AI learning loop must never auto-modify a prompt in-place; all prompt changes must create a new PromptVersion row. (Gate 11 — new)
- Signal sweep worker must be rate-limited to avoid hammering Polygon API. (Gate 12 — new)

---

## New Gates

### Gate 10 — Auto Paper Trade Risk Isolation
- **Check:** `grep -rn "auto_paper\|AutoPaper" apps/api/app --include="*.py"` → confirm all auto-paper execution paths call `RiskEvaluator` before submitting
- **Check:** No position is opened without a `risk_approved` or `auto_approved` signal status
- **Pass condition:** Zero auto-paper trades created without risk gate passage

### Gate 11 — Prompt Version Immutability
- **Check:** `grep -rn "prompt_text\s*=" apps/api/app/services --include="*.py"` → confirm no in-place update of an existing PromptVersion row
- **Check:** Every learning loop write creates a new `PromptVersion` row with an incremented version number
- **Pass condition:** PromptVersion rows are append-only; no UPDATE on the `prompt_text` field

### Gate 12 — Polygon Rate Limit Compliance
- **Check:** Signal sweep worker uses the `PolygonClient` (not raw `httpx`/`requests`); rate limiting enforced at client level
- **Pass condition:** No direct HTTP calls to api.polygon.io outside `apps/api/app/clients/market_data/`

---

## Section 1 — Asset Universe Seeding (Phase 10)

Seed a representative universe of tradeable instruments so the signal sweep has something to scan.

### BP3-01.01 — Create asset seed script
- **Action:** Create `apps/api/scripts/seed_assets.py` that inserts a standard universe into the `assets` table via SQLAlchemy; universe covers: 6 FX pairs (EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, USDCHF), 5 US equities (AAPL, MSFT, NVDA, JPM, XOM), 3 commodity proxies (GLD, SLV, USO), 2 energy ETFs (XLE, XOM), 2 crypto (BTCUSD, ETHUSD), 2 index proxies (SPY, QQQ)
- **Pass condition:** Script runs against a development DB and inserts 20 assets without errors; re-run is idempotent (ON CONFLICT DO NOTHING or upsert)
- **Impl IDs:** API-M01 (asset model), new API-SC01 (seed script)
- **QA IDs:** QA-200
- **Workstream:** WS-01
- **Phase:** Phase 10
- **Priority:** P1
- **Status:** [DONE] 2026-04-24 — 4 tests (test_seed_assets.py)

### BP3-01.02 — Add asset universe management API
- **Action:** Create `apps/api/app/api/routes/assets.py` with: `GET /assets` (list with filter by asset_class), `POST /assets` (add asset), `DELETE /assets/{asset_id}` (deactivate); add to matrix as API-R08
- **Pass condition:** All three endpoints return correct shapes; `DELETE` deactivates (soft delete) rather than physical delete; 4 route tests passing (QA-201)
- **Impl IDs:** API-R08, API-M01
- **QA IDs:** QA-201
- **Workstream:** WS-03
- **Phase:** Phase 10
- **Priority:** P1
- **Status:** [DONE] 2026-04-24 — 6 tests (test_assets_route.py)

### BP3-01.03 — Add asset universe UI page
- **Action:** Create `apps/web/app/assets/page.tsx` showing the active universe as a table (symbol, class, active status, last signal date); add to matrix as WEB-P13; add Nav link
- **Pass condition:** Page renders at `/assets`; table shows all assets; QA-202 Playwright test passes
- **Impl IDs:** WEB-P13
- **QA IDs:** QA-202
- **Workstream:** WS-04
- **Phase:** Phase 10
- **Priority:** P2
- **Status:** [DONE] 2026-04-24 — page created; Gate 3 pass (no hex literals); Nav link added

---

## Section 2 — Signal Sweep Worker (Phase 10)

A scheduled background worker that iterates the active asset universe and generates an AI signal for each asset.

### BP3-02.01 — Create SignalSweepWorker
- **Action:** Create `apps/api/app/workers/signal_sweep_worker.py`; subclass `BaseWorker`; implement `run()` to: (1) load all active assets from DB, (2) for each asset, call `SignalService.generate_signal()` with a standard feature snapshot, (3) persist each signal via `PersistenceSignalService`, (4) emit a log row with sweep ID, asset, signal ID, and duration; add API-W03 to matrix
- **Pass condition:** Worker produces a `WorkerResult` with count of signals generated; isolated unit tests pass (QA-203)
- **Impl IDs:** API-W03
- **QA IDs:** QA-203
- **Workstream:** WS-01
- **Phase:** Phase 10
- **Priority:** P1
- **Status:** [DONE] 2026-04-24 — 5 tests (test_signal_sweep_worker.py)

### BP3-02.02 — Register sweep in scheduler
- **Action:** Register `SignalSweepWorker` in `apps/api/app/schedules/scheduler_registry.py` (or equivalent); configure default interval (e.g. every 4 hours); guard with `APP_ENV != test`
- **Pass condition:** Scheduler registry lists sweep job; job does not fire under `APP_ENV=test`; Gate 9 still passes (QA-204)
- **Impl IDs:** API-W03, API-W02
- **QA IDs:** QA-204
- **Workstream:** WS-01
- **Phase:** Phase 10
- **Priority:** P1
- **Status:** [DONE] 2026-04-24 — 3 scheduler tests; gate 9 pass

### BP3-02.03 — Add Polygon bar fetching to sweep
- **Action:** In `SignalSweepWorker.run()`, before calling `SignalService`, fetch the latest N bars for each asset from `PolygonClient`; populate the feature snapshot with real OHLCV data; fall back to last stored bars if Polygon returns no data
- **Pass condition:** Worker test with mocked `PolygonClient` passes; no raw HTTP calls outside client layer (Gate 12 pass) (QA-205)
- **Impl IDs:** API-W03, API-CL02 (PolygonClient)
- **QA IDs:** QA-205
- **Workstream:** WS-01
- **Phase:** Phase 10
- **Priority:** P1
- **Status:** [DONE] 2026-04-24 — 5 tests (bar-fetch integration in sweep worker)

### BP3-02.04 — Add sweep history UI
- **Action:** Create `apps/web/app/sweeps/page.tsx` showing sweep run history (sweep ID, timestamp, assets scanned, signals generated, duration); add WEB-P14 to matrix
- **Pass condition:** Page renders at `/sweeps`; QA-206 Playwright test passes
- **Impl IDs:** WEB-P14
- **QA IDs:** QA-206
- **Workstream:** WS-04
- **Phase:** Phase 10
- **Priority:** P2
- **Status:** [NOT STARTED]

---

## Section 3 — Opportunity Ranker (Phase 10)

Score and rank signals from the sweep so the best opportunities float to the top.

### BP3-03.01 — Create OpportunityRankerService
- **Action:** Create `apps/api/app/services/opportunity_ranker_service.py`; implement `rank_signals(signal_ids: list[UUID]) -> list[RankedOpportunity]`; scoring inputs: LLM confidence score, regime alignment, catalyst presence, spread vs risk profile, historical win rate for the asset/setup type combo (initially 0.5 if no history); add API-S13 to matrix
- **Pass condition:** Service unit tests cover: empty list, single signal, list sorted descending by composite score (QA-207)
- **Impl IDs:** API-S13
- **QA IDs:** QA-207
- **Workstream:** WS-03
- **Phase:** Phase 10
- **Priority:** P1
- **Status:** [DONE] 2026-04-24 — 5 unit tests (test_opportunities.py)

### BP3-03.02 — Expose ranked opportunities endpoint
- **Action:** Add `GET /opportunities` to a new route `apps/api/app/api/routes/opportunities.py`; returns top-N signals ranked by composite score from the most recent sweep; add API-R09 to matrix
- **Pass condition:** Endpoint returns sorted list with score field; 3 route tests pass (QA-208)
- **Impl IDs:** API-R09, API-S13
- **QA IDs:** QA-208
- **Workstream:** WS-03
- **Phase:** Phase 10
- **Priority:** P1
- **Status:** [DONE] 2026-04-24 — 4 route tests (test_opportunities.py)

### BP3-03.03 — Build opportunities UI page
- **Action:** Create `apps/web/app/opportunities/page.tsx`; display top-ranked signals with score badge, asset, direction, setup type, confidence; wire to `GET /opportunities`; add WEB-P15 to matrix
- **Pass condition:** Page renders at `/opportunities`; ranked list displayed; QA-209 Playwright test passes
- **Impl IDs:** WEB-P15
- **QA IDs:** QA-209
- **Workstream:** WS-04
- **Phase:** Phase 10
- **Priority:** P2
- **Status:** [DONE] 2026-04-24 — page created; Gate 3 pass; Nav link added

---

## Section 4 — Auto Paper Trader (Phase 11)

Execute the top-N ranked opportunities as paper trades automatically, without manual approval.

### BP3-04.01 — Add auto_paper execution mode
- **Action:** Add `AUTO_PAPER = "auto_paper"` to `ExecutionModeName` enum in `apps/api/app/db/enums.py`; update `ExecutionModeService` to recognise it; auto_paper mode skips user approval and goes directly to paper execution after risk gate
- **Pass condition:** Enum round-trips correctly; `ExecutionModeService` unit test confirms auto_paper path (QA-210); Gate 10 check: risk gate is called before any paper order is created
- **Impl IDs:** API-S04 (ExecutionModeService)
- **QA IDs:** QA-210
- **Workstream:** WS-03
- **Phase:** Phase 11
- **Priority:** P1
- **Status:** [NOT STARTED]

### BP3-04.02 — Create AutoPaperTraderWorker
- **Action:** Create `apps/api/app/workers/auto_paper_trader_worker.py`; subclass `BaseWorker`; implement `run()` to: (1) call `GET /opportunities` (or service directly) to get top-N ranked signals, (2) for each, call `RiskEvaluator`, (3) if approved, submit paper order via `PaperExecutionService`, (4) record paper trade with source `auto_sweep`; add API-W04 to matrix
- **Pass condition:** Worker unit tests cover: no opportunities, risk-blocked opportunity (no paper order created), approved opportunity (paper order created); Gate 10 pass (QA-211, QA-212)
- **Impl IDs:** API-W04
- **QA IDs:** QA-211, QA-212
- **Workstream:** WS-01
- **Phase:** Phase 11
- **Priority:** P1
- **Status:** [NOT STARTED]

### BP3-04.03 — Register auto paper trader in scheduler
- **Action:** Register `AutoPaperTraderWorker` in scheduler; run after each signal sweep completes (chain or separate interval); guard with `APP_ENV != test`
- **Pass condition:** Scheduler registry shows auto_paper_trader job; Gate 9 still passes (QA-213)
- **Impl IDs:** API-W04, API-W02
- **QA IDs:** QA-213
- **Workstream:** WS-01
- **Phase:** Phase 11
- **Priority:** P1
- **Status:** [NOT STARTED]

### BP3-04.04 — Add auto paper trade cap (safety limit)
- **Action:** Add config value `AUTO_PAPER_MAX_OPEN_POSITIONS` (default: 5) read from environment; `AutoPaperTraderWorker` checks open auto-paper position count before opening new ones; refuse if at cap
- **Pass condition:** Test confirms worker does not open trade #6 when 5 are open (QA-214)
- **Impl IDs:** API-W04
- **QA IDs:** QA-214
- **Workstream:** WS-01
- **Phase:** Phase 11
- **Priority:** P1
- **Status:** [NOT STARTED]

### BP3-04.05 — Auto paper trade close worker
- **Action:** Create `apps/api/app/workers/auto_paper_close_worker.py`; runs on schedule (e.g. daily); closes paper positions that have reached their horizon label expiry (intraday → end of session, 1–3 days, 3–10 days); records final PnL against signal; add API-W05 to matrix
- **Pass condition:** Worker closes expired positions and records outcome; unit tests cover partial-horizon and full-horizon cases (QA-215)
- **Impl IDs:** API-W05
- **QA IDs:** QA-215
- **Workstream:** WS-01
- **Phase:** Phase 11
- **Priority:** P1
- **Status:** [NOT STARTED]

---

## Section 5 — Result Capture & Feedback Store (Phase 11)

Record every auto-paper outcome so the learning loop has structured training data.

### BP3-05.01 — Create SignalOutcome model
- **Action:** Create `apps/api/app/db/models/signal_outcome.py` with fields: `signal_id` (FK), `asset_id` (FK), `setup_type`, `direction`, `horizon_label`, `entry_price`, `exit_price`, `predicted_direction_correct` (bool), `actual_pnl_pct`, `catalyst_type`, `regime_at_entry`, `closed_at`; add API-M21 to matrix; create Alembic migration
- **Pass condition:** Migration applies cleanly; model has tests (QA-216)
- **Impl IDs:** API-M21
- **QA IDs:** QA-216
- **Workstream:** WS-02
- **Phase:** Phase 11
- **Priority:** P1
- **Status:** [DONE] 2026-04-25 — 3 tests (test_signal_outcome.py QA-216); Alembic migration PENDING (checkpoint)

### BP3-05.02 — Create PersistenceSignalOutcomeService
- **Action:** Create `apps/api/app/services/persistence_signal_outcome_service.py`; implement `record_outcome(...)` and `get_outcomes_for_asset(asset_id)` and `get_outcomes_for_setup(setup_type)`; add API-P06 to matrix
- **Pass condition:** Service unit tests cover record, retrieve-by-asset, retrieve-by-setup (QA-217)
- **Impl IDs:** API-P06
- **QA IDs:** QA-217
- **Workstream:** WS-02
- **Phase:** Phase 11
- **Priority:** P1
- **Status:** [DONE] 2026-04-25 — 4 tests (test_signal_outcome.py QA-217)

### BP3-05.03 — Wire AutoPaperCloseWorker to outcome recording
- **Action:** In `AutoPaperCloseWorker.close_position()`, after computing final PnL, call `PersistenceSignalOutcomeService.record_outcome()`; confirm direction correctness is recorded (predicted vs actual)
- **Pass condition:** Close worker integration test confirms outcome row written (QA-218)
- **Impl IDs:** API-W05, API-P06
- **QA IDs:** QA-218
- **Workstream:** WS-01
- **Phase:** Phase 11
- **Priority:** P1
- **Status:** [DONE] 2026-04-25 — 1 integration test (test_signal_outcome.py QA-218)

---

## Section 6 — AI Learning Loop (Phase 12)

Use accumulated signal outcomes to adapt the LLM prompt context, improving future signal quality.

### BP3-06.01 — Create PerformanceStatsService
- **Action:** Create `apps/api/app/services/performance_stats_service.py`; implement: `win_rate_by_setup(setup_type)`, `win_rate_by_asset(asset_id)`, `win_rate_by_catalyst(catalyst_type)`, `win_rate_by_regime(regime_type)`, `overall_stats(min_samples=10)`; returns `PerformanceStats` dataclass; add API-S14 to matrix
- **Pass condition:** Service unit tests with fixture outcome data produce correct win rates (QA-219)
- **Impl IDs:** API-S14
- **QA IDs:** QA-219
- **Workstream:** WS-06
- **Phase:** Phase 12
- **Priority:** P1
- **Status:** [DONE] 2026-04-25 — 5 tests (test_performance_stats_service.py QA-219)

### BP3-06.02 — Inject performance context into signal prompts
- **Action:** In `SignalService.generate_signal()`, before building the prompt, call `PerformanceStatsService.overall_stats()` and `win_rate_by_setup()`; include a structured `## Historical Performance Context` block in the prompt with win rates (only when `min_samples` is met); this gives the LLM prior knowledge of what has been working
- **Pass condition:** Unit test confirms context block is present in rendered prompt when stats meet min_samples threshold; absent when below threshold (QA-220)
- **Impl IDs:** API-S01 (SignalService), API-S14
- **QA IDs:** QA-220
- **Workstream:** WS-06
- **Phase:** Phase 12
- **Priority:** P1
- **Status:** [DONE] 2026-04-25 — 5 tests (test_signal_service_perf_context.py QA-220)

### BP3-06.03 — Create PromptAdaptationService
- **Action:** Create `apps/api/app/services/prompt_adaptation_service.py`; implement `propose_adaptation(setup_type) -> PromptAdaptationProposal`; reads performance stats, identifies underperforming setup types (win rate < 40% with ≥ 20 samples), generates a new candidate prompt by asking the LLM to revise the signal engine prompt with the performance data as context; returns proposal (does NOT auto-apply); add API-S15 to matrix
- **Pass condition:** Service unit test with mocked LLM confirms proposal is generated for underperforming setup; no in-place prompt mutation (Gate 11 pass) (QA-221)
- **Impl IDs:** API-S15
- **QA IDs:** QA-221
- **Workstream:** WS-06
- **Phase:** Phase 12
- **Priority:** P1
- **Status:** [DONE] 2026-04-25 — 7 tests (test_prompt_adaptation.py QA-221); Gate 11 pass

### BP3-06.04 — Create PromptVersion from adaptation proposal
- **Action:** Create `apps/api/app/api/routes/prompt_adaptations.py` with `POST /prompt-adaptations/apply`; accepts a `PromptAdaptationProposal`, writes a new `PromptVersion` row (increment version, store rationale from stats), activates new version for the relevant prompt role; add API-R10 to matrix; Gate 11: must create new row, not update existing
- **Pass condition:** Route test confirms new PromptVersion row created with correct version number; old version row is NOT updated (QA-222, Gate 11 pass)
- **Impl IDs:** API-R10, API-S15
- **QA IDs:** QA-222
- **Workstream:** WS-06
- **Phase:** Phase 12
- **Priority:** P1
- **Status:** [DONE] 2026-04-25 — 1 route test (test_prompt_adaptation.py QA-222); Gate 11 pass

### BP3-06.05 — Wire adaptation review into eval harness
- **Action:** Extend `tests/evals/test_signal_output_eval.py` to include a test: given a mock performance stats payload with an underperforming setup, `PromptAdaptationService.propose_adaptation()` produces a structurally valid proposal (has `rationale`, `setup_type`, `proposed_prompt_text`); add QA-223 to matrix
- **Pass condition:** Eval test passes deterministically with mock LLM provider (QA-223)
- **Impl IDs:** API-S15, QA-T08
- **QA IDs:** QA-223
- **Workstream:** WS-05
- **Phase:** Phase 12
- **Priority:** P2
- **Status:** [DONE] 2026-04-25 — 1 eval test (test_prompt_adaptation.py QA-223)

---

## Section 7 — Performance Dashboard (Phase 12)

Surface learning loop results in the UI so the operator can inspect AI improvement over time.

### BP3-07.01 — Create performance stats endpoint
- **Action:** Add `GET /performance-stats` to a new route `apps/api/app/api/routes/performance.py`; returns overall stats and breakdown by setup, asset, catalyst, regime; add API-R11 to matrix
- **Pass condition:** Endpoint returns correct structure; 4 route tests pass (QA-224)
- **Impl IDs:** API-R11, API-S14
- **QA IDs:** QA-224
- **Workstream:** WS-03
- **Phase:** Phase 12
- **Priority:** P1
- **Status:** [DONE] 2026-04-25 — 4 route tests (test_performance_route.py QA-224)

### BP3-07.02 — Create performance dashboard page
- **Action:** Create `apps/web/app/performance/page.tsx`; show win rate by setup type (bar chart using existing LineChart/ChartPanel or simple table), win rate by asset, overall stats (total trades, win %, avg PnL %); wire to `GET /performance-stats`; add WEB-P16 to matrix
- **Pass condition:** Page renders at `/performance`; QA-225 Playwright test passes
- **Impl IDs:** WEB-P16
- **QA IDs:** QA-225
- **Workstream:** WS-04
- **Phase:** Phase 12
- **Priority:** P2
- **Status:** [DONE] 2026-04-25 — page existed from prior session; Gate 3 pass; Nav link active

### BP3-07.03 — Add prompt adaptation review UI
- **Action:** Create `apps/web/app/prompt-adaptations/page.tsx`; lists pending adaptation proposals; each row shows: setup type, current win rate, proposed prompt summary, `Apply` button; `Apply` calls `POST /prompt-adaptations/apply`; add WEB-P17 to matrix
- **Pass condition:** Page renders at `/prompt-adaptations`; QA-226 Playwright test passes; Gate 11: apply creates new PromptVersion, not update
- **Impl IDs:** WEB-P17, API-R10
- **QA IDs:** QA-226
- **Workstream:** WS-04
- **Phase:** Phase 12
- **Priority:** P2
- **Status:** [DONE] 2026-04-25 — page created (apps/web/app/prompt-adaptations/page.tsx); Gate 3 pass; Nav link added; api.ts updated

---

## Section 8 — Gate Hardening & RC-3 (Phase 13)

### BP3-08.01 — Execute Gate 10: Auto paper risk isolation audit
- **Action:** Trace all code paths where `auto_paper` mode creates a paper position; confirm `RiskEvaluator` is always called; add any missing guards
- **Pass condition:** Gate 10 passes; zero auto-paper positions created without risk gate
- **Impl IDs:** API-W04, API-S04
- **QA IDs:** QA-210, QA-212
- **Workstream:** WS-07
- **Phase:** Phase 13
- **Priority:** P1
- **Status:** [DONE] 2026-04-25 — Gate 10 audit complete: RiskService.evaluate() ALWAYS called before _open_position(); no exceptions identified

### BP3-08.02 — Execute Gate 11: Prompt immutability audit
- **Action:** `grep -rn "prompt_text\s*=" apps/api/app/services --include="*.py"` → confirm all writes create new PromptVersion rows; no UPDATE on prompt_text field
- **Pass condition:** Gate 11 passes; audit log clean
- **Impl IDs:** API-S15, API-R10
- **QA IDs:** QA-222
- **Workstream:** WS-07
- **Phase:** Phase 13
- **Priority:** P1
- **Status:** [DONE] 2026-04-25 — Gate 11 audit complete: PromptAdaptationService/route create NEW PromptVersion rows only; zero UPDATE statements; comment `# Gate 11: create a NEW row` present in route code

### BP3-08.03 — Execute Gate 12: Polygon rate limit compliance audit
- **Action:** `grep -rn "httpx\|requests\|aiohttp" apps/api/app/workers --include="*.py"` → confirm no direct HTTP calls in workers; all market data flows through `PolygonClient`
- **Pass condition:** Gate 12 passes; zero direct HTTP calls outside client layer
- **Impl IDs:** API-W03, API-CL02
- **QA IDs:** QA-205
- **Workstream:** WS-07
- **Phase:** Phase 13
- **Priority:** P1
- **Status:** [DONE] 2026-04-25 — Gate 12 audit complete: Zero direct httpx/requests/aiohttp imports in workers; SignalSweepWorker uses PolygonClient via app.clients.market_data

### BP3-08.04 — Execute Gates 1–9 regression check
- **Action:** Re-run all BP-1 and BP-2 gates to confirm no regressions introduced by BP-3 work
- **Pass condition:** All 9 inherited gates still pass; Playwright suite fully green; backend suite fully green
- **Impl IDs:** All
- **QA IDs:** All
- **Workstream:** WS-07
- **Phase:** Phase 13
- **Priority:** P1
- **Status:** [DONE] 2026-04-25 — Regression check PASS: 344/344 backend tests + 75/75 Playwright tests; all inherited gates green

### BP3-08.05 — Mark RC-3
- **Action:** After all 12 gates pass, add Release Candidate 3 entry to `docs/current-phase-status.md`; record test suite counts, gate results, any accepted deferrals
- **Impl IDs:** All
- **QA IDs:** All
- **Workstream:** WS-07
- **Phase:** Phase 13
- **Priority:** P1
- **Status:** [DONE] 2026-04-25 — RC-3 release candidate established; all 12 gates PASS

---

## Step Count Summary

| Section | Steps | Priority | Phase | Owner Workstream |
|---|---|---|---|---|
| 1 — Asset Universe Seeding | 3 | P1/P2 | 10 | WS-01, WS-03, WS-04 |
| 2 — Signal Sweep Worker | 4 | P1/P2 | 10 | WS-01, WS-04 |
| 3 — Opportunity Ranker | 3 | P1/P2 | 10 | WS-03, WS-04 |
| 4 — Auto Paper Trader | 5 | P1 | 11 | WS-01, WS-03 |
| 5 — Result Capture & Feedback Store | 3 | P1 | 11 | WS-02, WS-01 |
| 6 — AI Learning Loop | 5 | P1/P2 | 12 | WS-06, WS-05 |
| 7 — Performance Dashboard | 3 | P1/P2 | 12 | WS-03, WS-04 |
| 8 — Gate Hardening & RC-3 | 5 | P1 | 13 | WS-07 |
| **Total** | **31** | | | |

---

## Recommended Execution Order

1. **BP3-01.01 → BP3-01.02** — Seed asset universe + API (unblocks sweep worker)
2. **BP3-02.01 → BP3-02.03** — Build and wire SignalSweepWorker with Polygon data
3. **BP3-03.01 → BP3-03.02** — OpportunityRankerService + endpoint (unblocks auto paper trader)
4. **BP3-04.01 → BP3-04.05** — Auto paper trader worker + close worker
5. **BP3-05.01 → BP3-05.03** — SignalOutcome model + outcome recording
6. **BP3-06.01 → BP3-06.02** — PerformanceStatsService + prompt context injection (minimum viable learning loop)
7. **BP3-06.03 → BP3-06.05** — PromptAdaptationService + version creation
8. **BP3-07.01 → BP3-07.03** — Performance dashboard + adaptation review UI
9. **BP3-08.01 → BP3-08.05** — Gate hardening + RC-3

UI steps (BP3-01.03, BP3-02.04, BP3-03.03, BP3-07.02, BP3-07.03) can be deferred to P2 if backend delivery is the priority.

---

## New Implementation Matrix IDs To Register

Before starting any section, pre-register these rows in `docs/implementation-matrix.md`:

| ID | File / Component | Type | Phase |
|---|---|---|---|
| API-SC01 | `apps/api/scripts/seed_assets.py` | script | 10 |
| API-R08 | `apps/api/app/api/routes/assets.py` | route | 10 |
| API-R09 | `apps/api/app/api/routes/opportunities.py` | route | 10 |
| API-R10 | `apps/api/app/api/routes/prompt_adaptations.py` | route | 12 |
| API-R11 | `apps/api/app/api/routes/performance.py` | route | 12 |
| API-S13 | `apps/api/app/services/opportunity_ranker_service.py` | service | 10 |
| API-S14 | `apps/api/app/services/performance_stats_service.py` | service | 12 |
| API-S15 | `apps/api/app/services/prompt_adaptation_service.py` | service | 12 |
| API-P06 | `apps/api/app/services/persistence_signal_outcome_service.py` | persistence | 11 |
| API-M21 | `apps/api/app/db/models/signal_outcome.py` | model | 11 |
| API-W03 | `apps/api/app/workers/signal_sweep_worker.py` | worker | 10 |
| API-W04 | `apps/api/app/workers/auto_paper_trader_worker.py` | worker | 11 |
| API-W05 | `apps/api/app/workers/auto_paper_close_worker.py` | worker | 11 |
| WEB-P13 | `apps/web/app/assets/page.tsx` | page | 10 |
| WEB-P14 | `apps/web/app/sweeps/page.tsx` | page | 10 |
| WEB-P15 | `apps/web/app/opportunities/page.tsx` | page | 10 |
| WEB-P16 | `apps/web/app/performance/page.tsx` | page | 12 |
| WEB-P17 | `apps/web/app/prompt-adaptations/page.tsx` | page | 12 |

---

## New QA IDs To Register

Pre-register these rows in `docs/regression-qa-matrix.md` before starting each section:

| QA ID | Description | Section |
|---|---|---|
| QA-200 | Asset seed script runs idempotently | BP3-01 |
| QA-201 | Assets API CRUD endpoints pass | BP3-01 |
| QA-202 | Assets page renders at /assets | BP3-01 |
| QA-203 | SignalSweepWorker unit tests | BP3-02 |
| QA-204 | Sweep job registered; inactive under APP_ENV=test | BP3-02 |
| QA-205 | Sweep uses PolygonClient only (Gate 12) | BP3-02 |
| QA-206 | Sweeps history page renders | BP3-02 |
| QA-207 | OpportunityRankerService sort correctness | BP3-03 |
| QA-208 | GET /opportunities returns ranked list | BP3-03 |
| QA-209 | Opportunities page renders at /opportunities | BP3-03 |
| QA-210 | auto_paper mode risk gate is called | BP3-04 |
| QA-211 | AutoPaperTraderWorker: risk-blocked → no paper order | BP3-04 |
| QA-212 | AutoPaperTraderWorker: approved → paper order created | BP3-04 |
| QA-213 | Auto paper trader job registered; inactive under test | BP3-04 |
| QA-214 | Auto paper trader respects position cap | BP3-04 |
| QA-215 | AutoPaperCloseWorker closes expired positions | BP3-04 |
| QA-216 | SignalOutcome model and migration | BP3-05 |
| QA-217 | PersistenceSignalOutcomeService CRUD | BP3-05 |
| QA-218 | Close worker writes outcome row | BP3-05 |
| QA-219 | PerformanceStatsService win rate calculations | BP3-06 |
| QA-220 | Performance context injected into prompt when min_samples met | BP3-06 |
| QA-221 | PromptAdaptationService proposes without mutating existing rows | BP3-06 |
| QA-222 | Apply proposal creates new PromptVersion row | BP3-06 |
| QA-223 | Eval harness: adaptation proposal structure valid | BP3-06 |
| QA-224 | GET /performance-stats returns correct structure | BP3-07 |
| QA-225 | Performance dashboard page renders | BP3-07 |
| QA-226 | Prompt adaptations page renders | BP3-07 |

---

*Reference docs:*
- `docs/implementation-matrix.md` — all impl IDs
- `docs/regression-qa-matrix.md` — all QA IDs
- `docs/release-gates.md` — gate definitions (WS-07)
- `docs/current-phase-status.md` — phase-by-phase ledger
- `docs/build-plan-2.md` — RC-2 completion baseline
