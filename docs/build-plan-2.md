# Build Plan 2 — Road to Guarded Live Trading

Date: 2026-04-24
Last updated by: autonomous RC-2 gate execution

## Purpose

Build Plan 1 achieved paper-trading MVP with all six release gates passing.
Build Plan 2 completes the full architecture goal:

> **simulation → paper trading → guarded live trading**

Every capability gap between the current RC state and a production-ready guarded live trading system
is covered in this plan. Steps are sequenced so each section unlocks the next.

Architecture target from `docs/architecture.md`:
- Polygon: primary market data provider
- IBKR: long-term live execution broker
- Real positions and PnL tracked in DB
- Background workers running on schedule
- Prompt and model versions stored and auditable
- Eval harness results persisted

## How To Use This Plan

Same rules as Build Plan 1:

1. Work top to bottom within each section.
2. Before starting a step, mark it `[IN-PROGRESS]` in this file.
3. When done, mark it `[DONE]` and update the referenced matrix rows.
4. If a step produces a new file or service, add it to `docs/implementation-matrix.md` first.
5. If a step produces a new test, add its QA ID to `docs/regression-qa-matrix.md` first.
6. Never mark a step DONE without updating the linked matrix rows.

## Anti-Drift Rules (inherited + extended)

- Gate 1–6 from `docs/release-gates.md` remain in force.
- No broker calls outside the broker adapter layer. (Gate 7 — new)
- No raw market data calls outside the market data client layer. (Gate 8 — new)
- Every new worker must extend BaseWorker. (Gate 9 — new)
- Every new scheduled job must register via BaseScheduler. (Gate 9 — new)

---

## Section 1 — Close Pending Manual QA (Immediate)

These three items have been `pending` since BP1. Convert to automated Playwright tests to eliminate
the manual audit debt permanently.

### BP2-01.01 — Automate QA-013: LLM toggle renders warning state
- **Action:** In `apps/web/tests/regression.spec.ts`, add a test that navigates to `/signals`, clicks the "Live LLM mode" toggle, and asserts a warning indicator (⚠ or `data-testid="llm-warning"`) is visible; then clicks again and confirms it disappears
- **Pass condition:** Test green; QA-013 status updated from `pending` to `passing`
- **Impl IDs:** WEB-P05, API-R02
- **QA IDs:** QA-013
- **Workstream:** WS-05
- **Phase:** Phase 9
- **Priority:** P1
- **Status:** [DONE]

### BP2-01.02 — Automate QA-033: Chart axis contrast in both themes
- **Action:** In `regression.spec.ts`, navigate to `/analytics` in dark mode and assert SVG axis text elements exist and are not `display:none`; repeat with light mode; confirm no CSS token override hides them
- **Pass condition:** Test green; QA-033 `passing`
- **Impl IDs:** WEB-C02, WEB-F02
- **QA IDs:** QA-033
- **Workstream:** WS-05
- **Phase:** Phase 9
- **Priority:** P1
- **Status:** [DONE]

### BP2-01.03 — Automate QA-034: Series toggles and time range controls
- **Action:** In `regression.spec.ts`, navigate to `/analytics`, assert `SeriesToggle` buttons exist and are clickable (no `disabled` attribute), assert `TimeRangeBar` buttons exist; verify clicking a range button changes `aria-pressed` or active class
- **Pass condition:** Test green; QA-034 `passing`
- **Impl IDs:** WEB-C04, WEB-C05
- **QA IDs:** QA-034
- **Workstream:** WS-05
- **Phase:** Phase 9
- **Priority:** P1
- **Status:** [DONE]

---

## Section 2 — Documentation Hardening

Rows still marked `partial` in the implementation matrix. Required before Gate 1 of RC-2 can pass.

### BP2-02.01 — Harden route documentation API-R01 through API-R06
- **Action:** For each of API-R01 (health), API-R02 (signals), API-R03 (risk), API-R04 (workflow), API-R05 (approvals), API-R06 (execution): read the file, write a one-line contract summary in the matrix notes field, set documentation to `documented`
- **Impl IDs:** API-R01, API-R02, API-R03, API-R04, API-R05, API-R06
- **QA IDs:** QA-050
- **Workstream:** WS-01
- **Phase:** Phase 9
- **Priority:** P2
- **Status:** [DONE]

### BP2-02.02 — Harden model documentation API-M01 through API-M12
- **Action:** For each active model row (Asset through AuditLog), add entity-level contract note (key columns, relationships, migration state) and set documentation to `documented`
- **Impl IDs:** API-M01 through API-M12
- **QA IDs:** (process — no new test required)
- **Workstream:** WS-01
- **Phase:** Phase 2
- **Priority:** P2
- **Status:** [DONE]

