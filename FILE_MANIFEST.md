# Complete File Manifest: Market Hunter MVP Refactor

This document lists every file that needs to be created (or refactored) across all 13 phases.

**Format:** `[status] path/file.ext — description`  
**Status:** ✨ new | 🔄 refactor | 🗑️ delete | ✅ done (from Phase 0)

---

## PHASE 1: FRONTEND SHELL MODERNIZATION

### Shell Components

```
✨ apps/web/components/shell/AppShell.tsx — Root layout wrapper (sidebar + topbar + content)
✨ apps/web/components/shell/AppShell.module.css — AppShell styles
✨ apps/web/components/shell/Sidebar.tsx — Navigation sidebar with sections
✨ apps/web/components/shell/Sidebar.module.css — Sidebar styles
✨ apps/web/components/shell/SidebarSection.tsx — Sidebar section wrapper
✨ apps/web/components/shell/Topbar.tsx — Fixed header (branding, theme, user menu)
✨ apps/web/components/shell/Topbar.module.css — Topbar styles
✨ apps/web/components/shell/PageHeader.tsx — Page title + breadcrumb + actions
✨ apps/web/components/shell/PageHeader.module.css — PageHeader styles
```

### UI Primitives

```
✨ apps/web/components/ui/Button.tsx — Semantic button component
✨ apps/web/components/ui/Button.module.css — Button styles (primary/secondary/ghost variants)
✨ apps/web/components/ui/Card.tsx — Container primitive
✨ apps/web/components/ui/Card.module.css — Card styles
✨ apps/web/components/ui/MetricCard.tsx — Metric display card (replaces StatCard)
✨ apps/web/components/ui/MetricCard.module.css — MetricCard styles
✨ apps/web/components/ui/Panel.tsx — Larger container with header/legend/content slots
✨ apps/web/components/ui/Panel.module.css — Panel styles
✨ apps/web/components/ui/Badge.tsx — Status/label badge
✨ apps/web/components/ui/Badge.module.css — Badge styles (success/warning/danger/info)
✨ apps/web/components/ui/LoadingState.tsx — Skeleton/loader display
✨ apps/web/components/ui/LoadingState.module.css — Loading styles
✨ apps/web/components/ui/ErrorState.tsx — Error message display
✨ apps/web/components/ui/ErrorState.module.css — Error styles
✨ apps/web/components/ui/EmptyState.tsx — Empty data display
✨ apps/web/components/ui/EmptyState.module.css — Empty styles
✨ apps/web/components/ui/SegmentedControl.tsx — Tab-like control
✨ apps/web/components/ui/SegmentedControl.module.css — SegmentedControl styles
✨ apps/web/components/ui/FilterBar.tsx — Filter controls container
✨ apps/web/components/ui/FilterBar.module.css — FilterBar styles
```

### Chart Components (Refactored)

```
🔄 apps/web/components/chart/ChartPanel.tsx — Refactored to use Panel primitive
✨ apps/web/components/chart/ChartPanel.module.css — ChartPanel CSS module
✨ apps/web/components/chart/ChartLegend.tsx — Legend component
✨ apps/web/components/chart/ChartToolbar.tsx — Chart controls/tools
✨ apps/web/components/chart/ChartTooltip.tsx — Hover tooltip
```

### Page Components (Refactored)

```
✨ apps/web/components/dashboard/DashboardMetricsSection.tsx — Metrics grid section
✨ apps/web/components/dashboard/DashboardChartsSection.tsx — Charts section
✨ apps/web/components/dashboard/DashboardAlertsSection.tsx — Alerts/recent activity section
🔄 apps/web/components/PersonalDashboard.tsx — Refactored to orchestrate sections
```

### Layout Files

```
✨ apps/web/app/(shell)/layout.tsx — Root layout using AppShell
🗑️ apps/web/components/Nav.tsx — Deleted (replaced by shell system)
🗑️ apps/web/components/StatCard.tsx — Deleted (replaced by MetricCard)
```

### Styles

```
✨ apps/web/styles/shell.module.css — Shell-related styles
✨ apps/web/styles/pages/dashboard.module.css — Dashboard page styles
✨ apps/web/styles/pages/analytics.module.css — Analytics page styles
✨ apps/web/styles/pages/execution.module.css — Execution page styles
✨ apps/web/styles/ui/button.module.css — Button utility styles
✨ apps/web/styles/ui/forms.module.css — Form element styles
```

