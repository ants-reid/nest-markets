# Regression And QA Matrix

Date: 2026-05-21

## Purpose

This matrix is the numbered test and verification layer for the catch-up plan.

Use these IDs in commits, notes, PRs, and bug fixes so validation stays attached to the work.

Status values:

- passing
- failing
- pending
- blocked

Method values:

- automated
- manual
- mixed

## Core Control Rule

No feature is complete unless it links to at least one QA item in this file.

## Release-Gate Verification Snapshot

Fresh evidence from 2026-05-21:

- backend Ruff: failing with `11` existing issues
- backend full pytest: `2475 passed`, `167 failed`, `50 errors`
- learning suite: `99 passed`
- frontend lint/build: passed
- smoke suite on rebuilt web plus live API: `22 passed`
- responsive suite: `52 passed`
- visual suite: `48 passed`
- full Playwright suite: `292 passed`, `0 failed`

The browser matrix is green again on the fresh MH-BROWSER-STABILITY-001 evidence set, but the broader repo release gate remains blocked by unrelated backend baseline failures.

## Route Regression Checks

| ID | Scope | Check | Method | Status | Related Items | Notes |
|---|---|---|---|---|---|---|
| QA-001 | Home | page loads and backend status card renders | automated | passing | WEB-P01 | Existing smoke coverage |
| QA-002 | Dashboard | dashboard loads without broken primary panels | automated | passing | WEB-P02 | `regression.spec.ts` passing (2026-04-24) |
| QA-003 | Analytics | analytics route loads and key panels render | automated | passing | WEB-P03 | Full Playwright rerun green on 2026-05-19 after chart empty-state fix and stable SVG assertions |
| QA-004 | Workflow | workflow run renders result surface | automated | passing | WEB-P04 | Existing smoke coverage |
| QA-005 | Signals | mock signal submit renders payload | automated | passing | WEB-P05, API-R02 | Existing smoke coverage |
| QA-006 | Risk | risk submit renders payload | automated | passing | WEB-P06, API-R03 | Existing smoke coverage |
| QA-007 | Approvals | approval request renders payload or persisted response | automated | passing | WEB-P07, API-R05 | Existing smoke coverage |
| QA-008 | Execution | paper execution submit renders payload | automated | passing | WEB-P08, API-R06 | Existing smoke coverage |
| QA-009 | Execution | live execution remains disabled in MVP | automated | passing | WEB-P08, API-S06 | Existing smoke coverage and policy guard |
| QA-012 | Research UI | `/data-centre`, `/strategy-lab`, and `/data-quality` render their main route sections | automated | passing | WEB-PX06, WEB-PX18, WEB-PX20 | Covered by `routes.spec.ts` and `smoke.spec.ts`; fresh full Playwright rerun green on 2026-05-19 |
| QA-013 | Signals | real LLM mode toggle renders warning state when activated | automated | passing | WEB-P05, API-R02 | Automated in `regression.spec.ts`; check/uncheck cycle verifies ⚠ label appears and disappears (2026-04-24) |
| QA-010 | Alerts | alerts route loads key sections and watchlist chart | automated | passing | WEB-P09 | Full Playwright rerun green on 2026-05-19 after watchlist chart shell fix and stable SVG assertions |
| QA-011 | Notifications | notifications route loads without broken states | automated | passing | WEB-P10 | `regression.spec.ts` passing (2026-04-24) |
| QA-014 | Broker UI | sidebar navigation reaches `/broker` without layout or shell failure | automated | passing | WEB-PX29 | Covered by `full-flow.spec.ts`; fresh full Playwright rerun green on 2026-05-19 |
| QA-015 | Auxiliary page build | auxiliary operator pages compile in the production Next build | automated | passing | WEB-PX01, WEB-PX04, WEB-PX05, WEB-PX19, WEB-PX21, WEB-PX22, WEB-PX23, WEB-PX24, WEB-PX27, WEB-PX28, WEB-PX30 | `cd apps/web && npm run build` passed on 2026-05-19 |
| QA-016 | Cockpit and monitor build | cockpit, audit, and monitor pages compile in the production Next build | automated | passing | WEB-PX07, WEB-PX08, WEB-PX09, WEB-PX09A, WEB-PX09B, WEB-PX09C, WEB-PX09D, WEB-PX10, WEB-PX11, WEB-PX12, WEB-PX13, WEB-PX14, WEB-PX15, WEB-PX16, WEB-PX17, WEB-PX25, WEB-PX26, WEB-PX31 | `cd apps/web && npm run lint && npm run build` remained green on 2026-05-22 while adding the MH-COCKPIT-09 `/cockpit/daily-scoreboard` surface. |
| QA-017 | Asset card pages | asset-card list and detail pages compile in the production Next build | automated | passing | WEB-PX02, WEB-PX03 | `cd apps/web && npm run build` passed on 2026-05-19 |