### BP2-02.03 — Harden frontend page documentation WEB-P04, WEB-P05, WEB-P06
- **Action:** Update matrix rows for `/workflow`, `/signals`, `/risk` from `partial` to `documented`; add current state notes covering mock vs real LLM toggle status, known gaps
- **Impl IDs:** WEB-P04, WEB-P05, WEB-P06
- **QA IDs:** (process)
- **Workstream:** WS-01
- **Phase:** Phase 8
- **Priority:** P2
- **Status:** [DONE]

### BP2-02.04 — Harden shared foundation documentation WEB-F01, WEB-F02, WEB-F03
- **Action:** Update matrix rows for layout, globals.css, Nav to `documented`; capture current token count and responsive breakpoint coverage
- **Impl IDs:** WEB-F01, WEB-F02, WEB-F03
- **QA IDs:** (process)
- **Workstream:** WS-04
- **Phase:** Phase 8
- **Priority:** P2
- **Status:** [DONE]

---

## Section 3 — Signal Persistence Completion

API-P01 (`persistence_signal_service.py`) has been `partial/unverified` since initial inventory. The
service exists and has a `persist_signal` method but is not wired to the signal route and has no tests.

### BP2-03.01 — Audit persistence_signal_service.py
- **Action:** Read `apps/api/app/services/persistence_signal_service.py` fully; confirm `persist_signal` and `persist_risk_decision` method contracts; document in matrix notes; update API-P01 status from `partial` to `implemented`
- **Impl IDs:** API-P01
- **QA IDs:** QA-050
- **Workstream:** WS-01
- **Phase:** Phase 5
- **Priority:** P1
- **Status:** [DONE]

### BP2-03.02 — Wire signal persistence into POST /signals/generate
- **Action:** In `apps/api/app/api/routes/signals.py`, after `SignalService.generate_signal()` returns, call `PersistenceSignalService.persist_signal()` with a DB session injected via `Depends(get_db)`; also persist risk decision if present in result; handle DB errors gracefully (log + continue, do not fail the signal response)
- **Impl IDs:** API-R02, API-P01, API-S01
- **QA IDs:** (new QA-100)
- **Workstream:** WS-01
- **Phase:** Phase 5
- **Priority:** P1
- **Status:** [DONE]

### BP2-03.03 — Add backend tests for signal persistence
- **Action:** Add `tests/services/test_persistence_signal_service.py`; cover: `persist_signal` stores signal row with correct asset FK, `persist_risk_decision` stores risk row linked to signal, duplicate signal ID raises or skips gracefully
- **Pass condition:** New test file passes; QA-100 added to regression matrix
- **Impl IDs:** API-P01
- **QA IDs:** QA-100
- **Workstream:** WS-05
- **Phase:** Phase 5
- **Priority:** P1
- **Status:** [DONE]

---

## Section 4 — Position and PnL Tracking

API-M13 (Position) and API-M14 (PnlSnapshot) are scaffold models with no service, no route, no
frontend. This section wires them into the execution layer so paper trading produces real position
state.

### BP2-04.01 — Create position_service.py
- **Action:** Create `apps/api/app/services/position_service.py`; contract: `open_position(session, paper_order_id, asset_id, direction, size, entry_price) -> Position`; `close_position(session, position_id, exit_price) -> Position`; `get_open_positions(session) -> list[Position]`; all methods are session-scoped; no business logic beyond DB operations; add API-S14 row to implementation matrix
- **Impl IDs:** API-S14 (new), API-M13
- **QA IDs:** (new QA-101)
- **Workstream:** WS-01
- **Phase:** Phase 6
- **Priority:** P1
- **Status:** [DONE]

### BP2-04.02 — Create pnl_service.py
- **Action:** Create `apps/api/app/services/pnl_service.py`; contract: `snapshot_pnl(session, position_id, mark_price) -> PnlSnapshot`; `get_pnl_history(session, position_id) -> list[PnlSnapshot]`; add API-S15 row to implementation matrix
- **Impl IDs:** API-S15 (new), API-M14
- **QA IDs:** (new QA-102)
- **Workstream:** WS-01
- **Phase:** Phase 6
- **Priority:** P1
- **Status:** [DONE]

### BP2-04.03 — Add positions and PnL endpoints to execution route
- **Action:** In `apps/api/app/api/routes/execution.py`, add: `GET /execution/positions` (returns open positions list), `GET /execution/positions/{id}/pnl` (returns PnL history for a position), `POST /execution/positions/{id}/snapshot` (force a PnL snapshot at current mark price); wire to position_service and pnl_service via Depends; no business logic in route
- **Impl IDs:** API-R06, API-S14, API-S15
- **QA IDs:** QA-101, QA-102
- **Workstream:** WS-01
- **Phase:** Phase 6
- **Priority:** P1
- **Status:** [DONE]

### BP2-04.04 — Auto-open position when paper order fills
- **Action:** In `paper_execution_service.py`, after `simulate_fill()` completes, call `PositionService.open_position()` with the filled order data; this wires the fill → position lifecycle; update API-S05 notes in matrix
- **Impl IDs:** API-S05, API-S14
- **QA IDs:** QA-101
- **Workstream:** WS-01
- **Phase:** Phase 6
- **Priority:** P1
- **Status:** [DONE]

