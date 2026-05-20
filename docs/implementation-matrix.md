# Implementation Matrix

Date: 2026-05-20

## How To Use This Matrix

This is the control document for keeping work on track.

Every tracked item gets:

- a stable ID
- a layer classification
- a status
- a validation state
- a documentation state
- a notes field for drift, fixes, or blockers

## Restart Stabilisation Rebaseline

As of 2026-05-20, the current local validation baseline is:

- backend full suite: `2303 passed` against a migrated local `market_hunter` Postgres database
- learning suite: `99 passed` via `scripts/test/test-learning.sh`
- frontend build-ready evidence remains green from the same stabilisation pass
- smoke verification is green on the rebuilt web app with API running
- responsive verification is green
- visual verification is green after snapshot rebaseline: `48 passed`
- full Playwright verification is green: `280 passed`, `0 failed`
- MH-RESTART-004 plus MH-FEED-MONITOR-001 reconcile the live Gate 1 surface to 40 active backend route modules, 82 active backend service modules, 47 frontend route modules, and 49 shared TSX component modules; support files are catalogued separately below
- Gate 1 is green when the live route/service/page/component inventory still matches this file after the inventory diff checks recorded in the release-control pass

Status values:

- implemented
- mock-backed
- scaffold
- partial

Validation values:

- tested
- manually verified
- unverified

Documentation values:

- documented
- partial
- undocumented

## Workstream IDs

- WS-01: Source of truth and inventory
- WS-02: Build-order reconciliation
- WS-03: Architecture compliance audit
- WS-04: Theme and token governance
- WS-05: Regression baseline
- WS-06: New-feature integration review
- WS-07: Release gates and anti-drift process

## Backend Routes

| ID | File | Purpose | Status | Validation | Documentation | Workstream | Notes |
|---|---|---|---|---|---|---|---|
| API-R01 | `app/api/routes/health.py` | health endpoint | implemented | unverified | documented | WS-01 | Foundation route; expected Phase 1 complete |
| API-R02 | `app/api/routes/signals.py` | signal route surface | partial | manually verified | documented | WS-01 | Mock-safe and live-LLM signal endpoints plus `/signals/{signal_id}/features`; persistence failures are logged without breaking operator responses. Updated 2026-05-19 during MH-RESTART-004. |
| API-R03 | `app/api/routes/risk.py` | risk route surface | implemented | tested | documented | WS-01 | Thin deterministic route over RiskService and risk profile defaults with typed request/response schemas |
| API-R04 | `app/api/routes/workflow.py` | workflow route surface | partial | tested | documented | WS-01 | End-to-end workflow orchestration route; delegates signal, risk, execution-mode, approval, and paper/live branching to service layer; restart rebaseline refreshed Stage 6 smoke coverage by explicitly seeding the required `EURUSD` asset and retained the mock/live signal mode extraction. Updated 2026-05-19 during MH-RESTART-004. |
| API-R05 | `app/api/routes/approvals.py` | approval route surface | implemented | tested | documented | WS-01 | Approval creation plus alert rule, active alert, and notification routes backed by persistence services and typed schemas |
| API-R06 | `app/api/routes/execution.py` | execution route surface | partial | tested | documented | WS-01 | Paper execution lifecycle and journal routes plus live scaffold endpoint; business logic delegated to persistence and execution services; restart rebaseline fixed additive schema drift for `positions.close_price` |
| API-R07 | `app/api/routes/prompts.py` | prompt versioning route | implemented | tested | documented | WS-06 | GET /prompts lists system/ and user/ prompt files; GET /prompts/{subdir}/{filename} returns content; path traversal protected; 4 tests QA-081a-d passing 2026-04-24 |
| API-R08 | `app/api/routes/market_data.py` | market data status, sync, and news route | implemented | tested | documented | WS-06 | GET /market-data/status, POST /market-data/sync, and GET /market-data/news/{ticker}; covered by route tests and worker integration checks; documented 2026-04-24 |
| API-R09 | `app/api/routes/evals.py` | eval run listing and detail route | implemented | tested | documented | WS-06 | GET /evals/runs and GET /evals/runs/{id}; thin read-only route over EvalRun/EvalCase models; documented 2026-04-24 |
| API-R10 | `app/api/routes/assets.py` | asset universe CRUD | implemented | manually verified | partial | WS-03 | GET /assets plus create/deactivate flows over the Asset model; active route was previously stranded in the BP3 backlog section and was reclassified into the live inventory on 2026-05-19 |
| API-R11 | `app/api/routes/opportunities.py` | ranked opportunity list | implemented | manually verified | partial | WS-03 | GET /opportunities plus manual sweep trigger surface over OpportunityRankerService and SignalSweepWorker; active route reclassified from stale BP3 backlog on 2026-05-19 |
| API-R12 | `app/api/routes/performance.py` | performance stats endpoint | implemented | manually verified | partial | WS-03 | GET /performance-stats aggregates SignalOutcome win-rate breakdowns via PerformanceStatsService; active route reclassified from stale BP3 backlog on 2026-05-19 |
| API-R13 | `app/api/routes/prompt_adaptations.py` | prompt adaptation apply | implemented | manually verified | partial | WS-06 | POST /prompt-adaptations/apply creates a new PromptVersion row and never mutates an existing version in place; active route reclassified from stale BP3 backlog on 2026-05-19 |
| API-RX01 | `app/api/routes/asset_cards.py` | asset cards route surface | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-RX02 | `app/api/routes/baseline_candidates.py` | baseline candidates route surface | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-RX03 | `app/api/routes/broker.py` | broker route surface | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-RX04 | `app/api/routes/broker_submit_decisions.py` | broker submit decisions route surface | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-RX05 | `app/api/routes/cockpit_auto_paper_status.py` | cockpit auto paper status route surface | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-RX05A | `app/api/routes/cockpit_mode.py` | cockpit mode selector route surface | implemented | tested | documented | WS-01 | Added 2026-05-20 during MH-COCKPIT-03 as a safe `/cockpit/mode` GET/POST surface. Validation includes focused backend pytest and router drift-lock coverage. |
| API-RX06 | `app/api/routes/cockpit_notifications.py` | cockpit notifications route surface | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-RX07 | `app/api/routes/governance.py` | governance route surface | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-RX08 | `app/api/routes/llm_logs.py` | llm logs route surface | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-RX09 | `app/api/routes/markets.py` | markets route surface | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-RX10 | `app/api/routes/models.py` | models route surface | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-RX11 | `app/api/routes/monitor_health_history.py` | monitor health history route surface | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-RX12 | `app/api/routes/monitor_incidents.py` | monitor incidents route surface | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-RX13 | `app/api/routes/monitor_worker_run_log.py` | monitor worker run log route surface | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-RX14 | `app/api/routes/news_articles.py` | news articles route surface | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-RX15 | `app/api/routes/news_in_decision_log.py` | news in decision log route surface | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-RX16 | `app/api/routes/options.py` | options route surface | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-RX17 | `app/api/routes/paper_recommendations.py` | paper recommendations route surface | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-RX18 | `app/api/routes/paper_validation.py` | paper validation route surface | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-RX19 | `app/api/routes/regime.py` | regime route surface | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-RX20 | `app/api/routes/research_data.py` | research data route surface | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-RX21 | `app/api/routes/research_jobs.py` | research jobs route surface | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-RX22 | `app/api/routes/risk_decisions.py` | risk decisions route surface | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-RX23 | `app/api/routes/risk_limits.py` | risk limits route surface | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-RX24 | `app/api/routes/scoring.py` | scoring route surface | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-RX25 | `app/api/routes/strategy_lab.py` | strategy lab route surface | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-RX26 | `app/api/routes/trading_halt.py` | trading halt route surface | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-RX27 | `app/api/routes/monitor_feeds.py` | monitor feeds route surface | implemented | tested | partial | WS-01 | Added 2026-05-19 during MH-FEED-MONITOR-001 as a read-only `/monitor/feeds` aggregator over provider probes plus broker gateway runtime reachability. |

