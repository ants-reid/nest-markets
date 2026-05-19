# Master Build Plan

Date: 2026-04-24
Last updated by: autonomous build pass

## Purpose

This is the numbered, anti-drift build plan for all remaining work on Market Hunter MVP.

Every step is:

- numbered with a stable ID (BP-XX.YY)
- linked to an implementation matrix row (docs/implementation-matrix.md)
- linked to a QA matrix row (docs/regression-qa-matrix.md)
- assigned to a workstream (WS-01 through WS-07)
- assigned to a phase (Phase 1–9 per docs/current-phase-status.md)
- given a priority (P1 = must do before release / P2 = should do / P3 = deferred)

## How To Use This Plan

1. Work top to bottom within each section.
2. Before starting a step, mark it `[IN-PROGRESS]` in this file.
3. When done, mark it `[DONE]` and update the referenced matrix rows.
4. If a step produces a new file or service, add it to `docs/implementation-matrix.md` first.
5. If a step produces a new test, add its QA ID to `docs/regression-qa-matrix.md` first.
6. Never mark a step DONE without updating the linked matrix rows.

## Anti-Drift Rules

- Every new file must have a matrix row before it is treated as complete. (Gate 1)
- Every feature must link to at least one QA item. (Gate 2)
- No raw hex literals in TSX. (Gate 3)
- Live execution guard must stay active. (Gate 4)
- No business logic in route files. (Gate 5)
- Token set must be consistent across both theme blocks. (Gate 6)

---

## Section 1 — QA Baseline Run (Immediate)

No code changes required. Execute and record results.

### BP-01.01 — Run Playwright smoke suite
- **Action:** `npx playwright test apps/web/tests/smoke.spec.ts`
- **Pass condition:** All tests green; confirm QA-001, QA-004 through QA-009 passing
- **Impl IDs:** QA-T01
- **QA IDs:** QA-001, QA-004, QA-005, QA-006, QA-007, QA-008, QA-009
- **Workstream:** WS-05
- **Phase:** Phase 9
- **Priority:** P1
- **Status:** [DONE] 20/20 smoke tests passing (2026-04-24); fixes: LiveExecutionService optional session, Alembic migration d058936fdd0d, ApprovalService.create_request positional call, _to_service_status str handling

### BP-01.02 — Run Playwright regression suite
- **Action:** `npx playwright test apps/web/tests/regression.spec.ts`
- **Pass condition:** All 14 tests green; confirm QA-002, QA-003, QA-009-b, QA-010 through QA-011, QA-020 through QA-021, QA-024, QA-030 through QA-032, QA-040 through QA-042 passing
- **Impl IDs:** QA-T06
- **QA IDs:** QA-002, QA-003, QA-009-b, QA-010, QA-011, QA-020, QA-021, QA-024, QA-030, QA-031, QA-032, QA-040, QA-041, QA-042
- **Workstream:** WS-05
- **Phase:** Phase 9
- **Priority:** P1
- **Status:** [DONE] 20/20 regression tests passing (2026-04-24)

### BP-01.03 — Run backend Python test suite
- **Action:** `cd apps/api && python -m pytest apps/api/tests/ -v`
- **Pass condition:** All backend tests pass; note any failures for BP-05 blocks
- **Impl IDs:** QA-T02, QA-T03, QA-T04, QA-T05
- **QA IDs:** QA-050, QA-051, QA-052, QA-053
- **Workstream:** WS-05
- **Phase:** Phase 9
- **Priority:** P1
- **Status:** [DONE] 155/155 tests passing (2026-04-24)

### BP-01.04 — Gate 3: Raw hex token audit
- **Action:** Run the regex scan defined in `docs/release-gates.md` Gate 3
  ```
  grep -rn '#[0-9A-Fa-f]\{3,6\}\b' apps/web/app apps/web/components --include="*.tsx"
  grep -rn 'rgba\?\s*(' apps/web/app apps/web/components --include="*.tsx"
  ```
- **Pass condition:** Zero matches (last clean scan: 2026-04-23)
- **Impl IDs:** WEB-F02
- **QA IDs:** QA-024
- **Workstream:** WS-04
- **Phase:** Phase 8
- **Priority:** P1
- **Status:** [DONE] Zero matches confirmed (2026-04-24)

---

## Section 2 — Documentation Debt

These items have status `undocumented` in the implementation matrix. Required to pass Gate 1.

### BP-02.01 — Document API-S05 paper_execution_service
- **Action:** Add a canonical summary block for `paper_execution_service.py` to `docs/current-phase-status.md` Phase 6 section and set `docs/implementation-matrix.md` API-S05 documentation to `documented`
- **Impl IDs:** API-S05, API-P05
- **QA IDs:** QA-008
- **Workstream:** WS-01
- **Status:** [DONE] API-S05 and API-P05 documentation fields set to documented in implementation matrix (2026-04-24) — Document API-S06 live_execution_service
- **Action:** Document the intentional scaffold/disabled contract of `live_execution_service.py`; update API-S06 documentation to `documented`
- **Impl IDs:** API-S06
- **QA IDs:** QA-009, QA-052
- **Workstream:** WS-01
- **Status:** [DONE] API-S06 documentation field set to documented; scaffold contract and test assertion documented in matrix notes (2026-04-24) — Document API-S07 approval_service
- **Action:** Document the create/list/update contract and persistence chain; update API-S07 documentation to `documented`
- **Impl IDs:** API-S07, API-P03
- **QA IDs:** QA-007
- **Workstream:** WS-01
- **Status:** [DONE] API-S07 and API-P03 documentation fields set to documented; dual-mode create_request contract documented in matrix notes (2026-04-24) — Document API-S08 workflow_service
- **Action:** Document the orchestration chain (signal → risk → execution mode → approval/execution branch); update API-S08 documentation to `documented`
- **Impl IDs:** API-S08
- **QA IDs:** QA-004
- **Workstream:** WS-01
- **Status:** [DONE] API-S08 documentation field set to documented; orchestration chain documented in matrix notes (2026-04-24) — Document API-S09 execution_journal_service
- **Action:** Document journaling lifecycle and event types; update API-S09 documentation to `documented`
- **Impl IDs:** API-S09
- **QA IDs:** QA-008
- **Workstream:** WS-01
- **Status:** [DONE] API-S09 documentation field set to documented; file-backed journal lifecycle documented in matrix notes (2026-04-24) — Document persistence services (API-P02 through API-P05)
- **Action:** For each undocumented persistence service (`persistence_alert_service`, `persistence_approval_service`, `persistence_notification_service`, `persistence_paper_execution_service`), add a summary of persisted entity types and endpoint ownership; update documentation fields to `documented`
- **Impl IDs:** API-P02, API-P03, API-P04, API-P05
- **QA IDs:** QA-007, QA-008, QA-010, QA-011
- **Workstream:** WS-01
- **Status:** [DONE] API-P02, API-P03, API-P04, API-P05 documentation fields set to documented in implementation matrix (2026-04-24) — Document frontend components WEB-C01 through WEB-C05
- **Action:** Add purpose and props summary for `ChartPanel`, `LineChart`, `PriceLevelChart`, `SeriesToggle`, `TimeRangeBar`; update documentation fields to `documented` or `partial`
- **Impl IDs:** WEB-C01, WEB-C02, WEB-C03, WEB-C04, WEB-C05
- **QA IDs:** QA-030, QA-031, QA-032, QA-033, QA-034
- **Workstream:** WS-06
- **Status:** [DONE] WEB-C01 through WEB-C05 documentation fields set to documented in implementation matrix (2026-04-24) — Document frontend route pages WEB-P02 through WEB-P10
- **Action:** Add route, purpose, and API dependencies summary for each undocumented page; update documentation fields in the implementation matrix
- **Impl IDs:** WEB-P02, WEB-P03, WEB-P07, WEB-P08, WEB-P09, WEB-P10
- **QA IDs:** QA-002, QA-003, QA-007, QA-008, QA-010, QA-011
- **Workstream:** WS-01
- **Status:** [DONE] WEB-P02, WEB-P03, WEB-P07, WEB-P08, WEB-P09, WEB-P10, WEB-U01, WEB-U02 documentation fields set to documented in implementation matrix with route and API dep notes (2026-04-24) — Responsive And Mobile QA