## Theme And Token Checks

| ID | Scope | Check | Method | Status | Related Items | Notes |
|---|---|---|---|---|---|---|
| QA-020 | Theme | dark mode persists across route changes | automated | passing | WEB-F01, WEB-F03 | `regression.spec.ts` passing (2026-04-24) |
| QA-021 | Theme | light mode persists across route changes | automated | passing | WEB-F01, WEB-F03 | `regression.spec.ts` passing (2026-04-24) |
| QA-022 | Theme | major text surfaces remain readable in dark mode | manual | passing | WEB-F02 | Visual audit across all 10 routes completed (2026-04-24) |
| QA-023 | Theme | major text surfaces remain readable in light mode | manual | passing | WEB-F02 | Visual audit across all 10 routes completed (2026-04-24) |
| QA-024 | Token usage | raw color literals do not reappear in app/components TSX | automated | passing | WS-04 | 2026-05-20 regex scan over `apps/web/app/**/*.tsx` and `apps/web/components/**/*.tsx` found no raw hex or `rgb()/rgba()` literals |

## Chart Checks

| ID | Scope | Check | Method | Status | Related Items | Notes |
|---|---|---|---|---|---|---|
| QA-030 | LineChart | single-point series remains visible | automated | passing | WEB-C02 | Full Playwright rerun green on 2026-05-19 after SVG empty-state stub and aria-label anchor fix |
| QA-031 | LineChart | multi-point line remains readable in dark mode | automated | passing | WEB-C02 | Full Playwright rerun green on 2026-05-19 after stable chart anchor update |
| QA-032 | LineChart | multi-point line remains readable in light mode | automated | passing | WEB-C02 | Full Playwright rerun green on 2026-05-19 after stable chart anchor update |
| QA-033 | Chart axes | axis labels and hover guides remain readable in both themes | automated | passing | WEB-C02, WEB-F02 | Full Playwright rerun green on 2026-05-19 after chart rendering fix |
| QA-034 | Chart controls | series toggles and time range controls remain usable | automated | passing | WEB-C04, WEB-C05 | Automated in `regression.spec.ts`; TimeRangeBar 7d/30d/90d/all buttons present and clickable; no crash on click (2026-04-24) |

## Table And Surface Checks

| ID | Scope | Check | Method | Status | Related Items | Notes |
|---|---|---|---|---|---|---|
| QA-040 | Tables | headers, row text, badges, and links remain readable in dark mode | automated | passing | WEB-P03, WEB-P08, WEB-P09 | `regression.spec.ts` passing (2026-04-24) |
| QA-041 | Tables | headers, row text, badges, and links remain readable in light mode | automated | passing | WEB-P03, WEB-P08, WEB-P09 | `regression.spec.ts` passing (2026-04-24) |
| QA-042 | Empty states | empty and loading states render with readable contrast | automated | passing | WEB-P01, WEB-P10 | `regression.spec.ts` passing (2026-04-24) |

## Backend And Policy Checks