### Storybook

```
✨ .storybook/main.ts — Storybook config
✨ .storybook/preview.ts — Storybook global settings
✨ apps/web/components/ui/Button.stories.tsx — Button stories
✨ apps/web/components/ui/Card.stories.tsx — Card stories
✨ apps/web/components/ui/MetricCard.stories.tsx — MetricCard stories
✨ apps/web/components/ui/Panel.stories.tsx — Panel stories
✨ apps/web/components/ui/Badge.stories.tsx — Badge stories
✨ apps/web/components/shell/Topbar.stories.tsx — Topbar stories
✨ apps/web/components/shell/Sidebar.stories.tsx — Sidebar stories
```

---

## PHASE 2: FRONTEND STATE CLEANUP

### API Client Modules

```
✨ apps/web/lib/api/core.ts — Base API functions (apiRequest, auth)
✨ apps/web/lib/api/execution.ts — Execution endpoints
✨ apps/web/lib/api/analytics.ts — Analytics/market data endpoints
✨ apps/web/lib/api/signals.ts — Signal endpoints
✨ apps/web/lib/api/models.ts — Model registry endpoints (new)
✨ apps/web/lib/api/news.ts — News endpoints (new)
✨ apps/web/lib/api/index.ts — Re-exports (backward compat)
🗑️ apps/web/lib/api.ts — Deprecated (moved to modules)
```

### State Management

```
✨ apps/web/lib/state/analyticsReducer.ts — Analytics filter/view state reducer
✨ apps/web/lib/state/executionReducer.ts — Execution list/detail/journal reducer
✨ apps/web/lib/state/types.ts — Reducer state type definitions
```

### Controller Hooks

```
✨ apps/web/lib/hooks/useExecutionPageController.ts — Execution page state orchestration
✨ apps/web/lib/hooks/useAnalyticsPageController.ts — Analytics page state orchestration
✨ apps/web/lib/hooks/useTheme.ts — Theme toggle/persistence (refactored)
```

### Query Client (Optional)

```
✨ apps/web/lib/query/client.ts — React Query client config
✨ apps/web/lib/query/execution.ts — Execution queries/mutations
✨ apps/web/lib/query/analytics.ts — Analytics queries
```

### Utility Modules

```
✨ apps/web/lib/utils/formatting.ts — Format numbers, dates, etc.
✨ apps/web/lib/utils/validation.ts — Input validation helpers
✨ apps/web/lib/utils/time.ts — Time/date utilities
```

### Page Refactors

```
🔄 apps/web/app/execution/page.tsx — Refactored to use useExecutionPageController
🔄 apps/web/app/analytics/page.tsx — Refactored to use useAnalyticsPageController
```

### Tests

```
✨ apps/web/tests/visual.spec.ts — Visual regression tests (all pages, responsive, theme)
✨ apps/web/tests/full-flow.spec.ts — End-to-end user flow test
✨ apps/web/__tests__/state/analyticsReducer.test.ts — Analytics reducer unit tests
✨ apps/web/__tests__/state/executionReducer.test.ts — Execution reducer unit tests
✨ apps/web/__tests__/hooks/useExecutionPageController.test.ts — Hook unit tests
✨ apps/web/__tests__/hooks/useAnalyticsPageController.test.ts — Hook unit tests
```

---

## PHASE 3: BACKEND RUNTIME CLEANUP

### New Service Modules

```
✨ apps/api/app/services/runtime/__init__.py
✨ apps/api/app/services/runtime/scoring_service.py — Scoring computation (decoupled from signal)
✨ apps/api/app/services/runtime/scoring_config_service.py — Load/manage scoring config from DB
✨ apps/api/app/services/runtime/signal_generation_service.py — Signal generation only (split from scoring)
✨ apps/api/app/services/governance/__init__.py
✨ apps/api/app/services/governance/model_registry_service.py — Model registry CRUD
✨ apps/api/app/services/governance/model_promotion_service.py — Candidate → active promotion
✨ apps/api/app/services/governance/model_rollback_service.py — Active → previous rollback
✨ apps/api/app/services/governance/model_audit_service.py — Audit trail logging
```

### Execution Services (Reorganized)

