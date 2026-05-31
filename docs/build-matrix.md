# Market Hunter — Build Control Matrix

> **Rule**: Every phase must update `docs/build-ledger.md` on completion with:
> changed files, migrations added, tests run, pass/fail count, known limitations,
> and recommended next phase.

---

## Phase Registry

## Restart Stabilisation Note — 2026-05-19

- frontend build-ready evidence is green from the stabilisation pass
- backend local DB bootstrap is restored and backend pytest is green locally (`2301 passed`, `0 warnings`)
- learning bootstrap is green locally (`99 passed`)
- Gate 1 implementation-matrix inventory has been reconciled to the live repo surface and Gate 2 QA linkage has been extended to cover the new route/page IDs
- smoke verification is green on the rebuilt web app (`20/20 passed`)
- responsive verification is green after the 390px topbar fix (`46/46 passed`)
- visual verification is green after snapshot rebaseline (`48/48 passed`)
- full Playwright verification is green (`272/272 passed`)
- release readiness is now GO / release-ready candidate on the MH-RESTART-004 evidence set

| Phase  | Title                              | Status      | Depends On | Drift Lock |
|--------|------------------------------------|-------------|------------|------------|
| MH-00  | Repo Audit & Build Control         | ✅ Complete  | —          | No new features |
| MH-01  | Data Centre Foundation             | ✅ Complete  | MH-00      | No Strategy Lab, no live trading |
| MH-02  | Historical Import Manager          | ⏳ Pending   | MH-01      | No UI yet |
| MH-03  | Data Quality Alerting              | ⏳ Pending   | MH-01      | No broker changes |
| MH-04  | Data Centre UI (read-only)         | 🟡 Partial  | MH-01      | Split via cycle 26: 04-RO read-only subset ✅, 04-WR write actions ⏳ |
| MH-04-RO | Data Centre UI — read-only subset (filters, coverage/quality/gaps/import-runs tables) | ✅ Complete | MH-01      | Strictly read-only filters + tables; consumes `GET /research/data/*` only |
| MH-04-WR | Data Centre UI — write actions (start/cancel/retry import + quality jobs)             | ⏳ Pending  | MH-04-RO, MH-02 | Mutating job actions; out of scope until MH-02 import manager lands |
| MH-05  | Strategy Lab Engine                | 🔒 Locked    | MH-04      | Do not start before MH-04 |
| MH-06  | Historical Replay Engine           | 🔒 Locked    | MH-05      | Do not start before MH-05 |
| MH-07  | Mock Trade Simulator               | 🔒 Locked    | MH-06      | Do not start before MH-06 |
| MH-08  | AI Backtest Reports                | 🔒 Locked    | MH-07      | Do not start before MH-07 |
| MH-09  | Baseline Manager                   | 🔒 Locked    | MH-08      | Do not start before MH-08 |
| MH-10  | Journal Migration (DB-backed)      | ⏳ Pending   | MH-01      | Do not break existing JSON journal during migration |
| MH-11  | Broker Live Wiring (Paper IBKR)    | ⏳ Pending   | MH-01      | No auto_live; paper only |
| MH-12  | Tiny Live Mode                     | 🔒 Locked    | MH-11      | Do not start before MH-11 |

---

## Drift Lock Rules

These guards apply to ALL phases unless explicitly overridden by a phase spec:

1. **No duplicate candle table.** All OHLCV storage goes through `bars` / `Bar` model.
2. **No Strategy Lab in MH-00..MH-04.** Strategy engine is MH-05+.
3. **No replay engine before MH-05.**
4. **No live broker wiring before MH-11.** `auto_live` remains hardcoded disabled (Gate 4).
5. **No third-party charting libraries** without an explicit phase spec approving them.
6. **No unrelated refactors** within a phase. One phase, one scope.
7. **Build ledger must be updated** before a phase is marked complete.
8. **Existing tests must not regress.** New phases may add tests; never delete existing ones.
9. **Journal stays JSON-file-backed** until MH-10.
10. **OpenAI signal pipeline is frozen** until a phase explicitly targets it.
11. **Broker submit decision timeline is read-only.** `/broker/submit-decisions/recent` stays GET-only with a pinned filter signature and pinned response schema; the cockpit timeline page and its client helper must never reference `/broker/orders` or `/execution/paper` and must never import the broker submit lib. Pinned by `apps/api/tests/test_broker_submit_decision_timeline_route_surface_drift_lock.py` and `apps/api/tests/test_broker_submit_decision_timeline_frontend_drift_lock.py` (2026-05-31).