| ID | Scope | Check | Method | Status | Related Items | Notes |
|---|---|---|---|---|---|---|
| QA-050 | Backend routes | route handlers remain thin and free of business logic | manual | passing | API-R02, API-R03, API-R04, API-R05, API-R06 | Gate 5 route audit passed for all route files (2026-04-24) |
| QA-051 | LLM boundary | no AI calls outside provider layer | manual | passing | WS-03 | Architecture boundary audit passed; service layer ownership confirmed (2026-04-24) |
| QA-052 | Execution separation | paper and live execution remain isolated | manual | passing | API-S05, API-S06 | Live execution guard and route tests confirm strict separation (2026-04-24) |
| QA-053 | Risk policy | risk rules are applied consistently across modes | manual | passing | API-S02, API-S04 | Risk route and workflow integration checks passed in Gate 5/Gate 4 audit cycle (2026-04-24) |
| QA-080 | Prompt versioning UI | `/prompts` page loads, lists prompt files, and renders selected content | manual | passing | WEB-P11 | Verified against running app and backend prompt endpoint on 2026-04-24 |
| QA-081 | Prompt versioning API | `GET /prompts` and `GET /prompts/{subdir}/{filename}` return expected list/content with safe 404 behavior | automated | passing | API-R07 | Covered by `apps/api/tests/test_prompts_route.py` (4 tests) |
| QA-082 | Eval harness | `SignalService.generate_signal()` returns structurally valid output for canonical input | automated | passing | API-S01 | Covered by `apps/api/tests/evals/test_signal_output_eval.py` (13 invariant checks) |
| QA-100 | Signal persistence | signal and risk decision rows persist from signal generation flow | automated | passing | API-P01, API-R02 | Covered by `apps/api/tests/services/test_persistence_signal_service.py` and route wiring tests (2026-04-24) |
| QA-101 | Positions | position lifecycle persists open and close state correctly | automated | passing | API-S14, API-M13 | Covered by `apps/api/tests/services/test_position_pnl_service.py` (2026-04-24) |
| QA-102 | PnL snapshots | PnL snapshot creation and history ordering are correct | automated | passing | API-S15, API-M14 | Covered by `apps/api/tests/services/test_position_pnl_service.py` (2026-04-24) |
| QA-103 | Execution positions UI | open positions panel renders persisted position state on execution page | automated | passing | WEB-P08, API-S14 | Covered by `apps/web/tests/regression.spec.ts`; full Playwright suite passing 75/75 (2026-04-24) |
| QA-104 | Feature snapshots | signal-linked feature snapshots persist and are queryable | automated | passing | API-P01, API-M15, API-R02 | Covered by persistence service tests and `/signals/{signal_id}/features` route tests (2026-04-24) |
| QA-105 | Scheduler runtime | data-sync and news scheduler registrations remain stable and test-safe | automated | passing | API-W03, API-W04, API-W05 | Covered by `apps/api/tests/infrastructure/test_worker_scheduler_scaffold.py` (2026-04-24) |
| QA-106 | Polygon ingestion | Polygon client and market data service map and upsert bars correctly | automated | passing | API-C01, API-S13 | Covered by `apps/api/tests/clients/test_polygon_client.py` and `apps/api/tests/services/test_market_data_service.py` (2026-04-24) |
| QA-107 | Market data routes | status, manual sync, and persisted news endpoints respond correctly | automated | passing | API-R08 | Covered by `apps/api/tests/test_market_data_route.py` and route tests for sync/status (2026-04-24) |
| QA-108 | Data freshness indicators | analytics and signals pages render market-data freshness badge gracefully | automated | passing | WEB-P03, WEB-P05, API-R08 | Covered by `apps/web/tests/regression.spec.ts`; full Playwright suite passing 75/75 (2026-04-24) |
| QA-109 | Prompt version seeding | prompt version rows seed idempotently from prompt files on disk | automated | passing | API-S16, API-M16 | Covered by `apps/api/tests/services/test_prompt_version_service.py` (2026-04-24) |
| QA-110 | Prompt history | prompt version history endpoint returns versions and prompts UI renders history table | mixed | passing | API-R07, WEB-P11 | API covered by `apps/api/tests/test_prompts_history_route.py`; UI covered by `apps/web/tests/regression.spec.ts`; final RC-2 suites green (2026-04-24) |
| QA-111 | Eval runs | eval run list/detail endpoints respond and `/evals` page renders run table | mixed | passing | API-R09, WEB-P12 | API covered by `apps/api/tests/test_evals_route.py`; UI covered by `apps/web/tests/regression.spec.ts`; final RC-2 suites green (2026-04-24) |
| QA-112 | News ingest scaffold | placeholder news client and ingest worker degrade safely without provider key | automated | passing | API-C02, API-W05 | Covered by `apps/api/tests/test_news_ingest.py` (2026-04-24) |
| QA-113 | News feed surfaces | signals page news panel and news route return graceful empty state or recent items | mixed | passing | API-R08, WEB-P05, API-M20 | API covered by `apps/api/tests/test_market_data_route.py`; UI covered by `apps/web/tests/regression.spec.ts`; final RC-2 suites green (2026-04-24) |
| QA-114 | Broker protocol | BrokerInterface protocol: PositionInfo, expanded AccountInfo, get_positions() method | automated | passing | API-C03 | Covered by `apps/api/tests/clients/test_ibkr_adapter.py` (Phase 15 2026-04-24) |
| QA-115 | IBKR session | IBKRAdapter connect/tickle/disconnect uses IB REST API 2.30.0 (httpx, no TWS socket) | automated | passing | API-C04 | Covered by `apps/api/tests/clients/test_ibkr_adapter.py` test_connect_* (Phase 15 2026-04-24) |
| QA-116 | IBKR orders | submit_order maps OrderRequest to REST array body; cancel_order calls DELETE endpoint | automated | passing | API-C04 | Covered by `apps/api/tests/clients/test_ibkr_adapter.py` test_submit_order_* / test_cancel_order (Phase 15 2026-04-24) |
| QA-117 | IBKR bracket | submit_bracket_order sends 3-leg array with parentId linkage | automated | passing | API-C04 | Covered by `apps/api/tests/clients/test_ibkr_adapter.py` test_bracket_order (Phase 15 2026-04-24) |
| QA-118 | IBKR OCA | submit_oca_order adds isSingleGroup:true to each leg | automated | passing | API-C04 | Covered by `apps/api/tests/clients/test_ibkr_adapter.py` test_oca_order (Phase 15 2026-04-24) |
| QA-119 | IBKR positions | get_positions returns PositionInfo list; excludes zero-qty rows | automated | passing | API-C04 | Covered by `apps/api/tests/clients/test_ibkr_adapter.py` test_get_positions (Phase 15 2026-04-24) |
| QA-120 | IBKR market data | get_snapshot and get_history call correct endpoints with params | automated | passing | API-C04 | Covered by `apps/api/tests/clients/test_ibkr_adapter.py` test_snapshot / test_history (Phase 15 2026-04-24) |
| QA-121 | IBKR options chain | get_option_months/strikes/contracts implements 3-step mandatory sequential flow | automated | passing | API-C04 | Covered by `apps/api/tests/clients/test_ibkr_adapter.py` test_options_chain (Phase 15 2026-04-24) |
| QA-122 | IBKR retry | _request retries once on 401 session-expired response | automated | passing | API-C04 | Covered by `apps/api/tests/clients/test_ibkr_adapter.py` test_retry_on_401 (Phase 15 2026-04-24) |
| QA-123 | API route registry | all active backend route modules remain included and prefix-pinned in `app.main` | automated | passing | API-RX01, API-RX02, API-RX03, API-RX04, API-RX05, API-RX06, API-RX07, API-RX08, API-RX09, API-RX10, API-RX11, API-RX12, API-RX13, API-RX14, API-RX15, API-RX16, API-RX17, API-RX18, API-RX19, API-RX20, API-RX21, API-RX22, API-RX23, API-RX24, API-RX25, API-RX26, API-RX27, API-RX28 | Covered by `apps/api/tests/test_router_include_catalog_drift_lock.py`, `apps/api/tests/test_router_prefix_catalog_drift_lock.py`, `apps/api/tests/test_route_registry_drift_lock.py`, and the MH-MON-10 focused backend rerun on 2026-05-22 |
| QA-124 | Broker and safety APIs | broker, options, paper recommendation, risk-limit, and trading-halt routes keep expected request and response behavior | automated | passing | API-RX03, API-RX16, API-RX17, API-RX23, API-RX26 | Covered by `apps/api/tests/routes/test_broker_*.py`, `apps/api/tests/routes/test_risk_limits.py`, `apps/api/tests/routes/test_trading_halt.py`, and the fresh backend pytest rerun on 2026-05-19 |
| QA-125 | Monitor and audit APIs | cockpit, monitor, llm-log, broker-submit-decision, news-in-decision-log, risk-decision, feed-monitor, cockpit-mode, cockpit-EOD, cockpit in-flight adjustments, cockpit trade-close explanations, cockpit daily scoreboard, and monitor-test routes remain safely pinned and non-mutating | automated | passing | API-RX04, API-RX05, API-RX05A, API-RX05B, API-RX05C, API-RX05D, API-RX05E, API-RX06, API-RX08, API-RX11, API-RX12, API-RX13, API-RX15, API-RX22, API-RX27, API-RX28 | Covered by route tests, audit response-shape drift locks, targeted `/monitor/feeds` pytest coverage, MH-MON-10 route/service tests, MH-COCKPIT-05 route/service tests, MH-COCKPIT-07 route/service tests, MH-COCKPIT-08 route/service tests, MH-COCKPIT-09 route/service tests, and focused backend reruns including router drift locks |
| QA-126 | Model and regime APIs | scoring, models, governance, and regime routes remain green under backend route suites | automated | passing | API-RX07, API-RX10, API-RX19, API-RX24 | Covered by `apps/api/tests/test_phase3_routes.py`, `apps/api/tests/test_model_governance_routes.py`, and the fresh backend pytest rerun on 2026-05-19 |
| QA-127 | Research and asset-card APIs | asset-card, baseline-candidate, markets, news-article, paper-validation, research-data, research-job, and strategy-lab surfaces stay registered and schema-safe | automated | passing | API-RX01, API-RX02, API-RX09, API-RX14, API-RX18, API-RX20, API-RX21, API-RX25 | Covered by route tests, schema drift-locks, and the fresh backend pytest rerun on 2026-05-19 |
| QA-128 | Feed monitor browser surface | `/monitor/feeds` renders on the live stack, keeps filter/search interactions stable under mocked monitor payloads, and avoids 390px horizontal overflow | automated | passing | WEB-PX31, API-RX27 | Covered by `apps/web/tests/feed-monitor.spec.ts`, `apps/web/tests/routes.spec.ts`, `apps/web/tests/smoke.spec.ts`, and `apps/web/tests/responsive.spec.ts`; the refreshed MH-BROWSER-STABILITY-001 browser reruns on 2026-05-21 kept full visual coverage green (`48/48`) and restored the full Playwright gate to `292/292`, and the 2026-05-22 reboot recovery rerun re-confirmed the targeted feed-monitor slice (`3/3` plus `5/5`) on the restored local stack while broader full-suite failures remained clustered outside this feature slice. |
| QA-129 | Cockpit mode selector surface | `/cockpit` renders safe selectable modes, keeps assisted/live/auto-live visibly locked, accepts only safe mode changes, and avoids 390px overflow | automated | passing | WEB-PX08, API-RX05A, API-SX09A | Covered by `apps/web/tests/cockpit-mode-selector.spec.ts` plus exact `routes.spec.ts`, `smoke.spec.ts`, and `responsive.spec.ts` cockpit reruns on 2026-05-20; backend contract and drift-lock coverage passed in focused pytest (`16 passed`) |
| QA-130 | Monitor operator dry-probe endpoint | `POST /monitor/test/{service_id}` is auth-gated, rejects unknown service IDs, returns dry-probe-safe payloads for known probes (including degraded/error states), and never returns secret-like fields | automated | passing | API-RX28, API-SX79, API-H02 | Covered by `apps/api/tests/test_monitor_test_route.py`, `apps/api/tests/test_monitor_test_service.py`, and auth/route drift-lock reruns (`21 passed`) on 2026-05-22 |
| QA-131 | Monitor test endpoint hardening | `POST /monitor/test/{service_id}` enforces safe allow-list and cooldown, recursively scrubs secret-like evidence keys, converts probe failures/timeouts into safe non-500 payloads, and preserves dry-probe-only execution with no broker/live submit path | automated | passing | API-RX28, API-SX79, API-H02 | Covered by expanded `apps/api/tests/test_monitor_test_route.py` and `apps/api/tests/test_monitor_test_service.py` during MH-MON-09 focused reruns and full backend pytest on 2026-05-22 |