```
✨ apps/api/app/services/runtime/execution/__init__.py
✨ apps/api/app/services/runtime/execution/paper_execution_service.py — (moved from services/)
✨ apps/api/app/services/runtime/execution/execution_mode_service.py — (moved from services/)
✨ apps/api/app/services/runtime/execution/position_service.py — Position management
✨ apps/api/app/services/runtime/execution/pnl_service.py — PnL calculation
```

### New Routes

```
✨ apps/api/app/api/routes/models.py — Model registry endpoints
✨ apps/api/app/api/routes/scoring.py — Scoring config endpoints (GET /scoring/active, etc.)
✨ apps/api/app/api/routes/regime.py — Regime detection endpoints
✨ apps/api/app/api/routes/governance.py — Model promotion/rollback endpoints
```

### Refactored Route Files

```
🔄 apps/api/app/api/routes/workflow.py — Use new scoring config service
🔄 apps/api/app/api/routes/execution.py — Consolidate persisted execution path
```

### New Schemas

```
✨ apps/api/app/schemas/scoring.py — ScoringConfig, BucketConfig, etc.
✨ apps/api/app/schemas/models.py — ModelVersion, ModelPromotion, etc.
✨ apps/api/app/schemas/regime.py — RegimeSnapshot, etc.
```

### Tests

```
✨ apps/api/tests/services/test_scoring_service.py — Scoring computation tests
✨ apps/api/tests/services/test_scoring_config_service.py — Config resolution tests
✨ apps/api/tests/services/test_model_registry_service.py — Registry CRUD tests
✨ apps/api/tests/services/test_model_promotion_service.py — Promotion logic tests
✨ apps/api/tests/routes/test_scoring_routes.py — Scoring endpoint tests
✨ apps/api/tests/routes/test_models_routes.py — Model registry endpoint tests
```

---

## PHASE 4: DATA MODEL EXPANSION

### New DB Models

```
✨ apps/api/app/db/models/score_model_registry.py — Model versions and metadata
✨ apps/api/app/db/models/score_model_parameters.py — Model parameter sets
✨ apps/api/app/db/models/score_model_evaluations.py — Model validation results
✨ apps/api/app/db/models/score_model_promotions.py — Promotion audit trail
✨ apps/api/app/db/models/score_model_rollbacks.py — Rollback audit trail
✨ apps/api/app/db/models/market_regimes.py — Regime classifications
✨ apps/api/app/db/models/feature_snapshots.py — PIT feature snapshots
✨ apps/api/app/db/models/feature_definitions.py — Feature metadata
✨ apps/api/app/db/models/scored_opportunities.py — Scored signal opportunities
✨ apps/api/app/db/models/opportunity_outcomes.py — Outcome labels for learning
✨ apps/api/app/db/models/missed_opportunity_labels.py — Missed trade labels
✨ apps/api/app/db/models/news_items.py — News articles/headlines
✨ apps/api/app/db/models/news_symbol_links.py — Symbol → news associations
✨ apps/api/app/db/models/filing_events.py — SEC filing/earnings events
✨ apps/api/app/db/models/fundamental_snapshots.py — Company fundamentals PIT
✨ apps/api/app/db/models/macro_series.py — Macro series metadata (CPI, yields, etc.)
✨ apps/api/app/db/models/macro_observations.py — Macro data points
```

### Alembic Migrations

```
✨ apps/api/alembic/versions/[hash]_add_model_governance_tables.py
✨ apps/api/alembic/versions/[hash]_add_regime_feature_tables.py
✨ apps/api/alembic/versions/[hash]_add_opportunity_learning_tables.py
✨ apps/api/alembic/versions/[hash]_add_news_fundamentals_tables.py
```

### Documentation

```
✨ docs/data/er-diagram.md — Entity relationship diagram for new tables
✨ docs/data/table-glossary.md — Definition of every table and column
✨ docs/data/point-in-time-rules.md — PIT join rules for historical correctness
✨ docs/data/retention-policy.md — Data retention and archival policy
```

---

## PHASE 5: MARKET DATA AND ADAPTER LAYER

### Adapter Base Classes

```
✨ apps/api/app/clients/market_data/base.py — MarketDataAdapter interface
✨ apps/api/app/clients/news/base.py — NewsAdapter interface
✨ apps/api/app/clients/fundamentals/base.py — FundamentalsAdapter interface
✨ apps/api/app/clients/macro/base.py — MacroAdapter interface
```

