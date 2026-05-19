# Market Hunter MVP — Developer Handoff Pack

**Date:** 2026-04-25  
**Status:** Phase 0 (Current State Assessment)  
**Audience:** Implementation team

---

## Overview

This document is your complete build blueprint for Market Hunter MVP. It covers:

- Current state of the application
- 13-phase refactoring roadmap
- Exact folder structure for all phases
- Complete file manifest (150+ files)
- Database schema additions
- API contract specifications
- First 30 implementation tickets

**Core principle:** Build on the existing foundation. Do not rebuild. Refactor in controlled phases.

---

## Current State (Phase 0)

Your application currently has:

### Frontend (Next.js 15.3.1 + React 19.1.0)
- 10 routes (dashboard, analytics, execution, workflow, signals, risk, approvals, alerts, notifications, opportunities, performance, prompt-adaptations)
- 5 reusable components (Nav, StatCard, ChartPanel, PersonalDashboard, charts)
- CSS token system (43 tokens, dark/light themes)
- 66/66 Playwright tests passing
- Responsive system with data-rs utilities

### Backend (FastAPI)
- 6 route files (signals, risk, workflow, approvals, execution, assets, etc.)
- 31 service files (signal, workflow, risk, execution, approval, paper_execution, etc.)
- 20 ORM models (Signal, Position, SignalOutcome, PaperOrder, RiskDecision, etc.)
- 174/174 tests passing
- Workflow orchestration (signal → risk → execution → approval/paper/live branches)
- Paper execution with deterministic sizing
- Opportunity ranking (40/30/10/20 weighted scoring)
- Learning loop (signal outcomes with r_multiple, mae/mfe)

### Test Coverage
- **Frontend:** 66 Playwright tests (smoke, regression, responsive, theme)
- **Backend:** 174 pytest tests (routes, services, models, integration)
- **All gates passing:** Gate 1 (matrix), Gate 2 (QA), Gate 3 (hex), Gate 4 (live guard), Gate 5 (arch), Gate 6 (tokens)

---

## 13-Phase Build Roadmap

| Phase | Focus | Duration | Status |
|-------|-------|----------|--------|
| **0** | Current state snapshot, baseline tests | **DONE** | ✅ Complete |
| **1** | Frontend shell modernization | ~2 weeks | 📋 Planned |
| **2** | Frontend state cleanup (controllers, reducers) | ~2 weeks | 📋 Planned |
| **3** | Backend runtime cleanup (scoring split, config) | ~2 weeks | 📋 Planned |
| **4** | Data model expansion (governance, regime, features, opportunities) | ~1 week | 📋 Planned |
| **5** | Provider adapters (IBKR, Twelve Data, Finnhub, FRED, SEC) | ~3 weeks | 📋 Planned |
| **6** | Historical backfill and ingestion jobs | ~2 weeks | 📋 Planned |
| **7** | Feature store and regime engine | ~3 weeks | 📋 Planned |
| **8** | Scoring engine v2 (config-driven, bucketed, regime-aware) | ~2 weeks | 📋 Planned |
| **9** | Learning loop and labeling | ~2 weeks | 📋 Planned |
| **10** | Training and validation pipelines | ~3 weeks | 📋 Planned |
| **11** | Model governance and rollout | ~2 weeks | 📋 Planned |
| **12** | Research and intelligence UI | ~2 weeks | 📋 Planned |
| **13** | Monitoring, observability, and ops | ~1 week | 📋 Planned |

**Total timeline:** ~31 weeks (7-8 months with two-week sprints)

---

## Repository Structure Target