---

## Phase Detail Summaries

### MH-00 — Repo Audit & Build Control
- Created `docs/build-matrix.md` (this file) and `docs/build-ledger.md`.
- Recorded current repo state: assets, bars, market-data providers, feature pipeline,
  paper execution, OpenAI signal pipeline, journal storage, IBKR adapter scaffold.
- Established build ledger rules.

### MH-01 — Data Centre Foundation
- New DB models: `MarketDataImportRun`, `MarketDataQualityReport`, `MarketDataGap`,
  `ProviderCoverageReport`.
- Alembic migration: `a2b3c4d5e6f7_add_data_centre_tables.py`.
- New services: `MarketDataCoverageService`, `MarketDataQualityService`.
- New route: `apps/api/app/api/routes/research_data.py`.
- Endpoints: `GET /research/data/{assets,providers,coverage,quality,gaps}`.
- Tests: route registration, coverage shape, quality shape, empty-state, no duplicate
  candle table.

### MH-02 — Historical Import Manager *(pending)*
- Will add `ImportSchedule` model and bulk-import workers.
- Will hook into existing `MarketDataService.ingest_bars()`.
- Will write import run records to `market_data_import_runs`.

### MH-04 — Data Centre UI *(pending)*
- Read-only Next.js page at `/data-centre`.
- Consumes `GET /research/data/*` endpoints.
- No new charting libraries; reuse existing SVG chart components.

### MH-10 — Journal Migration *(pending)*
- Migrate `execution_journals.json` to a `execution_journals` Postgres table.
- Keep `ExecutionJournalService` interface stable; swap storage backend only.

### MH-11 — Broker Live Wiring (Paper IBKR) *(pending)*
- Wire `IBKRAdapter` into `LiveExecutionService` via `gateway_factory.py`.
- Set `PAPER_TRADING_ENABLED=true` in `.env` to activate.
- `auto_live` remains hardcoded disabled (Gate 4 invariant).

## Broker/Paper Canonical Source Model

| Mode | Canonical path(s) | execution_source | balance_source | fees_source | fills_source | positions_source | serious_paper_source | is_canonical_paper | IBKR calls | Can place order | Live lock status |
|------|-------------------|------------------|----------------|-------------|--------------|------------------|----------------------|--------------------|------------|-----------------|------------------|
| internal_mock_simulator | `/execution/paper` + `PaperExecutionService` + `PersistencePaperExecutionService` | internal_mock_simulator | app_simulated | estimated | simulated | app_db_simulated | ibkr_paper | false | No | Simulated only | N/A (not live-capable) |
| ibkr_paper | `/broker/account`, `/broker/positions`, `/broker/orders`, `/broker/orders/dry-run`, `BrokerService` + `IBKRAdapter` in paper mode | ibkr_paper (`broker_dry_run` for dry-run) | ibkr_paper | ibkr_reported (trade events when available) | ibkr_paper | ibkr_paper | ibkr_paper | true | Yes (read + paper submit path) | Yes (paper only, mode-gated) | Live remains blocked by trading-control and mode guards |
| ibkr_live_locked | Same broker abstraction (`BrokerService` + `IBKRAdapter`) when env is fully live | ibkr_live_locked | ibkr_live_locked | unavailable | unavailable | ibkr_live_locked | ibkr_paper | false | Read paths possible; live submit intentionally blocked | No (current phase) | Hard locked (`live_order_submission_allowed=false`) |

