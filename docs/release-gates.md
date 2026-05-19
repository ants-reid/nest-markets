# Release Gates

Date: 2026-04-23
Workstream: WS-07

## Purpose

This document defines what "done" means before any code crosses from development to a shared or staged environment.

Every gate must pass before a release. Each gate has a check method, a responsible artifact, and a clear pass/fail condition.

## Verification Snapshot — 2026-05-19

Current release-gate status after MH-RESTART-004:

| Gate | Result | Fresh evidence |
|---|---|---|
| Gate 1 — Implementation Matrix Completeness | PASS | `docs/implementation-matrix.md` was reconciled to the live Gate 1 surface and now covers 39 active backend route modules, 81 active backend service modules, 46 frontend route modules, and 49 shared TSX component modules, with excluded/supporting surfaces explicitly documented |
| Gate 2 — QA Coverage Minimum | PASS | `docs/regression-qa-matrix.md` was extended to link the newly inventoried `API-RX*` and `WEB-PX*` surfaces, and fresh browser validation ended `272 passed, 0 failed` |
| Gate 3 — Raw Hex Token Audit | PASS | Regex scan over `apps/web/app/**/*.tsx` and `apps/web/components/**/*.tsx` found no raw `#rrggbb` or `rgb()/rgba()` literals in TSX surfaces after the token cleanup |
| Gate 4 — Live Execution Guard | PASS | `QA-009-b` passed on 2026-05-19 and live execution still returns the disabled scaffold response |
| Gate 5 — Architecture Compliance | PASS | Route-wide grep found no import statements inside function bodies in `apps/api/app/api/routes/` after the broker-route hygiene fix |
| Gate 6 — Theme Token Completeness | PASS | `apps/web/app/globals.css` defines the same token set in `:root` and `:root[data-theme="light"]` |
| Gate 7 — Broker Call Isolation | PASS | Concrete `IBKRAdapter` imports and constructor dependencies were removed from service and route files outside the broker client layer; broker-facing services now depend on broker protocols from `app/clients/broker/broker_interface.py` |
| Gate 8 — Market Data Call Isolation | PASS | Fresh grep hits were limited to broker-gateway/Flex HTTP helpers and a `Polygon.io` label string; no direct market-data HTTP call was identified outside the client layer |
| Gate 9 — Worker And Scheduler Compliance | PASS | Scheduler silence check remained green under pytest and targeted RC2 checks stayed green on 2026-05-19 |

RC-2 status on the same evidence set:

| Gate | Result | Fresh evidence |
|---|---|---|
| RC2-Gate 1 — Backend Test Suite | PASS | `cd apps/api && .venv/bin/python -m pytest tests/ -q` → `2301 passed` |
| RC2-Gate 2 — Playwright E2E Suite | PASS | `cd apps/web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3000 ./node_modules/.bin/playwright test --reporter=line` → `272 passed`, `0 failed` |
| RC2-Gate 3 — APScheduler silent during pytest | PASS | `cd apps/api && .venv/bin/python -m pytest tests/ -q 2>&1 | grep -i scheduler` returned no output |
| RC2-Gate 4 — Prompt Version Seeding idempotent | PASS | `tests/services/test_prompt_version_service.py` → `9 passed` |
| RC2-Gate 5 — News ingest graceful degradation | PASS | `tests/test_news_ingest.py` → `7 passed` |
| RC2-Gate 6 — IBKR scaffold safety | PASS | `tests/test_ibkr_scaffold.py` → `6 passed` |

Current release verdict: all release gates and RC-2 gates are green on fresh evidence. Market Hunter is now a release-ready candidate, not just safe for controlled feature work.

---

## Gate 1 — Implementation Matrix Completeness

**Check method:** Open `docs/implementation-matrix.md`.

**Pass condition:**

- Every active backend route, backend service, frontend route, and shared component has a row with a non-empty status.
- No row has status `not started` unless explicitly deferred in the Phase 7 Infrastructure section.
- All rows added since the last release are dated in their notes field.

**Fail condition:**

- Any new file present in `apps/api/app/api/routes/`, `apps/api/app/services/`, or `apps/web/app/` without a matrix row.
- Any row with status blank or `drifted`.

**Artifacts:** `docs/implementation-matrix.md`

---

## Gate 2 — QA Coverage Minimum

**Check method:** Open `docs/regression-qa-matrix.md`.

**Pass condition:**

- Every backend route row in the implementation matrix links to at least one QA item.
- Every frontend route row links to at least one QA item.
- No QA item has status `failing` or `blocked`.
- Automated QA items are confirmed passing (`pending run` is acceptable if the test suite has been run and passed in the current branch).