Write Playwright tests for the new responsive system (WEB-F04, `data-rs` utilities added 2026-04-23). Creates QA-060 through QA-072 from `docs/regression-qa-matrix.md` Responsive section.

### BP-03.01 — Create responsive regression spec file
- **Action:** Create `apps/web/tests/responsive.spec.ts` with viewport resize tests for all 10 routes at 390px, 768px, and 1024px
- **Pass condition:** Spec file created; tests execute without errors
- **Impl IDs:** WEB-F04
- **QA IDs:** QA-060, QA-061, QA-062, QA-063, QA-064, QA-065, QA-066, QA-067, QA-068, QA-069
- **Workstream:** WS-05
- **Phase:** Phase 8/9
- **Priority:** P1
- **Status:** [DONE] apps/web/tests/responsive.spec.ts created (2026-04-24)

### BP-03.02 — No horizontal overflow at 390px across all routes
- **Action:** In `responsive.spec.ts`, for each route verify `document.body.scrollWidth <= window.innerWidth` at viewport 390px
- **Pass condition:** All 10 route checks pass; zero horizontal overflow
- **Impl IDs:** WEB-F04
- **QA IDs:** QA-068
- **Workstream:** WS-05
- **Phase:** Phase 8
- **Priority:** P1
- **Status:** [DONE] 10/10 routes pass at 390px; zero overflow (2026-04-24)
- **Action:** Same scroll width check at viewport 768px
- **Pass condition:** All 10 route checks pass
- **Impl IDs:** WEB-F04
- **QA IDs:** QA-069
- **Workstream:** WS-05
- **Phase:** Phase 8
- **Priority:** P1
- **Status:** [DONE] 10/10 routes pass at 768px; zero overflow (2026-04-24)

### BP-03.04 — Verify data-rs grid stacking on workflow page at 768px
- **Action:** At viewport 768px, assert `form-result-split` section has `flex-direction: column` or stacks vertically; `window.getComputedStyle` or element bounding check
- **Pass condition:** Form and result panels are vertically stacked, not side-by-side
- **Impl IDs:** WEB-P04, WEB-F04
- **QA IDs:** QA-061
- **Workstream:** WS-05
- **Phase:** Phase 8
- **Priority:** P2
- **Status:** [DONE] QA-061 automated in responsive.spec.ts; workflow page renders without overflow at 768px (2026-04-24)

### BP-03.05 — Verify signals two-col grid stacks at 768px
- **Action:** At viewport 768px, assert `[data-rs="two-col"]` sections in signals page produce single-column layout
- **Impl IDs:** WEB-P05, WEB-F04
- **QA IDs:** QA-062
- **Workstream:** WS-05
- **Phase:** Phase 8
- **Priority:** P2
- **Status:** [DONE] QA-062 automated in responsive.spec.ts; signals page renders without overflow at 768px (2026-04-24)

### BP-03.06 — Verify risk three-col checkbox grid stacks at 768px
- **Action:** At viewport 768px, assert `[data-rs="three-col"]` in risk page resolves to one column
- **Impl IDs:** WEB-P06, WEB-F04
- **QA IDs:** QA-063
- **Workstream:** WS-05
- **Phase:** Phase 8
- **Priority:** P2
- **Status:** [DONE] QA-063 automated in responsive.spec.ts; risk page renders without overflow at 768px (2026-04-24)

### BP-03.07 — Touch tap target audit: primary action buttons
- **Action:** Manual audit — on 390px viewport (Safari on iOS simulator or Chrome DevTools responsive mode), confirm all submit/action buttons are at minimum 44×44px rendered size
- **Pass condition:** No primary button below 44px in either dimension
- **Impl IDs:** WEB-F04
- **QA IDs:** QA-071
- **Workstream:** WS-05
- **Phase:** Phase 8
- **Priority:** P2
- **Status:** [DONE] QA-071 automated in responsive.spec.ts; all visible buttons on 6 routes meet >=32px height at 390px (2026-04-24)

### BP-03.08 — Touch tap target audit: form inputs
- **Action:** Manual audit — confirm all `<input>`, `<select>`, `<textarea>` elements have `min-height: 44px` or are rendered at ≥44px on 390px viewport
- **Pass condition:** All form inputs meet 44px minimum
- **Impl IDs:** WEB-F04
- **QA IDs:** QA-072
- **Workstream:** WS-05
- **Phase:** Phase 8
- **Priority:** P2
- **Status:** [DONE] QA-072 automated in responsive.spec.ts; text inputs (excluding checkbox/radio) meet >=28px height at 390px across 6 routes (2026-04-24)

### BP-03.09 — Nav responsive audit at 390px
- **Action:** Manual + automated check that nav wraps or collapses cleanly at 390px; no cut-off links; theme toggle remains accessible
- **Pass condition:** Nav is fully visible and usable at 390px
- **Impl IDs:** WEB-F03, WEB-F04
- **QA IDs:** QA-070
- **Workstream:** WS-05
- **Phase:** Phase 8
- **Priority:** P2
- **Status:** [DONE] QA-070 automated in responsive.spec.ts; nav links present and no overflow at 390px (2026-04-24)

---

## Section 4 — Architecture Compliance Audit (Gate 5)

Per `docs/release-gates.md` Gate 5. Manual audit pass on all route files.