### BP2-04.05 — Add backend tests for position and PnL services
- **Action:** Create `tests/services/test_position_pnl_service.py`; cover: open_position creates DB row, close_position updates status and exit_price, snapshot_pnl creates snapshot row, get_pnl_history returns ordered snapshots; use in-memory SQLite test session pattern consistent with existing service tests
- **Pass condition:** All tests pass; QA-101 and QA-102 added to regression matrix
- **Impl IDs:** API-S14, API-S15
- **QA IDs:** QA-101, QA-102
- **Workstream:** WS-05
- **Phase:** Phase 6
- **Priority:** P1
- **Status:** [DONE]

### BP2-04.06 — Frontend: positions panel on /execution page
- **Action:** In `apps/web/app/execution/page.tsx`, add a "Open Positions" section below the paper orders table; fetch from `GET /execution/positions`; display asset, direction, size, entry price, unrealized PnL (from latest snapshot); add QA-103 to regression matrix and a Playwright test in `regression.spec.ts`
- **Impl IDs:** WEB-P08, API-S14
- **QA IDs:** QA-103
- **Workstream:** WS-06
- **Phase:** Phase 6
- **Priority:** P2
- **Status:** [DONE]

---

## Section 5 — Feature Snapshot Persistence

API-M15 (FeatureSnapshot) is a scaffold model. Persisting feature snapshots alongside signals
creates a complete audit trail: what features the model saw when it generated a signal.

### BP2-05.01 — Wire FeatureSnapshot into signal generation flow
- **Action:** After `SignalService.generate_signal()` builds its `FeatureInput`, call a new `persist_feature_snapshot(session, signal_id, feature_input)` method; create this method on `PersistenceSignalService` (keeping API-P01 as the owner); it writes an `API-M15` row; update API-P01 notes
- **Impl IDs:** API-P01, API-M15, API-S01
- **QA IDs:** (new QA-104)
- **Workstream:** WS-01
- **Phase:** Phase 3
- **Priority:** P2
- **Status:** [DONE]

### BP2-05.02 — Add feature snapshot endpoint
- **Action:** In `apps/api/app/api/routes/signals.py`, add `GET /signals/{signal_id}/features` returning the FeatureSnapshot row for that signal; 404 if not found; add to API-R02 notes
- **Impl IDs:** API-R02, API-M15
- **QA IDs:** QA-104
- **Workstream:** WS-01
- **Phase:** Phase 3
- **Priority:** P2
- **Status:** [DONE]

### BP2-05.03 — Add backend tests for feature snapshot persistence
- **Action:** Add feature snapshot coverage to `test_persistence_signal_service.py`; confirm snapshot is created with correct signal FK and non-empty feature fields
- **Pass condition:** Tests pass; QA-104 added to regression matrix
- **Impl IDs:** API-P01, API-M15
- **QA IDs:** QA-104
- **Workstream:** WS-05
- **Phase:** Phase 3
- **Priority:** P2
- **Status:** [DONE]

---

## Section 6 — Phase 7 Runtime: Scheduler Engine

The BaseWorker/BaseScheduler scaffolds from BP-10.01/10.02 have no runtime engine. This section
adds APScheduler as the lightweight job runner and wires it into the app lifespan.

### BP2-06.01 — Add APScheduler to requirements
- **Action:** Add `apscheduler>=3.10` to `apps/api/requirements.txt`; confirm install with `.venv/bin/pip install apscheduler`; confirm no dependency conflicts with Python 3.14; add fallback note if version incompatibility found
- **Pass condition:** `import apscheduler` succeeds inside `.venv`
- **Impl IDs:** API-W01, API-W02
- **QA IDs:** (infrastructure)
- **Workstream:** WS-01
- **Phase:** Phase 7
- **Priority:** P1
- **Status:** [DONE]

### BP2-06.02 — Implement concrete DataSyncWorker
- **Action:** Create `apps/api/app/workers/data_sync_worker.py`; extends `BaseWorker`; `run()` method is a no-op placeholder that returns `WorkerResult(status="ok", message="data_sync: no-op placeholder")`; will be filled by Section 7; add API-W03 row to implementation matrix
- **Impl IDs:** API-W03 (new), API-W01
- **QA IDs:** (new QA-105)
- **Workstream:** WS-01
- **Phase:** Phase 7
- **Priority:** P1
- **Status:** [DONE]

### BP2-06.03 — Implement DataSyncScheduler
- **Action:** Create `apps/api/app/schedules/data_sync_scheduler.py`; extends `BaseScheduler`; registers one job: `cron_expr="*/5 * * * *"` (every 5 minutes), handler=DataSyncWorker().run, enabled=True; add API-W04 row to implementation matrix
- **Impl IDs:** API-W04 (new), API-W02
- **QA IDs:** QA-105
- **Workstream:** WS-01
- **Phase:** Phase 7
- **Priority:** P1
- **Status:** [DONE]