## Backend Clients

| ID | File | Purpose | Status | Validation | Documentation | Workstream | Notes |
|---|---|---|---|---|---|---|---|
| API-C01 | `app/clients/market_data/polygon_client.py` | Polygon bar-data client | implemented | tested | documented | WS-02 | Async Polygon REST client with typed BarData mapping, timeframe normalization, auth/error handling, and safe empty-key no-op behavior |
| API-C02 | `app/clients/market_data/news_client.py` | Polygon news client scaffold | implemented | tested | documented | WS-02 | Compatibility module exports NewsClient, PolygonNewsClient scaffold, and provider factory; current RC-2 behavior degrades safely to empty results |
| API-C03 | `app/clients/broker/broker_interface.py` | broker adapter protocol | implemented | tested | documented | WS-02 | BrokerInterface protocol expanded: PositionInfo dataclass added; AccountInfo gains excess_liquidity, margin, unrealized_pnl; get_positions() added to protocol (Phase 15 2026-04-24) |
| API-C04 | `app/clients/broker/ibkr_adapter.py` | IB REST API 2.30.0 adapter | implemented | tested | documented | WS-02 | Full IBKRAdapter: session (connect/tickle/disconnect), contract lookup, account info, positions, order submit/cancel/modify, bracket orders, OCA orders, snapshot, history, options chain discovery (Phase 15 2026-04-24) |
| API-C05 | `app/clients/broker/gateway_factory.py` | broker gateway factory | implemented | tested | partial | WS-02 | Broker boundary support surface. Inventoried 2026-05-19 during MH-RESTART-004. |
| API-C06 | `app/clients/market_data/{base,ibkr,mock,tiingo,twelvedata,yfinance_client}.py` | market data client family | implemented | unverified | partial | WS-02 | Active client files: `base.py`, `ibkr.py`, `mock.py`, `tiingo.py`, `twelvedata.py`, `yfinance_client.py`. Inventoried 2026-05-19 during MH-RESTART-004. |
| API-C07 | `app/clients/news/{base,mock,gdelt,perplexity,finnhub,alpaca_news,news_client}.py` | news provider client family | implemented | unverified | partial | WS-02 | Active client files: `base.py`, `mock.py`, `gdelt.py`, `perplexity.py`, `finnhub.py`, `alpaca_news.py`, `news_client.py`. Inventoried 2026-05-19 during MH-RESTART-004. |
| API-C08 | `app/clients/macro/{base,mock,fred}.py` | macro client family | implemented | unverified | partial | WS-02 | Active client files: `base.py`, `mock.py`, `fred.py`. Inventoried 2026-05-19 during MH-RESTART-004. |
| API-C09 | `app/clients/fundamentals/{base,mock,sec}.py` | fundamentals client family | implemented | unverified | partial | WS-02 | Active client files: `base.py`, `mock.py`, `sec.py`. Inventoried 2026-05-19 during MH-RESTART-004. |
| API-C10 | `app/clients/llm/{base,helpers,router,openai_provider}.py` | llm provider client family | implemented | tested | partial | WS-02 | Active client files: `base.py`, `helpers.py`, `router.py`, `openai_provider.py`. Inventoried 2026-05-19 during MH-RESTART-004. |

## Backend Services

