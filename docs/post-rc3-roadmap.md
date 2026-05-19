# Post-RC-3 Development Roadmap

**Date Created:** 2026-04-25  
**Status:** Release Candidate 3 established; ready for next phase planning

---

## Executive Summary

**Release Candidate 3** was completed on 2026-04-25 with:
- 31 Build Plan 3 items (sections 1-8) completed
- 12 release gates passing (including new Gates 10-12 for BP3 work)
- 419 total QA test cases passing (344 backend + 75 frontend)
- Full AI learning loop integrated (outcome capture → performance stats → prompt adaptation)
- Autonomous paper trading operational with risk gating

The system is now in a **production-ready state** for deployment. Below is the recommended next phase roadmap.

---

## Phase 14 — Post-RC-3 Hardening (Optional, P2)

If additional validation before production deployment is desired:

### POH-01 — Alembic migration validation in staging environment
- **Action:** Apply Alembic migration `e7f8g9h0i1j2_add_signal_outcomes_table.py` to staging DB; confirm `signal_outcomes` table created with correct schema
- **Pass condition:** Table exists, columns match model definition, foreign key constraints verified
- **Owner:** Infrastructure/DevOps

### POH-02 — Paper trade end-to-end flow test
- **Action:** In staging, manually trigger full flow: asset seed → signal generation → opportunity ranking → auto-paper position creation → close by horizon expiry → outcome capture
- **Pass condition:** All steps complete, outcome row created, no errors in logs
- **Owner:** QA / Integration testing

### POH-03 — Learning loop validation
- **Action:** Populate `signal_outcomes` with seed data; call `GET /performance-stats`; call `POST /prompt-adaptations/apply` with test proposal; confirm new PromptVersion created (not update)
- **Pass condition:** Stats aggregate correctly, proposal route works, Gate 11 (immutability) verified
- **Owner:** Integration testing

### POH-04 — Load test: Polygon API rate limits under paper trading load
- **Action:** Simulate 1000 asset sweeps in rapid succession; confirm zero direct HTTP calls, confirm PolygonClient batching/throttling works, confirm no 429 rate limit errors
- **Pass condition:** Gate 12 (rate limit compliance) validated under load
- **Owner:** Performance testing

---

## Phase 15 — Broker Integration (P1 Deferred, Future Release)

The `LiveExecutionService` remains intentionally **scaffold/disabled**. To enable live trading:

### BIK-01 — Implement IBKR client library integration
- **Action:** Create `apps/api/app/clients/broker/ibkr_client.py`; wrap IB TWS/Gateway SDK; add methods for account info, order submission, position updates
- **Pass condition:** Client tests pass with mock IB server
- **Owner:** Backend

### BIK-02 — Implement live order execution service
- **Action:** Replace `LiveExecutionService` scaffold with real implementation; call IBKR client; return actual order IDs and fill confirmations
- **Pass condition:** Route test confirms orders submitted to real account (or simulated paper in IB)
- **Owner:** Backend

### BIK-03 — Add broker account connectivity test
- **Action:** Create integration test that connects to IB account, fetches positions, confirms account is accessible
- **Pass condition:** Test passes with valid IBKR credentials
- **Owner:** QA / Integration

### BIK-04 — Implement position sync from broker
- **Action:** Add background worker that periodically fetches open positions from IBKR; syncs with local `Position` table for reconciliation
- **Pass condition:** Worker tests pass, position data matches after sync
- **Owner:** Backend

---

## Phase 16 — Enhanced Signal Engine (P2 Deferred, Optional)

Improvements to signal generation and outcome learning:

### ESE-01 — Dynamic threshold adaptation
- **Action:** Modify `PromptAdaptationService` to recommend threshold adjustments (not just prompt text) based on win rate distribution by asset or regime
- **Pass condition:** Service returns suggested thresholds alongside prompt proposal
- **Owner:** Backend

### ESE-02 — Regime classification feedback loop
- **Action:** After outcomes close, re-classify regime at close; if regime predictions were wrong, log as "regime drift event"; feed to prompt adaptation logic
- **Pass condition:** Service identifies regime drift, includes in adaptation rationale
- **Owner:** Backend

### ESE-03 — Signal source diversity
- **Action:** Extend signal generation to accept multiple LLM models in a voting ensemble; aggregate signals by majority vote
- **Pass condition:** Ensemble signal endpoint returns merged output
- **Owner:** Backend

---

## Phase 17 — Advanced Analytics (P3 Deferred, Optional)

Operator-facing dashboards and performance insights:

### AAL-01 — Win rate decomposition by time-of-day
- **Action:** Extend `PerformanceStatsService` with time-of-day grouping; return win rates by hour/session
- **Pass condition:** Dashboard can show intraday performance patterns
- **Owner:** Backend

### AAL-02 — Drawdown waterfall visualization
- **Action:** Create frontend component showing cumulative PnL over time; highlight losing periods and recovery phases
- **Pass condition:** Chart renders on performance dashboard; interactive drill-down by trade
- **Owner:** Frontend

### AAL-03 — Signal source attribution
- **Action:** Track which LLM model generated each signal; analyze win rates per model; recommend best model per setup
- **Pass condition:** Attribution table shows model performance breakdown
- **Owner:** Backend + Frontend

---

## Deferred Items from BP3 (Can Resume Now)

The following items were explicitly deferred as P2 during BP3. Can be picked up immediately post-RC-3:

### DEF-01 — Sweep history UI (BP3-02.04)
- **Action:** Create endpoint `GET /sweeps?limit=100&days=7`; return paginated sweep results with signal counts
- **Action:** Create `apps/web/app/sweeps/page.tsx` with table showing daily sweep summaries
- **Owner:** Backend + Frontend

### DEF-02 — Position cap configurability (BP3-04)
- **Action:** Move `_DEFAULT_MAX_OPEN = 5` to Settings model; expose via admin UI
- **Pass condition:** Cap can be adjusted without code change
- **Owner:** Backend

### DEF-03 — Adaptive learning threshold
- **Action:** Instead of hard-coded `≥10 samples` for performance context injection, compute threshold dynamically based on asset volatility
- **Pass condition:** Context block appears with lower sample counts for stable assets
- **Owner:** Backend

---

## Critical Operational Checkpoints

Before moving to production, verify:

1. **Database backup strategy** — signal_outcomes table must be backed up daily
2. **API rate limiting** — PolygonClient API key limits understood and monitored
3. **Paper trade logging** — all auto_paper positions logged for audit trail
4. **Performance baseline** — response times for GET /performance-stats measured and acceptable
5. **Outcome data quality** — sample SignalOutcome rows manually inspected for correctness

---

## Recommended Next Action

**If deploying RC-3 to production now:**
1. Apply Alembic migration to production DB
2. Run POH-01 through POH-03 in staging
3. Deploy to production
4. Monitor logs for 24 hours; watch for any outcome capture errors
5. Proceed to Phase 15 (broker integration) or Phase 16 (enhanced signals) based on priorities

**If holding for additional validation:**
1. Complete Phase 14 items (POH-01 through POH-04)
2. Document any issues found
3. Create follow-up tickets for Phase 15+
4. Schedule Phase 15 kickoff

---

## Reference

- **BP3 completion:** [build-plan-3.md](build-plan-3.md) — all 31 items [DONE]
- **RC-3 details:** [current-phase-status.md](current-phase-status.md) — RC-3 section
- **Gate definitions:** [release-gates.md](release-gates.md) — Gates 1-12
- **Implementation matrix:** [implementation-matrix.md](implementation-matrix.md) — all features and their state