Notes:
- Internal simulator is useful for tests, demos, and UI flow validation, but it is not the serious pre-live proving path.
- Serious paper means IBKR paper (`serious_paper_source=ibkr_paper`).
- Proving the future live process requires using the IBKR paper path, not `/execution/paper`.
- This model does not enable live trading and does not relax existing broker/trading-control guards.

MH-BROKER-PAPER-CANONICAL-02 delta:
- `POST /broker/orders` remains the canonical serious-paper order route only when broker mode is coherently paper.
- `POST /broker/orders/dry-run` remains available in live-config environments for inspection only, but now emits live-locked balance/positions lineage (`ibkr_live_locked`) plus `broker_account_mode=live`, `live_state=ibkr_live_locked`, and `is_canonical_paper=false`.
- Dry-run never upgrades a live-config environment into a canonical paper path and never unlocks live submission.

MH-BROKER-PAPER-CANONICAL-03 delta:
- `GET /broker/paper/canonical-route` is now the explicit read-only route-check for intentional serious-paper workflows.
- Serious paper resolves only to `/broker/orders` in coherent paper mode and never resolves to `/execution/paper`.
- Live or unknown broker/account tuples fail closed with no resolved submit path.
- Background workers gain no new broker submit capability from this phase; the route-check is read-only and the existing auto worker seam remains separately gated.

MH-BROKER-PAPER-CANONICAL-04 delta:
- `GET /paper/recommendations/{recommendation_id}/serious-paper-route-check` now lets an operator inspect whether a persisted recommendation is eligible for the canonical manual IBKR paper path.
- Eligible recommendations resolve only to `/broker/orders` in coherent paper mode; the recommendation route-check never resolves `/execution/paper`.
- Live or unknown broker/account tuples fail closed, and recommendations that are not yet operator-approved or are missing required order context return `route_check_status=missing_context` instead of guessing submit intent.
- The recommendation route-check is read-only and non-submitting; actual submit still uses the existing guarded `POST /broker/orders` path, workers remain non-submitting by default, and live remains locked.

Operator review surface delta — 2026-05-23:
- `/cockpit/in-flight-adjustments` now renders a narrow operator-facing recommendation route-check panel for paper recommendations only.
- The panel is read-only, displays `eligible` / `blocked` / `missing_context` results from the existing backend contract, and links operators back into the guarded `/broker` dry-run/manual paper flow without adding any submit button.
- Validation recovery also repaired an unrelated asset-card baseline test expectation so the full API suite returned to green; no broker, worker, or live-trading behavior changed.

---

## Post-MH-141 Phase Registry (Locked-In via MH-142 Safety Review, 2026-05-02)

> Canonical detail and rationale for every row below lives in `docs/build-ledger.md`
> entry **MH-142-A — Build Matrix Lock-In** (Sections A–K).
> Drift Lock (Gate 4: no live execution; auto-paper enforcement remains OFF until
> Bucket 1 is fully green) is **inherited by every row** unless the row is itself
> a Bucket 4 live-prereq phase.

### Bucket 1 — Must Fix Before Auto-Paper Enforcement (blocks enforcement)