### Market Data Adapters

```
✨ apps/api/app/clients/market_data/ibkr.py — IBKR market data (real broker)
✨ apps/api/app/clients/market_data/twelvedata.py — Twelve Data adapter
✨ apps/api/app/clients/market_data/tiingo.py — Tiingo adapter
✨ apps/api/app/clients/market_data/mock.py — Mock adapter for testing
```

### News Adapters

```
✨ apps/api/app/clients/news/finnhub.py — Finnhub news adapter
✨ apps/api/app/clients/news/alpaca_news.py — Alpaca news adapter
✨ apps/api/app/clients/news/gdelt.py — GDELT events adapter
✨ apps/api/app/clients/news/mock.py — Mock news adapter
```

### Fundamental/Macro Adapters

```
✨ apps/api/app/clients/fundamentals/sec.py — SEC EDGAR adapter
✨ apps/api/app/clients/fundamentals/mock.py — Mock fundamentals adapter
✨ apps/api/app/clients/macro/fred.py — Federal Reserve Economic Data (FRED) adapter
✨ apps/api/app/clients/macro/mock.py — Mock macro adapter
```

### Ingestion Services

```
✨ apps/api/app/services/market/__init__.py
✨ apps/api/app/services/market/instrument_registry_service.py — Symbol/contract registry
✨ apps/api/app/services/market/market_data_ingestion_service.py — Bars/quotes intake
✨ apps/api/app/services/market/news_ingestion_service.py — News articles intake
✨ apps/api/app/services/market/fundamentals_ingestion_service.py — Company data intake
✨ apps/api/app/services/market/macro_ingestion_service.py — Macro series intake
✨ apps/api/app/services/market/provider_dispatcher_service.py — Route to best provider
```

### Tests

```
✨ apps/api/tests/clients/test_market_data_adapters.py — Adapter contract tests
✨ apps/api/tests/clients/test_news_adapters.py
✨ apps/api/tests/clients/test_fundamentals_adapters.py
✨ apps/api/tests/clients/test_macro_adapters.py
✨ apps/api/tests/services/test_ingestion_services.py
```

---

## PHASE 6: HISTORICAL BACKFILL AND INGESTION

### Learning App (New)

```
✨ apps/learning/__init__.py
✨ apps/learning/README.md
✨ apps/learning/pyproject.toml
✨ apps/learning/requirements.txt
```

### Backfill Jobs

```
✨ apps/learning/jobs/__init__.py
✨ apps/learning/jobs/backfill_bars_job.py — Historical bars ingestion
✨ apps/learning/jobs/backfill_news_job.py — Historical news ingestion
✨ apps/learning/jobs/backfill_macro_job.py — Historical macro data ingestion
✨ apps/learning/jobs/backfill_filings_job.py — Historical filings ingestion
✨ apps/learning/jobs/refresh_universe_job.py — Update instrument master
```

### Backfill Services

```
✨ apps/learning/services/__init__.py
✨ apps/learning/services/backfill/__init__.py
✨ apps/learning/services/backfill/bars_backfill_service.py — Bars ingestion coordination
✨ apps/learning/services/backfill/news_backfill_service.py — News coordination
✨ apps/learning/services/backfill/macro_backfill_service.py — Macro coordination
✨ apps/learning/services/normalization/__init__.py
✨ apps/learning/services/normalization/symbol_mapper.py — Symbol normalization
✨ apps/learning/services/normalization/news_normalizer.py — News field mapping
✨ apps/learning/services/storage/__init__.py
✨ apps/learning/services/storage/storage_service.py — Database persistence
```

### Documentation

```
✨ docs/runbooks/backfill-runbook.md — Step-by-step backfill instructions
✨ docs/data/universes.md — Instrument universe definitions
✨ docs/data/provider-priority-matrix.md — Provider precedence rules
```

### Tests

```
✨ apps/learning/tests/__init__.py
✨ apps/learning/tests/test_backfill_bars_job.py
✨ apps/learning/tests/test_backfill_news_job.py
✨ apps/learning/tests/test_normalization.py
✨ apps/learning/tests/test_idempotency.py
```

---

## PHASE 7: FEATURE STORE AND REGIME ENGINE

### Feature Modules

