# Release Candidate 3 — Deployment Checklist

**Release Date:** 2026-04-25  
**Version:** RC-3  
**Approval Status:** ☐ Pending review

---

## Pre-Deployment Verification (WS-07)

### Code Quality & Testing
- [x] Backend test suite: 344/344 passing
- [x] Frontend test suite: 75/75 passing
- [x] All 12 release gates passing
- [x] No merge conflicts in code
- [x] No uncommitted changes in tracked files

### Documentation
- [x] build-plan-3.md: All 31 items marked [DONE]
- [x] current-phase-status.md: RC-3 entry complete with gate results
- [x] post-rc3-roadmap.md: Created with future phase guidance
- [x] release-gates.md: All gate definitions documented
- [x] implementation-matrix.md: All BP3 items registered

### Alembic Migration
- [x] Migration file created: `e7f8g9h0i1j2_add_signal_outcomes_table.py`
- [x] Migration syntax validated (no syntax errors)
- [x] SignalOutcome model matches migration schema
- [ ] Migration tested in staging environment (POH-01)
- [ ] Backup of production DB created before applying migration
- [ ] Rollback procedure documented

### New Features Ready
- [x] Asset universe seeding (20+ assets, FX/ETF/COMMODITY/CRYPTO)
- [x] SignalSweepWorker operational (Polygon integration)
- [x] OpportunityRankerService operational
- [x] AutoPaperTraderWorker operational (Gate 10 compliant)
- [x] SignalOutcome capture (ready pending migration)
- [x] PerformanceStatsService operational
- [x] PromptAdaptationService operational (Gate 11 compliant)
- [x] Performance dashboard page ready
- [x] Prompt adaptations UI page ready

### Gate Audit Results

| Gate | Status | Notes |
|---|---|---|
| Gate 1 — Implementation Matrix | PASS | All 25+ impl IDs present and documented |
| Gate 2 — QA Coverage | PASS | 419 total QA cases, all passing |
| Gate 3 — Hex Token Audit | PASS | Zero raw hex literals or rgba() in TSX |
| Gate 4 — Live Execution Guard | PASS | LiveExecutionService scaffold preserved; guarded |
| Gate 5 — Architecture Compliance | PASS | No inline logic in routes; all services delegated |
| Gate 6 — Token Parity | PASS | Dark and light theme blocks identical (43 tokens) |
| Gate 7 — Broker Isolation | PASS | No direct broker SDK calls outside client layer |
| Gate 8 — Market Data Isolation | PASS | No direct HTTP calls; PolygonClient enforced |
| Gate 9 — Worker Compliance | PASS | All workers extend BaseWorker; schedulers extend BaseScheduler |
| Gate 10 — Auto-Paper Risk Gating | PASS | RiskService.evaluate() ALWAYS called before position creation |
| Gate 11 — Prompt Immutability | PASS | NEW PromptVersion rows only; zero UPDATE statements |
| Gate 12 — Polygon Rate Limits | PASS | Zero direct httpx/requests/aiohttp in workers |

---

## Staging Deployment (Pre-Production)

### Phase A: Database Setup
- [ ] Provision staging PostgreSQL instance (or use existing staging DB)
- [ ] Apply Alembic migration to staging: `alembic upgrade head`
- [ ] Verify `signal_outcomes` table created with correct schema
- [ ] Run POST-HOC-01 validation test

### Phase B: Seed Data
- [ ] Run seed_assets.py on staging to populate 20 initial assets
- [ ] Verify asset count in DB: `SELECT COUNT(*) FROM assets WHERE is_active = true;`
- [ ] Create 1-2 sample signal_outcomes rows manually for testing

### Phase C: Integration Testing
- [ ] Run POH-02 end-to-end paper trade flow in staging
- [ ] Run POH-03 learning loop validation
- [ ] Monitor logs for errors; verify no exceptions

### Phase D: Performance Baseline
- [ ] Measure GET /performance-stats latency (target: <500ms)
- [ ] Measure GET /opportunities response time (target: <1s)
- [ ] Run POH-04 simulated load test (1000 asset sweeps)

### Phase E: Monitoring & Alerting
- [ ] Set up log aggregation to watch for signal_outcomes insert errors
- [ ] Configure alerts for Polygon API rate limit breaches
- [ ] Set up database backup cronjob for signal_outcomes table

---

## Production Deployment

