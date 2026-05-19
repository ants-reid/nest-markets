# Current Phase Status

Date: 2026-05-19

## Purpose

This document is the current-state ledger for Phases 1 to 9.

## Restart Stabilisation Rebaseline

Date: 2026-05-19

Current verified state for the restart pass:

- frontend is build-ready: `cd apps/web && npm run lint && npm run build` passed during the stabilisation pass
- backend local test infrastructure is restored against `postgresql+psycopg://postgres:postgres@localhost:5432/market_hunter`
- backend validation is green on the restored DB path: `2301 passed`
- learning bootstrap is stabilised through `scripts/test/test-learning.sh`: `99 passed`
- release-gate verification has now been rerun through MH-RESTART-004 and all documented release gates are green

Notes:

- `scripts/db/start-test-db.sh` now supports either Docker Compose or a native local PostgreSQL toolchain
- the backend schema drift on `positions.close_price` was fixed additively via a new Alembic migration
- workflow smoke tests now seed the required `EURUSD` asset explicitly instead of relying on ambient DB state

## Release-Gate Verification Pass

Date: 2026-05-19

Fresh verification outcome for MH-RESTART-004:

- backend lint and full pytest are green: `2301 passed`, `0 warnings`
- learning suite is green: `99 passed`
- frontend lint and production build are green
- Gate 1 implementation-matrix reconciliation is complete across backend routes, backend services, frontend routes, and shared TSX components
- Gate 2 QA linkage is green after adding coverage rows for the newly inventoried route and page IDs
- smoke suite is green on the rebuilt web app with API running: `20 passed`
- responsive suite is green on the rebuilt web app: `46 passed`
- visual suite is green after a targeted assets-page snapshot rebaseline: `48 passed`
- targeted RC2 slices are green: scheduler silence check, prompt version idempotence, news ingest graceful degradation, IBKR scaffold safety, and `QA-009-b`
- full Playwright release gate is green: `272 passed`, `0 failed`

Current release blockers:

- none on the documented release-gate surface

Release verdict:

- safe to resume feature development: yes
- release-ready: yes, release-ready candidate on the current evidence set

It answers four questions for each phase:

1. what the phase was meant to contain
2. what exists in the repo today
3. what is still missing or unclear
4. which numbered workstream owns the recovery

Status values:

- complete
- substantial
- partial
- unclear
- not evident

## Phase 1

Status: complete

Intended scope:

- config
- logging
- app bootstrap
- DB base/session
- health route

Current evidence:

- API foundation files exist
- health route exists
- config/logging/DB session structure exists

Recovery needed:

- none beyond ordinary maintenance

Owner workstream:

- `WS-02`

## Phase 2

Status: partial to substantial, still unclear in detail

Intended scope:

- database models
- migrations
- seed assets

Current evidence:

- `alembic/` exists
- DB model references are present in services
- persistence services clearly depend on model-backed structures

Recovery needed:

- model inventory audit
- migration completeness audit
- seed-data status check

Owner workstream:

- `WS-01`
- `WS-02`

## Phase 3

Status: complete

Intended scope:

- indicators
- feature engine

Current evidence:

- indicator and feature modules exist
- tests exist
- summary documentation exists

Recovery needed:

- none beyond linking to current control docs

Owner workstream:

- `WS-02`

## Phase 4

Status: complete

Intended scope:

- LLM provider interface
- OpenAI provider
- prompt loading
- schema loading

Current evidence:

- provider/router/helper layers exist
- tests exist
- summary documentation exists

Recovery needed:

- architecture boundary verification during `WS-03`

Owner workstream:

- `WS-02`
- `WS-03`

## Phase 5

Status: substantial

Intended scope:

- signal service
- risk service
- risk profiles
- execution mode router

Current evidence:

- signal service is documented and tested
- risk route and risk services are in active use
- execution mode routing is wired into risk/workflow flow

Recovery needed:

- explicit validation of all risk and routing paths
- clearer current-state documentation in phase language

Owner workstream:

- `WS-02`
- `WS-03`
- `WS-05`

## Phase 6

Status: complete

Intended scope:

- paper execution service
- approval workflow
- live execution scaffold