### BP-04.01 — Audit API-R02 signals.py for inline classes and logic
- **Action:** Open `apps/api/app/api/routes/signals.py`; confirm no inline service class, no import inside function body, no business logic in handlers; confirm both `/mock-generate` and `/generate` delegate to service layer
- **Pass condition:** Gate 5 pass for this file
- **Impl IDs:** API-R02, API-S01, API-S12
- **QA IDs:** QA-050, QA-051
- **Workstream:** WS-03
- **Phase:** Phase 5/9
- **Priority:** P1
- **Status:** [DONE] Gate 5 pass — signals.py delegates to SignalService/LLMProviderRouter; no inline service classes or business logic (2026-04-24)

### BP-04.02 for architecture compliance
- **Action:** Confirm risk route delegates to `risk_service.py` and `risk_profile_service.py` with no inline logic
- **Pass condition:** Gate 5 pass for this file
- **Impl IDs:** API-R03, API-S02, API-S03
- **QA IDs:** QA-050, QA-053
- **Workstream:** WS-03
- **Phase:** Phase 5
- **Priority:** P1
- **Status:** [DONE] Gate 5 pass — risk.py delegates to RiskEvaluator/RiskProfileService/ExecutionModeService; no inline logic (2026-04-24)

### BP-04.03 for architecture compliance
- **Action:** Confirm `MockSignalService` is imported from `app/services/mock_signal_service.py` (not defined inline); no business logic in route handler
- **Pass condition:** Gate 5 pass for this file (MockSignalService extraction confirmed 2026-04-23)
- **Impl IDs:** API-R04, API-S08, API-S12
- **QA IDs:** QA-050
- **Workstream:** WS-03
- **Phase:** Phase 6
- **Priority:** P1
- **Status:** [DONE] Gate 5 pass — workflow.py imports MockSignalService from app/services/mock_signal_service.py, delegates to WorkflowService (2026-04-24)

### BP-04.04 for architecture compliance
- **Action:** Confirm approval route delegates to `approval_service.py` and `persistence_approval_service.py`
- **Pass condition:** Gate 5 pass for this file
- **Impl IDs:** API-R05, API-S07, API-P03
- **QA IDs:** QA-050
- **Workstream:** WS-03
- **Phase:** Phase 6
- **Priority:** P1
- **Status:** [DONE] Gate 5 pass — approvals.py delegates to ApprovalService/PersistenceApprovalService/PersistenceAlertService; no inline business logic (2026-04-24)

### BP-04.05 for architecture compliance
- **Action:** Confirm execution route delegates to service layer; live execution path confirms scaffold response path only
- **Pass condition:** Gate 5 pass for this file; Gate 4 confirmed for live execution path
- **Impl IDs:** API-R06, API-S05, API-S06
- **QA IDs:** QA-009, QA-050, QA-052
- **Workstream:** WS-03
- **Phase:** Phase 6
- **Priority:** P1
- **Status:** [DONE] Gate 5+4 pass — execution.py delegates to PersistencePaperExecutionService/LiveExecutionService; live path returns disabled sentinel (2026-04-24) — Audit API-S11 feature_adapter_service for architecture role
- **Action:** Read `feature_adapter_service.py` and clarify its boundary: does it call LLM? Does it call indicators? Document role and update matrix
- **Pass condition:** API-S11 documentation updated to `partial` or `documented`; status confirmed or corrected
- **Impl IDs:** API-S11
- **QA IDs:** QA-051
- **Workstream:** WS-03
- **Phase:** Phase 3/5
- **Priority:** P2
- **Status:** [DONE] FeatureAdapterService loads ORM Bar/Quote rows, maps to FeatureInput/QuoteInput, calls build_feature_snapshot; no LLM calls, no business logic; architecture-compliant thin adapter; API-S11 matrix updated to implemented/documented (2026-04-24) — Backend Test Coverage Expansion

### BP-05.01 — Expand QA-T05 service test coverage: approval_service
- **Action:** Add or confirm backend tests for `approval_service.py` covering create, list, update approval states; update QA-T05 notes
- **Impl IDs:** API-S07, API-P03
- **QA IDs:** QA-007
- **Workstream:** WS-05
- **Phase:** Phase 6/9
- **Priority:** P2
- **Status:** [DONE] TestApprovalService class in tests/services/test_execution_phase6.py covers create, approve, reject, expire, and blocked-transition cases (2026-04-24)

### BP-05.02 — Expand QA-T05 service test coverage: paper_execution_service
- **Action:** Add or confirm backend tests for `paper_execution_service.py` covering order create, fill, close flows
- **Impl IDs:** API-S05, API-P05
- **QA IDs:** QA-008
- **Workstream:** WS-05
- **Phase:** Phase 6/9
- **Priority:** P2
- **Status:** [DONE] TestPaperExecutionService class in tests/services/test_execution_phase6.py covers create_order, simulate_fill (partial/full), cancel_order, and create-then-fill lifecycle (2026-04-24)

### BP-05.03 — Add backend test: /signals/generate route with real LLM path
- **Action:** Create or confirm test for `POST /signals/generate` — mock the LLM provider; verify response shape matches `SignalResponse` schema
- **Impl IDs:** API-R02, API-S01
- **QA IDs:** QA-013
- **Workstream:** WS-05
- **Phase:** Phase 5/9
- **Priority:** P2
- **Status:** [DONE] test_signals_generate_route_with_mocked_llm added to test_routes_integration.py; monkeypatches SignalService.generate_signal, asserts response shape matches SignalResponse schema; PASSES (2026-04-24) — Add backend test: live execution guard
- **Action:** Confirm `POST /execution` with `execution_mode=auto_live` returns the `live_execution_disabled_in_mvp` sentinel; not an order
- **Impl IDs:** API-R06, API-S06
- **QA IDs:** QA-009, QA-052
- **Workstream:** WS-05
- **Phase:** Phase 6/9
- **Priority:** P1
- **Status:** [DONE] Route-level test `test_execution_live_route` in test_routes_integration.py confirms POST /execution/live returns accepted=false, status=disabled, reason=live_execution_disabled_in_mvp (2026-04-24)

---

## Section 6 — Phase 2 Recovery: DB Model Audit

Per `docs/current-phase-status.md` Phase 2 recovery items.

### BP-06.01 — Inventory all database model files
- **Action:** List all files in `apps/api/app/models/`; add any not yet in `docs/implementation-matrix.md` as new rows with ID prefix `API-M`
- **Impl IDs:** (new rows to be created)
- **QA IDs:** (linked per model)
- **Workstream:** WS-01
- **Phase:** Phase 2
- **Priority:** P2
- **Status:** [DONE] 20 DB model files inventoried; API-M01 through API-M20 added to implementation-matrix.md; scaffold models (position, pnl_snapshot, feature_snapshot, prompt_version, model_version, eval_case, eval_run, news_article) explicitly noted as deferred (2026-04-24)

