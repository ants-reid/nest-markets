# Catch-Up Action Plan

Date: 2026-04-23

## Goal

Bring the project back into a controlled state where:

- the docs match the real implementation
- each feature is clearly classified as real, mock-backed, scaffold, or missing
- architecture rules are enforced instead of assumed
- new frontend features are covered by regression checks
- theme, token, chart, and contrast work does not regress
- later work can be added without reopening the same gaps

This plan is designed to catch up without losing existing momentum.

## Numbered Control System

To stop drift, this plan is now controlled by numbered workstreams and tracking docs:

- WS-01: Source of truth and inventory
- WS-02: Build-order reconciliation
- WS-03: Architecture compliance audit
- WS-04: Theme and token governance
- WS-05: Regression baseline
- WS-06: New-feature integration review
- WS-07: Release gates and anti-drift process

Tracking documents:

- `docs/implementation-matrix.md`
- `docs/regression-qa-matrix.md`

Rule:

- any fix, test, or new feature must reference at least one implementation ID and one workstream ID

## Success Criteria

The catch-up work is complete when all of the following are true:

1. There is one authoritative implementation matrix for backend services, routes, frontend pages, and shared components.
2. Every current user-facing route has a defined owner state: production intent, mock/demo, scaffold, or backlog.
3. Phases 6 to 9 are either documented as implemented, documented as partial, or explicitly marked not started.
4. Theme, chart, table, and contrast regressions are covered by repeatable tests or checklists.
5. Rules from architecture and coding docs are mapped to enforcement steps, not just documentation.
6. New features can only merge with documentation and validation attached.

## Working Rules For The Catch-Up

1. Stop expanding surface area until the implementation map and validation baseline are complete.
2. Treat all undocumented features as partial until proven otherwise.
3. No new route or shared component should be considered done without a validation entry.
4. Keep MVP live trading disabled.
5. Prioritise thin routes, thin UI pages, shared primitives, and token-based styling.

## WS-01: Freeze Drift And Build The Source Of Truth

Objective:

Create a single status system that reflects what actually exists today.

Tasks:

1. Create an implementation matrix covering:
   - backend routes
   - backend services
   - backend persistence surfaces
   - frontend routes
   - shared UI components
   - shared chart components
2. Add a status field to every item:
   - implemented
   - mock-backed
   - scaffold
   - partial
   - not started
3. Add a validation field to every item:
   - tested
   - manually verified
   - unverified
4. Add a dependency field for each item so phase ordering is visible.
5. Record whether each item is documented, undocumented, or drifted from docs.

Deliverables:

- implementation matrix doc
- updated phase status summary

Acceptance gate:

- A new contributor can open one document and understand what is real, what is fake, and what still needs work.

## WS-02: Reconcile Build Order With Reality

Objective:

Update the planning docs so the repo is no longer pretending to be earlier than it is.

Tasks:

1. Update the build-order document to distinguish:
   - original intended phase sequence
   - actual current implementation state
   - deferred work still not complete
2. Write explicit summaries for missing phase records:
   - Phase 6: paper execution, approval workflow, live execution scaffold
   - Phase 7: workers, schedules, sync jobs or explicit statement that they do not yet exist
   - Phase 8: actual frontend scope, not just dashboard
   - Phase 9: evals, prompt versioning, regression coverage status
3. Mark where the project intentionally jumped ahead and why.
4. Mark what must be brought back into sequence before new work proceeds.

Deliverables:

- updated build-order doc
- missing phase summary docs

Acceptance gate:

- The docs no longer conflict with the actual repository structure.

## WS-03: Audit Architecture Compliance

Objective:

Check that the code follows the architecture principles already written down.

Audit checklist:

1. Backend route audit:
   - confirm route files are request/response only
   - identify any route-level business logic
2. LLM boundary audit:
   - confirm AI calls stay inside the provider layer
   - confirm prompt strings are not embedded in business services
3. Broker boundary audit:
   - confirm live execution remains scaffolded and isolated
4. Execution separation audit:
   - confirm no mixed paper/live execution classes
5. Risk enforcement audit:
   - confirm risk rules are shared across modes rather than duplicated or bypassed
6. Frontend responsibility audit:
   - identify any page components carrying business logic that should move to lib or service helpers

Deliverables:

- architecture compliance checklist
- findings log with severity and remediation actions

Acceptance gate:

- Every architecture rule is either verified, failed with owner/action, or marked unknown pending audit.

## WS-04: Lock Down Frontend Design-System Consistency

Objective:

Make the theme and semantic-token work durable instead of depending on manual cleanup passes.

Scope to cover:

- alerts
- analytics
- dashboard
- execution
- workflow
- signals
- risk
- approvals
- notifications
- home