### BP2-06.04 — Wire APScheduler to app startup lifespan
- **Action:** In `apps/api/app/main.py`, add a `@asynccontextmanager` lifespan that starts an `AsyncIOScheduler` on startup, registers all jobs from `DataSyncScheduler.list_jobs()`, and shuts down on app teardown; scheduler only starts when `APP_ENV != "test"` to avoid interfering with pytest
- **Impl IDs:** API-W01, API-W02, API-W03, API-W04
- **QA IDs:** QA-105
- **Workstream:** WS-01
- **Phase:** Phase 7
- **Priority:** P1
- **Status:** [DONE]

### BP2-06.05 — Add runtime worker and scheduler tests
- **Action:** In `tests/infrastructure/test_worker_scheduler_scaffold.py`, add: (1) `DataSyncWorker().run()` returns `WorkerResult(status="ok")`; (2) `DataSyncScheduler().list_jobs()` returns one job named `data_sync`; (3) confirm APP_ENV=test guard prevents scheduler from registering in pytest context
- **Pass condition:** All new tests pass alongside existing 2 infrastructure tests
- **Impl IDs:** API-W03, API-W04
- **QA IDs:** QA-105
- **Workstream:** WS-05
- **Phase:** Phase 7
- **Priority:** P1
- **Status:** [DONE]

---

## Section 7 — Market Data Ingestion (Polygon)

Without real market data, signals use mocked feature inputs. This section adds the Polygon client
and a bar/quote ingestion service. The `Bar` and `Quote` ORM models already exist (API-M02, API-M03).

### BP2-07.01 — Create Polygon market data client
- **Action:** Create `apps/api/app/clients/market_data/polygon_client.py`; define a `MarketDataClient` protocol with methods: `get_bars(ticker, from_date, to_date, timeframe) -> list[BarData]`; create `PolygonClient` implementing the protocol using `httpx` (async); read API key from `settings.POLYGON_API_KEY`; add API-C01 row to implementation matrix
- **Pass condition:** Client instantiates without error; protocol enforced; `POLYGON_API_KEY` is read from env, never hardcoded
- **Impl IDs:** API-C01 (new)
- **QA IDs:** (new QA-106)
- **Workstream:** WS-02
- **Phase:** Phase 10 (new)
- **Priority:** P1
- **Status:** [DONE]

### BP2-07.02 — Create market_data_service.py
- **Action:** Create `apps/api/app/services/market_data_service.py`; contract: `ingest_bars(session, ticker, from_date, to_date) -> int` (returns count of bars written); upserts into `Bar` ORM model on (asset_id, timeframe, timestamp) unique key to avoid duplicates; `ingest_quotes(session, ticker) -> int`; add API-S13 row to implementation matrix
- **Impl IDs:** API-S13 (new), API-M02, API-M03
- **QA IDs:** QA-106
- **Workstream:** WS-02
- **Phase:** Phase 10
- **Priority:** P1
- **Status:** [DONE]

### BP2-07.03 — Fill DataSyncWorker with real bar ingestion
- **Action:** Update `data_sync_worker.py` run() to: load all active assets from DB, call `MarketDataService.ingest_bars()` for each with a 24h lookback window, return `WorkerResult` with count of rows upserted; inject `PolygonClient` and DB session via constructor; guard with `try/except` — log error, return `WorkerResult(status="error", message=str(e))`
- **Impl IDs:** API-W03, API-S13, API-C01
- **QA IDs:** QA-106
- **Workstream:** WS-02
- **Phase:** Phase 10
- **Priority:** P1
- **Status:** [DONE]

### BP2-07.04 — Add backend tests for Polygon client and market data service (mocked)
- **Action:** Create `tests/clients/test_polygon_client.py`; mock `httpx.AsyncClient.get` to return sample Polygon JSON; assert `PolygonClient.get_bars()` maps to `BarData` objects correctly; assert 401 raises `PolygonAuthError`; create `tests/services/test_market_data_service.py`; assert `ingest_bars()` creates Bar rows; assert re-run with same data does not duplicate
- **Pass condition:** All tests pass; QA-106 added to regression matrix
- **Impl IDs:** API-C01, API-S13
- **QA IDs:** QA-106
- **Workstream:** WS-05
- **Phase:** Phase 10
- **Priority:** P1
- **Status:** [DONE]

### BP2-07.05 — Add POLYGON_API_KEY to config and env example
- **Action:** Add `POLYGON_API_KEY: str = ""` to `apps/api/app/config.py` Settings class; add `POLYGON_API_KEY=your_key_here` to `.env.example` (do not commit a real key); document that an empty key disables Polygon client and DataSyncWorker silently logs a warning and exits early
- **Impl IDs:** API-C01
- **QA IDs:** (process)
- **Workstream:** WS-01
- **Phase:** Phase 10
- **Priority:** P1
- **Status:** [DONE]