**Fail condition:**

- Any feature marked `implemented` in the implementation matrix without a corresponding QA item.
- Any QA item status `failing`.

**Artifacts:** `docs/regression-qa-matrix.md`, `apps/web/tests/regression.spec.ts`, `apps/web/tests/smoke.spec.ts`

---

## Gate 3 — Raw Hex Token Audit

**Check method:** Run a regex scan over all TSX files in `apps/web/app/` and `apps/web/components/`:

```
grep -rn '#[0-9A-Fa-f]\{3,6\}\b' apps/web/app apps/web/components --include="*.tsx"
grep -rn 'rgba\?\s*(' apps/web/app apps/web/components --include="*.tsx"
```

**Pass condition:**

- Zero matches for raw `#rrggbb` or `rgb()/rgba()` literals in inline styles.
- All color values use `var(--token-name)` from `apps/web/app/globals.css`.
- `color-mix(in oklab, var(...))` pattern is acceptable for derived opacity values.

**Fail condition:**

- Any match for a raw hex literal or inline `rgb()/rgba()` call in a `.tsx` file.

**Artifacts:** `apps/web/app/globals.css`, all `.tsx` component and page files

---

## Gate 4 — Live Execution Guard

**Check method:** Review `apps/api/app/services/live_execution_service.py` and the execution route.

**Pass condition:**

- `live_execution_service.py` returns a scaffold/disabled response for all live execution calls.
- The frontend execution page renders the disabled-mode guard state.
- Smoke test `QA-009` (live execution remains disabled) is passing.
- No route accepts `auto_live` execution mode and produces a real order.

**Fail condition:**

- Any code path that can route a real order to a live broker without explicit operator confirmation.
- `QA-009` or `QA-009-b` failing or removed.

**Artifacts:** `apps/api/app/services/live_execution_service.py`, `apps/web/app/execution/page.tsx`, `apps/web/tests/smoke.spec.ts`, `apps/web/tests/regression.spec.ts`

---

## Gate 5 — Architecture Compliance

**Check method:** Audit route files in `apps/api/app/api/routes/`.

**Pass condition:**

- No route file defines an inline service class or contains business logic beyond request parsing, service dispatch, and response serialization.
- All services are imported from `apps/api/app/services/`.
- No `from app.schemas.X import Y` imports are buried inside function bodies.
- Mock implementations live in `app/services/` not in route files.

**Fail condition:**

- Any inline class definition in a route file.
- Any import statement inside a function body.
- Business logic (conditional branching, data transformation, policy decisions) directly in a route handler.

**Artifacts:** All files in `apps/api/app/api/routes/`

---

## Gate 6 — Theme Token Completeness

**Check method:** Open `apps/web/app/globals.css`.

**Pass condition:**

- Both `:root` (dark default) and `:root[data-theme="light"]` blocks define the same set of CSS custom property names.
- All tokens used in TSX files exist as named entries in `globals.css`.
- Chart series tokens (`--chart-series-1` through `--chart-series-6`) are defined in both theme blocks.
- State tokens (`--state-success`, `--state-danger`, `--state-warning`, `--state-info`) and their `-soft`/`-border` variants are defined in both blocks.

**Fail condition:**

- A CSS custom property referenced in a TSX file that is not defined in `globals.css`.
- A token defined in `:root` but missing from `:root[data-theme="light"]` (or vice versa), causing a theme-switch regression.

**Artifacts:** `apps/web/app/globals.css`, all `.tsx` files using `var(--...)` tokens

---

## Gate 7 — Broker Call Isolation

**Check method:** Search service and route files for direct broker integration usage outside `clients/broker/`.

```
grep -RniE 'ibkr|tws|ib_insync|place_order|cancel_order' apps/api/app/services apps/api/app/api/routes
```

**Pass condition:**

- No direct broker SDK or adapter calls appear outside the broker client layer.
- Services depend on `BrokerInterface` rather than a concrete broker SDK.

**Fail condition:**

- Any direct IBKR/TWS/broker call in a service or route file.

**Artifacts:** `apps/api/app/clients/broker/`, `apps/api/app/services/`, `apps/api/app/api/routes/`

---

## Gate 8 — Market Data Call Isolation

**Check method:** Search for direct market-data HTTP calls outside `clients/market_data/`.

```
grep -RniE 'polygon.io|httpx\.|requests\.' apps/api/app/services apps/api/app/api/routes
```

**Pass condition:**

- External market-data HTTP calls are contained within the market-data client layer.
- Routes and services depend on client/service abstractions instead of raw HTTP.