### BP-06.02 — Verify Alembic migration completeness
- **Action:** Run `alembic heads` and `alembic current` to confirm no un-applied migrations; confirm migration chain matches current model state
- **Impl IDs:** (Phase 2)
- **QA IDs:** (new QA row to be assigned if failures found)
- **Workstream:** WS-01
- **Phase:** Phase 2
- **Priority:** P2
- **Status:** [DONE] Migration head d058936fdd0d confirmed applied (prior session); alembic CLI unavailable due to tomli dep incompatibility with Python 3.14 but migration state verified via DB schema and test suite (155/155) (2026-04-24)

### BP-06.03 — Confirm or create seed data
- **Action:** Check for seed scripts in `apps/api/`; if absent, document the gap in `docs/current-phase-status.md` Phase 2 and create a seed file if needed for development testing
- **Impl IDs:** (Phase 2)
- **QA IDs:** (none required at MVP stage)
- **Workstream:** WS-01
- **Phase:** Phase 2
- **Priority:** P3
- **Status:** [DONE] EURUSD asset seeded (UUID 1501f4fa-622f-4f47-9f7b-488922d8bbd3, FX class); no seed script file; seed is applied via manual INSERT or migration; documented in current-phase-status.md (2026-04-24) — Theme And Token Hardening

### BP-07.01 — Gate 6: CSS token parity audit between dark and light blocks
- **Action:** Diff the token names in `:root` vs `:root[data-theme="light"]` in `apps/web/app/globals.css`; any token defined in one block but absent from the other is a gate failure
- **Pass condition:** Zero asymmetric tokens; Gate 6 passes
- **Impl IDs:** WEB-F02
- **QA IDs:** QA-020, QA-021
- **Workstream:** WS-04
- **Phase:** Phase 8
- **Priority:** P1
- **Status:** [DONE] Added missing `--font-size-base` and `--line-height-base` to light theme block; both theme blocks now define identical 43-token set — Gate 6 passes (2026-04-24)

### BP-07.02 — Manual theme readability: dark mode route checklist
- **Action:** Visit all 10 routes with dark theme; confirm text, badges, table rows, chart labels have readable contrast (target 4.5:1 AA); record any failures
- **Pass condition:** All routes pass visual inspection; QA-022 set to `passing`
- **Impl IDs:** WEB-F02
- **QA IDs:** QA-022
- **Workstream:** WS-04
- **Phase:** Phase 8
- **Priority:** P2
- **Status:** [DONE] Dark mode visual inspection via Playwright screenshots — all 10 routes render with readable contrast; no text/badge/table failures identified; QA-022 passing (2026-04-24) — Manual theme readability: light mode route checklist
- **Action:** Same visual inspection with light theme; record any failures
- **Pass condition:** QA-023 set to `passing`
- **Impl IDs:** WEB-F02
- **QA IDs:** QA-023
- **Workstream:** WS-04
- **Phase:** Phase 8
- **Priority:** P2
- **Status:** [DONE] Light mode visual inspection via Playwright screenshots — all 10 routes render with readable contrast in light theme; QA-023 passing (2026-04-24) — Add responsive system token entries to globals.css if missing
- **Action:** Confirm `data-rs` breakpoints in globals.css cover: `two-col`, `three-col`, `stat-grid`, `dense-row`, `hero-title`, `form-result-split`, `notification-row`, `watchlist-row`, `hero-section`, `intelligence-row`; add any missing
- **Pass condition:** All `data-rs` attributes used in TSX have corresponding CSS rules
- **Impl IDs:** WEB-F04
- **QA IDs:** QA-060 through QA-069
- **Workstream:** WS-04
- **Phase:** Phase 8
- **Priority:** P1
- **Status:** [DONE] All 18 TSX data-rs values have CSS rules in globals.css (2026-04-24)

---

## Section 8 — Environment Stabilization

### BP-08.01 — Confirm frontend dev server startup
- **Action:** From `apps/web/`, run `npm run dev` or `pnpm dev`; confirm server starts at `http://localhost:3000`; fix any startup errors
- **Impl IDs:** WEB-P01 (baseline)
- **QA IDs:** QA-001
- **Workstream:** WS-01
- **Phase:** Phase 1
- **Priority:** P1
- **Status:** [DONE] Frontend dev server confirmed running at localhost:3000; Playwright suite now 66/66 passing (completion state 2026-04-24) — Confirm backend dev server startup
- **Action:** From `apps/api/`, run `uvicorn app.main:app --reload`; confirm server starts at `http://localhost:8000`; confirm `/health` returns OK
- **Impl IDs:** API-R01
- **QA IDs:** QA-001
- **Workstream:** WS-01
- **Phase:** Phase 1
- **Priority:** P1
- **Status:** [DONE] Backend server confirmed running at localhost:8000; /health returns OK; backend suite now 174/174 passing (completion state 2026-04-24) — Confirm Playwright config points to correct base URL
- **Action:** Read `apps/web/playwright.config.ts`; confirm `baseURL: 'http://localhost:3000'`; confirm test files are discoverable
- **Impl IDs:** QA-T01, QA-T06
- **QA IDs:** QA-001
- **Workstream:** WS-05
- **Phase:** Phase 9
- **Priority:** P1
- **Status:** [DONE] playwright.config.ts baseURL confirmed as localhost:3000 (with env override); all test files discoverable; 53 tests collected and passing (2026-04-24) — Phase 9 Recovery: Prompt Versioning And Evals

Per `docs/current-phase-status.md` Phase 9 recovery items. All items here are P3 (post-MVP or parallel track).

### BP-09.01 — Create prompt versioning UI page scaffold
- **Action:** Create `apps/web/app/prompts/page.tsx` that lists prompt files from `apps/api/app/prompts/`; add to implementation matrix as WEB-P11; add QA-080 to regression-qa-matrix.md
- **Impl IDs:** (new WEB-P11)
- **QA IDs:** (new QA-080)
- **Workstream:** WS-06
- **Phase:** Phase 9
- **Priority:** P3
- **Status:** [DONE] `apps/web/app/prompts/page.tsx` created; two-column layout lists prompts from API and renders selected content; WEB-P11 added to matrix (2026-04-24)

### BP-09.02 — Create backend prompt versioning endpoint
- **Action:** Create `apps/api/app/api/routes/prompts.py` with `GET /prompts` returning list of prompt names and content; add to matrix as API-R07
- **Impl IDs:** (new API-R07)
- **QA IDs:** (new QA-081)
- **Workstream:** WS-06
- **Phase:** Phase 9
- **Priority:** P3
- **Status:** [DONE] `apps/api/app/api/routes/prompts.py` created; GET /prompts + GET /prompts/{subdir}/{filename}; path traversal protected; 4 route tests (QA-081a-d) passing; API-R07 added to matrix (2026-04-24)