| Phase        | Title                                          | Status  | Depends On                  | Drift Lock |
|--------------|------------------------------------------------|---------|-----------------------------|------------|
| MH-143       | Position Sizing Service                        | 🟡 Partial | MH-141                    | 143-A service module ✅; 143-B worker wiring deferred |
| MH-144       | Drop MARKET fallback in worker                 | ⏳ Pending | MH-143                    | LIMIT-only path |
| MH-145       | Real RiskInput values (spread/DD/recent loss)  | 🟡 Partial | MH-143                    | 145-A `MarketContextSnapshotService` scaffolding ✅ (NOT wired into worker; drift-lock test enforces); 145-B worker wiring deferred |
| MH-146       | `Position.opened_by` column + backfill         | ✅ Complete | —                          | Additive column, default 'unknown' |
| MH-147       | Unified `would_block` enforcement semantics    | ✅ Complete | MH-145                  | Fail-closed on would_block/unknown/error submit preflight |
| MH-148       | `BrokerSubmitDecision` audit table             | ✅ Complete | MH-147                  | 148-A table+model ✅, 148-B read endpoint ✅, 148-C writer ✅ (dry-run + submit-preflight + submit-attempt) |
| MH-149       | Catalyst-context sanitization                  | ✅ Complete | —                          | Untrusted-text policy |
| MH-150       | `LLMRequestLog` (full request/response)        | ✅ Complete | —                          | No PII bleed; redact keys |
| MH-151       | Signal geometry validation (entry/stop/target) | ✅ Complete | —                          | Rejects inverted / NaN / wrong-side geometry |
| MH-152       | Worker async refactor (drop `asyncio.run`)     | ⏳ Pending | MH-148                    | No behaviour change in this phase |
| MH-153       | `risk_profile_id` denormalization              | 🟡 Partial | MH-148                    | 153-A column ✅; 153-B writer still deferred |
| MH-154       | Persist risk-block reason (queryable)          | 🟡 Partial | MH-148                    | 154-A column ✅; 154-B writer still deferred |
| MH-MON-01    | Health endpoint registry (`/health/services`)  | ✅ Complete | —                          | Read-only; no toggles |
| MH-MON-02    | Feeds-In probes                                | ✅ Complete | MH-MON-01                | Probe-only, advisory |
| MH-MON-03    | Feeds-Out probes                               | ✅ Complete | MH-MON-01                | Probe-only, advisory |
| MH-MON-04    | Trading Safety Decision aggregator             | ✅ Complete | MH-MON-02, MH-MON-03      | Reads gates; never writes |
| MH-MON-05    | Incidents log (`/monitor/incidents`)           | ✅ Complete | MH-MON-01                | Append-only |

### Bucket 2 — Should Fix Before Paper-Auto Performance Testing

| Phase           | Title                                          | Status  | Depends On             | Drift Lock |
|-----------------|------------------------------------------------|---------|------------------------|------------|
| MH-155          | Auto `SignalOutcome` on close                  | ⏳ Pending | MH-146, MH-148        | Backfill safe |
| MH-156          | Cost model on paper (slippage/fees)            | ⏳ Pending | MH-155                | Paper-only |
| MH-157          | Performance dimensions (regime/sector/session) | ⏳ Pending | MH-155                | Read-only views |
| MH-158          | Worker-run-log archive                         | ✅ Complete | —                      | Retention policy |
| MH-159          | Prompt frontmatter + content hash              | ✅ Complete | MH-150                | Immutable per version |
| MH-160          | Correlation ID plumbing                        | ✅ Complete | MH-150                | End-to-end trace |
| MH-NEWS-01      | Perplexity/Sonar provider client               | ✅ Complete | —                      | Research-only |
| MH-NEWS-02      | News normalized JSON schema + storage          | ✅ Complete | MH-NEWS-01            | Raw + normalized + citations |
| MH-NEWS-03      | News cache + freshness window                  | ✅ Complete | MH-NEWS-02            | TTL configurable |
| MH-NEWS-04      | News Risk advisory flag (paper-only)           | ⏳ Pending | MH-NEWS-02, MH-148    | Never relaxes risk |
| MH-NEWS-06      | `evidence_class="research_only"` enforcement   | ✅ Complete | MH-NEWS-02            | DB CHECK constraint |
| MH-NEWS-07      | News UI surface (Cockpit + Asset Detail)       | ✅ Complete | MH-NEWS-02            | Citations always shown |
| MH-NEWS-08      | News-in-decision audit log                     | 🟡 Partial | MH-NEWS-04, MH-150    | 08-A table+model+CHECK shipped (cycle 23, no writer); 08-B writer deferred until MH-NEWS-04 lands |
| MH-MON-06       | `/system-health` frontend page                 | ✅ Complete | MH-MON-04             | View-only |
| MH-MON-07       | Provider Configuration view                    | ✅ Complete | MH-MON-01             | Read-only |
| MH-MON-08       | Health History charts                          | ✅ Complete | MH-MON-05             | Reuse SVG chart lib |
| MH-MON-10       | Operator `POST /monitor/test/{service}` endpoint | ✅ Complete | MH-MON-01           | Auth-gated, dry probes only |
| MH-COCKPIT-01   | Markets-open snapshot endpoint                 | ✅ Complete | —                      | Read-only |
| MH-COCKPIT-02   | Asset cards + market quality                   | ✅ Complete | MH-COCKPIT-01         | Read-only |
| MH-COCKPIT-03   | Mode selector (Learning / Manual / Auto Paper) | ✅ Complete | MH-COCKPIT-01, MH-MON-04 | Live modes remain disabled in backend and UI |
| MH-COCKPIT-04   | Plain-English explainer                        | ✅ Complete | MH-150                | Reads decision audit only |
| MH-COCKPIT-05   | EOD report                                     | ✅ Complete | MH-155                | Paper scope |
| MH-COCKPIT-06   | Notifications surface                          | ✅ Complete | MH-MON-05             | In-app only initially |