## Responsive And Mobile Checks

Viewport breakpoints: mobile = 390px, tablet = 768px, desktop = 1024px.
All automated checks go in `apps/web/tests/responsive.spec.ts` (BP-03.01).

| ID | Scope | Check | Method | Status | Related Items | Notes |
|---|---|---|---|---|---|---|
| QA-060 | Responsive | home/dashboard does not overflow horizontally at 390px | automated | passing | WEB-P01, WEB-F04 | `responsive.spec.ts` passing (2026-04-24) |
| QA-061 | Responsive | workflow form-result-split stacks vertically at 768px | automated | passing | WEB-P04, WEB-F04 | `responsive.spec.ts` passing (2026-04-24) |
| QA-062 | Responsive | signals two-col grids collapse to single column at 768px | automated | passing | WEB-P05, WEB-F04 | `responsive.spec.ts` passing (2026-04-24) |
| QA-063 | Responsive | risk three-col checkbox grid collapses to single column at 768px | automated | passing | WEB-P06, WEB-F04 | `responsive.spec.ts` passing (2026-04-24) |
| QA-064 | Responsive | approvals two-col grids collapse to single column at 768px | automated | passing | WEB-P07, WEB-F04 | `responsive.spec.ts` passing (2026-04-24) |
| QA-065 | Responsive | execution panels stack vertically at 768px | automated | passing | WEB-P08, WEB-F04 | `responsive.spec.ts` passing (2026-04-24) |
| QA-066 | Responsive | alerts notification rows wrap cleanly at 390px | automated | passing | WEB-P09, WEB-F04 | `responsive.spec.ts` passing (2026-04-24) |
| QA-067 | Responsive | analytics stat-grid wraps to two columns at 390px | automated | passing | WEB-P03, WEB-F04 | `responsive.spec.ts` passing (2026-04-24) |
| QA-068 | Responsive | no route produces horizontal overflow at 390px | automated | passing | WEB-F04 | `responsive.spec.ts` green on 2026-05-19 after the 390px topbar overflow fix |
| QA-069 | Responsive | no route produces horizontal overflow at 768px | automated | passing | WEB-F04 | `responsive.spec.ts` passing across all routes (2026-04-24) |
| QA-070 | Responsive | nav wraps and remains fully usable at 390px | automated | passing | WEB-F03, WEB-F04 | `responsive.spec.ts` green on 2026-05-19 after shrinking the topbar status controls on very small screens |
| QA-071 | Touch | all primary action buttons meet 44×44px minimum tap target | automated | passing | WEB-F04 | Automated proxy in `responsive.spec.ts` confirms button height threshold coverage at 390px (2026-04-24) |
| QA-072 | Touch | all form inputs meet 44px minimum touch height at 390px | automated | passing | WEB-F04 | Automated proxy in `responsive.spec.ts` confirms visible text-input height threshold coverage at 390px (2026-04-24) |