**Fail condition:**

- Any direct market-data HTTP call in a route or service file.

**Artifacts:** `apps/api/app/clients/market_data/`, `apps/api/app/services/`, `apps/api/app/api/routes/`

---

## Gate 9 — Worker And Scheduler Compliance

**Check method:** Review files in `app/workers/` and `app/schedules/`.

**Pass condition:**

- Every concrete worker subclasses `BaseWorker`.
- Every scheduler registry subclasses `BaseScheduler`.
- Scheduler startup registers only declared jobs and remains disabled when `APP_ENV=test`.

**Fail condition:**

- Any worker or scheduler bypasses the shared base classes.
- Test environment starts background jobs.

**Artifacts:** `apps/api/app/workers/`, `apps/api/app/schedules/`, `apps/api/app/main.py`

---

## Pre-Release Checklist

Before marking any release ready:

- [x] Gate 1 passed — implementation matrix complete with no undated new rows
- [x] Gate 2 passed — QA matrix linked and no failing items
- [x] Gate 3 passed — raw hex scan returns zero matches
- [x] Gate 4 passed — live execution guard confirmed active, QA-009/QA-009-b passing
- [x] Gate 5 passed — no business logic or inline classes in route files
- [x] Gate 6 passed — CSS token set consistent across both theme blocks

---

## Gate Failure Response

If a gate fails:

1. File a note in the relevant workstream section of `docs/current-phase-status.md`.
2. Add or update the row in `docs/implementation-matrix.md` with a `drifted` status.
3. Block the release until the gate is re-run and passes.

Do not override or bypass gates. Gates exist because these failure modes have occurred previously.

---

## RC-2 Specific Gates

These gates must pass before the RC-2 tag is cut.

---

### RC2-Gate 1 — Backend Test Suite ≥ 249 passing, 0 failing

**Check method:** Run the full pytest suite:

```
cd apps/api && .venv/bin/python -m pytest tests/ -q
```

**Pass condition:**

- All tests pass. 0 failures, 0 errors.
- Test count ≥ 249 (the count at the end of Build Plan 2 execution).

**Fail condition:**

- Any test failure or error.
- Test count below 249.

---

### RC2-Gate 2 — Playwright E2E Suite ≥ 70 passing, 0 failing

**Check method:** Run the full Playwright suite from `apps/web/`:

```
cd apps/web && npx playwright test --reporter=dot
```

**Pass condition:**

- All E2E tests pass. 0 failures.
- Test count ≥ 70.

**Fail condition:**

- Any Playwright test failure.

---

### RC2-Gate 3 — APScheduler does not start during pytest

**Check method:** Run the test suite with verbose output and confirm no `APScheduler` log lines appear:

```
cd apps/api && .venv/bin/python -m pytest tests/ -q 2>&1 | grep -i scheduler
```

**Pass condition:**

- Zero lines output (the grep finds nothing).

**Fail condition:**

- Any APScheduler log line in the test output, indicating the scheduler
  started during tests (violates the `APP_ENV=test` guard).

---

### RC2-Gate 4 — Prompt Version Seeding is idempotent

**Check method:** Run `test_prompt_version_service.py` twice in succession:

```
cd apps/api && .venv/bin/python -m pytest tests/services/test_prompt_version_service.py -v
```

**Pass condition:**

- All tests pass both runs. The idempotency test (`test_seed_prompt_versions_idempotent_no_change`) must pass.

---

### RC2-Gate 5 — News ingest worker degrades gracefully with no API key

**Check method:** Run `test_news_ingest.py`:

```
cd apps/api && .venv/bin/python -m pytest tests/test_news_ingest.py -v
```

**Pass condition:**

- `test_placeholder_client_returns_empty` passes — no articles returned when no key is set.
- `test_news_ingest_worker_placeholder_no_new_rows` passes — no DB writes attempted.

---

### RC2-Gate 6 — IBKR scaffold raises NotImplementedError for all live calls

**Check method:** Run `test_ibkr_scaffold.py`:

```
cd apps/api && .venv/bin/python -m pytest tests/test_ibkr_scaffold.py -v
```

**Pass condition:**

- All three scaffold tests (`test_submit_order_raises_not_implemented`,
  `test_cancel_order_raises_not_implemented`, `test_get_account_info_raises_not_implemented`)
  pass — confirming no live trades can be accidentally routed through this adapter.

**Fail condition:**

- Any of those three tests not raising `NotImplementedError`.

---

## RC-2 Pre-Release Checklist