```
✨ apps/learning/features/__init__.py
✨ apps/learning/features/technical/__init__.py
✨ apps/learning/features/technical/momentum.py — Multi-timeframe momentum
✨ apps/learning/features/technical/volatility.py — ATR, realized vol
✨ apps/learning/features/technical/levels.py — Support/resistance, VWAP
✨ apps/learning/features/technical/patterns.py — Breakout compression, etc.
✨ apps/learning/features/technical/volume.py — Volume analysis
✨ apps/learning/features/cross_sectional/__init__.py
✨ apps/learning/features/cross_sectional/sector_strength.py — Sector relative strength
✨ apps/learning/features/cross_sectional/breadth.py — Market breadth
✨ apps/learning/features/cross_sectional/relative_rank.py — Ranking features
✨ apps/learning/features/macro/__init__.py
✨ apps/learning/features/macro/yield_curve.py — Rate environment
✨ apps/learning/features/macro/liquidity.py — Liquidity conditions
✨ apps/learning/features/macro/volatility.py — Market volatility (VIX, etc.)
✨ apps/learning/features/news/__init__.py
✨ apps/learning/features/news/sentiment.py — News sentiment scoring
✨ apps/learning/features/news/event_proximity.py — Event distance features
✨ apps/learning/features/execution/__init__.py
✨ apps/learning/features/execution/spread.py — Bid/ask spread metrics
✨ apps/learning/features/execution/liquidity_score.py — Execution liquidity
```

### Regime Services

```
✨ apps/learning/services/regime/__init__.py
✨ apps/learning/services/regime/regime_classifier.py — Classify market regime
✨ apps/learning/services/regime/regime_snapshot_service.py — PIT regime snapshots
✨ apps/learning/services/regime/regime_validation_service.py — Regime correctness tests
```

### Feature Store Services

```
✨ apps/learning/services/features/__init__.py
✨ apps/learning/services/features/feature_builder.py — Compute feature snapshots
✨ apps/learning/services/features/feature_cache_service.py — Cache computed features
✨ apps/learning/services/features/feature_drift_detector.py — Detect stale features
```

### Documentation

```
✨ docs/models/feature-catalog.md — All features defined and documented
✨ docs/models/regime-taxonomy.md — Regime definitions and classification rules
```

### Tests

```
✨ apps/learning/tests/test_technical_features.py
✨ apps/learning/tests/test_cross_sectional_features.py
✨ apps/learning/tests/test_regime_classifier.py
✨ apps/learning/tests/test_feature_pit_correctness.py
```

---

## PHASE 8: SCORING ENGINE V2

### Scoring Services

```
✨ apps/api/app/services/runtime/scoring/__init__.py
✨ apps/api/app/services/runtime/scoring/score_resolver.py — Resolve active scoring config
✨ apps/api/app/services/runtime/scoring/score_explainer.py — Explain score breakdown
✨ apps/api/app/services/runtime/scoring/score_bucket_service.py — Assign bucket (asset/strategy/timeframe)
✨ apps/api/app/services/runtime/scoring/score_calibration_service.py — Calibration metrics
✨ apps/api/app/services/runtime/scoring/score_threshold_service.py — Threshold enforcement
✨ apps/api/app/services/runtime/scoring/dnt_probability_service.py — Do-not-trade probability
```

### Schemas

```
✨ apps/api/app/schemas/scoring.py — ScoreExplanation, ScoreBucket, etc.
```

### Routes

```
✨ apps/api/app/api/routes/scoring.py — GET /scoring/active, /scoring/explain/{signal_id}
✨ apps/api/app/api/routes/regime.py — GET /regime/current, /regime/snapshot
```

### Tests

```
✨ apps/api/tests/services/test_score_resolver.py
✨ apps/api/tests/services/test_score_explainer.py
✨ apps/api/tests/services/test_score_bucket_service.py
✨ apps/api/tests/services/test_calibration.py
```

---

## PHASE 9: LEARNING LOOP AND LABELING

### Labeling Services

```
✨ apps/learning/services/labeling/__init__.py
✨ apps/learning/services/labeling/traded_outcome_labeler.py — Label executed trades
✨ apps/learning/services/labeling/missed_opportunity_labeler.py — Label missed opportunities
✨ apps/learning/services/labeling/blocked_opportunity_labeler.py — Label blocked trades
✨ apps/learning/services/labeling/forward_return_labeler.py — Forward-return labels
✨ apps/learning/services/labeling/execution_quality_labeler.py — Slippage, commission labels
```