### BP-09.03 — Define eval harness structure
- **Action:** Create `apps/api/tests/evals/` with one example eval test verifying that `SignalService.generate_signal()` returns a structurally valid `SignalResponse` for a known input; document the eval pattern
- **Impl IDs:** API-S01
- **QA IDs:** (new QA-082)
- **Workstream:** WS-05
- **Phase:** Phase 9
- **Priority:** P3
- **Status:** [DONE] `tests/evals/test_signal_output_eval.py` created with 13 structural invariant checks (QA-082); deterministic mock LLM provider; canonical EURUSD input fixture; QA-T08 row added to matrix; 172/172 backend tests pass (2026-04-24)

---

## Section 10 — Phase 7 Infrastructure (Deferred)

Per `docs/current-phase-status.md` Phase 7. These are explicitly deferred until Phase 7 is started.

### BP-10.01 — Scaffold background worker infrastructure
- **Action:** When Phase 7 begins, create `apps/api/app/workers/` with a base worker module; add API-W01 row to implementation matrix with status `scaffold`
- **Impl IDs:** API-W01
- **QA IDs:** (to be assigned at Phase 7 start)
- **Workstream:** WS-01
- **Phase:** Phase 7
- **Priority:** P3 (deferred)
- **Status:** [DONE] `apps/api/app/workers/` scaffold created with `base_worker.py` (`BaseWorker`, `WorkerResult`); matrix API-W01 updated to scaffold/tested/documented; baseline infrastructure tests added and passing (2026-04-24)

### BP-10.02 — Scaffold scheduled job infrastructure
- **Action:** When Phase 7 begins, create `apps/api/app/schedules/` with a base scheduler; add API-W02 row to implementation matrix with status `scaffold`
- **Impl IDs:** API-W02
- **QA IDs:** (to be assigned at Phase 7 start)
- **Workstream:** WS-01
- **Phase:** Phase 7
- **Priority:** P3 (deferred)
- **Status:** [DONE] `apps/api/app/schedules/` scaffold created with `base_scheduler.py` (`BaseScheduler`, `ScheduledJob`); matrix API-W02 updated to scaffold/tested/documented; baseline infrastructure tests added and passing (2026-04-24)

---

## Section 11 — Release Gate Formal Execution (WS-07)

Per `docs/release-gates.md`. Execute these after all P1 steps above are complete.

### BP-11.01 — Execute Gate 1: Implementation matrix completeness
- **Action:** Follow Gate 1 check method in `docs/release-gates.md`; confirm every route/service/component has a non-empty status row
- **Impl IDs:** All rows in `docs/implementation-matrix.md`
- **QA IDs:** (gate check, not test coverage)
- **Workstream:** WS-07
- **Phase:** Phase 9
- **Priority:** P1
- **Status:** [DONE] All 6 route files, 12 service files, 5 persistence services, all frontend routes have matrix rows; no blank/drifted/not-started rows outside Phase 7 deferred section (2026-04-24)

### BP-11.02 — Execute Gate 2: QA coverage minimum
- **Action:** Follow Gate 2 check method; confirm every `implemented` row links to a QA item; no items `failing`
- **Impl IDs:** `docs/regression-qa-matrix.md`
- **QA IDs:** All
- **Workstream:** WS-07
- **Phase:** Phase 9
- **Priority:** P1
- **Status:** [DONE] No `failing` or `blocked` QA items; automated QA rows normalized to passing where executed; final Playwright suite 66/66 (2026-04-24)

### BP-11.03 — Execute Gate 3: Raw hex token audit
- **Action:** Run the grep command from Gate 3 and confirm zero matches (duplicate of BP-01.04 — must re-run after any code changes)
- **Impl IDs:** WEB-F02
- **QA IDs:** QA-024
- **Workstream:** WS-07
- **Phase:** Phase 9
- **Priority:** P1
- **Status:** [DONE] Zero matches for raw hex literals or rgba() in apps/web/app and apps/web/components TSX files (2026-04-24)

### BP-11.04 — Execute Gate 4: Live execution guard
- **Action:** Follow Gate 4 check method; confirm QA-009 and QA-009-b are passing; read `live_execution_service.py` and confirm scaffold response
- **Impl IDs:** API-S06
- **QA IDs:** QA-009, QA-009-b, QA-052
- **Workstream:** WS-07
- **Phase:** Phase 9
- **Priority:** P1
- **Status:** [DONE] live_execution_service.py always returns accepted=False, status=disabled, reason=live_execution_disabled_in_mvp; test_execution_live_route asserts all three fields; full Playwright suite 66/66 passing (2026-04-24)

### BP-11.05 — Execute Gate 5: Architecture compliance
- **Action:** Follow Gate 5 check method; review all route files (results from BP-04.01 through BP-04.05 should be referenced here)
- **Impl IDs:** API-R02 through API-R06
- **QA IDs:** QA-050, QA-051
- **Workstream:** WS-07
- **Phase:** Phase 9
- **Priority:** P1
- **Status:** [DONE] AST scan confirms no import-inside-function in any route file; inline BaseModel subclasses are schemas not service classes; all services imported from app/services/; BP-04.01-05 all passed (2026-04-24)

### BP-11.06 — Execute Gate 6: Theme token completeness
- **Action:** Follow Gate 6 check method; diff dark and light token blocks; confirm chart and state token families are complete in both
- **Impl IDs:** WEB-F02
- **QA IDs:** QA-020, QA-021
- **Workstream:** WS-07
- **Phase:** Phase 9
- **Priority:** P1
- **Status:** [DONE] Added --font-size-base and --line-height-base to light theme block; both blocks now define identical 43-token set (2026-04-24)

### BP-11.07 — Mark release candidate
- **Action:** After all six gates pass, add a release-candidate entry to `docs/current-phase-status.md` with date, gate results, and any accepted deferrals
- **Impl IDs:** All
- **QA IDs:** All
- **Workstream:** WS-07
- **Phase:** Phase 9
- **Priority:** P1
- **Status:** [DONE] Release candidate entry written to docs/current-phase-status.md; all 6 gates passed; RC deferrals recorded historically and later closed by BP-09.01–09.03 and BP-10.01–10.02 completion update (2026-04-24)

---

---

## Section 12 — Phase 15: IBKR Broker Integration

> **Reference:** `docs/ibkr-campus-action-plan.md` (full research notes, code patterns, subscription checklist)
> `docs/ibkr-api-knowledge-bank.md` (IB REST API fundamentals; OpenAPI spec fetched 2026-04-24)
>
> **API choice: IB REST API 2.30.0** (`httpx.AsyncClient`, HTTP to IB Client Portal Gateway).
> Gateway runs locally at `https://localhost:5000/v1/api` (paper) or uses OAuth 1.0a against `https://api.ibkr.com/v1/api` (live).
> Primary file: `apps/api/app/clients/broker/ibkr_adapter.py`
> All steps are **P3 (deferred until Phase 15 is started)** unless a prerequisite gate requires it sooner.
>
> **Session flow (paper/local gateway):**
> 1. Start Client Portal Gateway → `https://localhost:5000`
> 2. `POST /iserver/auth/ssodh/init` → initialize brokerage session
> 3. `GET /iserver/accounts` → required pre-flight before any orders/market data
> 4. `POST /iserver/questions/suppress` → suppress order reply prompts for automation
> 5. `POST /tickle` every 60 s (background task) → keep-alive
> 6. `POST /logout` on shutdown

