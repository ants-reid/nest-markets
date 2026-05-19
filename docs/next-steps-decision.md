# Next Steps: RC-3 → Production → Phase 15

**Status:** RC-3 is production-ready. Three parallel paths available.

---

## 🚀 Path 1: Deploy RC-3 to Production (Immediate)

**Timeline:** 1-2 hours

### Steps:
1. **Apply Alembic migration** to production database:
   ```bash
   cd apps/api
   alembic upgrade head
   ```

2. **Deploy backend code** (CI/CD or manual):
   - Current: `apps/api/` with all Phase 1-8 features
   - Includes signal generation, risk evaluation, paper trading, approvals, execution workflow, alerts, notifications, performance stats, prompt adaptations

3. **Deploy frontend code** (CI/CD or manual):
   - Current: `apps/web/` with responsive design, all 13 routes
   - Includes dashboard, workflows, signals, risk, execution, alerts, approvals, assets, analytics, performance, prompt adaptations

4. **Run health checks:**
   ```bash
   curl http://<prod>/health  # Backend
   # Verify frontend loads without 404s
   ```

5. **Monitor for 24 hours:**
   - Watch logs for signal generation errors
   - Verify paper positions open/close correctly
   - Check that outcome capture works (signal_outcomes table populated)

**Rollback Plan:** If issues occur, revert to previous code; migration is forward-compatible.

---

## 💻 Path 2: Continue with Phase 15 (Broker Integration)

**Timeline:** 10-14 days of development

### What's New:
- Replace live execution scaffold with IBKR integration
- Add pre-flight safety gates (position limits, margin checks)
- Real-money execution capability (sandbox → production)

### Deliverables:
- `IBKRClientService` (IBKR API wrapper)
- Rewritten `LiveExecutionService` (replaces scaffold)
- `ExecutionSafetyGate` (risk validation)
- End-to-end tests + staging validation

**See:** `phase-15-broker-integration-plan.md` (just created)

### Next Step if Choosing Path 2:
1. Provision IBKR sandbox account
2. Start BP-15.1.1 (IBKR client service)
3. Follow the 4-week plan: Weeks 1-2 (client + service), Week 2-3 (route + safety), Week 3 (staging validation)

---

## 📋 Path 3: Complete Deferred Items (Optional Polish)

**Timeline:** 3-5 days

### Items:
- **Sweep history UI** (BP3-02.04) — Show historical signal sweeps and ranking deltas
- **Position cap configurability** — Admin panel to adjust execution limits
- **Chart enhancements** — Drawdown visualization, time-of-day decomposition
- **Mobile optimizations** — Touch-friendly controls for mobile trading

### Impact:
- Improves UX but not required for production
- No blocking dependencies

---

## ✅ Recommended Sequence

**For fastest go-live with Phase 15 capability:**

1. **Now (T+0):** Deploy RC-3 to staging or production
   - Verify all systems working
   - 24-hour observation period

2. **Parallel (T+1):** Start Phase 15 development
   - Provision IBKR sandbox account
   - Begin BP-15.1.1 while monitoring production

3. **T+14:** Phase 15 complete; ready for IBKR sandbox testing

4. **T+21:** After 7 days of staging IBKR testing, promote to production

---

## 📊 Current System State

### ✅ Validated Features (RC-3, 355/355 tests passing)
- Signal generation (LLM-powered + mock)
- Risk evaluation (leverage, concentration, drawdown)
- Paper trading (open/close positions, fill simulation)
- Approval workflow (manual approval gates)
- Position tracking (notional, direction, status)
- Alerts & notifications (rule-based)
- Performance stats (win rate by setup/asset/regime)
- Prompt adaptations (underperformance detection)
- Responsive design (mobile to desktop)
- Dark/light theme (CSS token parity)

### ⚠️ What's Not Ready Yet
- **Live execution** (IBKR integration = Phase 15)
- **Background workers** (scheduled tasks = Phase 7)
- **Advanced analytics** (drawdown, time decomposition = Phase 17)

---

## 🎯 Decision Required

**Which path would you like to pursue?**

- **A** → Deploy RC-3 now; start Phase 15 separately
- **B** → Deploy RC-3 now; pause development (observe production)
- **C** → Pause; prepare Phase 15 first, then deploy combined
- **D** → Custom combination

**Default recommendation:** **A** — Deploy RC-3 immediately (it's ready); begin Phase 15 in parallel.

---

*For details on Phase 15, see `phase-15-broker-integration-plan.md`*  
*For production deployment steps, see `rc3-deployment-checklist.md`*
