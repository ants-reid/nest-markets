# Site Build And Architecture Status Report

Date: 2026-04-23

## Purpose

This report compares the current repository state against:

- the planned build sequence in `docs/build-order.md`
- the intended platform architecture in `docs/architecture.md`
- the repository rules in `docs/coding-rules.md`, `docs/file-contracts.md`, and `docs/risk-rules.md`

It also records the main gaps, missed steps, and recommended next actions.

## Executive Summary

The repository is ahead of the original MVP frontend milestone in breadth, but not cleanly aligned with the documented build sequence.

What is clearly in place:

- Backend foundation through the documented Phase 5 stack is present and documented.
- The web app is substantially beyond a simple dashboard and now includes multiple operational routes.
- Global dark/light theme infrastructure is in place at the root layout level and has been pushed into shared semantic tokens.
- Shared chart components exist and have been hardened for contrast and sparse-data visibility.

What is not cleanly aligned:

- The documented build order says to complete phases strictly in sequence, but the repo already contains broad frontend surfaces while later backend phases remain only partially documented or only partially validated.
- Current documentation does not provide a single source of truth for actual implementation status across Phases 6 to 9.
- Validation is still shallow relative to the current surface area. The frontend mainly has smoke coverage, not regression-grade UI or accessibility coverage.

Bottom line: the project has good momentum and solid shared UI primitives, but it now needs a cleanup pass on architecture tracking, validation depth, and phase discipline.

## Current Repository Shape

### Top-level areas

- `apps/api`: FastAPI backend with config, DB, features, indicators, clients, services, routes, tests, and migration artifacts.
- `apps/web`: Next.js app-router frontend with route-level pages, shared components, charts, Playwright smoke tests, and semantic theme tokens.
- `docs`: Build order, architecture, rules, contracts, and governance docs.

### Backend status

Observed backend structure includes:

- foundation files: `app/main.py`, `app/config.py`, `app/logging.py`, `app/db/*`
- routes: `health.py`, `signals.py`, `risk.py`, `workflow.py`, `approvals.py`, `execution.py`
- service layer: signal, risk, risk profile, paper execution, live execution, approval, workflow, persistence services, and execution journaling
- LLM client layer and prompt/schema support under `app/clients`
- deterministic indicators and feature calculation layers under `app/indicators` and `app/features`

Documented summaries exist for:

- Phase 3
- Phase 4
- Phase 5

This means the backend implementation footprint has moved beyond the docs set that currently anchors the official build progress.

### Frontend status

Observed route surfaces include:

- `/`
- `/dashboard`
- `/analytics`
- `/workflow`
- `/signals`
- `/risk`
- `/approvals`
- `/execution`
- `/alerts`
- `/notifications`

Shared frontend architecture includes:

- global layout and theme bootstrap in `app/layout.tsx`
- semantic theme tokens in `app/globals.css`
- global navigation and theme toggle in `components/Nav.tsx`
- reusable chart primitives in `components/chart/*`
- larger shared panels such as dashboard, analytics, learning, notification, and workflow/result components

The site is no longer just a dashboard shell. It is already an application shell with multiple domain workflows.

## Build Order Comparison

## Planned sequence from `docs/build-order.md`

1. Phase 1: config, logging, app bootstrap, DB base/session, health route
2. Phase 2: models, migrations, seed assets
3. Phase 3: indicators, feature engine
4. Phase 4: LLM provider interface, OpenAI provider, prompt loading, schema loading
5. Phase 5: signal service, risk service, risk profiles, execution mode router
6. Phase 6: paper execution service, approval workflow, live execution scaffold
7. Phase 7: workers, schedules, sync jobs
8. Phase 8: frontend dashboard
9. Phase 9: evals, prompt versioning pages, regression tests

Rule stated in the build doc:

- build one phase at a time
- do not jump ahead
- do not add live trading in MVP

## Actual repo status against that plan

### Phase 1

Status: complete

Evidence:

- FastAPI bootstrap and health route are present.
- Config and logging modules exist.
- DB base/session modules exist.