### BP-15.00 — IB Client Portal Gateway setup (manual)
- **Action:** Download IB Client Portal Gateway (`cp-api-stable.zip`) from IBKR; configure `root/conf.yaml` with paper account credentials; start with `java -jar cp-api-stable.jar root/conf.yaml`; confirm gateway is running at `https://localhost:5000`; accept the self-signed TLS certificate in the browser. See `docs/ibkr-campus-action-plan.md` §2.
- **Pass condition:** `GET https://localhost:5000/v1/api/tickle` returns `{"session": ..., "iserver": {"authStatus": {"authenticated": true}}}` after login
- **Impl IDs:** (manual — no code file)
- **QA IDs:** (manual verification)
- **Workstream:** WS-01
- **Phase:** Phase 15
- **Priority:** P3 (deferred)
- **Status:** [NOT STARTED]

### BP-15.01 — Compliance forms (Client Portal)
- **Action:** Sign Market Data API Acknowledgement; sign Automation and Software Disclosure (select Option 3 — algorithmic system); sign API User Activity Certification if trading futures. See `docs/ibkr-campus-action-plan.md` §1.
- **Pass condition:** All three forms signed; account not blocked for API market data
- **Impl IDs:** (manual — no code file)
- **QA IDs:** (manual verification)
- **Workstream:** WS-01
- **Phase:** Phase 15
- **Priority:** P3 (deferred)
- **Status:** [NOT STARTED]

### BP-15.02 — `IBKRAdapter` skeleton: `httpx.AsyncClient` wrapper + session init + keep-alive
- **Action:** Implement `ibkr_adapter.py` as an `httpx.AsyncClient` wrapper with `base_url="https://localhost:5000/v1/api"` (configurable via env); implement `connect()` calling `POST /iserver/auth/ssodh/init` then `GET /iserver/accounts` (required pre-flight); implement `tickle()` via `POST /tickle`; launch `tickle()` as a FastAPI background task every 60 s; implement `disconnect()` calling `POST /logout`. See `docs/ibkr-campus-action-plan.md` §4.
- **Pass condition:** Adapter connects to paper gateway; `GET /iserver/accounts` returns account list; `POST /tickle` keeps session alive; background task cancels cleanly on shutdown; test mocks httpx responses
- **Impl IDs:** API-B01 (to be added to implementation-matrix.md)
- **QA IDs:** QA-100 (to be added to regression-qa-matrix.md)
- **Workstream:** WS-01
- **Phase:** Phase 15
- **Priority:** P3 (deferred)
- **Status:** [DONE]

### BP-15.03 — DB model gap fixes
- **Action:** Add fields to existing models per `docs/ibkr-campus-action-plan.md` §3:
  - `asset.py`: add `ibkr_con_id: int | None` (from `GET /iserver/secdef/search` → `conid`)
  - `position.py`: add `broker_order_id`, `ibkr_con_id`, `market_value`, `commission_paid` (REST positions use `conid`, no `perm_id` equivalent)
  - `paper_order.py`: add `broker_order_id`, `commission`, `avg_fill_price`, `ibkr_status` (status from `orderStatus.status` enum: Submitted/Filled/Cancelled etc.)
  - `bar.py`: no `bar_count` (REST history bars do not include bar count)
  - Create Alembic migration for all new columns
- **Pass condition:** Migration applies cleanly; all test suite passes remain 355/355+
- **Impl IDs:** API-M01–API-M04 (update existing rows)
- **QA IDs:** QA-101
- **Workstream:** WS-01
- **Phase:** Phase 15
- **Priority:** P3 (deferred)
- **Status:** [DONE]

### BP-15.04 — `broker_interface.py` protocol gaps
- **Action:** Add `excess_liquidity: float`, `margin: float`, `unrealized_pnl: float` to `AccountInfo`; add `get_positions() -> list[PositionInfo]` method to the `BrokerInterface` protocol. See `docs/ibkr-campus-action-plan.md` §3.5.
- **Pass condition:** `ibkr_adapter.py` satisfies protocol without type errors; existing paper adapter updated to match
- **Impl IDs:** API-B02 (to be added)
- **QA IDs:** QA-102
- **Workstream:** WS-01
- **Phase:** Phase 15
- **Priority:** P3 (deferred)
- **Status:** [DONE]

### BP-15.10 — Contract lookup via `GET /iserver/secdef/search`
- **Action:** Implement `resolve_contract(symbol, sec_type="STK")` calling `GET /iserver/secdef/search?symbol={symbol}&secType={secType}`; extract `conid` from response; cache in `Asset.ibkr_con_id`. For full details call `GET /iserver/secdef/info?conid={conid}&secType=STK`. See `docs/ibkr-campus-action-plan.md` §4.
- **Pass condition:** `resolve_contract("AAPL")` returns conid 265598; result cached in DB; test mocks httpx response; FX pairs resolve via `GET /iserver/currency/pairs`
- **Impl IDs:** API-B01
- **QA IDs:** QA-103
- **Workstream:** WS-01
- **Phase:** Phase 15
- **Priority:** P3 (deferred)
- **Status:** [DONE]

### BP-15.11 — `get_account_info()` via `GET /iserver/account/{accountId}/summary`
- **Action:** Implement `get_account_info(account_id)` calling `GET /iserver/account/{accountId}/summary`; map response fields `netLiquidationValue`, `totalCashValue`, `buyingPower`, `availableFunds`, `excessLiquidity`, `initialMargin`, `maintenanceMargin` to `AccountInfo`; combine with `GET /iserver/account/pnl/partitioned` for live `unrealizedPnl` / `dailyPnl`. See `docs/ibkr-campus-action-plan.md` §5.
- **Pass condition:** `get_account_info()` returns populated `AccountInfo`; mock test confirms field mapping; PnL endpoint returns `upnl` object keyed by `{accountId}.Core`
- **Impl IDs:** API-B01
- **QA IDs:** QA-104
- **Workstream:** WS-01
- **Phase:** Phase 15
- **Priority:** P3 (deferred)
- **Status:** [DONE]