Canonical summary (2026-04-23):

All three areas are implemented and production-wired.

Paper execution:
- `paper_execution_service.py` handles order creation, status tracking, and fill simulation
- `persistence_paper_execution_service.py` persists to the database
- `/api/execution` route exposes create, list, and status endpoints
- Frontend `/execution` page allows paper submit and live-disabled submit

Approval workflow:
- `approval_service.py` and `persistence_approval_service.py` form a full create/list/update cycle
- `/api/approvals` route is fully wired (API-R05: implemented)
- Frontend `/approvals` page integrates real create and list calls

Live execution scaffold:
- `live_execution_service.py` exists and explicitly returns `live_execution_disabled_in_mvp` sentinel
- Enforced in frontend; test QA-009 verifies the guard is active

Execution journal:
- `execution_journal_service.py` records execution lifecycle events

Classification summary:

| Item | Status |
|---|---|
| paper_execution_service | implemented |
| approval_service | implemented |
| live_execution_service | scaffold (intentional MVP gate) |
| execution_journal_service | implemented |
| /api/execution route | implemented |
| /api/approvals route | implemented |
| /execution frontend | implemented |
| /approvals frontend | implemented |

Owner workstream:

- `WS-02`
- `WS-05`
- `WS-06`

## Phase 7

Status: complete

Intended scope:

- workers
- schedules
- sync jobs

Canonical summary (2026-04-24):

Phase 7 runtime infrastructure is now implemented and release-gated:

- `apps/api/app/workers/base_worker.py` defines the shared worker contract
- `apps/api/app/workers/data_sync_worker.py` and `apps/api/app/workers/news_ingest_worker.py` both subclass `BaseWorker`
- `apps/api/app/schedules/base_scheduler.py` defines the shared scheduler contract
- `apps/api/app/schedules/data_sync_scheduler.py` subclasses `BaseScheduler` and registers `data_sync` plus `news_ingest`
- `apps/api/app/main.py` starts APScheduler only outside `APP_ENV=test`
- Coverage exists in `apps/api/tests/infrastructure/test_worker_scheduler_scaffold.py`

Recovery needed:

- None for RC-2 scope

Owner workstream:

- `WS-01`

## Phase 8

Status: complete and beyond original scope

Intended scope (original wording):

- frontend dashboard

Canonical summary (2026-04-23):

Phase 8 delivered a full multi-route web application, not just a dashboard. The original wording understated the delivered scope.

Routes implemented:

| Route | Status | QA ID |
|---|---|---|
| `/` (home / PersonalDashboard) | implemented | QA-001 |
| `/dashboard` | implemented (PersonalDashboard) | QA-002 |
| `/analytics` | implemented (real data hook) | QA-003 |
| `/workflow` | mixed (real route, mock signal) | QA-004 |
| `/signals` | mock-backed | QA-005 |
| `/risk` | implemented | QA-006 |
| `/approvals` | implemented | QA-007 |
| `/execution` | implemented | QA-008, QA-009 |
| `/alerts` | implemented | QA-010 |
| `/notifications` | implemented | QA-011 |

Shared infrastructure delivered in this phase:

- Global dark/light theme with localStorage persistence and `prefers-color-scheme` fallback
- Semantic CSS token system (`--app-shell-bg`, `--text-strong`, `--surface-fill`, etc.)
- Shared chart components: `LineChart`, `ChartPanel`, `SeriesToggle`, `TimeRangeBar`
- Shared `Nav`, `LearnTooltip`, `OperatorNotificationSurface`, `PersonalDashboard`

Owner workstream:

- `WS-01`
- `WS-02`
- `WS-04`
- `WS-05`
- `WS-06`

## Phase 9

Status: complete

Intended scope:

- evals
- prompt versioning pages
- regression tests

Canonical summary (2026-04-24):

Regression tests:
- `apps/web/tests/smoke.spec.ts` covers the six core routes with submit + response assertions (QA-001, QA-004 through QA-009)
- `apps/web/tests/regression.spec.ts` has been created (2026-04-23) and covers QA-002, QA-003, QA-010, QA-011, QA-020, QA-021, QA-024, QA-030, QA-031, QA-032, QA-040, QA-041, QA-042, QA-009-b
- Backend unit and integration tests exist in `apps/api/tests/`