Tasks:

1. Audit all route pages and shared components for raw color literals, stray shadows, and local one-off surface styles.
2. Finish token migration anywhere still using direct color values.
3. Define token categories clearly:
   - text
   - surfaces
   - controls
   - state colors
   - chart primitives
   - overlays and shadows
4. Add a frontend rule doc for semantic token usage.
5. Add an automated literal-color scan for app and component TSX files.
6. Add a review checklist for dark mode and light mode parity.

Deliverables:

- token governance doc
- automated raw-color scan step
- route-by-route theme checklist

Acceptance gate:

- Regressions in color-token usage are detectable without manual repo-wide cleanup.

## WS-05: Build A Proper Regression Baseline

Objective:

Replace shallow smoke confidence with route-specific regression confidence.

Test plan:

1. Backend tests:
   - run existing service tests
   - identify failures and classify as environment issue, broken contract, or outdated docs
2. Frontend route tests:
   - home
   - dashboard
   - analytics
   - workflow
   - signals
   - risk
   - approvals
   - execution
   - alerts
   - notifications
3. Theme tests:
   - dark mode persists across navigation
   - light mode persists across navigation
   - no unreadable low-contrast text on primary surfaces
4. Chart tests:
   - single-point series remains visible
   - multi-series line visibility
   - tooltip and axis text remain readable in both themes
5. Table tests:
   - headers, row text, badges, and action links remain readable in both themes
6. MVP policy tests:
   - live execution disabled behavior remains enforced

Deliverables:

- expanded Playwright suite
- backend validation report
- regression checklist for manual visual QA items not yet automated

Acceptance gate:

- The highest-risk user-visible workflows have repeatable regression coverage.

## WS-06: Catch Up The Newer Features Specifically

Objective:

Make sure newly added features are not just present, but fully integrated into the architecture and validation model.

Feature buckets to review:

1. Alerts and notifications
2. Watchlist exposure and shared charts
3. Execution details, intelligence, history, and journal surfaces
4. Workflow results and learning mode surfaces
5. Analytics panels and dashboard widgets
6. Theme toggle and global theme bootstrap

For each feature bucket, record:

1. source files
2. backend dependencies
3. whether data is real, mock, derived, or mixed
4. validation status
5. token/theme status
6. documentation status
7. open defects or risk items

Deliverables:

- feature-integration checklist
- bucketed defect/remediation list

Acceptance gate:

- Every newer feature is explicitly tracked and no longer hidden inside broad route pages.

## WS-07: Introduce Release Gates For Future Changes

Objective:

Prevent the same drift from coming back as new features are added.

Required gate for new work:

1. feature or route added to implementation matrix
2. documentation updated
3. validation updated
4. theme/token review completed if UI changed
5. architecture boundary check completed if backend changed
6. MVP policy check completed if execution behavior changed

Recommended CI and review gates:

1. run lint
2. run frontend smoke plus route regressions
3. run backend targeted tests for changed services
4. run raw-color scan for web app files
5. require PR checklist entry for docs and validation impact

Deliverables:

- PR checklist
- contribution gate rules

Acceptance gate:

- New work cannot land without being visible in docs and validation.

## Missed Steps To Recover Explicitly

These are the recovery items that should be treated as mandatory, not optional:

1. Document actual Phase 6 through Phase 9 state.
2. Inventory which routes are true workflows versus mock/demo surfaces.
3. Add regression coverage for the expanded frontend surface.
4. Add theme and chart regression protection.
5. Add architecture compliance review instead of relying only on intent docs.
6. Update planning docs so they stop understating the project scope.
7. Add a mechanism to stop raw style literals from creeping back into route components.

## Recommended Execution Order

1. WS-01: source of truth
2. WS-02: build-order reconciliation
3. WS-03: architecture audit
4. WS-04: token and UI consistency lockdown
5. WS-05: regression baseline
6. WS-06: newer-feature integration review
7. WS-07: future release gates

## Priority View

### Critical

- implementation matrix
- missing phase docs
- regression baseline for high-risk routes
- architecture compliance audit

### High

- token governance
- automated color-literal scan
- feature-bucket review for alerts, execution, analytics, workflow

### Medium

- dependency upgrades such as outdated Next.js
- broader CI convenience improvements

## Suggested First Sprint

The fastest useful sprint should do only these things:

1. create the implementation matrix
2. classify every route and service as real, mock, scaffold, or partial
3. write missing Phase 6 to Phase 9 summaries
4. add Playwright coverage for alerts, execution, analytics, and theme persistence
5. add a raw-color scan and token-governance note

If that sprint completes, the project will be materially safer to extend.