| ID | File | Purpose | Status | Validation | Documentation | Workstream | Notes |
|---|---|---|---|---|---|---|---|
| API-S01 | `app/services/signal_service.py` | signal generation orchestration | implemented | tested | documented | WS-01 | Covered by Phase 5 summary |
| API-S02 | `app/services/risk_service.py` | risk evaluation | implemented | tested | partial | WS-01 | Actively used by risk and workflow routes; still needs architecture-rule audit |
| API-S03 | `app/services/risk_profile_service.py` | risk profile logic | partial | unverified | partial | WS-01 | Exists; needs contract audit |
| API-S04 | `app/services/execution_mode_service.py` | execution routing policy | implemented | tested | partial | WS-01 | Used by risk and workflow routing decisions |
| API-S05 | `app/services/paper_execution_service.py` | paper execution flow | implemented | tested | documented | WS-01 | DB-backed order lifecycle: create_order (pending), simulate_fill (filled), close_order (closed); stateless PaperExecutionResult kept for backward compat; documented 2026-04-24 |
| API-S06 | `app/services/live_execution_service.py` | live execution scaffold | scaffold | tested | documented | WS-01 | Always returns accepted=False, status=disabled, reason=live_execution_disabled_in_mvp; session arg optional; test_execution_live_route asserts all three sentinel fields; documented 2026-04-24 |
| API-S07 | `app/services/approval_service.py` | approval workflow logic | implemented | tested | documented | WS-01 | Dual-mode: session-based create_request(risk_decision_id, reason) and stateless create_request(signal, execution_mode, risk_approved, ttl_minutes); used by /approvals/create and workflow route; documented 2026-04-24 |
| API-S08 | `app/services/workflow_service.py` | workflow orchestration | partial | tested | documented | WS-01 | Orchestrates signal→risk→execution_mode→approval/paper/live branch; WorkflowResult typed summary; runs with mock or real signal generator via SignalGenerator protocol; documented 2026-04-24 |
| API-S09 | `app/services/execution_journal_service.py` | execution journaling | implemented | manually verified | documented | WS-01 | File-backed JSON store (thread-safe); get_journal and upsert_journal by UUID; ExecutionJournalRecord with outcome_tag, note, tags, updated_at; documented 2026-04-24 |
| API-S10 | `app/services/feature_service.py` | feature service orchestration | implemented | tested | documented | WS-01 | Backed by Phase 3 docs |
| API-S11 | `app/services/feature_adapter_service.py` | feature adaptation layer | implemented | tested | documented | WS-03 | Loads ORM Bar/Quote rows for an asset, maps to FeatureInput, calls build_feature_snapshot; architecture-compliant thin adapter; no business logic; documented and audited 2026-04-24 |
| API-S12 | `app/services/mock_signal_service.py` | deterministic no-trade mock signal | implemented | manually verified | partial | WS-03 | Extracted from inline route class 2026-04-23; used by workflow service |
| API-S13 | `app/services/market_data_service.py` | market data ingestion orchestration | implemented | tested | documented | WS-02 | Upserts bar rows from MarketDataClient input keyed by asset/timeframe/timestamp; AssetNotFoundError on missing ticker; documented 2026-04-24 |
| API-S14 | `app/services/position_service.py` | position lifecycle service | implemented | tested | documented | WS-06 | Opens, marks to market, closes, and lists positions with typed PositionResult values; documented 2026-04-24 |
| API-S15 | `app/services/pnl_service.py` | pnl snapshot service | implemented | tested | documented | WS-06 | Records equity/PnL snapshots and returns latest/recent history ordered oldest-first for charting; documented 2026-04-24 |
| API-S16 | `app/services/prompt_version_service.py` | prompt version seeding service | implemented | tested | documented | WS-06 | Seeds PromptVersion rows from prompt files with hash-based idempotency and filename-derived role/version metadata; documented 2026-04-24 |
| API-S17 | `app/services/opportunity_ranker_service.py` | signal scoring and ranking | implemented | manually verified | partial | WS-03 | Live ranking service used by `/opportunities`; stale BP3 backlog entry was promoted into the active inventory on 2026-05-19 |
| API-S18 | `app/services/performance_stats_service.py` | outcome win-rate analytics | implemented | manually verified | partial | WS-06 | Aggregates win-rate breakdowns by setup, asset, catalyst, and regime for `/performance-stats`; stale BP3 entry promoted into the active inventory on 2026-05-19 |
| API-S19 | `app/services/prompt_adaptation_service.py` | AI-driven prompt improvement support | partial | unverified | partial | WS-06 | Active service surface exists in the repo and was removed from the stale BP3 backlog on 2026-05-19; deeper validation/classification still pending |
| API-SX01 | `app/services/advanced_order_service.py` | advanced order service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX02 | `app/services/asset_card_service.py` | asset card service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX03 | `app/services/audit_log_service.py` | audit log service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX04 | `app/services/ai_backtest_report_service.py` | ai backtest report service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX05 | `app/services/baseline_candidate_service.py` | baseline candidate service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX06 | `app/services/broker_mode_guard.py` | broker mode guard service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX07 | `app/services/broker_service.py` | broker service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX08 | `app/services/broker_trade_event_service.py` | broker trade event service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX09 | `app/services/cockpit_auto_paper_status_service.py` | cockpit auto paper status service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX09A | `app/services/cockpit_mode_service.py` | cockpit mode selector service | implemented | tested | documented | WS-01 | Added 2026-05-20 during MH-COCKPIT-03 as an advisory-only selector layered on top of trading-control state; locked live modes are rejected server-side and live flags stay false. |
| API-SX10 | `app/services/commission_tracking_service.py` | commission tracking service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX11 | `app/services/contract_resolution_service.py` | contract resolution service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX12 | `app/services/correlation_context.py` | correlation context service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX13 | `app/services/data_quality_engine.py` | data quality engine service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX14 | `app/services/eval_persistence_service.py` | eval persistence service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX15 | `app/services/execution_cost_model.py` | execution cost model service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX16 | `app/services/feeds_in_probe.py` | feeds in probe service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX17 | `app/services/feeds_out_probe.py` | feeds out probe service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX18 | `app/services/flex_reconciliation_service.py` | flex reconciliation service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX19 | `app/services/health_history_service.py` | health history service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX20 | `app/services/health_registry.py` | health registry service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX21 | `app/services/historical_import_service.py` | historical import service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX22 | `app/services/historical_replay_service.py` | historical replay service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX23 | `app/services/ibkr_market_data_service.py` | ibkr market data service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX24 | `app/services/ibkr_pnl_service.py` | ibkr pnl service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX25 | `app/services/incident_log_service.py` | incident log service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX26 | `app/services/llm_input_sanitizer.py` | llm input sanitizer service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX27 | `app/services/llm_request_log_sink.py` | llm request log sink service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX28 | `app/services/market_context_snapshot_service.py` | market context snapshot service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX29 | `app/services/market_data_coverage_service.py` | market data coverage service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX30 | `app/services/market_data_quality_service.py` | market data quality service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX31 | `app/services/market_session_service.py` | market session service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX32 | `app/services/mock_trade_simulator_service.py` | mock trade simulator service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX33 | `app/services/news_cache_service.py` | news cache service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX34 | `app/services/news_normalizer.py` | news normalizer service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX35 | `app/services/notifications_digest_service.py` | notifications digest service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX36 | `app/services/option_chain_service.py` | option chain service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX37 | `app/services/paper_recommendation_service.py` | paper recommendation service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX38 | `app/services/paper_validation_service.py` | paper validation service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX39 | `app/services/pnl_snapshot_worker.py` | pnl snapshot worker service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX40 | `app/services/position_sizing_service.py` | position sizing service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX41 | `app/services/prompt_registry.py` | prompt registry service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX42 | `app/services/provider_inventory_service.py` | provider inventory service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX43 | `app/services/research_job_service.py` | research job service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX44 | `app/services/risk_limit_service.py` | risk limit service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX45 | `app/services/signal_geometry_validator.py` | signal geometry validator service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX46 | `app/services/strategy_comparison_service.py` | strategy comparison service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX47 | `app/services/strategy_lab_service.py` | strategy lab service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX48 | `app/services/strategy_result_quality_service.py` | strategy result quality service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX49 | `app/services/trading_control_arming_state_service.py` | trading control arming state service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX50 | `app/services/trading_control_service.py` | trading control service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX51 | `app/services/trading_halt_service.py` | trading halt service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX52 | `app/services/trading_safety_aggregator.py` | trading safety aggregator service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX53 | `app/services/visual_seed.py` | visual seed service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX54 | `app/services/walk_forward_validation_service.py` | walk forward validation service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX55 | `app/services/worker_run_log_overview_service.py` | worker run log overview service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX56 | `app/services/worker_run_log_service.py` | worker run log service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX57 | `app/services/governance/model_audit_service.py` | model audit service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX58 | `app/services/governance/model_candidate_service.py` | model candidate service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX59 | `app/services/governance/model_policy_service.py` | model policy service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX60 | `app/services/governance/model_promotion_service.py` | model promotion service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX61 | `app/services/governance/model_registry_service.py` | model registry service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX62 | `app/services/governance/model_rollback_service.py` | model rollback service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX63 | `app/services/market/fundamentals_ingestion_service.py` | fundamentals ingestion service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX64 | `app/services/market/instrument_registry_service.py` | instrument registry service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX65 | `app/services/market/macro_ingestion_service.py` | macro ingestion service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX66 | `app/services/market/market_data_ingestion_service.py` | market data ingestion service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX67 | `app/services/market/news_ingestion_service.py` | news ingestion service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX68 | `app/services/market/provider_dispatcher_service.py` | provider dispatcher service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX69 | `app/services/runtime/scoring/dnt_probability_service.py` | dnt probability service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX70 | `app/services/runtime/scoring/score_bucket_service.py` | score bucket service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX71 | `app/services/runtime/scoring/score_calibration_service.py` | score calibration service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX72 | `app/services/runtime/scoring/score_explainer.py` | score explainer service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX73 | `app/services/runtime/scoring/score_resolver.py` | score resolver service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX74 | `app/services/runtime/scoring/score_threshold_service.py` | score threshold service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX75 | `app/services/runtime/scoring_config_service.py` | scoring config service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX76 | `app/services/runtime/scoring_service.py` | scoring service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX77 | `app/services/runtime/signal_generation_service.py` | signal generation service | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| API-SX78 | `app/services/feed_monitor_service.py` | feed monitor service | implemented | tested | partial | WS-01 | Added 2026-05-19 during MH-FEED-MONITOR-001; consolidates feeds-in, feeds-out, and broker gateway runtime posture without mutating any provider or trading control. |

## Backend Persistence Services