## Visual Regression Checks

| ID | Scope | Check | Method | Status | Related Items | Notes |
|---|---|---|---|---|---|---|
| QA-073 | Visual | dashboard, analytics, execution, performance, assets, opportunities, alerts, and notifications snapshots match baseline across mobile, tablet, desktop, and both themes | automated | passing | WEB-F02, WEB-F04, WEB-P02, WEB-P03, WEB-P08, WEB-P09, WEB-P10, WEB-P13, WEB-P15, WEB-P16 | `visual.spec.ts` passed `48/48` on 2026-05-20 after dashboard/assets diff review confirmed the hydrated UI was correct and the stale loading-state baselines were intentionally refreshed |

## Process Checks

| ID | Scope | Check | Method | Status | Related Items | Notes |
|---|---|---|---|---|---|---|
| QA-090 | Process | new features are added to implementation matrix before sign-off | manual | passing | WS-07 | Gate 1 pass confirms matrix-first workflow on final build pass |
| QA-091 | Process | docs are updated when route/service scope changes | manual | passing | WS-02, WS-07 | Build-plan, implementation, QA, and phase docs updated in lock-step on completion pass |
| QA-092 | Process | every fix references at least one QA item or creates a new one | manual | passing | WS-07 | Final pass included explicit QA additions for prompt/eval/infra work |