### BP2-07.06 — Add market data route for status and manual trigger
- **Action:** Create `apps/api/app/api/routes/market_data.py`; endpoints: `GET /market-data/status` (returns last ingest timestamp per asset/timeframe), `POST /market-data/sync` (triggers DataSyncWorker.run() manually, returns WorkerResult); register router in main.py; add API-R08 row to implementation matrix; add QA-107 to regression matrix
- **Impl IDs:** API-R08 (new), API-S13, API-W03
- **QA IDs:** QA-107
- **Workstream:** WS-01
- **Phase:** Phase 10
- **Priority:** P2
- **Status:** [DONE]

### BP2-07.07 — Frontend: data freshness indicator on /analytics and /signals
- **Action:** In `apps/web/app/analytics/page.tsx` and `apps/web/app/signals/page.tsx`, add a small "Data last updated: {timestamp}" badge that calls `GET /market-data/status`; show "No data" state gracefully if endpoint returns empty; add QA-108 to regression matrix
- **Impl IDs:** WEB-P03, WEB-P05, API-R08
- **QA IDs:** QA-108
- **Workstream:** WS-06
- **Phase:** Phase 10
- **Priority:** P2
- **Status:** [DONE]

---

## Section 8 — Prompt and Model Versioning (ORM wire-up)

Prompt governance rules (`docs/prompt-governance.md`) require: every prompt versioned, seeded into DB,
linked to a schema. API-M16 through API-M19 exist as scaffolds. This section wires them.

### BP2-08.01 — Wire PromptVersion ORM on app startup
- **Action:** In `apps/api/app/main.py` lifespan, after scheduler start, call a `seed_prompt_versions(session)` function that reads all prompt files from `app/prompts/system/` and `app/prompts/user/` and upserts a `PromptVersion` row for each (using file hash as idempotency key); add API-S16 row for `prompt_version_service.py` (new) to implementation matrix
- **Impl IDs:** API-S16 (new), API-M16
- **QA IDs:** (new QA-109)
- **Workstream:** WS-06
- **Phase:** Phase 9
- **Priority:** P2
- **Status:** [DONE]

### BP2-08.02 — Record ModelVersion on each signal generation
- **Action:** In `SignalService.generate_signal()`, after calling the LLM provider, write a `ModelVersion` row with: model name, provider, prompt version FK, called_at timestamp; inject DB session; add `model_version_id` FK to `Signal` ORM model if not already present; add notes to API-M17
- **Impl IDs:** API-S01, API-M17
- **QA IDs:** QA-109
- **Workstream:** WS-06
- **Phase:** Phase 9
- **Priority:** P2
- **Status:** [DONE]

### BP2-08.03 — Persist EvalCase and EvalRun from eval harness
- **Action:** Add a `write_eval_results(session, eval_run: EvalRun, cases: list[EvalCase])` method; call it from a new `tests/evals/conftest.py` fixture that optionally writes results when `PERSIST_EVALS=1` env var is set (off by default in CI); this keeps tests fast while enabling production eval logging
- **Impl IDs:** API-M18, API-M19, QA-T08
- **QA IDs:** QA-109
- **Workstream:** WS-05
- **Phase:** Phase 9
- **Priority:** P2
- **Status:** [DONE]

### BP2-08.04 — Extend /prompts route with version history
- **Action:** In `apps/api/app/api/routes/prompts.py`, add `GET /prompts/{subdir}/{filename}/history` returning a list of `PromptVersion` rows for that file (sorted by created_at desc); return 404 if no versions found; update API-R07 notes in matrix
- **Impl IDs:** API-R07, API-M16
- **QA IDs:** (new QA-110)
- **Workstream:** WS-06
- **Phase:** Phase 9
- **Priority:** P2
- **Status:** [DONE]

### BP2-08.05 — Frontend: prompt version history on /prompts page
- **Action:** In `apps/web/app/prompts/page.tsx`, below the content view, add a "Version History" table showing version rows fetched from `GET /prompts/{subdir}/{filename}/history`; show created_at, file hash, and model_version count; add QA-110 to regression matrix
- **Impl IDs:** WEB-P11, API-R07
- **QA IDs:** QA-110
- **Workstream:** WS-06
- **Phase:** Phase 9
- **Priority:** P2
- **Status:** [DONE]

### BP2-08.06 — Create /evals frontend page
- **Action:** Create `apps/web/app/evals/page.tsx`; fetch `GET /evals/runs` (new endpoint, see next step); display table of eval runs with: run_id, ran_at, pass rate, model_version; click to expand individual case results; add WEB-P12 row to implementation matrix; add QA-111
- **Impl IDs:** WEB-P12 (new)
- **QA IDs:** QA-111
- **Workstream:** WS-06
- **Phase:** Phase 9
- **Priority:** P3
- **Status:** [DONE]