- [ ] RC2-Gate 1 passed — ≥ 249 backend tests passing
- [ ] RC2-Gate 2 passed — ≥ 70 Playwright E2E tests passing
- [ ] RC2-Gate 3 passed — APScheduler silent during pytest
- [ ] RC2-Gate 4 passed — prompt version seeding is idempotent
- [ ] RC2-Gate 5 passed — news worker degrades gracefully without key
- [ ] RC2-Gate 6 passed — IBKR scaffold raises NotImplementedError safely

---

## Build Plan 3 Gates (RC-3)

Three new gates are added for the multi-asset, auto-paper-trader, and AI learning loop work.
Gates 1–9 from RC-1 and RC-2 remain in force.

---

### Gate 10 — Auto Paper Trade Risk Isolation

**Purpose:** Confirm that the auto paper trader never opens a position without first passing
through the risk evaluator. Prevents the scheduler from bypassing the risk gate.

**Check method:**

```bash
# Confirm every auto-paper execution path calls RiskEvaluator before creating an order
grep -rn "auto_paper\|AutoPaperTraderWorker" apps/api/app --include="*.py" | grep -v test
```

Trace each result: the call chain must include `RiskEvaluator.evaluate()` before any
`PaperExecutionService.create_order()` call.

**Automated check:**
```bash
cd apps/api && .venv/bin/python -m pytest tests/ -k "auto_paper" -v
```

**Pass condition:**
- QA-210, QA-211, QA-212 all passing.
- No auto-paper position exists in test DB without a `risk_approved` or `auto_approved` signal status.
- `AUTO_PAPER_MAX_OPEN_POSITIONS` cap enforced (QA-214 passing).

**Fail condition:**
- Any auto-paper order created without `RiskEvaluator` being called first.
- Position count cap test (QA-214) failing.

---

### Gate 11 — Prompt Version Immutability

**Purpose:** Confirm that the AI learning loop never overwrites an existing prompt.
All prompt changes must produce a new `PromptVersion` row with an incremented version number.
This makes every prompt change auditable and reversible.

**Check method:**

```bash
# Confirm no service updates the prompt_text field on an existing row
grep -rn "prompt_text\s*=" apps/api/app/services --include="*.py"
```

Every match must be an INSERT-path (ORM object creation), not an UPDATE.
If any match is a `.prompt_text = ` reassignment on a fetched ORM object, that is a gate failure.

**Automated check:**
```bash
cd apps/api && .venv/bin/python -m pytest tests/ -k "prompt_version or adaptation" -v
```

**Pass condition:**
- QA-221 and QA-222 both passing.
- `PromptVersion` row count increases by exactly 1 after each `apply` call (no duplicates, no overwrites).
- Old version rows remain in DB with their original `prompt_text` intact.

**Fail condition:**
- Any `.prompt_text` field updated on an existing ORM row.
- `PromptVersion` row count unchanged after an apply call.

---

### Gate 12 — Polygon Rate Limit Compliance

**Purpose:** Confirm that all market data access in workers routes through the `PolygonClient`
and never makes raw HTTP calls. This ensures rate limiting, error handling, and key management
are centralised.

**Check method:**

```bash
# Confirm no direct HTTP library usage in worker files
grep -rn "httpx\|requests\|aiohttp\|urllib" apps/api/app/workers --include="*.py"
grep -rn "api.polygon.io" apps/api/app --include="*.py" | grep -v "clients/market_data"
```

**Pass condition:**
- Zero matches for raw HTTP calls in `apps/api/app/workers/`.
- Zero direct `api.polygon.io` references outside `apps/api/app/clients/market_data/`.
- QA-205 passing (sweep worker uses PolygonClient mock in tests).

**Fail condition:**
- Any `httpx.get`, `requests.get`, or similar call in a worker file.
- Any hardcoded `api.polygon.io` URL outside the client layer.

---

## RC-3 Pre-Release Checklist

All RC-1 and RC-2 gates must also pass. The checklist below covers the new BP3-specific gates only.

- [ ] Gate 1 regression — implementation matrix complete for all BP3 rows
- [ ] Gate 2 regression — all QA-200 through QA-226 rows present and passing
- [ ] Gate 3 regression — zero new hex literals in TSX
- [ ] Gate 9 regression — all BP3 workers subclass BaseWorker; scheduler guard active
- [ ] Gate 10 — auto paper trade risk isolation confirmed
- [ ] Gate 11 — prompt version immutability confirmed
- [ ] Gate 12 — Polygon rate limit compliance confirmed
- [ ] Backend test count ≥ 320 passing
- [ ] Playwright test count ≥ 90 passing