### Phase 2

Status: likely present or largely present, but not audited in detail in this pass

Evidence:

- `alembic/` exists.
- DB/model and persistence-oriented service structure exists.
- README and summaries reference existing models and prompt persistence.

Gap:

- This pass did not fully audit the model inventory or migration completeness.

### Phase 3

Status: complete and documented

Evidence:

- Indicator and feature modules exist.
- Dedicated summary document exists.
- Tests are present for indicators/features.

### Phase 4

Status: complete and documented

Evidence:

- LLM base/router/provider/helpers exist.
- Dedicated summary document exists.
- Tests are present for clients/helpers.

### Phase 5

Status: substantially implemented and documented

Evidence:

- Signal service summary exists.
- Risk, risk profile, and execution mode services exist in the API service layer.

Gap:

- This pass did not execute backend tests, so implementation status is based on structure and docs, not fresh runtime verification.

### Phase 6

Status: partially implemented in code, not coherently documented as a completed phase

Evidence:

- `paper_execution_service.py`
- `live_execution_service.py`
- approval and workflow services
- frontend execution and approvals flows

Gap:

- No Phase 6 completion summary was inspected.
- Need explicit confirmation of what is production-ready vs mock/scaffold.

### Phase 7

Status: not evident from this pass

Evidence:

- No obvious workers/schedules/sync-jobs documentation was inspected.

Gap:

- If these systems exist, they are not surfaced in the current top-level status docs.
- If they do not exist, the repo has moved frontend breadth ahead of backend scheduling/completion discipline.

### Phase 8

Status: exceeded the original scope

Evidence:

- The frontend is far beyond a single dashboard.
- Multiple app routes and shared panels are implemented.
- Theme system and shared charts are in active use.

Gap:

- The build-order doc still describes this phase as only `frontend dashboard`, which no longer reflects reality.

### Phase 9

Status: partial at best

Evidence:

- Frontend has a Playwright smoke test file.

Gap:

- No clear eval framework was inspected.
- No prompt versioning pages were verified in the web route inventory.
- No meaningful regression suite beyond smoke behavior was verified.

## Architecture Alignment

## Areas aligned with `docs/architecture.md`

### Separation of AI proposal from execution

Alignment: good

Evidence:

- Architecture says AI proposes and deterministic rules approve.
- Backend summaries explicitly state the signal service proposes only.
- Live execution remains disabled in MVP behavior; frontend smoke tests expect the disabled live execution response.

### Provider isolation

Alignment: good

Evidence:

- LLM logic is isolated under `app/clients`.
- Architecture anti-drift rule says no LLM calls outside provider layer.
- The documented Phase 4 structure matches this rule.

### Thin API route pattern

Alignment: good from sampled inspection

Evidence:

- Sampled `signals.py` route is thin and returns a mock-safe payload.
- This fits the rule that routes should handle request/response, not business logic.

### Risk routing principle

Alignment: structurally good, full verification still needed

Evidence:

- Risk services and execution-mode services exist.
- Risk rules doc clearly enforces shared blocking logic across paper, confirm-before-trade, and auto modes.

Gap:

- This pass did not verify end-to-end enforcement through all routes and UI actions.

### Frontend semantic design system

Alignment: improving strongly

Evidence:

- Root theme bootstrap in `app/layout.tsx`
- centralized semantic tokens in `app/globals.css`
- shared chart/token usage in chart primitives and route components
- recent site-wide pass moved many literals to semantic tokens and improved cross-theme contrast

Gap:

- There is no evidence yet of automated enforcement for token use, contrast, or theme regression.

## Areas with drift or incomplete governance

### Build-sequence drift

Issue:

- The codebase has advanced into broad frontend workflow surfaces before the documented phase plan and completion records were updated to match.

Impact:

- It is harder to know what is truly complete, experimental, mock-backed, or scaffold-only.

### Documentation drift

Issue:

- Phase summaries stop at Phase 5 even though the repo includes execution, approvals, workflow, alerts, and broad frontend surfaces.

Impact:

- New contributors cannot reliably use docs alone to understand the true system state.

### Validation drift

Issue:

- Current frontend test coverage is primarily smoke-based.

Impact:

- UI regressions in theme, chart visibility, table contrast, or route-specific semantics can ship without detection.

## Rules Compliance Check

## Rules that appear to be followed

### No live trading in MVP

Status: followed

Evidence:

- Build rules explicitly forbid live trading in MVP.
- Smoke tests assert a disabled live execution payload.

### Thin backend routes

Status: followed in sampled files

Evidence:

- Sampled signal route contains request/response logic only.

### Shared semantic theming direction

Status: followed in the current frontend direction

Evidence:

- Theme is bootstrapped once at the document root.
- Semantic tokens are defined centrally and used broadly.

### Risk-policy consistency intent

Status: documented and structurally represented

Evidence:

- Risk service and risk profile service exist.
- Risk rules specify shared enforcement across execution modes.

## Rules that still need stronger enforcement

### Build one phase at a time

Status: not followed strictly

Evidence:

- Frontend breadth has outpaced the documented sequence and completion records.

### Regression-grade testing

Status: incomplete

Evidence:

- Only smoke coverage was confirmed on the frontend during this pass.

### Clear completion records per phase

Status: incomplete

Evidence:

- No inspected summary docs for Phases 6 to 9.

## Missed Steps

These are the main steps that appear to have been missed or under-completed.

1. The build-order document was not updated after the project moved beyond a simple frontend dashboard.
2. Phase completion reporting stopped too early relative to the real repo footprint.
3. Phase 6 and later work was not normalized into one clear status layer distinguishing mock, scaffold, and production-intent behavior.
4. Frontend route growth was not matched by stronger automated regression coverage.
5. Theme/token adoption was improved through implementation passes, but there is still no enforcement rule or audit automation to prevent new literal styles from creeping back in.
6. Accessibility/contrast validation appears manual rather than codified.
7. End-to-end architecture conformance is documented as a principle, but not yet surfaced as an explicit checklist or CI gate.
8. The project is still on Next.js `15.3.1`, and the browser dev overlay reported that version as outdated during validation.

## Recommended Next Steps

## Immediate next steps

1. Create a canonical implementation-status doc for Phases 1 to 9.
2. Split current features into three buckets: implemented, scaffolded/mock-backed, and planned.
3. Add a frontend regression pack for the highest-risk routes: alerts, analytics, dashboard, execution, workflow.
4. Add a theme regression checklist covering dark/light mode, tables, charts, tooltips, badges, and empty states.
5. Document Phase 6 explicitly: paper execution, approvals, execution journaling, live execution scaffold boundaries.

## Near-term architecture steps

1. Update `docs/build-order.md` so it matches the current repo reality.
2. Add a Phase 6 summary and, if applicable, Phase 7 to 9 summaries.
3. Add a route-to-service mapping doc for backend routes and major frontend pages.
4. Add a token-governance rule for the web app: no raw color literals in route components unless justified.
5. Add accessibility checks for contrast and chart visibility into Playwright or visual-regression coverage.

## Technical quality steps

1. Expand Playwright beyond smoke tests into route-specific assertions and theme assertions.
2. Add at least one test that verifies a single-point series remains visible in charts.
3. Add tests for light/dark persistence across route changes.
4. Add lint or search-based CI checks for reintroduced hard-coded colors in frontend TSX files.
5. Plan a framework maintenance pass for outdated Next.js dependencies.

## Suggested Delivery Order From Here

1. Freeze architecture/docs drift.
2. Mark each route and backend service as real, mock, or scaffold.
3. Harden test coverage around the currently visible UI surface.
4. Finish missing phase documentation.
5. Only then expand the product surface further.

## Practical Assessment

The project is in a better state than the original docs imply. The backend foundation is real, the service layer is broad, and the frontend has already matured into a multi-route operator console. The main weakness is not lack of code volume; it is lack of synchronized governance around what is complete, what is mocked, what has been validated, and what phase the project is actually in.

That is the main thing to fix next.