### Bucket 3 — Can Fix After Paper-Auto Is Safely Running

| Phase           | Title                                          | Status   | Depends On             | Drift Lock |
|-----------------|------------------------------------------------|----------|------------------------|------------|
| MH-161          | `BrokerService` split (refactor)               | ✅ Complete | Bucket 1 green        | No behaviour change |
| MH-162          | Post-lock simulation regression suite          | ✅ Complete | MH-161                | Test-only |
| MH-MON-09       | Backend test-service POST endpoint hardening   | ✅ Complete | MH-MON-10             | Auth + rate-limit |
| MH-COCKPIT-07   | In-flight adjustments view                     | ✅ Complete | MH-COCKPIT-05         | Paper scope; recommendation route-check, guarded broker dry-run preview, manual paper submit readiness review, manual paper submit handoff review, manual paper submit audit package, manual paper submit approval package, guarded manual paper submit preflight contract, future manual submit design review, guarded operator submit-decision review, guarded operator action review, final guarded operator submit interaction spec, the submit-readiness architecture checkpoint, and the dedicated manual paper submit confirmation surface remain read-only with `/broker/orders` preserved as the only serious-paper submit seam. The in-flight review panel and confirmation surface now share the same frontend-only review-chain derivation helper for read-only status context, the dedicated confirmation surface exposes a conservative payload freshness review that fails closed when timing evidence is missing, the in-flight panel now shows a compact read-only freshness summary from that same shared helper without duplicating derivation logic or adding any submit control, and both surfaces now reuse a shared missing-context triage contract that groups payload, route-check, dry-run, approval/preflight, freshness, source-label, broker-mode, and blocking gaps while keeping submit disabled, live locked, and workers non-submitting. |
| MH-COCKPIT-08   | Trade-close explanations                       | ✅ Complete | MH-150                | Audit-driven |
| MH-COCKPIT-09   | Daily scoreboard                               | ✅ Complete | MH-157                | Read-only |
| MH-COCKPIT-10   | Alerts needing attention                       | ✅ Complete | MH-MON-05             | Surfacing only |
| MH-COCKPIT-11   | Asset-detail deep-link                         | ✅ Complete | MH-COCKPIT-02         | Read-only; cockpit review surfaces now include asset-context navigation only |
| MH-COCKPIT-12   | Open-paper-positions live view                 | ⏳ Pending | MH-COCKPIT-05         | Read-only |
| MH-COCKPIT-13   | Auto-paper status card                         | ✅ Complete | MH-141                | Read-only |

Manual IBKR paper submit checkpoint note — 2026-05-24:
- The go/no-go review for the first executable manual IBKR paper submit phase is currently `NOT_READY_MISSING_SAFETY_TESTS`.
- The blocker is missing confirmation-control safety coverage, not a missing backend seam or missing frontend host.
- If and only if the missing safety cases are added first, the next phase name remains `Guarded Manual IBKR Paper Submit Control, Paper-Only`.
- The dedicated confirmation route stays the only approved future UI host, the in-flight panel stays review-only, `/broker/orders` stays the only serious-paper submit seam, live stays locked, and workers stay non-submitting.