## Build Plan 3 — Multi-Asset, Auto Paper Trader, AI Learning Loop (QA-200+)

All rows below are `pending` until implemented. Status updates to `passing` only after validation is performed.

### BP3 Section 1 — Asset Universe

| ID | Scope | Check | Method | Status | Related Items | Notes |
|---|---|---|---|---|---|---|
| QA-200 | Asset seeding | seed script inserts 20 assets idempotently; re-run causes no duplicate rows | automated | pending | API-SC01, API-M01 | BP3-01.01 |
| QA-201 | Assets API | GET/POST/DELETE /assets return correct shapes; soft-delete preserves row | automated | pending | API-R08 | BP3-01.02; 4 route tests |
| QA-202 | Assets UI | /assets page renders active universe table with symbol, class, status | automated | pending | WEB-P13 | BP3-01.03; Playwright |

### BP3 Section 2 — Signal Sweep Worker

| ID | Scope | Check | Method | Status | Related Items | Notes |
|---|---|---|---|---|---|---|
| QA-203 | Signal sweep | SignalSweepWorker generates one signal per active asset and persists each | automated | pending | API-W03 | BP3-02.01; unit tests |
| QA-204 | Sweep scheduler | sweep job registered; does not fire under APP_ENV=test (Gate 9 regression) | automated | pending | API-W03, API-W02 | BP3-02.02 |
| QA-205 | Polygon isolation | sweep fetches bars via PolygonClient only; no raw HTTP calls (Gate 12) | automated | pending | API-W03, API-CL02 | BP3-02.03 |
| QA-206 | Sweeps UI | /sweeps page renders run history table with sweep ID, count, duration | automated | pending | WEB-P14 | BP3-02.04; Playwright |