### Tests

```
✨ apps/learning/tests/test_traded_outcome_labeler.py
✨ apps/learning/tests/test_missed_opportunity_labeler.py
✨ apps/learning/tests/test_label_consistency.py
```

---

## PHASE 10: TRAINING AND VALIDATION PIPELINES

### Pipeline Modules

```
✨ apps/learning/pipelines/__init__.py
✨ apps/learning/pipelines/train_regime_model.py — Regime classifier training
✨ apps/learning/pipelines/train_scoring_model.py — Scoring model training
✨ apps/learning/pipelines/train_execution_model.py — Execution model training
✨ apps/learning/pipelines/validate_walk_forward.py — Walk-forward validation
✨ apps/learning/pipelines/compare_shadow_vs_active.py — Shadow mode comparison
✨ apps/learning/pipelines/publish_candidate_model.py — Candidate model publication
```

### Validation Services

```
✨ apps/learning/services/validation/__init__.py
✨ apps/learning/services/validation/walk_forward_validator.py — WFV logic
✨ apps/learning/services/validation/shadow_compare_service.py — Candidate vs active
✨ apps/learning/services/validation/sample_size_policy_service.py — Sample gate enforcement
✨ apps/learning/services/validation/calibration_validator.py — Calibration tests
```

### Tests

```
✨ apps/learning/tests/test_walk_forward_validation.py
✨ apps/learning/tests/test_sample_size_gates.py
✨ apps/learning/tests/test_leakage_detection.py
✨ apps/learning/tests/test_reproducibility.py
```

---

## PHASE 11: MODEL GOVERNANCE AND ROLLOUT

### Governance Services

```
✨ apps/api/app/services/governance/__init__.py
✨ apps/api/app/services/governance/model_registry_service.py
✨ apps/api/app/services/governance/model_candidate_service.py — Manage candidates
✨ apps/api/app/services/governance/model_promotion_service.py — Promotion logic
✨ apps/api/app/services/governance/model_rollback_service.py — Rollback logic
✨ apps/api/app/services/governance/model_audit_service.py — Audit trail
✨ apps/api/app/services/governance/model_policy_service.py — Policy enforcement
```

### Routes

```
✨ apps/api/app/api/routes/models.py — POST/GET /models, /models/{id}/promote, /models/{id}/rollback
✨ apps/api/app/api/routes/governance.py — Governance endpoints
```

### Tests

```
✨ apps/api/tests/services/test_model_promotion_policy.py
✨ apps/api/tests/services/test_model_rollback_policy.py
✨ apps/api/tests/routes/test_model_governance_routes.py
```

---

## PHASE 12: RESEARCH AND INTELLIGENCE UI

### Frontend Pages

```
✨ apps/web/app/models/page.tsx — Model registry page
✨ apps/web/app/models/layout.tsx — Model page layout
✨ apps/web/components/models/ModelRegistry.tsx — Model list + detail
✨ apps/web/components/models/ModelVersionDetail.tsx — Model version view
✨ apps/web/components/models/ModelMetrics.tsx — Performance metrics

✨ apps/web/app/regime/page.tsx — Regime monitor page
✨ apps/web/components/regime/RegimeMonitor.tsx — Current regime display
✨ apps/web/components/regime/RegimeHistory.tsx — Regime transitions

✨ apps/web/app/calibration/page.tsx — Score calibration page
✨ apps/web/components/calibration/CalibrationPlots.tsx — Calibration curves

✨ apps/web/app/drift/page.tsx — Feature/model drift detection page
✨ apps/web/components/drift/DriftDetector.tsx — Drift charts

✨ apps/web/app/news/page.tsx — News/event intelligence page
✨ apps/web/components/news/NewsIntelligence.tsx — News display

✨ apps/web/app/replay/page.tsx — Historical replay/backtesting lab
✨ apps/web/components/replay/ReplayLab.tsx — Replay controls + results

✨ apps/web/app/promotions/page.tsx — Model promotion queue
✨ apps/web/components/promotions/PromotionQueue.tsx — Promotion list + approve/reject
```

### Tests

```
✨ apps/web/tests/models.spec.ts — Model page E2E tests
✨ apps/web/tests/regime.spec.ts — Regime page E2E tests
✨ apps/web/tests/promotions.spec.ts — Promotion page E2E tests
```

---