Manual IBKR paper submit safety-tests-only follow-up — 2026-05-24:
- The missing confirmation-control safety coverage named by the checkpoint is now implemented and validated in tests only.
- No submit implementation was added, no enabled submit button was added, no `/broker/orders` UI call was added from the confirmation surface, and no `submitBrokerOrder` import was added.
- The dedicated confirmation route remains the only approved future UI host, the in-flight panel remains review-only, `/broker/orders` remains the only serious-paper submit seam, live remains locked, and workers remain non-submitting.
- This block closes the named safety-test gap but does not itself reassess executable enablement.

Manual IBKR paper submit post-implementation safety audit — 2026-05-24:
- Verdict: `PAPER_ONLY_MANUAL_SUBMIT_IMPLEMENTED_AND_LIVE_LOCKED`.
- The dedicated confirmation route now owns the only executable cockpit submit control and is guarded by explicit final confirmation plus fail-closed review, freshness, triage, paper-mode, live-lock, and worker-lock gates.
- The in-flight panel remains review-only, `/broker/orders` remains the only serious-paper submit seam, `/execution/paper` remains simulator/monitoring-only, live remains locked, and workers remain non-submitting.

Broker submit decision timeline / paper submit result history — 2026-05-24:
- Status: complete.
- The existing `GET /broker/submit-decisions/recent` surface now returns a typed timeline-friendly response with extracted decision metadata and read-only filters for `source`, `decision_status`, `correlation_id`, and `recommendation_id`.
- The existing cockpit audit route `/cockpit/audit/broker-submit-decisions` now serves as the operator-facing read-only timeline/history surface, and the cockpit hub links directly to it.
- The guarded submit seam remains unchanged: `/broker/orders` is still the only serious-paper submit route, live remains locked, and workers remain non-submitting.

Paper submit result UX / operator outcome view — 2026-06-01:
- Status: complete (frontend UX-only).
- The dedicated manual IBKR paper submit confirmation page now renders a post-attempt `OperatorOutcomeView` that summarises whether the submit was `allowed`, `blocked`, or `failed`, echoes the persistent safety badges (Paper only, Live remains locked, Workers cannot submit, No live order was placed), shows the attempt details (symbol, side, qty, order type, TIF, estimated notional, recommendation id, correlation id, timestamp), surfaces the guard result (broker mode, preflight status, allowed_to_submit, would_block, response status, blocked reasons, safe error message), links to the read-only `/cockpit/audit/broker-submit-decisions?correlation_id=…&recommendation_id=…` timeline, and renders outcome-specific next-step guidance with no auto-resubmit control.
- No new submit route, no live unlock, no auto-submit, no worker submit, no new mutation. `/broker/orders` remains the only serious-paper submit seam, `/execution/paper` remains simulator-only, live remains locked, and workers remain non-submitting.

### Bucket 4 — Future Live-Trading Prerequisites (Locked)

| Phase           | Title                                          | Status   | Depends On             | Drift Lock |
|-----------------|------------------------------------------------|----------|------------------------|------------|
| MH-163          | Live-prereq doc + checklist                    | 🔒 Locked | All Bucket 1+2 green  | No code yet |
| MH-NEWS-05L     | News Risk gate for live (manual approval req.) | 🔒 Locked | MH-NEWS-04, MH-163    | Requires explicit unlock |
| MH-COCKPIT-14   | Assisted Live Trade mode UI                    | 🔒 Locked | MH-163                | Per-trade approval only |
| MH-AI-01        | Per-task model env config                      | 🔒 Locked | MH-150                | `OPENAI_*` registry |
| MH-AI-02        | Per-call model parameter passing               | 🔒 Locked | MH-AI-01              | No silent default |
| MH-AI-03        | Decision-replay store                          | 🔒 Locked | MH-150, MH-159        | Immutable snapshots |
| MH-AI-04        | Strategy/model/prompt comparison harness       | 🔒 Locked | MH-AI-03              | Offline only |