### BP2-08.07 — Create /evals backend route
- **Action:** Create `apps/api/app/api/routes/evals.py`; endpoints: `GET /evals/runs` (list EvalRun rows desc), `GET /evals/runs/{id}` (EvalRun + EvalCase list); register in main.py; add API-R09 row to implementation matrix
- **Impl IDs:** API-R09 (new), API-M18, API-M19
- **QA IDs:** QA-111
- **Workstream:** WS-06
- **Phase:** Phase 9
- **Priority:** P3
- **Status:** [DONE]

---

## Section 9 — News Data Ingestion

API-M20 (NewsArticle) is a scaffold model. News data is listed as a data ingestion source in the
architecture. Wire it through the same pattern as bars/quotes.

### BP2-09.01 — Create news_client.py (Polygon news endpoint)
- **Action:** Create `apps/api/app/clients/market_data/news_client.py`; `NewsClient` protocol + `PolygonNewsClient` implementation; `get_news(ticker, limit) -> list[NewsItem]`; uses same `POLYGON_API_KEY`; add API-C02 row to implementation matrix
- **Impl IDs:** API-C02 (new), API-M20
- **QA IDs:** (new QA-112)
- **Workstream:** WS-02
- **Phase:** Phase 10
- **Priority:** P3
- **Status:** [DONE]

### BP2-09.02 — Create news_ingest_worker.py
- **Action:** Create `apps/api/app/workers/news_ingest_worker.py`; extends BaseWorker; calls `PolygonNewsClient.get_news()` for each active asset; upserts `NewsArticle` rows on article_id; returns WorkerResult; add API-W05 row to implementation matrix
- **Impl IDs:** API-W05 (new), API-C02, API-M20
- **QA IDs:** QA-112
- **Workstream:** WS-02
- **Phase:** Phase 10
- **Priority:** P3
- **Status:** [DONE]

### BP2-09.03 — Register news job in DataSyncScheduler
- **Action:** Add a second job to `DataSyncScheduler`: name=`news_ingest`, cron=`0 * * * *` (hourly), handler=NewsIngestWorker().run, enabled=True; update API-W04 notes
- **Impl IDs:** API-W04, API-W05
- **QA IDs:** QA-112
- **Workstream:** WS-02
- **Phase:** Phase 10
- **Priority:** P3
- **Status:** [DONE]

### BP2-09.04 — Add news tests (mocked)
- **Action:** Create `tests/clients/test_news_client.py`; mock Polygon news JSON; assert client maps to `NewsItem` objects; create `tests/workers/test_news_ingest_worker.py`; mock client; assert worker returns `WorkerResult(status="ok")` and upserts rows
- **Pass condition:** Tests pass; QA-112 `passing`
- **Impl IDs:** API-C02, API-W05
- **QA IDs:** QA-112
- **Workstream:** WS-05
- **Phase:** Phase 10
- **Priority:** P3
- **Status:** [DONE]

### BP2-09.05 — Frontend: news feed panel on /signals page
- **Action:** In `apps/web/app/signals/page.tsx`, add a "Recent News" section below the signal builder; fetch `GET /market-data/news/{ticker}` (add to market_data route); display headline, source, published_at; limit to 5 items; graceful empty state; add QA-113
- **Impl IDs:** WEB-P05, API-R08, API-M20
- **QA IDs:** QA-113
- **Workstream:** WS-06
- **Phase:** Phase 10
- **Priority:** P3
- **Status:** [DONE]

---

## Section 10 — Broker Interface: IBKR Scaffold

Architecture names IBKR as the long-term live execution broker. This section creates the interface
and scaffold adapter so the live execution layer has a real wiring target when the guard is lifted.
Live trading remains disabled throughout this section. Guard is not lifted in this plan.

### BP2-10.01 — Create broker interface protocol
- **Action:** Create `apps/api/app/clients/broker/broker_interface.py`; define `BrokerInterface` Protocol with methods: `place_order(order: BrokerOrder) -> BrokerOrderResult`, `cancel_order(broker_order_id: str) -> bool`, `get_position(ticker: str) -> BrokerPosition | None`, `get_account_summary() -> BrokerAccountSummary`; all methods raise `NotImplementedError` in the base; add API-C03 row to implementation matrix; Gate 7 check: any broker call outside this interface is a gate failure
- **Impl IDs:** API-C03 (new)
- **QA IDs:** (new QA-114)
- **Workstream:** WS-02
- **Phase:** Phase 11 (new — Guarded Live Trading)
- **Priority:** P3
- **Status:** [DONE]

### BP2-10.02 — Create IBKRAdapter scaffold
- **Action:** Create `apps/api/app/clients/broker/ibkr_adapter.py`; implements `BrokerInterface`; all methods log `"IBKR adapter: not implemented"` and raise `NotImplementedError`; class docstring clearly states this is a scaffold awaiting IBKR TWS API integration; add API-C04 row to implementation matrix
- **Impl IDs:** API-C04 (new), API-C03
- **QA IDs:** QA-114
- **Workstream:** WS-02
- **Phase:** Phase 11
- **Priority:** P3
- **Status:** [DONE]