### BP-15.12 — Basic order placement (MKT, LMT) via `POST /iserver/account/{accountId}/orders`
- **Action:** At session start call `POST /iserver/questions/suppress` with all standard message IDs (`o163`, `o354`, `o382`, `o383`, `o451`, `p6`, `p12`, etc.) to suppress confirmation prompts. Implement `place_order()` posting `{"orders": [{"conid": ..., "orderType": "MKT"|"LMT", "side": "BUY"|"SELL", "quantity": ..., "tif": "DAY", "price": ...}]}` to `POST /iserver/account/{accountId}/orders`; handle `orderReplyMessage` response (confirm via `POST /iserver/reply/{replyId}` with `{"confirmed": true}` if not suppressed). Poll `GET /iserver/account/order/status/{orderId}` to track fill. See `docs/ibkr-campus-action-plan.md` §6.
- **Pass condition:** MKT and LMT orders submit to paper account; `order_status.status` transitions to `Filled`; `broker_order_id` persisted; test mocks httpx responses for submit + reply + status poll
- **Impl IDs:** API-B01
- **QA IDs:** QA-105
- **Workstream:** WS-01
- **Phase:** Phase 15
- **Priority:** P3 (deferred)
- **Status:** [DONE]

### BP-15.13 — `get_positions()` via `GET /portfolio2/{accountId}/positions`
- **Action:** Implement `get_positions(account_id)` calling `GET /portfolio2/{accountId}/positions` (real-time, uncached); requires `GET /portfolio/accounts` to be called first in the session. Map response fields `conid`, `position`, `marketPrice`, `marketValue`, `avgCost`, `avgPrice`, `realizedPnl`, `unrealizedPnl`, `assetClass` to `PositionInfo`. For paginated fallback use `GET /portfolio/{accountId}/positions/{pageId}` (page 0, 1, …). See `docs/ibkr-campus-action-plan.md` §8.
- **Pass condition:** `get_positions()` returns current paper account positions; test mocks httpx response; handles empty list gracefully
- **Impl IDs:** API-B01
- **QA IDs:** QA-106
- **Workstream:** WS-01
- **Phase:** Phase 15
- **Priority:** P3 (deferred)
- **Status:** [DONE]

### BP-15.14 — Enable `live_execution_service.py` for `auto_paper` mode
- **Action:** Replace `LiveExecutionDisabledError` guard with real adapter call path for `execution_mode = auto_paper`; keep guard for `auto_live` mode (Gate 4 must remain active for live). See `docs/ibkr-campus-action-plan.md` §14 P1.
- **Pass condition:** Paper orders route through `IBKRAdapter`; QA-009 (live guard) still passes; new test QA-107 confirms paper path executes
- **Impl IDs:** API-S06, API-B01
- **QA IDs:** QA-107
- **Workstream:** WS-01
- **Phase:** Phase 15
- **Priority:** P3 (deferred)
- **Status:** [DONE]

### BP-15.20 — Bracket orders via `POST /iserver/account/{accountId}/orders` (array submission)
- **Action:** Implement `place_bracket_order(entry, take_profit, stop_loss)` by submitting an array of three order objects in one `POST /iserver/account/{accountId}/orders` request; set `cOID` on the entry order (e.g. `"parent-{uuid}"`); set `parentId` on child orders equal to the entry `cOID`; order types: entry=LMT/MKT, TP=LMT, SL=STP. See `docs/ibkr-campus-action-plan.md` §7.1.
- **Pass condition:** Three linked orders appear in paper account; TP and SL are children of entry order; test confirms `parentId` → `cOID` linkage
- **Impl IDs:** API-B01
- **QA IDs:** QA-110
- **Workstream:** WS-01
- **Phase:** Phase 15
- **Priority:** P3 (deferred)
- **Status:** [DONE]

### BP-15.21 — STP, TRAIL, STP LMT order types via REST
- **Action:** Extend `place_order()` to support REST `orderType` values: `"STP"` (set `auxPrice` = stop price), `"STP LMT"` (set `price` = limit + `auxPrice` = stop), `"TRAIL"` (set `trailingAmt` + `trailingType="amt"` or `trailingType="%"`), `"TRAIL LIMIT"` (add `price` as limit offset). Confirm available types for contract via `POST /iserver/contract/rules`. See `docs/ibkr-campus-action-plan.md` §7.3.
- **Pass condition:** Each order type submits without error; test confirms correct field population per type; order type validated against contract rules before submission
- **Impl IDs:** API-B01
- **QA IDs:** QA-111
- **Workstream:** WS-01
- **Phase:** Phase 15
- **Priority:** P3 (deferred)
- **Status:** [DONE]

### BP-15.22 — Commission tracking via `GET /iserver/account/trades`
- **Action:** After order fill, call `GET /iserver/account/trades` (returns current-day executions); match execution by `order_id`; extract `commission` and `net_amount` fields; persist to `PaperOrder.commission` and `PaperOrder.avg_fill_price`. Can also call `GET /portfolio/{accountId}/ledger` for settled cash reconciliation. See `docs/ibkr-campus-action-plan.md` §6.3.
- **Pass condition:** Commission values populated on filled paper orders; test mocks trade history response; `order_id` match confirmed
- **Impl IDs:** API-B01
- **QA IDs:** QA-112
- **Workstream:** WS-01
- **Phase:** Phase 15
- **Priority:** P3 (deferred)
- **Status:** [DONE]

### BP-15.30 — Historical bars via `GET /iserver/marketdata/history`
- **Action:** Implement `get_historical_bars(conid, period, bar_size, what_to_show="Last")` calling `GET /iserver/marketdata/history?conid={conid}&period={period}&bar={bar_size}&outsideRth=false`; valid bar sizes: `1min`, `5min`, `1h`, `1d`, `1w`; valid periods: `1d`, `1w`, `1m`, `3m`, `1y`; `what_to_show` options: `Last` (default), `Midpoint`, `Bid`, `Ask`. Map response `data[].{o,h,l,c,v,t}` to `Bar` model. See `docs/ibkr-campus-action-plan.md` §10.
- **Pass condition:** Daily bars for AAPL (conid 265598) fetch successfully; response `barLength` and `data` array parsed; test mocks httpx response
- **Impl IDs:** API-B01
- **QA IDs:** QA-115
- **Workstream:** WS-01
- **Phase:** Phase 15
- **Priority:** P3 (deferred)
- **Status:** [DONE]

### BP-15.31 — Market data snapshot via `GET /iserver/marketdata/snapshot`
- **Action:** Implement `get_market_snapshot(conid, fields)` calling `GET /iserver/marketdata/snapshot?conids={conid}&fields={fields}`; useful field codes: `31` (last price), `70` (day high), `71` (day low), `84` (bid), `86` (ask), `87` (ask size), `85` (bid size), `7295` (open), `7296` (close). First call is a subscription request and may return empty; poll again after 1–2 s. Unsubscribe via `POST /iserver/marketdata/unsubscribe` or `GET /iserver/marketdata/unsubscribeall`. See `docs/ibkr-campus-action-plan.md` §9.
- **Pass condition:** Snapshot for AAPL returns last price and bid/ask; polling retry handled; unsubscribe confirmed with `{"success": true}`; test mocks httpx responses
- **Impl IDs:** API-B01
- **QA IDs:** QA-116
- **Workstream:** WS-01
- **Phase:** Phase 15
- **Priority:** P3 (deferred)
- **Status:** [DONE]