### Park (Do Not Build Yet)

| Phase           | Title                                          | Status   | Notes |
|-----------------|------------------------------------------------|----------|-------|
| MH-COCKPIT-15   | Limited Auto Live Trade                        | ⛔ Parked | Requires 30+ days paper, 100+ trades, positive expectancy, manual unlock |

---

## Post-MH-141 Drift Lock Additions

Applies to ALL Bucket 1–4 phases above:

11. **Auto-paper enforcement stays OFF** until every Bucket 1 row is green and signed off in `docs/build-ledger.md`. `assert_auto_trading_allowed()` continues to raise unconditionally.
12. **News, Monitor, and Cockpit modules are consumption-only.** No FK from any trading table to `news_*`, `monitor_*`, or `cockpit_*` tables. One-way imports only (trading → none of them).
13. **News output is `evidence_class="research_only"`** at the DB-CHECK level. News may add caution; it must never relax a risk control.
14. **`trade_mode_settings.real_money_enabled` is forced `false`** by a DB CHECK constraint until MH-163 explicitly removes it.
15. **The "Auto Trade Today" button is permanently disabled** in the UI until Bucket 4 unlock; mode selectors render Live/Limited-Auto-Live as disabled with a lock tooltip.
16. **Loss-framing rule**: every plain-English explainer must surface downside before upside.
17. **No frontend toggle may bypass a backend gate.** Monitor and Cockpit pages render the gate state read-only; toggling UI must POST to a gated backend endpoint that re-validates.
18. **Broker submit decision timeline is body-hash-pinned.** The read-only handler `list_recent_broker_submit_decisions` and the client helper `getRecentBrokerSubmitDecisions` are SHA-256-pinned; any body change must re-verify read-only/GET-only posture and update the pinned constants. The cockpit-audit landing page must keep linking to `/cockpit/audit/broker-submit-decisions` via the read-only audit feed.
19. **Timeline page body is SHA-pinned.** `apps/web/app/cockpit/audit/broker-submit-decisions/page.tsx` is SHA-256-pinned (full file); any change must re-verify the page is still read-only/submit-free and update the hash. The cockpit audit hub tile must keep deriving its row-count from the audit envelope's `count` field; switching to `items.length`/`total`/`size`/`length` is explicitly forbidden.
20. **Sibling cockpit audit feeds carry explicit `response_model=` bindings.** `GET /risk-decisions/recent`, `GET /news-in-decision-log/recent`, `GET /llm-logs/recent`, and `GET /monitor/worker-run-log/overview` each bind a typed Pydantic envelope from `apps/api/app/schemas/audit_feeds.py`; the response-model catalog scan in `apps/api/tests/test_response_model_catalog_drift_lock.py` requires their presence, and `apps/api/tests/test_audit_feed_response_model_no_secret_drift_lock.py` forbids credential-shaped field names on every audit-feed schema (added 2026-06-01).

---

## Recommended Next 10 Phases (in order)

1. **MH-146** — `Position.opened_by` column + backfill (smallest migration; unblocks MH-155).
2. **MH-143** — Position Sizing Service (removes hardcoded `Decimal("1.0")`).
3. **MH-144** — Drop MARKET fallback in worker (LIMIT-only path).
4. **MH-145** — Real `RiskInput` values (spread, daily DD, recent losses).
5. **MH-148** — `BrokerSubmitDecision` audit table (persist preflight JSON).
6. **MH-147** — Unified `would_block` enforcement semantics (fail-closed).
7. **MH-154** — Persist structured risk-block reason.
8. **MH-153** — `risk_profile_id` denormalization onto orders/positions.
9. **MH-149** — Catalyst-context sanitization (prompt-injection guard).
10. **MH-150** — `LLMRequestLog` (full request/response, redacted).

(MH-151, MH-152, MH-MON-01..05 follow to close Bucket 1 before any enforcement-flip discussion.)