## PHASE 13: MONITORING, OBSERVABILITY, AND OPS

### Observability Config

```
✨ infra/observability/prometheus.yml — Prometheus config
✨ infra/observability/dashboards/ingestion-lag.json — Grafana dashboard
✨ infra/observability/dashboards/model-drift.json — Model drift dashboard
✨ infra/observability/dashboards/broker-health.json — Broker connectivity
✨ infra/observability/dashboards/queue-health.json — Job queue health
✨ infra/observability/dashboards/api-latency.json — API performance

✨ infra/observability/alerts/provider-outage.yml — Provider failure alert
✨ infra/observability/alerts/model-drift.yml — Model drift alert
✨ infra/observability/alerts/ingestion-lag.yml — Ingestion lag alert
✨ infra/observability/alerts/broker-disconnect.yml — Broker disconnect alert
✨ infra/observability/alerts/queue-failure.yml — Job queue failure alert
```

### Infrastructure

```
✨ infra/docker/Dockerfile.web — Web app Docker image
✨ infra/docker/Dockerfile.api — API app Docker image
✨ infra/docker/Dockerfile.learning — Learning app Docker image
✨ infra/docker/docker-compose.yml — Development docker-compose
✨ infra/docker/.dockerignore

✨ infra/db/init.sql — Database initialization
✨ infra/db/seeds/default_scoring_config.sql — Seed scoring configs
✨ infra/db/seeds/default_risk_profiles.sql — Seed risk profiles
```

### CI/CD

```
✨ .github/workflows/test-web.yml — Web app tests
✨ .github/workflows/test-api.yml — API app tests
✨ .github/workflows/test-learning.yml — Learning app tests
✨ .github/workflows/deploy-web.yml — Web deployment
✨ .github/workflows/deploy-api.yml — API deployment
✨ .github/workflows/deploy-learning.yml — Learning pipeline deployment
```

### Scripts

```
✨ scripts/db/init-dev.sh — Dev database setup
✨ scripts/db/migrate.sh — Run migrations
✨ scripts/db/seed.sh — Seed data

✨ scripts/learning/backfill-bars.sh — Run bars backfill
✨ scripts/learning/backfill-news.sh — Run news backfill
✨ scripts/learning/train-models.sh — Train all models
✨ scripts/learning/promote-model.sh — Promote candidate model

✨ scripts/deploy/deploy-web.sh — Deploy web app
✨ scripts/deploy/deploy-api.sh — Deploy API
✨ scripts/deploy/deploy-learning.sh — Deploy learning pipelines
✨ scripts/deploy/rollback.sh — Rollback deployment

✨ scripts/test/test-all.sh — Run all tests
✨ scripts/test/test-web.sh — Web tests only
✨ scripts/test/test-api.sh — API tests only
✨ scripts/test/test-learning.sh — Learning tests only
```

### Documentation

```
✨ docs/runbooks/incidents.md — Incident response guide
✨ docs/runbooks/model-rollback.md — Model rollback procedure
✨ docs/runbooks/provider-failure.md — Provider outage handling
✨ docs/runbooks/deployments.md — Deployment procedures
✨ docs/architecture/current-state.md — Current app snapshot
✨ docs/architecture/target-architecture.md — Target design
✨ docs/architecture/runtime-vs-learning.md — Decoupling strategy
✨ docs/architecture/service-boundaries.md — Service contracts
✨ docs/architecture/flow-diagrams.md — Execution flow diagrams
✨ docs/api/current-endpoints.md — Existing API endpoints
✨ docs/api/new-endpoints.md — All new API endpoints
✨ docs/api/contracts-execution.md — Execution service contracts
✨ docs/api/contracts-scoring.md — Scoring service contracts
✨ docs/api/contracts-models.md — Model registry contracts
✨ docs/api/contracts-governance.md — Governance contracts
✨ docs/api/contracts-learning.md — Learning API contracts
✨ docs/product/ui-modernization-plan.md — UI redesign plan
✨ docs/product/page-inventory.md — All pages and routes
✨ docs/product/component-library.md — UI component specs
✨ docs/product/navigation-plan.md — Navigation structure
✨ docs/models/feature-catalog.md — Feature definitions
✨ docs/models/regime-taxonomy.md — Regime classifications
✨ docs/models/training-policy.md — Training guidelines
✨ docs/models/model-promotion-policy.md — Promotion criteria
✨ docs/models/sample-size-policy.md — Sample gates
✨ docs/models/score-explanation-spec.md — Score explanation format
✨ docs/testing/baseline-test-report.md — Test coverage baseline
✨ docs/testing/test-strategy.md — Testing approach
✨ docs/testing/model-validation-checklist.md — Model validation steps
✨ docs/testing/visual-regression-plan.md — Visual testing plan
✨ docs/testing/release-gates.md — Release gating criteria
```