Prompt versioning:
- `apps/web/app/prompts/page.tsx` now provides operator-facing prompt inspection UI
- `apps/api/app/api/routes/prompts.py` now exposes `GET /prompts`, `GET /prompts/{subdir}/{filename}`, and `GET /prompts/{subdir}/{filename}/history`
- `apps/api/app/services/prompt_version_service.py` seeds `PromptVersion` rows from prompt files during startup

Evals:
- `apps/api/tests/evals/test_signal_output_eval.py` provides formal structured eval harness checks (QA-082)
- `apps/api/app/api/routes/evals.py` exposes eval run list/detail endpoints
- `apps/web/app/evals/page.tsx` renders the eval run table
- optional eval persistence is wired through `apps/api/app/services/eval_persistence_service.py` and `apps/api/tests/evals/conftest.py`

Recovery needed:

- Continue extending eval cases beyond structural invariants as model/prompt versions evolve

Owner workstream:

- `WS-01`
- `WS-02`
- `WS-05`

## Phase 10

Status: complete

Intended scope:

- market data ingestion
- market data routes
- news ingestion

Current evidence:

- `apps/api/app/clients/market_data/polygon_client.py` contains the Polygon bar-data client
- `apps/api/app/services/market_data_service.py` upserts market-data bars
- `apps/api/app/api/routes/market_data.py` exposes status, manual sync, and news endpoints
- `apps/api/app/workers/data_sync_worker.py` and `apps/api/app/workers/news_ingest_worker.py` run the ingestion paths
- `apps/web/app/analytics/page.tsx` and `apps/web/app/signals/page.tsx` render market-data freshness badges
- `apps/web/app/signals/page.tsx` renders the recent-news panel

Recovery needed:

- None for RC-2 scope

Owner workstream:

- `WS-01`
- `WS-02`
- `WS-05`
- `WS-06`

## Phase 11

Status: complete within guarded scope

Intended scope:

- broker abstraction
- guarded live-trading seam

Current evidence:

- `apps/api/app/clients/broker/broker_interface.py` defines the broker protocol boundary
- `apps/api/app/clients/broker/ibkr_adapter.py` provides the intentional scaffold adapter
- `apps/api/app/services/live_execution_service.py` accepts a broker dependency but remains disabled unless `LIVE_TRADING_ENABLED` is explicitly enabled
- broker isolation and live-trading guard checks passed in RC-2 gate execution

Recovery needed:

- Actual IBKR execution remains intentionally deferred beyond RC-2

Owner workstream:

- `WS-02`
- `WS-05`
- `WS-07`

## Operational Rule

For any future change, reference:

1. one phase from this file
2. one implementation ID from `docs/implementation-matrix.md`
3. one QA ID from `docs/regression-qa-matrix.md`
4. one workstream ID from `docs/catch-up-action-plan.md`

That is the minimum anti-drift linkage.

---

## Release Candidate — 2026-04-24

**Date:** 2026-04-24
**Build Plan Version:** 53-step plan (docs/build-plan.md)
**All six release gates passed.**

### Gate Results

| Gate | Result | Notes |
|---|---|---|
| Gate 1 — Implementation Matrix Completeness | PASS | All 6 routes, 12 services, 5 persistence services, 10 frontend routes, 4 shared foundations tracked; no blank/drifted rows; Phase 7 deferred rows explicitly noted |
| Gate 2 — QA Coverage Minimum | PASS | No `failing` or `blocked` QA items; automated items `passing` or `pending run`; full Playwright suite ran 53/53 passing |
| Gate 3 — Raw Hex Token Audit | PASS | Zero matches for raw hex literals or rgba() in all TSX files under apps/web/app/ and apps/web/components/ |
| Gate 4 — Live Execution Guard | PASS | `live_execution_service.py` always returns `accepted=False, status=disabled, reason=live_execution_disabled_in_mvp`; `test_execution_live_route` backend test asserts all three fields; QA-009 and QA-052 passing |
| Gate 5 — Architecture Compliance | PASS | AST scan: zero imports inside function bodies in any route file; all service logic lives in app/services/; BP-04.01–04.05 passed |
| Gate 6 — Theme Token Completeness | PASS | Both `:root` and `:root[data-theme="light"]` blocks define identical 43-token set; fixed: added `--font-size-base` and `--line-height-base` to light block |