### BP3 Section 3 — Opportunity Ranker

| ID | Scope | Check | Method | Status | Related Items | Notes |
|---|---|---|---|---|---|---|
| QA-207 | Ranker sort | OpportunityRankerService returns signals sorted descending by composite score | automated | pending | API-S13 | BP3-03.01; 3 unit tests |
| QA-208 | Opportunities API | GET /opportunities returns ranked list with score field | automated | pending | API-R09, API-S13 | BP3-03.02; 3 route tests |
| QA-209 | Opportunities UI | /opportunities page renders ranked signal list with score badges | automated | pending | WEB-P15 | BP3-03.03; Playwright |

### BP3 Section 4 — Auto Paper Trader

| ID | Scope | Check | Method | Status | Related Items | Notes |
|---|---|---|---|---|---|---|
| QA-210 | auto_paper mode | auto_paper execution mode calls RiskEvaluator before any paper order (Gate 10) | automated | pending | API-S04 | BP3-04.01 |
| QA-211 | Worker risk block | AutoPaperTraderWorker: risk-blocked opportunity produces no paper order | automated | pending | API-W04 | BP3-04.02 |
| QA-212 | Worker approval | AutoPaperTraderWorker: risk-approved opportunity produces paper order | automated | pending | API-W04 | BP3-04.02 |
| QA-213 | Auto trader scheduler | auto_paper_trader job registered; inactive under APP_ENV=test | automated | pending | API-W04, API-W02 | BP3-04.03 |
| QA-214 | Position cap | AutoPaperTraderWorker refuses to open trade N+1 when cap is reached | automated | pending | API-W04 | BP3-04.04 |
| QA-215 | Close worker | AutoPaperCloseWorker closes horizon-expired positions and records final PnL | automated | pending | API-W05 | BP3-04.05 |
| QA-215A | Auto Paper cockpit status | `/cockpit/auto-paper-status` and the `/cockpit` Auto Paper summary render simulation-only messaging, operator next action, and locked live/auto-live notes from mocked status payloads | automated | passing | API-RX05, API-SX09, WEB-PX08, WEB-PX09 | Added 2026-05-21 during MH-AUTO-PAPER-RELIABILITY-001; covered by `apps/web/tests/auto-paper-status.spec.ts`. |
| QA-215B | Cockpit EOD report surface | `/cockpit/eod-report` stays paper-only and read-only, renders summary/empty/error states, avoids trade-action buttons, and keeps 390px overflow green while the backend route returns stable typed EOD payloads | automated | passing | API-RX05B, API-SX09B, WEB-PX08, WEB-PX09A | Added 2026-05-22 during MH-COCKPIT-05; covered by `apps/api/tests/test_cockpit_eod_report_{service,route}.py`, `apps/web/tests/eod-report.spec.ts`, and targeted `routes.spec.ts` / `responsive.spec.ts` reruns. |
| QA-215C | Cockpit in-flight adjustments surface | `/cockpit/in-flight-adjustments` stays paper-only and read-only, renders summary/empty/error states, surfaces item reason/evidence safely, enforces `is_actionable=false`, and keeps 390px overflow green while the backend route returns stable typed payloads | automated | passing | API-RX05C, API-SX09C, WEB-PX08, WEB-PX09B | Added 2026-05-22 during MH-COCKPIT-07; covered by `apps/api/tests/test_cockpit_in_flight_adjustments_{service,route}.py`, `apps/web/tests/in-flight-adjustments.spec.ts`, and targeted `routes.spec.ts` / `responsive.spec.ts` / `smoke.spec.ts` reruns. |
| QA-215D | Cockpit trade-close explanations surface | `/cockpit/trade-close-explanations` stays paper-only and read-only, renders summary/empty/error states, exposes deterministic close-label evidence safely, enforces `is_actionable=false`, and keeps responsive overflow checks green while the backend route returns stable typed payloads | automated | passing | API-RX05D, API-SX09D, WEB-PX08, WEB-PX09C | Added 2026-05-22 during MH-COCKPIT-08; covered by `apps/api/tests/test_cockpit_trade_close_explanations_{service,route}.py`, `apps/web/tests/trade-close-explanations.spec.ts`, and targeted `routes.spec.ts` / `responsive.spec.ts` / `smoke.spec.ts` reruns. |
| QA-215E | Cockpit daily scoreboard surface | `/cockpit/daily-scoreboard` stays paper-only and read-only, renders summary/empty/error states, surfaces unknown metrics safely, avoids trade-action buttons, and keeps responsive overflow checks green while the backend route returns stable typed payloads | automated | passing | API-RX05E, API-SX09E, WEB-PX08, WEB-PX09D | Added 2026-05-22 during MH-COCKPIT-09; covered by `apps/api/tests/test_cockpit_daily_scoreboard_{service,route}.py`, `apps/web/tests/daily-scoreboard.spec.ts`, and targeted `routes.spec.ts` / `responsive.spec.ts` / `smoke.spec.ts` reruns. |