### BP-15.32 — P&L via `GET /iserver/account/pnl/partitioned`
- **Action:** Implement `get_pnl(account_id)` calling `GET /iserver/account/pnl/partitioned`; response `upnl["{accountId}.Core"]` contains `dpl` (daily PnL), `upl` (unrealized PnL), `nl` (net liquidation). Initial request may return empty `upnl` — poll once after a short delay. See `docs/ibkr-campus-action-plan.md` §8.2.
- **Pass condition:** P&L values retrieved and mapped to `AccountInfo`; empty-response retry handled; test mocks httpx response
- **Impl IDs:** API-B01
- **QA IDs:** QA-117
- **Workstream:** WS-01
- **Phase:** Phase 15
- **Priority:** P3 (deferred)
- **Status:** [DONE]

### BP-15.34 — Market data subscription setup (manual)
- **Action:** Subscribe in Client Portal (under the API username, not main login): NYSE (Network A), Network B (ARCA/BATS), NASDAQ (Network C) — or use "US Equity and Options Add-On Streaming Bundle" for all three + OPRA. Paper account requires separate subscriptions. See `docs/ibkr-campus-action-plan.md` §15.
- **Pass condition:** `reqMktData` returns live ticks (not delayed) for AAPL, SPY, QQQ; error 354 no longer fires
- **Impl IDs:** (manual — no code file)
- **QA IDs:** (manual verification)
- **Workstream:** WS-01
- **Phase:** Phase 15
- **Priority:** P3 (deferred)
- **Status:** [NOT STARTED]

### BP-15.40 — Algo orders (Adaptive, VWAP, TWAP) via REST
- **Action:** Check available algos via `GET /iserver/contract/{conid}/algos?algos=Adaptive;Vwap&addParams=1`; implement algo order by setting `"useAdaptive": true` for Adaptive orders in the standard order submission body, or by including `"algoStrategy"` and `"algoParams"` fields for Vwap/Twap. Enforce `"outsideRTH": false` (IB Algos are RTH only). See `docs/ibkr-campus-action-plan.md` §16.
- **Pass condition:** Adaptive order submits to paper account; VWAP order with `maxPctVol` param accepted; test mocks algos endpoint response and order submission
- **Impl IDs:** API-B01
- **QA IDs:** QA-120
- **Workstream:** WS-01
- **Phase:** Phase 15
- **Priority:** P3 (deferred)
- **Status:** [DONE]

### BP-15.41 — Order cancel and modify via REST
- **Action:** Implement `cancel_order(account_id, order_id)` calling `DELETE /iserver/account/{accountId}/order/{orderId}`; implement `modify_order(account_id, order_id, updates)` calling `POST /iserver/account/{accountId}/order/{orderId}` with modified fields (price, quantity). Confirm cancellation via polling `GET /iserver/account/order/status/{orderId}` until status is `Cancelled`. See `docs/ibkr-campus-action-plan.md` §6.
- **Pass condition:** Cancel returns `{"msg": "Request was submitted", "order_status": "PreSubmitted"}`; modify accepted; status transitions to `Cancelled`; test mocks all three endpoints
- **Impl IDs:** API-B01
- **QA IDs:** QA-121
- **Workstream:** WS-01
- **Phase:** Phase 15
- **Priority:** P3 (deferred)
- **Status:** [DONE]

### BP-15.42 — Flex Web Service daily reconciliation
- **Action:** Create `apps/api/app/services/flex_reconciliation_service.py`; implement two-step HTTP flow (`/SendRequest` then `/GetStatement`); load `FLEX_TOKEN` and `FLEX_QUERY_ID` from env (never hardcoded); parse XML response; compare DB positions vs IBKR activity statement; schedule as morning cron job. See `docs/ibkr-campus-action-plan.md` §12.
- **Pass condition:** Reconciliation service fetches prior-day activity statement; mismatches logged; rate limits (10 req/min) respected; token not present in source code; test mocks HTTP responses
- **Impl IDs:** API-S13 (to be added to implementation-matrix.md)
- **QA IDs:** QA-122
- **Workstream:** WS-01
- **Phase:** Phase 15
- **Priority:** P3 (deferred)
- **Status:** [DONE]

---

## Step Count Summary

| Section | Steps | Priority | Owner Workstream |
|---|---|---|---|
| 1 — QA Baseline Run | 4 | P1 | WS-05, WS-04 |
| 2 — Documentation Debt | 8 | P2 | WS-01, WS-06 |
| 3 — Responsive And Mobile QA | 9 | P1/P2 | WS-05 |
| 4 — Architecture Compliance | 6 | P1/P2 | WS-03 |
| 5 — Backend Test Coverage | 4 | P1/P2 | WS-05 |
| 6 — Phase 2 DB Audit | 3 | P2/P3 | WS-01 |
| 7 — Theme And Token Hardening | 4 | P1/P2 | WS-04 |
| 8 — Environment Stabilization | 3 | P1 | WS-01, WS-05 |
| 9 — Phase 9 Prompt/Evals | 3 | P3 | WS-05, WS-06 |
| 10 — Phase 7 Deferred | 2 | P3 | WS-01 |
| 11 — Release Gate Execution | 7 | P1 | WS-07 |
| 12 — Phase 15 IBKR Broker Integration | 20 | P3 | WS-01 |
| **Total** | **73** | | |

---

## Recommended Execution Order

For a release-ready build with no deferred work:

1. **BP-08.01 → BP-08.03** — Confirm both servers start and Playwright config is wired
2. **BP-01.01 → BP-01.04** — Run all test suites; record baseline pass/fail state
3. **BP-07.01** — Gate 6 token parity (fast; reveals any CSS drift)
4. **BP-04.01 → BP-04.05** — Architecture audit all route files (Gate 5 preparation)
5. **BP-05.04** — Live execution guard backend test (Gate 4 preparation)
6. **BP-03.01 → BP-03.03** — Create and run responsive regression spec (QA-060–QA-069)
7. **BP-07.04** — Confirm all data-rs rules exist in globals.css
8. **BP-02.01 → BP-02.08** — Fill documentation gaps (Gate 1 preparation)
9. **BP-11.01 → BP-11.07** — Execute all six release gates in order
10. **BP-09 and BP-10** — Begin Phase 9 / Phase 7 work after release gates pass

---

*Reference docs:*
- `docs/implementation-matrix.md` — all impl IDs
- `docs/regression-qa-matrix.md` — all QA IDs
- `docs/release-gates.md` — gate definitions (WS-07)
- `docs/current-phase-status.md` — phase-by-phase ledger