```
market-hunter-mvp/
├── apps/
│   ├── web/                          [MODERNIZED]
│   │   ├── app/
│   │   │   ├── (shell)/
│   │   │   ├── analytics/
│   │   │   ├── execution/
│   │   │   ├── models/              [NEW]
│   │   │   ├── regime/              [NEW]
│   │   │   ├── news/                [NEW]
│   │   │   ├── calibration/         [NEW]
│   │   │   ├── drift/               [NEW]
│   │   │   ├── replay/              [NEW]
│   │   │   └── promotions/          [NEW]
│   │   ├── components/              [REFACTORED]
│   │   │   ├── shell/               [NEW]
│   │   │   ├── ui/                  [NEW]
│   │   │   ├── chart/               [UPGRADED]
│   │   │   └── ...
│   │   ├── lib/
│   │   │   ├── api/                 [SPLIT]
│   │   │   ├── hooks/               [NEW]
│   │   │   ├── state/               [NEW]
│   │   │   └── utils/
│   │   ├── styles/                  [NEW]
│   │   └── ...
│   │
│   ├── api/                         [REFACTORED]
│   │   ├── app/
│   │   │   ├── api/routes/
│   │   │   │   ├── [EXISTING]
│   │   │   │   ├── models.py        [NEW]
│   │   │   │   ├── scoring.py       [NEW]
│   │   │   │   ├── regime.py        [NEW]
│   │   │   │   └── governance.py    [NEW]
│   │   │   ├── services/
│   │   │   │   ├── runtime/         [NEW]
│   │   │   │   ├── governance/      [NEW]
│   │   │   │   ├── [EXISTING]
│   │   │   │   └── ...
│   │   │   ├── clients/             [EXPANDED]
│   │   │   ├── db/models/           [EXPANDED]
│   │   │   └── ...
│   │   ├── tests/
│   │   │   ├── services/
│   │   │   ├── routes/
│   │   │   └── evals/
│   │   └── ...
│   │
│   └── learning/                    [NEW APP]
│       ├── jobs/
│       │   ├── backfill_bars_job.py
│       │   ├── backfill_news_job.py
│       │   ├── backfill_macro_job.py
│       │   └── refresh_universe_job.py
│       ├── features/
│       │   ├── technical/
│       │   ├── cross_sectional/
│       │   ├── macro/
│       │   ├── news/
│       │   └── execution/
│       ├── services/
│       │   ├── backfill/
│       │   ├── regime/
│       │   ├── labeling/
│       │   └── normalization/
│       ├── pipelines/
│       │   ├── train_regime_model.py
│       │   ├── train_scoring_model.py
│       │   ├── validate_walk_forward.py
│       │   └── compare_shadow_vs_active.py
│       ├── tests/
│       └── ...
│
├── packages/                        [NEW]
│   ├── shared-types/
│   │   ├── src/
│   │   │   ├── scoring.ts
│   │   │   ├── regime.ts
│   │   │   ├── models.ts
│   │   │   └── index.ts
│   │   └── package.json
│   ├── shared-config/
│   │   ├── src/
│   │   │   ├── scoring-buckets.ts
│   │   │   ├── risk-profiles.ts
│   │   │   └── index.ts
│   │   └── package.json
│   └── shared-ui-tokens/
│       ├── src/
│       │   ├── colors.ts
│       │   ├── spacing.ts
│       │   ├── typography.ts
│       │   └── index.ts
│       └── package.json
│
├── infra/                           [NEW]
│   ├── docker/
│   │   ├── Dockerfile.web
│   │   ├── Dockerfile.api
│   │   ├── Dockerfile.learning
│   │   ├── docker-compose.yml
│   │   └── .dockerignore
│   ├── db/
│   │   ├── migrations/
│   │   ├── seeds/
│   │   └── init.sql
│   ├── observability/
│   │   ├── dashboards/
│   │   │   ├── ingestion-lag.json
│   │   │   ├── model-drift.json
│   │   │   ├── broker-health.json
│   │   │   └── queue-health.json
│   │   ├── alerts/
│   │   │   ├── provider-outage.yml
│   │   │   ├── model-drift.yml
│   │   │   ├── ingestion-lag.yml
│   │   │   └── queue-failure.yml
│   │   └── prometheus.yml
│   └── ci/
│       ├── .github/workflows/
│       │   ├── test-web.yml
│       │   ├── test-api.yml
│       │   ├── test-learning.yml
│       │   ├── deploy-web.yml
│       │   └── deploy-api.yml
│       └── ci-gates.yml
│
├── docs/                            [EXPANDED]
│   ├── architecture/
│   │   ├── current-state.md
│   │   ├── target-architecture.md
│   │   ├── runtime-vs-learning.md
│   │   ├── service-boundaries.md
│   │   └── flow-diagrams.md
│   ├── api/
│   │   ├── current-endpoints.md
│   │   ├── new-endpoints.md
│   │   ├── contracts-execution.md
│   │   ├── contracts-scoring.md
│   │   ├── contracts-models.md
│   │   ├── contracts-governance.md
│   │   └── contracts-learning.md
│   ├── data/
│   │   ├── er-diagram.md
│   │   ├── table-glossary.md
│   │   ├── universes.md
│   │   ├── provider-priority-matrix.md
│   │   ├── point-in-time-rules.md
│   │   └── retention-policy.md
│   ├── models/
│   │   ├── feature-catalog.md
│   │   ├── regime-taxonomy.md
│   │   ├── training-policy.md
│   │   ├── model-promotion-policy.md
│   │   ├── sample-size-policy.md
│   │   └── score-explanation-spec.md
│   ├── product/
│   │   ├── ui-modernization-plan.md
│   │   ├── page-inventory.md
│   │   ├── component-library.md
│   │   └── navigation-plan.md
│   ├── testing/
│   │   ├── baseline-test-report.md
│   │   ├── test-strategy.md
│   │   ├── model-validation-checklist.md
│   │   ├── visual-regression-plan.md
│   │   └── release-gates.md
│   └── runbooks/
│       ├── backfill-runbook.md
│       ├── provider-failure.md
│       ├── model-rollback.md
│       ├── incidents.md
│       └── deployments.md
│
├── scripts/
│   ├── db/
│   │   ├── init-dev.sh
│   │   ├── migrate.sh
│   │   └── seed.sh
│   ├── learning/
│   │   ├── backfill-bars.sh
│   │   ├── backfill-news.sh
│   │   ├── train-models.sh
│   │   └── promote-model.sh
│   ├── deploy/
│   │   ├── deploy-web.sh
│   │   ├── deploy-api.sh
│   │   ├── deploy-learning.sh
│   │   └── rollback.sh
│   └── test/
│       ├── test-all.sh
│       ├── test-web.sh
│       ├── test-api.sh
│       └── test-learning.sh
│
├── .github/
│   └── workflows/
│       ├── test.yml
│       ├── deploy.yml
│       └── release.yml
│
├── README.md
└── ROADMAP.md
```