### BP3 Section 5 — Result Capture

| ID | Scope | Check | Method | Status | Related Items | Notes |
|---|---|---|---|---|---|---|
| QA-216 | Outcome model | SignalOutcome migration applies; model stores direction_correct and actual_pnl_pct | automated | pending | API-M21 | BP3-05.01 |
| QA-217 | Outcome persistence | PersistenceSignalOutcomeService record, retrieve-by-asset, retrieve-by-setup | automated | pending | API-P06 | BP3-05.02; 3 unit tests |
| QA-218 | Outcome wiring | AutoPaperCloseWorker writes outcome row on position close | automated | pending | API-W05, API-P06 | BP3-05.03; integration test |

### BP3 Section 6 — AI Learning Loop

| ID | Scope | Check | Method | Status | Related Items | Notes |
|---|---|---|---|---|---|---|
| QA-219 | Stats service | PerformanceStatsService win_rate_by_setup and overall_stats compute correctly from fixture data | automated | pending | API-S14 | BP3-06.01 |
| QA-220 | Prompt context | performance context block present in prompt when min_samples met; absent when below | automated | pending | API-S01, API-S14 | BP3-06.02 |
| QA-221 | Adaptation proposal | PromptAdaptationService proposes without mutating any existing PromptVersion row (Gate 11) | automated | pending | API-S15 | BP3-06.03 |
| QA-222 | Adaptation apply | POST /prompt-adaptations/apply creates new PromptVersion row; old row unchanged (Gate 11) | automated | pending | API-R10 | BP3-06.04 |
| QA-223 | Adaptation eval | eval harness: adaptation proposal has rationale, setup_type, proposed_prompt_text fields | automated | pending | API-S15, QA-T08 | BP3-06.05 |

### BP3 Section 7 — Performance Dashboard

| ID | Scope | Check | Method | Status | Related Items | Notes |
|---|---|---|---|---|---|---|
| QA-224 | Stats API | GET /performance-stats returns overall stats and breakdowns by setup, asset, catalyst, regime | automated | pending | API-R11, API-S14 | BP3-07.01; 4 route tests |
| QA-225 | Performance UI | /performance page renders win-rate breakdown and overall stats | automated | pending | WEB-P16 | BP3-07.02; Playwright |
| QA-226 | Adaptations UI | /prompt-adaptations page renders proposals; Apply button calls POST /prompt-adaptations/apply | automated | pending | WEB-P17, API-R10 | BP3-07.03; Playwright |

---

## Operating Notes

1. When a bug is fixed, update the relevant QA row from `pending` or `failing` to `passing` only after validation is actually performed.
2. If a new feature does not fit an existing QA row, create a new numbered QA item before calling it complete.
3. Reference both implementation IDs and QA IDs in future work logs to keep build and validation linked.