### Test Suite State at RC

- Backend pytest: 155/155 passing
- Playwright (smoke + regression + responsive): 53/53 passing

### Accepted Deferrals at RC (Historical Snapshot)

| Item | Reason | Deferred To |
|---|---|---|
| API-W01 — Background worker infrastructure | Phase 7 not started; no worker infrastructure exists | Phase 7 start |
| API-W02 — Scheduled job infrastructure | Phase 7 not started; no scheduler infrastructure exists | Phase 7 start |
| BP-09 — Phase 9 prompt/evals | Prompt versioning UI and formal eval harness not yet built | Phase 9 start |
| BP-02.01–02.08 — Documentation debt | Implementation docs partial; no blocking compliance gaps | P2 backlog |

As of the completion update below, API-W01, API-W02, and BP-09 deferrals are now resolved.

### Owner Workstreams

- WS-07 (release gates) — gates executed and passed
- WS-05 (regression baseline) — test suites green
- WS-04 (theme/token governance) — Gate 3 and Gate 6 fixes applied

---

## Matrix Audit — 2026-04-28 (MH-23)

Audit scope:
- full matrix health check
- release readiness re-audit against `docs/release-gates.md`

Execution summary:
- Frontend health gates passed (`lint`, `tsc`, Strategy Lab Playwright route/smoke)
- Focused backend safety/research suites passed (`test_live_execution_service`, `test_strategy_lab_walk_forward`, `test_strategy_lab_result_quality`)

Blocking findings:
1. Gate 5 (Architecture Compliance) currently fails strict check criteria due
   route-level imports inside function bodies (observed in `broker.py` and
   `research_data.py`).
2. Gate 7 (Broker Isolation) currently fails strict check criteria due direct
   concrete IBKR adapter dependencies in service layer paths that should be
   abstracted behind protocol/interface wiring.
3. Full-matrix readiness remains not-ready while BP3 rows remain pre-registered
   and pending in implementation/QA matrices; scope interpretation must remain
   explicit when declaring release readiness.

Readiness verdict:
- Current implemented Strategy Lab/frontend slice: ready
- Full matrix release readiness: NO-GO pending Gate 5 and Gate 7 remediation

Owner workstreams:
- `WS-03` architecture compliance remediation
- `WS-07` release-gate rerun after remediation

---

## Completion Update — 2026-04-24

- Build plan completion: 54/54 `[DONE]` in `docs/build-plan.md`
- Backend pytest: 174/174 passing
- Playwright: 66/66 passing
- Phase 9 prompt/eval work completed (BP-09.01 to BP-09.03)
- Phase 7 scaffold infrastructure completed (BP-10.01 to BP-10.02)

---

## Release Candidate 2 — 2026-04-24

**Date:** 2026-04-24
**Build Plan Version:** 60-step plan (`docs/build-plan-2.md`)
**All nine release gates passed.**

### Gate Results

| Gate | Result | Notes |
|---|---|---|
| Gate 1 — Implementation Matrix Completeness | PASS | All BP2 implementation rows present, documented, and non-blank; no `not started` or `drifted` rows in the active matrix |
| Gate 2 — QA Coverage Minimum | PASS | QA-100 through QA-114 all present and linked; no `failing` or `blocked` rows; backend and Playwright suites both green |
| Gate 3 — Raw Hex Token Audit | PASS | Zero raw hex, `rgb()`, or `rgba()` matches in `apps/web/app/` and `apps/web/components/` TSX files |
| Gate 4 — Live Execution Guard | PASS | `LiveExecutionService` remains disabled by default; guarded live seam preserved; QA-009/QA-052/QA-114 still passing |
| Gate 5 — Architecture Compliance | PASS | Route audit found no buried imports after final cleanup and no inline service logic outside request/response orchestration |
| Gate 6 — Theme Token Completeness | PASS | Dark and light theme blocks define the same 43-token set |
| Gate 7 — Broker Call Isolation | PASS | No direct IBKR/TWS/broker SDK calls detected in routes or services outside the broker client layer |
| Gate 8 — Market Data Call Isolation | PASS | No direct market-data HTTP calls detected in routes or services outside the market-data client layer |
| Gate 9 — Worker And Scheduler Compliance | PASS | Concrete workers subclass `BaseWorker`, scheduler registry subclasses `BaseScheduler`, and startup remains disabled under `APP_ENV=test` |