---

## SHARED PACKAGES

### shared-types

```
✨ packages/shared-types/package.json
✨ packages/shared-types/tsconfig.json
✨ packages/shared-types/src/index.ts
✨ packages/shared-types/src/signal.ts — Signal, SignalOutput types
✨ packages/shared-types/src/execution.ts — Execution, Order, Position types
✨ packages/shared-types/src/scoring.ts — ScoredOpportunity, RankedOpportunity types
✨ packages/shared-types/src/models.ts — ModelVersion, ModelPromotion types
✨ packages/shared-types/src/regime.ts — RegimeSnapshot type
```

### shared-config

```
✨ packages/shared-config/package.json
✨ packages/shared-config/tsconfig.json
✨ packages/shared-config/src/index.ts
✨ packages/shared-config/src/scoring-buckets.ts — Asset class, strategy, timeframe, liquidity, regime buckets
✨ packages/shared-config/src/risk-profiles.ts — Default risk profile thresholds
✨ packages/shared-config/src/execution-modes.ts — Execution mode constants
```

### shared-ui-tokens

```
✨ packages/shared-ui-tokens/package.json
✨ packages/shared-ui-tokens/tsconfig.json
✨ packages/shared-ui-tokens/src/index.ts
✨ packages/shared-ui-tokens/src/colors.ts — Color tokens (dark/light)
✨ packages/shared-ui-tokens/src/spacing.ts — Spacing scale
✨ packages/shared-ui-tokens/src/typography.ts — Font sizes, weights, line heights
```

---

## ROOT-LEVEL FILES

```
✨ DEVELOPER_HANDOFF.md — This handoff guide
✨ TICKETS.md — First 30 implementation tickets
✨ FILE_MANIFEST.md — This file
✨ DB_SCHEMA.md — Database schema (tables, migrations)
✨ API_CONTRACTS.md — API contracts (endpoints, payloads)
✨ ANTI_DRIFT.md — Anti-drift policies and rules
✨ README.md — Updated with new structure
✨ ROADMAP.md — 13-phase roadmap overview
✨ renovate.json — Dependency update config (optional)
```

---

## Summary Statistics

| Phase | Component | Files | Status |
|-------|-----------|-------|--------|
| 1 | Frontend Shell | 35 | ✨ New |
| 2 | Frontend State | 20 | ✨ New |
| 3 | Backend Runtime | 15 | ✨ New |
| 4 | Data Models | 25 | ✨ New |
| 5 | Adapters | 20 | ✨ New |
| 6 | Backfill | 15 | ✨ New |
| 7 | Features | 35 | ✨ New |
| 8 | Scoring V2 | 10 | ✨ New |
| 9 | Labeling | 10 | ✨ New |
| 10 | Training | 15 | ✨ New |
| 11 | Governance | 10 | ✨ New |
| 12 | Research UI | 20 | ✨ New |
| 13 | Observability | 30 | ✨ New |
| Packages | Shared | 15 | ✨ New |
| Docs | Documentation | 25 | ✨ New |
| **TOTAL** | | **300+** | |

---

## Dependencies and Ordering

**Frontend first (Phases 1-2):** UI and state management must stabilize before integration with new backends.

**Backend cleanup (Phase 3):** Decouple scoring from signal generation, enable config-driven behavior.

**Data expansion (Phase 4):** Add schema for governance, regime, features before implementation.

**Adapters + Backfill (Phases 5-6):** Enable data ingestion from multiple providers.

**Feature engineering (Phase 7):** Build features once data is available.

**Scoring V2 (Phase 8):** Implement config-driven scoring once features are built.

**Learning loop (Phases 9-11):** Train, validate, promote models once features and scoring are stable.

**UI + Ops (Phases 12-13):** Expose learning insights and monitoring last.

---

**For detailed implementation, refer to TICKETS.md (first 30 tickets for Phases 1-2).**