---

## Implementation Entry Point

**Start here:** See `TICKETS.md` for the first 30 tickets in order.

**Key files created at Phase 0 completion:**
- ✅ [DEVELOPER_HANDOFF.md](DEVELOPER_HANDOFF.md) (this file)
- ✅ [TICKETS.md](TICKETS.md) (30 tickets, Phase 1-2)
- ✅ [FILE_MANIFEST.md](FILE_MANIFEST.md) (all 150+ files, all 13 phases)
- ✅ [DB_SCHEMA.md](DB_SCHEMA.md) (all table definitions, migrations)
- ✅ [API_CONTRACTS.md](API_CONTRACTS.md) (all new endpoints, request/response schemas)
- ✅ [ANTI_DRIFT.md](ANTI_DRIFT.md) (code, model, product drift controls)
- ✅ [RELEASE_GATES.md](docs/testing/release-gates.md) (8 gating phases)

---

## Quick Start for Sprint 1

**Goal:** Frontend shell modernization + state cleanup foundation

**Tickets:** 1-10  
**Duration:** 2 weeks  
**Deliverables:**
- New shell (AppShell, Sidebar, Topbar, PageHeader)
- Primitive components (Card, MetricCard, Panel, Button, Badge)
- Dashboard refactored to use shell
- Visual regression baseline

**Testing gates:**
- All new components have storybook stories
- All current routes render without visual diff
- Theme switching works
- Responsive tests pass at 390/768/1024px

---

## Next Steps

1. **Review** this handoff
2. **Read** TICKETS.md (first 30 tickets, 2-week plan)
3. **Read** FILE_MANIFEST.md (complete file tree)
4. **Read** DB_SCHEMA.md (all new tables)
5. **Read** API_CONTRACTS.md (all new endpoints)
6. **Start** Ticket 1 (create AppShell.tsx)

---

## Questions?

Refer to:
- **Architecture questions:** docs/architecture/
- **API questions:** docs/api/
- **Data questions:** docs/data/
- **Model questions:** docs/models/
- **Testing questions:** docs/testing/
- **Operational questions:** docs/runbooks/

---

**Good luck. Build incrementally. Test relentlessly. Keep the learning engine decoupled.**