### Test Suite State at RC-2

- Backend pytest: 261/261 passing, 0 failing, 1 warning
- Playwright: 75/75 passing, 0 failing

### Accepted Deferrals at RC-2

- No blocking deferrals accepted for RC-2
- IBKR execution remains scaffold-only by design; guarded live trading stays disabled outside explicit future work

---

## Release Candidate 3 — 2026-04-25

**Date:** 2026-04-25  
**Build Plan Version:** 31-step BP3 plan (`docs/build-plan-3.md`)  
**All twelve release gates passed.**

### Sections Completed in BP3

1. **BP3-01 — Asset Universe Seeding** (3 items)
   - Asset seed script, API route, UI page
2. **BP3-02 — Signal Sweep Worker** (4 items)
   - Worker implementation, Polygon bar integration, scheduler registration
3. **BP3-03 — Opportunity Ranker** (3 items)
   - OpportunityRankerService, API route, UI page
4. **BP3-04 — Auto Paper Trader** (5 items)
   - AUTO_PAPER enum, worker, scheduler integration, position cap, close worker
5. **BP3-05 — Result Capture** (3 items)
   - SignalOutcome model, PersistenceSignalOutcomeService, close worker wiring
6. **BP3-06 — AI Learning Loop** (5 items)
   - PerformanceStatsService, performance context injection, PromptAdaptationService, apply route, eval tests
7. **BP3-07 — Performance Dashboard** (3 items)
   - Performance stats endpoint, dashboard page (pre-existing), adaptation review UI
8. **BP3-08 — Gate Hardening & RC-3** (5 items)
   - Gate 10/11/12 audits, regression check, RC-3 marker

### Gate Results (New Gates 10-12)

| Gate | Result | Notes |
|---|---|---|
| Gate 10 — Auto Paper Risk Isolation | PASS | RiskService.evaluate() ALWAYS called before any auto_paper position is created; gate comment present in code |
| Gate 11 — Prompt Immutability | PASS | PromptAdaptationService and route create NEW PromptVersion rows only; zero UPDATE statements on existing prompts |
| Gate 12 — Polygon Rate Limit Compliance | PASS | Zero direct httpx/requests/aiohttp imports in workers; all market data flows through PolygonClient |

### Inherited Gate Results (Gates 1-9)

All inherited gates from RC-2 remain passing; no regressions introduced by BP3 work.

### Test Suite State at RC-3

- Backend pytest: **344/344 passing**, 0 failing (includes new QA-216 through QA-224)
- Playwright: **75/75 passing**, 0 failing
- **Total QA coverage:** 419 test cases across backend + frontend

### Accepted Deferrals at RC-3

- BP3-02.04 (sweep history UI) — deferred to P2; endpoint not yet implemented
- Alembic migration auto-application — migration file created and syntactically valid; manual `alembic upgrade head` required in production/staging environments

### New Implementation Matrix Entries (BP3)

- API-W03, API-W04: Signal sweep, auto-paper worker implementations
- API-S14, API-S15: PerformanceStatsService, PromptAdaptationService
- API-R10, API-R11: Prompt adaptations, performance stats endpoints
- API-M21: SignalOutcome model
- WEB-P16, WEB-P17: Performance dashboard, prompt adaptations pages

### Known Limitations / Future Work

- Live execution remains guarded (Gate 4); IBKR seam still scaffold-only
- AI learning loop captures outcomes but requires manual seed data for recommendation engine
- Performance context injected at ≥10 sample threshold; dynamic threshold adjustment deferred
- Position cap (_DEFAULT_MAX_OPEN = 5) is hard-coded; configurable via settings in future version%