### Pre-Flight (T-1 Day)
- [ ] Schedule maintenance window or zero-downtime deployment plan
- [ ] Notify stakeholders of deployment date/time
- [ ] Prepare rollback procedure (document down-revision Alembic command)
- [ ] Tag release in Git: `git tag -a rc-3-prod -m "Release Candidate 3 Production"`

### Deployment Day (T=0)
1. **Backup**
   - [ ] Create full database snapshot before migration
   - [ ] Verify backup integrity

2. **Code Deployment**
   - [ ] Deploy API code changes (all new services, routes, workers)
   - [ ] Deploy frontend code changes (all new pages and components)
   - [ ] Verify health check: `GET /health` → 200 OK

3. **Database Migration**
   - [ ] Connect to production DB
   - [ ] Run: `cd apps/api && alembic upgrade head`
   - [ ] Verify: `SELECT table_name FROM information_schema.tables WHERE table_name='signal_outcomes';`
   - [ ] Verify schema: `\d signal_outcomes` (psql) or equivalent

4. **Verification**
   - [ ] Test signal sweep manually; confirm no errors
   - [ ] Test opportunity ranking; confirm /opportunities returns data
   - [ ] Test performance stats; confirm /performance-stats responds
   - [ ] Check logs for any exceptions (should be none)

5. **Post-Deployment Monitoring (First 24 Hours)**
   - [ ] Monitor error logs in real-time
   - [ ] Check database query performance (signal_outcomes queries should be fast)
   - [ ] Monitor API response times
   - [ ] Verify Polygon API rate limits not exceeded
   - [ ] Confirm no duplicate signal_outcomes rows created
   - [ ] Check disk space usage (new table may grow; no urgent action needed at MVP scale)

### Rollback Procedure (If Needed)
If critical issues found within first hour:
1. Stop background workers: stop scheduled signal_sweep, auto_paper_trader, auto_paper_close
2. Rollback Alembic: `alembic downgrade d058936fdd0d` (previous migration)
3. Rollback code: deploy previous stable version
4. Restore from backup if data corruption suspected
5. Run full test suite again before re-deploying

---

## Post-Deployment (T+1 Day to T+7 Days)

### Observation Phase
- [ ] Monitor all key metrics: API latency, error rates, DB query performance
- [ ] Check signal_outcomes table growth rate (should be ~N outcomes per sweep)
- [ ] Verify Polygon API calls within quota
- [ ] Review logs for any warnings or unexpected behavior

### Success Criteria
- [ ] Zero critical errors in logs for 24 hours
- [ ] All API endpoints respond within SLA (<1s for most queries)
- [ ] Database queries on signal_outcomes complete in <100ms
- [ ] Paper trades execute and close without exceptions
- [ ] Outcomes captured correctly (manual spot checks)

### Next Steps
If all success criteria met:
- [ ] Close RC-3 release ticket
- [ ] Begin planning Phase 15 (Broker Integration) or Phase 16 (Enhanced Signals)
- [ ] Schedule post-mortem / lessons learned meeting

If issues found:
- [ ] Create incident ticket with detailed error logs
- [ ] Schedule triage meeting to determine root cause
- [ ] Either hotfix and redeploy, or rollback and plan fix for RC-4

---

## Sign-Off

| Role | Name | Date | Status |
|---|---|---|---|
| Build Lead | (autonomous) | 2026-04-25 | ✓ RC-3 verified ready |
| QA Lead | (not assigned) | — | ☐ Pending approval |
| DevOps Lead | (not assigned) | — | ☐ Pending approval |
| Product Owner | (not assigned) | — | ☐ Pending approval |

---

## Appendix: Quick Reference

**Key Files to Deploy:**
- API: `apps/api/app/` (all .py changes)
- Web: `apps/web/app/` (all .tsx changes)
- Migration: `apps/api/alembic/versions/e7f8g9h0i1j2_*.py`

**Environment Variables:**
- `APP_ENV=production` (disables test overrides)
- `POLYGON_API_KEY=<key>` (must be set)
- `DATABASE_URL=postgresql://...` (production DB)
- `OPENAI_API_KEY=<key>` (for signal generation)

**Health Check URL:**
```
GET http://<api-host>:8000/health
Expected: {"status": "ok"}
```

**Rollback Command:**
```bash
cd apps/api && alembic downgrade d058936fdd0d
```

**Database Verification Query:**
```sql
SELECT 
  table_name, 
  column_count 
FROM (
  SELECT table_name, COUNT(*) as column_count 
  FROM information_schema.columns 
  WHERE table_schema='public' 
  GROUP BY table_name
) t 
WHERE table_name = 'signal_outcomes';
```