### BP2-10.03 — Inject broker interface into LiveExecutionService
- **Action:** Update `apps/api/app/services/live_execution_service.py` to accept an optional `broker: BrokerInterface | None = None` constructor argument; if broker is None or `LIVE_TRADING_ENABLED` env is falsy, return the existing `live_execution_disabled_in_mvp` sentinel as before; if both are present, delegate to `broker.place_order()` (will still raise NotImplementedError until IBKR is implemented, but the wiring is in place); Gate 4 guard remains active; update API-S06 notes
- **Impl IDs:** API-S06, API-C03
- **QA IDs:** QA-009, QA-052, QA-114
- **Workstream:** WS-02
- **Phase:** Phase 11
- **Priority:** P3
- **Status:** [DONE]

### BP2-10.04 — Add broker interface tests
- **Action:** Create `tests/clients/test_broker_interface.py`; assert IBKRAdapter is a valid BrokerInterface implementor (Protocol check); assert each method raises NotImplementedError; assert LiveExecutionService with broker=None still returns disabled sentinel; Gate 4 remains green
- **Pass condition:** Tests pass; QA-114 `passing`; Gate 4 still passes
- **Impl IDs:** API-C03, API-C04, API-S06
- **QA IDs:** QA-114, QA-009, QA-052
- **Workstream:** WS-05
- **Phase:** Phase 11
- **Priority:** P3
- **Status:** [DONE]

---

## Section 11 — New Release Gates (BP2 additions)

Two new gates are introduced for Build Plan 2 to enforce the new architecture layers.

### BP2-11.01 — Define Gate 7: No broker calls outside broker adapter
- **Action:** Add Gate 7 to `docs/release-gates.md`: check method = grep for `ibkr`, `tws`, `ib_insync`, `place_order`, `cancel_order` in all service and route files excluding `clients/broker/`; pass condition = zero matches outside the adapter layer; fail condition = any direct broker call in services or routes
- **Impl IDs:** API-C03, API-C04
- **QA IDs:** (gate definition)
- **Workstream:** WS-07
- **Phase:** Phase 11
- **Priority:** P3
- **Status:** [DONE]

### BP2-11.02 — Define Gate 8: No raw market data calls outside market data client
- **Action:** Add Gate 8 to `docs/release-gates.md`: check method = grep for `polygon.io`, `requests.get`, `httpx.get` in all service and route files excluding `clients/market_data/`; pass condition = zero matches outside the client layer
- **Impl IDs:** API-C01, API-C02
- **QA IDs:** (gate definition)
- **Workstream:** WS-07
- **Phase:** Phase 10
- **Priority:** P2
- **Status:** [DONE]

### BP2-11.03 — Define Gate 9: Worker and scheduler compliance
- **Action:** Add Gate 9 to `docs/release-gates.md`: check method = confirm every file in `app/workers/` that is not `__init__.py` or `base_worker.py` imports and subclasses `BaseWorker`; confirm every file in `app/schedules/` subclasses `BaseScheduler`; AST check or grep is acceptable; pass condition = zero non-conforming workers
- **Impl IDs:** API-W01, API-W02
- **QA IDs:** (gate definition)
- **Workstream:** WS-07
- **Phase:** Phase 7
- **Priority:** P2
- **Status:** [DONE]

---

## Section 12 — Release Gate Formal Execution (RC-2)

Run after all P1 and P2 items in Sections 1–11 are DONE.

### BP2-12.01 — Execute Gate 1: Implementation matrix completeness
- **Action:** Confirm all new rows (API-S13 through API-S16, API-C01 through API-C04, API-W03 through API-W05, API-R08, API-R09, WEB-P12) are present and non-blank; no new files without rows
- **Workstream:** WS-07
- **Priority:** P1
- **Status:** [DONE]

### BP2-12.02 — Execute Gate 2: QA coverage minimum
- **Action:** Confirm QA-100 through QA-114 are all created and linked to impl IDs; no `failing` rows; run full pytest and Playwright suites
- **Workstream:** WS-07
- **Priority:** P1
- **Status:** [DONE]

### BP2-12.03 — Execute Gate 3: Raw hex token audit
- **Action:** Re-run hex grep scan; confirm zero matches; all new TSX must use CSS tokens
- **Workstream:** WS-07
- **Priority:** P1
- **Status:** [DONE]

### BP2-12.04 — Execute Gate 4: Live execution guard
- **Action:** Confirm `live_execution_service.py` still returns disabled sentinel when `LIVE_TRADING_ENABLED` is not set; QA-009 and QA-052 still passing; IBKR adapter wired but broker=None path active
- **Workstream:** WS-07
- **Priority:** P1
- **Status:** [DONE]

### BP2-12.05 — Execute Gate 5: Architecture compliance
- **Action:** Re-run AST scan for imports inside function bodies; confirm all new services are clean; confirm new routes delegate to service layer
- **Workstream:** WS-07
- **Priority:** P1
- **Status:** [DONE]