| ID | File | Purpose | Status | Validation | Documentation | Workstream | Notes |
|---|---|---|---|---|---|---|---|
| API-P01 | `app/services/persistence_signal_service.py` | signal persistence | implemented | tested | documented | WS-01 | Persists Signal, RiskDecision, and FeatureSnapshot rows; used by signal and workflow routes with graceful DB-failure handling; restart rebaseline confirmed workflow smoke coverage once required asset state was seeded explicitly |
| API-P02 | `app/services/persistence_alert_service.py` | alert persistence | implemented | manually verified | documented | WS-01 | Persists AlertRule entities; derives active alerts from execution context; owned by /approvals/alerts endpoints; documented 2026-04-24 |
| API-P03 | `app/services/persistence_approval_service.py` | approval persistence | implemented | tested | documented | WS-01 | persist_approval_request(signal_id, approval_request) links ApprovalRequest to signal; owned by /approvals/create and workflow route; documented 2026-04-24 |
| API-P04 | `app/services/persistence_notification_service.py` | notification persistence | implemented | manually verified | documented | WS-01 | Persists Notification entities; supports mark-read and list flows; owned by /approvals/alerts/notifications; documented 2026-04-24 |
| API-P05 | `app/services/persistence_paper_execution_service.py` | paper execution persistence | implemented | tested | documented | WS-01 | list, get, fill, close paper orders from DB; _to_service_status maps OrderStatus enum/string to service vocabulary; owned by /execution/paper endpoints; documented 2026-04-24 |
| API-P06 | `app/services/persistence_signal_outcome.py` | signal outcome persistence | implemented | unverified | partial | WS-06 | Inventoried 2026-05-19 during MH-RESTART-004. |

## Backend Schemas

| ID | File | Purpose | Status | Validation | Documentation | Workstream | Notes |
|---|---|---|---|---|---|---|---|
| API-H01 | `app/schemas/feed_monitor.py` | feed monitor response schemas | implemented | tested | partial | WS-01 | Added 2026-05-19 during MH-FEED-MONITOR-001; defines the typed read-only `/monitor/feeds` response contract consumed by the route and browser surface. |

## Frontend Routes

| ID | File | Route | Status | Validation | Documentation | Workstream | Notes |
|---|---|---|---|---|---|---|---|
| WEB-P01 | `app/page.tsx` | `/` | implemented | tested | partial | WS-01 | Home route uses PersonalDashboard; smoke test QA-001 passing |
| WEB-P02 | `app/dashboard/page.tsx` | `/dashboard` | implemented | unverified | documented | WS-01 | Thin route over PersonalDashboard; loads real execution, alerts, notification, and rule data; API deps: /execution/paper, /approvals/alerts/*, /approvals/alerts/notifications; documented 2026-04-24 |
| WEB-P03 | `app/analytics/page.tsx` | `/analytics` | implemented | manually verified | documented | WS-01 | Derived execution analytics; API deps: /execution/paper (list); renders LineChart, SeriesToggle, TimeRangeBar; documented 2026-04-24. Fresh Playwright reruns are green on 2026-05-19 after the chart empty-state repair and stable SVG assertions. |
| WEB-P04 | `app/workflow/page.tsx` | `/workflow` | partial | tested | documented | WS-01 | Workflow operator page over `/workflow/run`; supports mock/live signal mode and approval-aware orchestration summaries. Real LLM toggle and service-layer extraction remain in place after MH-RESTART-004. |
| WEB-P05 | `app/signals/page.tsx` | `/signals` | partial | tested | documented | WS-01 | Signal builder supports mock generation path, custom mode, result inspection, market-data freshness badge, recent-news panel, and the real-LLM toggle. Updated 2026-05-19 during MH-RESTART-004. |
| WEB-P06 | `app/risk/page.tsx` | `/risk` | partial | tested | documented | WS-01 | Risk evaluation page builds operator-controlled payloads and submits them to the real risk route; full risk context coverage remains present. Updated 2026-05-19 during MH-RESTART-004. |
| WEB-P07 | `app/approvals/page.tsx` | `/approvals` | partial | tested | documented | WS-01 | Creates real approval records and exposes alert/notification views; signal quality and price-level inputs remain wired for realistic scenarios. Updated 2026-05-19 during MH-RESTART-004. |
| WEB-P08 | `app/execution/page.tsx` | `/execution` | partial | tested | documented | WS-01 | Paper execution list/detail/history/journal + live scaffold guard; API deps: /execution/paper, /execution/paper/{id}, /execution/paper/{id}/fill, /execution/paper/{id}/close, /execution/paper/{id}/journal, /execution/live; documented 2026-04-24 |
| WEB-P09 | `app/alerts/page.tsx` | `/alerts` | implemented | manually verified | documented | WS-01 | Real route: alert rules, active alerts, notifications, watchlist/chart; API deps: /approvals/alerts/rules, /approvals/alerts/active, /approvals/alerts/notifications; documented 2026-04-24. Fresh Playwright reruns are green on 2026-05-19 after the watchlist chart shell repair and stable SVG assertions. |
| WEB-P10 | `app/notifications/page.tsx` | `/notifications` | implemented | unverified | documented | WS-01 | Operator notification surface via OperatorNotificationSurface component; API deps: /approvals/alerts/notifications; documented 2026-04-24 |
| WEB-P11 | `app/prompts/page.tsx` | `/prompts` | implemented | manually verified | documented | WS-06 | Lists prompt files, renders selected content, and now shows persisted prompt version history via GET /prompts/{subdir}/{filename}/history |
| WEB-P12 | `app/evals/page.tsx` | `/evals` | implemented | manually verified | documented | WS-06 | Fetches GET /evals/runs and renders evaluation-run table with provider, score, pass rate, and timestamps; added 2026-04-24 |
| WEB-P13 | `app/assets/page.tsx` | `/assets` | implemented | manually verified | partial | WS-04 | Active universe route is live in the app and was reclassified out of the stale BP3 backlog on 2026-05-19 |
| WEB-P14 | `app/opportunities/page.tsx` | `/opportunities` | implemented | manually verified | partial | WS-04 | Ranked opportunities route is live in the app and was reclassified out of the stale BP3 backlog on 2026-05-19 |
| WEB-P15 | `app/performance/page.tsx` | `/performance` | implemented | manually verified | partial | WS-04 | Performance dashboard route is live in the app and was reclassified out of the stale BP3 backlog on 2026-05-19 |
| WEB-P16 | `app/prompt-adaptations/page.tsx` | `/prompt-adaptations` | implemented | manually verified | partial | WS-04 | Prompt adaptation proposals route is live in the app and was reclassified out of the stale BP3 backlog on 2026-05-19 |
| WEB-PX01 | `app/regime/page.tsx` | `/regime` | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-PX02 | `app/asset-cards/page.tsx` | `/asset-cards` | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-PX03 | `app/asset-cards/[id]/page.tsx` | `/asset-cards/[id]` | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-PX04 | `app/explainer/page.tsx` | `/explainer` | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-PX05 | `app/system-health/page.tsx` | `/system-health` | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-PX06 | `app/strategy-lab/page.tsx` | `/strategy-lab` | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-PX07 | `app/cockpit/notifications/page.tsx` | `/cockpit/notifications` | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-PX08 | `app/cockpit/page.tsx` | `/cockpit` | implemented | tested | documented | WS-01 | Updated 2026-05-20 during MH-COCKPIT-03 from a static hub into an operator-facing mode selector with selectable Learning / Manual / Auto Paper states, locked live-mode cards, backend safety notes, and preserved cockpit links. Exact route, smoke, responsive, and dedicated mocked Playwright coverage passed. |
| WEB-PX09 | `app/cockpit/auto-paper-status/page.tsx` | `/cockpit/auto-paper-status` | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-PX10 | `app/cockpit/news/page.tsx` | `/cockpit/news` | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-PX11 | `app/cockpit/audit/page.tsx` | `/cockpit/audit` | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-PX12 | `app/cockpit/audit/broker-submit-decisions/page.tsx` | `/cockpit/audit/broker-submit-decisions` | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-PX13 | `app/cockpit/audit/risk-decisions/page.tsx` | `/cockpit/audit/risk-decisions` | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-PX14 | `app/cockpit/audit/news-in-decision-log/page.tsx` | `/cockpit/audit/news-in-decision-log` | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-PX15 | `app/cockpit/audit/llm-logs/page.tsx` | `/cockpit/audit/llm-logs` | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-PX16 | `app/replay/page.tsx` | `/replay` | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-PX17 | `app/cockpit/audit/worker-run-log/page.tsx` | `/cockpit/audit/worker-run-log` | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-PX18 | `app/data-centre/page.tsx` | `/data-centre` | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-PX19 | `app/models/page.tsx` | `/models` | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-PX20 | `app/data-quality/page.tsx` | `/data-quality` | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-PX21 | `app/news-archive/page.tsx` | `/news-archive` | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-PX22 | `app/drift/page.tsx` | `/drift` | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-PX23 | `app/promotions/page.tsx` | `/promotions` | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-PX24 | `app/markets-open/page.tsx` | `/markets-open` | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-PX25 | `app/monitor/health-history/page.tsx` | `/monitor/health-history` | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-PX26 | `app/monitor/worker-run-log/page.tsx` | `/monitor/worker-run-log` | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-PX27 | `app/calibration/page.tsx` | `/calibration` | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-PX28 | `app/providers/page.tsx` | `/providers` | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-PX29 | `app/broker/page.tsx` | `/broker` | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-PX30 | `app/news/page.tsx` | `/news` | implemented | unverified | partial | WS-01 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-PX31 | `app/monitor/feeds/page.tsx` | `/monitor/feeds` | implemented | tested | partial | WS-01 | Added 2026-05-19 during MH-FEED-MONITOR-001 as a filterable operator-facing page over the new read-only feed monitor API; dedicated route, smoke, responsive, and mocked browser coverage landed on 2026-05-20, and the final full visual (`48/48`) plus full Playwright (`280/280`) gates were recovered during MH-FEED-MONITOR-005. |

## Shared Frontend Foundations

| ID | File | Purpose | Status | Validation | Documentation | Workstream | Notes |
|---|---|---|---|---|---|---|---|
| WEB-F01 | `app/layout.tsx` | root layout and theme bootstrap | implemented | manually verified | documented | WS-04 | Root theme persistence now handled before hydration; foundation route shell remains stable across all pages |
| WEB-F02 | `app/globals.css` | semantic token system | implemented | manually verified | documented | WS-04 | Shared token system covers dark/light themes, state surfaces, chart series, and responsive shell tokens; governance gates documented 2026-04-24 |
| WEB-F03 | `components/Nav.tsx` | global nav and theme toggle | implemented | manually verified | documented | WS-04 | Global navigation and theme control shared across all app routes; syncs persisted theme with layout bootstrap |
| WEB-F04 | `app/globals.css` (responsive section) | responsive breakpoint utility system | implemented | manually verified | partial | WS-04 | Added 2026-04-23; `data-rs` attribute system with `@media` rules at 768px and 1024px; covers two-col, three-col, stat-grid, dense-row, hero-title, form-result-split, notification-row, watchlist-row, intelligence-row; QA-060 through QA-072. Fresh responsive rerun is green on 2026-05-19 after the 390px topbar overflow fix. |

## Shared UI Components

| ID | File | Purpose | Status | Validation | Documentation | Workstream | Notes |
|---|---|---|---|---|---|---|---|
| WEB-U01 | `components/PersonalDashboard.tsx` | dashboard orchestration surface | implemented | manually verified | documented | WS-06 | Loads real execution, alert, notification, and rule data for dashboard and home routes; documented 2026-04-24 |
| WEB-U02 | `components/OperatorNotificationSurface.tsx` | shared notification list surface | implemented | manually verified | documented | WS-06 | Lists operator notifications with mark-read; API dep: /approvals/alerts/notifications; documented 2026-04-24 |

## Additional Shared Components

| ID | File | Purpose | Status | Validation | Documentation | Workstream | Notes |
|---|---|---|---|---|---|---|---|
| WEB-UX01 | `components/FormSection.tsx` | FormSection shared component | implemented | unverified | partial | WS-04 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-UX02 | `components/regime/RegimeHistory.tsx` | regime RegimeHistory shared component | implemented | unverified | partial | WS-04 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-UX03 | `components/regime/RegimeMonitor.tsx` | regime RegimeMonitor shared component | implemented | unverified | partial | WS-04 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-UX04 | `components/InfographicRing.tsx` | InfographicRing shared component | implemented | unverified | partial | WS-04 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-UX05 | `components/OperatorAnalyticsPanel.tsx` | OperatorAnalyticsPanel shared component | implemented | unverified | partial | WS-04 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-UX06 | `components/ExecutionJournalPanel.tsx` | ExecutionJournalPanel shared component | implemented | unverified | partial | WS-04 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-UX07 | `components/replay/ReplayLab.tsx` | replay ReplayLab shared component | implemented | unverified | partial | WS-04 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-UX08 | `components/LearnTooltip.tsx` | LearnTooltip shared component | implemented | unverified | partial | WS-04 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-UX09 | `components/news/NewsIntelligence.tsx` | news NewsIntelligence shared component | implemented | unverified | partial | WS-04 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-UX10 | `components/promotions/PromotionQueue.tsx` | promotions PromotionQueue shared component | implemented | unverified | partial | WS-04 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-UX11 | `components/dashboard/DashboardChartsSection.tsx` | dashboard DashboardChartsSection shared component | implemented | unverified | partial | WS-04 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-UX12 | `components/dashboard/DashboardMetricsSection.tsx` | dashboard DashboardMetricsSection shared component | implemented | unverified | partial | WS-04 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-UX13 | `components/dashboard/DashboardAlertsSection.tsx` | dashboard DashboardAlertsSection shared component | implemented | unverified | partial | WS-04 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-UX14 | `components/LearningModePanel.tsx` | LearningModePanel shared component | implemented | unverified | partial | WS-04 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-UX15 | `components/ui/EmptyState.tsx` | ui EmptyState shared component | implemented | unverified | partial | WS-04 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-UX16 | `components/ui/Button.tsx` | ui Button shared component | implemented | unverified | partial | WS-04 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-UX17 | `components/ui/Badge.tsx` | ui Badge shared component | implemented | unverified | partial | WS-04 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-UX18 | `components/ui/DataTable.tsx` | ui DataTable shared component | implemented | unverified | partial | WS-04 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-UX19 | `components/ui/MetricCard.tsx` | ui MetricCard shared component | implemented | unverified | partial | WS-04 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-UX20 | `components/ui/Panel.tsx` | ui Panel shared component | implemented | unverified | partial | WS-04 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-UX21 | `components/ui/StatusChip.tsx` | ui StatusChip shared component | implemented | unverified | partial | WS-04 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-UX22 | `components/ui/PageShell.tsx` | ui PageShell shared component | implemented | unverified | partial | WS-04 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-UX23 | `components/ui/FilterBar.tsx` | ui FilterBar shared component | implemented | unverified | partial | WS-04 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-UX24 | `components/ui/Card.tsx` | ui Card shared component | implemented | unverified | partial | WS-04 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-UX25 | `components/JsonCard.tsx` | JsonCard shared component | implemented | unverified | partial | WS-04 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-UX26 | `components/drift/DriftDetector.tsx` | drift DriftDetector shared component | implemented | unverified | partial | WS-04 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-UX27 | `components/models/ModelRegistry.tsx` | models ModelRegistry shared component | implemented | unverified | partial | WS-04 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-UX28 | `components/models/ModelVersionDetail.tsx` | models ModelVersionDetail shared component | implemented | unverified | partial | WS-04 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-UX29 | `components/models/ModelMetrics.tsx` | models ModelMetrics shared component | implemented | unverified | partial | WS-04 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-UX30 | `components/StatCard.tsx` | StatCard shared component | implemented | unverified | partial | WS-04 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-UX31 | `components/JournalAttentionWidget.tsx` | JournalAttentionWidget shared component | implemented | unverified | partial | WS-04 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-UX32 | `components/shell/Sidebar.tsx` | shell Sidebar shared component | implemented | unverified | partial | WS-04 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-UX33 | `components/shell/AppShell.tsx` | shell AppShell shared component | implemented | unverified | partial | WS-04 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-UX34 | `components/shell/PageHeader.tsx` | shell PageHeader shared component | implemented | unverified | partial | WS-04 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-UX35 | `components/shell/Topbar.tsx` | shell Topbar shared component | implemented | unverified | partial | WS-04 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-UX36 | `components/shell/SidebarSection.tsx` | shell SidebarSection shared component | implemented | unverified | partial | WS-04 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-UX37 | `components/calibration/CalibrationPlots.tsx` | calibration CalibrationPlots shared component | implemented | unverified | partial | WS-04 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-UX38 | `components/HeatmapPanel.tsx` | HeatmapPanel shared component | implemented | unverified | partial | WS-04 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-UX39 | `components/CompactBars.tsx` | CompactBars shared component | implemented | unverified | partial | WS-04 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-UX40 | `components/WorkflowResultCard.tsx` | WorkflowResultCard shared component | implemented | unverified | partial | WS-04 | Inventoried 2026-05-19 during MH-RESTART-004. |
| WEB-UX41 | `components/OutcomeAnalysisPanel.tsx` | OutcomeAnalysisPanel shared component | implemented | unverified | partial | WS-04 | Inventoried 2026-05-19 during MH-RESTART-004. |

## Shared Chart Components

| ID | File | Purpose | Status | Validation | Documentation | Workstream | Notes |
|---|---|---|---|---|---|---|---|
| WEB-C01 | `components/chart/ChartPanel.tsx` | chart container surface | implemented | manually verified | documented | WS-06 | Wrapper for chart children with title, controls, theme-aware border; used on analytics/execution/alerts; documented 2026-04-24 |
| WEB-C02 | `components/chart/LineChart.tsx` | shared line chart renderer | implemented | manually verified | documented | WS-05 | SVG line/area chart; single-point fallback renders circle; props: data, series, colors via CSS tokens; documented 2026-04-24. Fresh Playwright reruns are green on 2026-05-19 after the empty-state SVG stub and stable aria-label test anchor update. |
| WEB-C03 | `components/chart/PriceLevelChart.tsx` | price-level visualization | partial | unverified | documented | WS-06 | Visualizes entry zone, stop, target price levels; needs theme contrast coverage; documented 2026-04-24 |
| WEB-C04 | `components/chart/SeriesToggle.tsx` | series visibility controls | implemented | manually verified | documented | WS-05 | Toggle buttons for showing/hiding named chart series; used in analytics/execution; documented 2026-04-24 |
| WEB-C05 | `components/chart/TimeRangeBar.tsx` | chart range controls | implemented | manually verified | documented | WS-05 | Preset range selector (7d, 30d, 90d, all); controls time filter for chart data; documented 2026-04-24 |

## Validation Surfaces

| ID | File | Scope | Status | Validation | Documentation | Workstream | Notes |
|---|---|---|---|---|---|---|---|
| QA-T01 | `apps/web/tests/smoke.spec.ts` | frontend smoke coverage | partial | tested | partial | WS-05 | Good start, insufficient for current route breadth |
| QA-T06 | `apps/web/tests/regression.spec.ts` | frontend regression coverage | implemented | tested | documented | WS-05 | Targeted chart/browser regressions are green on 2026-05-19 and the fresh full Playwright rerun is now release-green for this surface |
| QA-T07 | `apps/web/tests/responsive.spec.ts` | responsive regression coverage | implemented | tested | documented | WS-05 | Fresh responsive rerun is green on 2026-05-19 after the 390px topbar overflow fix |
| QA-T02 | `apps/api/tests/clients` | LLM client coverage | implemented | tested | documented | WS-05 | Backed by Phase 4 docs |
| QA-T03 | `apps/api/tests/features` | feature coverage | implemented | tested | documented | WS-05 | Backed by Phase 3 docs |
| QA-T04 | `apps/api/tests/indicators` | indicator coverage | implemented | tested | documented | WS-05 | Backed by Phase 3 docs |
| QA-T05 | `apps/api/tests/services` | service coverage | partial | tested | documented | WS-05 | Service and integration baseline rerun on 2026-05-19 finished `2301 passed`, `0 warnings`; backend test coverage is green and no longer the release blocker |
| QA-T08 | `apps/api/tests/evals/test_signal_output_eval.py` | eval harness — signal output structural invariants | implemented | tested | documented | WS-05 | 13 structural invariant checks for SignalOutput (QA-082); deterministic mock LLM; added 2026-04-24 |
| QA-T09 | `apps/api/tests/test_prompts_route.py` | prompts route coverage | implemented | tested | documented | WS-06 | 4 tests QA-081a-d covering list, content, 404 for unknown file, 404 for disallowed subdir; added 2026-04-24 |
| QA-T10 | `apps/web/tests/routes.spec.ts` | frontend route-render inventory coverage | implemented | tested | documented | WS-05 | Covers core plus auxiliary routes including `/data-centre`, `/strategy-lab`, and `/data-quality`; full Playwright rerun green on 2026-05-19 |
| QA-T11 | `apps/web/tests/full-flow.spec.ts` | navigation and flow coverage | implemented | tested | documented | WS-05 | Covers sidebar navigation, broker/stage-5 route access, signal/risk/workflow/execution flows, and key API retrieval checks; full Playwright rerun green on 2026-05-19 |
| QA-T12 | `apps/web/tests/{broker-health-and-control,broker-submit-and-dry-run,broker-provenance-and-audit,broker-readiness-history}.spec.ts` | broker UI and audit coverage | implemented | tested | documented | WS-05 | Broker and cockpit browser slices remain green inside the full Playwright rerun on 2026-05-19 |
| QA-T13 | `apps/web/tests/visual.spec.ts` | visual baseline coverage | implemented | tested | documented | WS-05 | Snapshot suite passed `48/48` on 2026-05-19 after responsive verification and rebaseline |
| QA-T14 | `apps/api/tests/test_router_include_catalog_drift_lock.py` | backend router registry coverage | implemented | tested | documented | WS-05 | Route include catalog stays pinned against `app.main`; full backend pytest rerun green on 2026-05-19 |
| QA-T15 | `apps/api/tests/routes` | backend route and safety route coverage | implemented | tested | documented | WS-05 | Route suites cover broker, broker health, risk limits, trading halt, paper recommendations, and broker audit paths; full backend pytest rerun green on 2026-05-19 |
| QA-T16 | `apps/api/tests/test_phase3_routes.py` | scoring/models/governance/regime route coverage | implemented | tested | documented | WS-05 | Phase 3 route suite covers scoring, models, governance, and regime endpoints; full backend pytest rerun green on 2026-05-19 |
| QA-T17 | `apps/api/tests/{test_route_registry_drift_lock.py,test_router_prefix_catalog_drift_lock.py}` | route inventory drift-lock coverage | implemented | tested | documented | WS-05 | Router registry and prefix catalogs keep the active API route surface pinned during backend pytest runs |
| QA-T18 | `apps/learning/tests` | learning validation coverage | implemented | tested | documented | WS-05 | Learning suite passed `99` tests on 2026-05-19 via `scripts/test/test-learning.sh` |

## Database Models

Inventoried 2026-04-24 (BP-06.01). All files in `apps/api/app/db/models/`.

| ID | File | Entity | Status | Validation | Documentation | Workstream | Notes |
|---|---|---|---|---|---|---|---|
| API-M01 | `app/db/models/asset.py` | Asset | implemented | tested | documented | WS-01 | Core tradable asset entity keyed by UUID; source for signals, paper orders, bars, quotes, and news association |
| API-M02 | `app/db/models/bar.py` | Bar | implemented | tested | documented | WS-01 | OHLCV market bar store keyed by asset/timeframe/timestamp; consumed by FeatureAdapterService and MarketDataService |
| API-M03 | `app/db/models/quote.py` | Quote | implemented | tested | documented | WS-01 | Bid/ask quote store for spread-aware feature generation and future execution checks |
| API-M04 | `app/db/models/signal.py` | Signal | implemented | tested | documented | WS-01 | Persisted signal entity linking asset, optional prompt/model versions, feature snapshot, and downstream risk decisions |
| API-M05 | `app/db/models/risk_decision.py` | RiskDecision | implemented | tested | documented | WS-01 | Typed risk evaluation result linked to a signal and persisted after route/service evaluation |
| API-M06 | `app/db/models/risk_profile.py` | RiskProfile | implemented | unverified | documented | WS-01 | Operator risk threshold profile controlling confidence, score, spread, drawdown, and cooldown rules |
| API-M07 | `app/db/models/paper_order.py` | PaperOrder | implemented | tested | documented | WS-01 | Paper-trading order lifecycle entity with submitted, filled, and closed transitions used by execution routes |
| API-M08 | `app/db/models/paper_fill.py` | PaperFill | implemented | unverified | documented | WS-01 | Fill record entity linked to paper orders for audit and lifecycle reconstruction |
| API-M09 | `app/db/models/approval_request.py` | ApprovalRequest | implemented | tested | documented | WS-01 | Approval workflow entity tying signals to operator approval windows and status transitions |
| API-M10 | `app/db/models/execution_mode.py` | ExecutionMode | implemented | unverified | documented | WS-01 | Execution-mode configuration entity supporting paper, approval-gated, and future guarded-live routing |
| API-M11 | `app/db/models/execution_policy.py` | ExecutionPolicy | implemented | unverified | documented | WS-01 | Execution policy entity for route-mode constraints and future live-routing rules |
| API-M12 | `app/db/models/audit_log.py` | AuditLog | implemented | manually verified | documented | WS-01 | Generic audit trail entity for blocked live-execution attempts and other mutable system events |
| API-M13 | `app/db/models/position.py` | Position | implemented | tested | documented | WS-06 | Real position entity used by PositionService for open/closed lifecycle and mark-to-market state; additive migration `g7h8i9j0k1l2` restores the persisted `close_price` column expected by current ORM and route queries |
| API-M14 | `app/db/models/pnl_snapshot.py` | PnlSnapshot | implemented | tested | documented | WS-06 | Snapshot entity used by PnlService for portfolio/equity history rows |
| API-M15 | `app/db/models/feature_snapshot.py` | FeatureSnapshot | implemented | tested | documented | WS-06 | Signal-linked feature snapshot entity; includes nullable signal_id FK added in migration a1b2c3d4e5f6 |
| API-M16 | `app/db/models/prompt_version.py` | PromptVersion | implemented | tested | documented | WS-06 | Prompt file version store seeded from disk with hash/idempotency metadata |
| API-M17 | `app/db/models/model_version.py` | ModelVersion | scaffold | unverified | undocumented | WS-06 | Model version entity; Phase 9 deferred |
| API-M18 | `app/db/models/eval_case.py` | EvalCase | partial | tested | documented | WS-06 | Read by eval routes; persistence write path remains deferred but route integration is active |
| API-M19 | `app/db/models/eval_run.py` | EvalRun | partial | tested | documented | WS-06 | Read by eval routes and evals page; persistence write path remains deferred but read integration is active |
| API-M20 | `app/db/models/news_article.py` | NewsArticle | implemented | tested | documented | WS-06 | Persisted news article store used by NewsIngestWorker scaffold and GET /market-data/news/{ticker} |

## Database Support And Additional Models

| ID | File | Entity | Status | Validation | Documentation | Workstream | Notes |
|---|---|---|---|---|---|---|---|
| API-D01 | `app/db/{base.py,session.py,enums.py,mixins.py}` | DB support surface | implemented | tested | partial | WS-01 | Core SQLAlchemy base/session/enum support files. Inventoried 2026-05-19 during MH-RESTART-004. |
| API-M21 | `app/db/models/{signal_outcome.py,drawdown_period.py,equity_curve_point.py,opportunity_outcomes.py,scored_opportunities.py}` | learning outcome model family | implemented | tested | partial | WS-06 | Active outcome and scoring-support model files inventoried 2026-05-19 during MH-RESTART-004. |
| API-M22 | `app/db/models/{baseline_candidate.py,paper_validation_plan.py,paper_validation_event.py,paper_validation_evidence.py,paper_recommendation.py}` | paper-validation and recommendation model family | implemented | tested | partial | WS-06 | Active paper-validation, baseline, and recommendation model files inventoried 2026-05-19 during MH-RESTART-004. |
| API-M23 | `app/db/models/{broker_submit_decision.py,broker_trade_event.py,trading_halt.py,trading_control_arming_state.py,risk_limit_config.py,incident_log.py,llm_request_log.py,news_in_decision_log.py}` | broker, safety, and audit model family | implemented | tested | partial | WS-06 | Active broker-control and audit model files inventoried 2026-05-19 during MH-RESTART-004. |
| API-M24 | `app/db/models/{market_data_import_run.py,market_data_gap.py,market_data_quality_report.py,provider_asset_coverage.py,provider_coverage_report.py,fundamental_snapshots.py,news_items.py,news_symbol_links.py,filing_events.py,macro_series.py,macro_observations.py,market_regimes.py,feature_definitions.py}` | provider, market-data, and research substrate model family | implemented | tested | partial | WS-06 | Active data-centre and provider model files inventoried 2026-05-19 during MH-RESTART-004. |
| API-M25 | `app/db/models/{score_model_registry.py,score_model_parameters.py,score_model_evaluations.py,score_model_promotions.py,score_model_rollbacks.py,model_version.py}` | model-governance model family | implemented | tested | partial | WS-06 | Active scoring/model-governance model files inventoried 2026-05-19 during MH-RESTART-004. |
| API-M26 | `app/db/models/{backtest_run.py,strategy_config.py,strategy_result.py,ai_backtest_report.py,research_job.py,mock_trade.py,quality_review_audit.py}` | strategy-lab and research job model family | implemented | tested | partial | WS-06 | Active strategy-lab and research-job model files inventoried 2026-05-19 during MH-RESTART-004. |

## Migration Surfaces

| ID | File | Purpose | Status | Validation | Documentation | Workstream | Notes |
|---|---|---|---|---|---|---|---|
| API-MG01 | `apps/api/alembic/versions/*.py` | Alembic revision chain | implemented | tested | partial | WS-01 | 33 active revision files plus `__init__.py` are present; backend drift-lock tests pin the revision chain and Alembic head. Inventoried 2026-05-19 during MH-RESTART-004. |
| API-MG02 | `apps/api/alembic/versions/{001_initial_tables.py,...,9c0191d5922a_sync_orm_drift.py}` | migration history surface | implemented | tested | partial | WS-01 | Current chain includes core, research, broker, monitoring, prompt, and ORM-drift revisions; validated by backend pytest drift-locks. Inventoried 2026-05-19 during MH-RESTART-004. |

## Phase 7 Infrastructure (Workers / Schedules) as of 2026-04-23. Confirmed by full-tree audit — no worker, scheduler, or cron infrastructure exists.

| ID | File | Purpose | Status | Validation | Documentation | Workstream | Notes |
|---|---|---|---|---|---|---|---|
| API-W01 | `app/workers/base_worker.py` | background worker infrastructure | scaffold | tested | documented | WS-01 | Phase 7 scaffold created 2026-04-24: BaseWorker + WorkerResult envelope; baseline infrastructure tests in `tests/infrastructure/test_worker_scheduler_scaffold.py` |
| API-W02 | `app/schedules/base_scheduler.py` | scheduled job infrastructure | scaffold | tested | documented | WS-01 | Phase 7 scaffold created 2026-04-24: BaseScheduler + ScheduledJob registry; baseline infrastructure tests in `tests/infrastructure/test_worker_scheduler_scaffold.py` |
| API-W03 | `app/workers/data_sync_worker.py` | market data sync worker | implemented | tested | documented | WS-02 | Scheduled bar-ingest worker over active assets; skips cleanly when Polygon API key is unset |
| API-W04 | `app/schedules/data_sync_scheduler.py` | runtime job registry | implemented | tested | documented | WS-02 | Registers `data_sync` and `news_ingest` jobs and maps job names to worker instances |
| API-W05 | `app/workers/news_ingest_worker.py` | news ingestion worker | implemented | tested | documented | WS-02 | BaseWorker-compliant news ingest scaffold with graceful empty-provider behavior and persisted NewsArticle rows |

## Learning Surfaces

| ID | File | Purpose | Status | Validation | Documentation | Workstream | Notes |
|---|---|---|---|---|---|---|---|
| LEARN-01 | `apps/learning/features/technical/*.py` | technical feature family | implemented | tested | documented | WS-06 | Active files: `levels.py`, `momentum.py`, `patterns.py`, `volatility.py`, `volume.py`. Inventoried 2026-05-19 during MH-RESTART-004. |
| LEARN-02 | `apps/learning/features/{execution,news,macro,cross_sectional}/*.py` | non-technical feature families | implemented | tested | documented | WS-06 | Active files include `spread.py`, `liquidity_score.py`, `event_proximity.py`, `sentiment.py`, `liquidity.py`, `volatility.py`, `yield_curve.py`, `breadth.py`, `relative_rank.py`, `sector_strength.py`. Inventoried 2026-05-19 during MH-RESTART-004. |
| LEARN-03 | `apps/learning/services/backfill/*.py` | backfill service family | implemented | tested | documented | WS-06 | Active files: `bars_backfill_service.py`, `macro_backfill_service.py`, `news_backfill_service.py`. Inventoried 2026-05-19 during MH-RESTART-004. |
| LEARN-04 | `apps/learning/services/{features,labeling,normalization,regime,storage,validation}/*.py` | learning service family | implemented | tested | documented | WS-06 | Active files include `feature_builder.py`, `feature_cache_service.py`, `feature_drift_detector.py`, `blocked_opportunity_labeler.py`, `execution_quality_labeler.py`, `forward_return_labeler.py`, `missed_opportunity_labeler.py`, `traded_outcome_labeler.py`, `news_normalizer.py`, `symbol_mapper.py`, `regime_classifier.py`, `regime_snapshot_service.py`, `regime_validation_service.py`, `storage_service.py`, `calibration_validator.py`, `sample_size_policy_service.py`, `shadow_compare_service.py`, and `walk_forward_validator.py`. Inventoried 2026-05-19 during MH-RESTART-004. |
| LEARN-05 | `apps/learning/pipelines/*.py` | training and validation pipeline family | implemented | tested | documented | WS-06 | Active files: `compare_shadow_vs_active.py`, `publish_candidate_model.py`, `train_execution_model.py`, `train_regime_model.py`, `train_scoring_model.py`, `validate_walk_forward.py`. Inventoried 2026-05-19 during MH-RESTART-004. |
| LEARN-06 | `apps/learning/jobs/*.py` | scheduled learning job family | implemented | tested | documented | WS-06 | Active files: `backfill_bars_job.py`, `backfill_filings_job.py`, `backfill_macro_job.py`, `backfill_news_job.py`, `refresh_universe_job.py`. Inventoried 2026-05-19 during MH-RESTART-004. |
| LEARN-07 | `apps/learning/tests/*.py` | learning regression suite | implemented | tested | documented | WS-06 | 14 active Python test files cover features, normalization, reproducibility, leakage, regime, walk-forward validation, sample-size gates, labeling, PIT correctness, and idempotency. Inventoried 2026-05-19 during MH-RESTART-004. |

## Control Documents And Release-Gate Mapping

| ID | File | Purpose | Status | Validation | Documentation | Workstream | Notes |
|---|---|---|---|---|---|---|---|
| CTRL-01 | `docs/implementation-matrix.md` | Gate 1 source of truth | implemented | manually verified | documented | WS-07 | Reconciled to the live route/service/page/component inventory on 2026-05-19 during MH-RESTART-004. |
| CTRL-02 | `docs/regression-qa-matrix.md` | Gate 2 source of truth | implemented | manually verified | documented | WS-07 | QA coverage matrix updated alongside inventory reconciliation when related items or gate results change. |
| CTRL-03 | `docs/release-gates.md` | release-gate control surface | implemented | manually verified | documented | WS-07 | Release verdict must match fresh command evidence and Gate 1 inventory coverage. |
| CTRL-04 | `docs/current-phase-status.md` | current release-readiness snapshot | implemented | manually verified | documented | WS-07 | Phase status must stay aligned with gate outputs and validation reruns. |
| CTRL-05 | `docs/build-matrix.md` | build-state dashboard | implemented | manually verified | documented | WS-07 | Build-state summary must reflect the latest validation baseline and release verdict. |
| CTRL-06 | `docs/build-ledger.md` | append-only execution ledger | implemented | manually verified | documented | WS-07 | Restart entries remain append-only and record validation commands/results. |

## Excluded And Supporting Surfaces

Support or generated files are intentionally not counted as primary Gate 1 rows when they do not represent standalone route/service/page/component surfaces.

- `apps/web/tests/visual.spec.ts-snapshots/*.png` are visual baselines, not product code surfaces.
- `apps/web/components/**/*.module.css`, `apps/web/components/chart/index.ts`, and `apps/web/components/chart/types.ts` are support files, not standalone shared TSX components.
- `__init__.py`, `__pycache__`, and `*.pyc` entries under API and learning folders are package/runtime support and are excluded from the active surface count.

## Deferred BP3 Backlog

The old BP3 pre-registration tables were removed from the active inventory on 2026-05-19 because Gate 1 treats backlog-only rows as release blockers once they live inside the matrix. Active BP3 files were promoted into the live route, service, persistence, model, and page sections above. Remaining deferred BP3 work should stay in build plans and tickets until concrete files land in the repo.

## Control Notes

1. Any new route, service, panel, or chart must be added here before it is treated as complete.
2. If a file changes classification, update the row rather than adding a duplicate row.
3. If a feature spans multiple files, add the feature bucket reference in the notes field.
4. Fixes are allowed during this process, but every fix must update status, validation, or notes in this matrix.