### BP2-12.06 — Execute Gate 6: Theme token completeness
- **Action:** Diff dark and light token blocks after any new TSX additions; confirm no new asymmetric tokens
- **Workstream:** WS-07
- **Priority:** P1
- **Status:** [DONE]

### BP2-12.07 — Execute Gate 7: Broker call isolation
- **Action:** Run Gate 7 grep check; zero broker calls outside clients/broker/
- **Workstream:** WS-07
- **Priority:** P1
- **Status:** [DONE]

### BP2-12.08 — Execute Gate 8: Market data call isolation
- **Action:** Run Gate 8 grep check; zero direct HTTP calls to market data APIs outside clients/market_data/
- **Workstream:** WS-07
- **Priority:** P1
- **Status:** [DONE]

### BP2-12.09 — Execute Gate 9: Worker and scheduler compliance
- **Action:** Confirm all workers subclass BaseWorker; all schedulers subclass BaseScheduler
- **Workstream:** WS-07
- **Priority:** P1
- **Status:** [DONE]

### BP2-12.10 — Mark Release Candidate 2
- **Action:** After all nine gates pass, add RC-2 entry to `docs/current-phase-status.md` with: date, gate results, test suite counts, accepted deferrals; increment "Last updated by" header in this file
- **Workstream:** WS-07
- **Priority:** P1
- **Status:** [DONE]

---

## Step Count Summary

| Section | Steps | Priority | Key Deliverable |
|---|---|---|---|
| 1 — Close Pending Manual QA | 3 | P1 | QA-013, QA-033, QA-034 automated |
| 2 — Documentation Hardening | 4 | P2 | All `partial` rows → `documented` |
| 3 — Signal Persistence | 3 | P1 | API-P01 wired and tested |
| 4 — Position and PnL Tracking | 6 | P1 | Positions visible in execution page |
| 5 — Feature Snapshot Persistence | 3 | P2 | Audit trail: features → signal |
| 6 — Phase 7 Runtime | 5 | P1 | APScheduler wired, jobs running |
| 7 — Market Data Ingestion (Polygon) | 7 | P1/P2 | Real bars/quotes in DB |
| 8 — Prompt and Model Versioning | 7 | P2/P3 | Prompts versioned in DB, /evals page |
| 9 — News Data Ingestion | 5 | P3 | NewsArticle model wired |
| 10 — Broker Interface (IBKR) | 4 | P3 | IBKR adapter scaffold, guard stays |
| 11 — New Release Gates | 3 | P2/P3 | Gates 7, 8, 9 defined |
| 12 — RC-2 Gate Execution | 10 | P1 | All 9 gates pass, RC-2 marked |
| **Total** | **60** | | |

---

## Recommended Execution Order

For the shortest path to a production-grade paper trading system with real market data:

1. **BP2-01.01 → BP2-01.03** — Close manual QA debt (fast; no code changes needed)
2. **BP2-03.01 → BP2-03.03** — Wire signal persistence (foundational for audit trail)
3. **BP2-04.01 → BP2-04.05** — Position and PnL services (required for paper trading state)
4. **BP2-06.01 → BP2-06.05** — APScheduler runtime (prerequisite for data sync)
5. **BP2-07.01 → BP2-07.05** — Polygon client + market data service (real data flow)
6. **BP2-05.01 → BP2-05.03** — Feature snapshot persistence (completes audit chain)
7. **BP2-07.06 → BP2-07.07** — Market data route and frontend freshness badge
8. **BP2-04.06** — Positions panel on /execution page
9. **BP2-02.01 → BP2-02.04** — Documentation hardening (Gate 1 prep)
10. **BP2-11.01 → BP2-11.03** — Define Gates 7, 8, 9
11. **BP2-08 (P2 items)** — Prompt/model versioning wiring
12. **BP2-09 (P3 items)** — News ingestion
13. **BP2-10 (P3 items)** — IBKR broker scaffold
14. **BP2-12.01 → BP2-12.10** — RC-2 gates and release candidate

---

## Architecture Provider Completion Status

| Provider | Purpose | Status at BP2 start | Target at BP2 end |
|---|---|---|---|
| OpenAI | Primary LLM provider | implemented | implemented + versioned |
| Polygon | Market data (bars, quotes, news) | not started | implemented (client + ingest worker) |
| IBKR | Live execution broker | not started | scaffold (adapter + interface) |
| PostgreSQL | Structured database | implemented | extended (positions, PnL, versions) |

---

*Reference docs:*
- `docs/build-plan.md` — Build Plan 1 (54/54 DONE)
- `docs/implementation-matrix.md` — all impl IDs
- `docs/regression-qa-matrix.md` — all QA IDs (next IDs: QA-100 through QA-114)
- `docs/release-gates.md` — gate definitions (Gates 7–9 added in BP2-11)
- `docs/current-phase-status.md` — phase-by-phase ledger (Phase 10 and Phase 11 are new)
- `docs/architecture.md` — architecture principles and provider direction
