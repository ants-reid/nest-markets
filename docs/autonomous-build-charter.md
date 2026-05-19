# Autonomous Build Charter

Date: 2026-04-24
Applies to: Build Plan 3 (`docs/build-plan-3.md`) and all subsequent build plans

## Purpose

This charter authorises an autonomous build agent to implement all steps in the current
active build plan **without requiring human approval between steps**, provided the rules
below are satisfied. The human owner only needs to review at gate checkpoints and make
decisions on the explicit escalation triggers listed here.

---

## Autonomous Execution Authority

The build agent is authorised to, **without asking for approval**:

| Action | Scope |
|---|---|
| Create new Python source files | `apps/api/app/**` |
| Create new TypeScript/TSX source files | `apps/web/app/**`, `apps/web/components/**` |
| Create new test files | `apps/api/tests/**`, `apps/web/tests/**` |
| Create Alembic migrations | `apps/api/alembic/versions/**` |
| Create seed scripts | `apps/api/scripts/**` |
| Edit any source file to implement a `[NOT STARTED]` build plan step | Any file in the codebase |
| Update docs to mark steps `[IN-PROGRESS]` and `[DONE]` | `docs/**` |
| Update `docs/implementation-matrix.md` row status fields | Status, validation, documentation columns |
| Update `docs/regression-qa-matrix.md` row status from `pending` to `passing` | After verified test pass |
| Add new rows to `docs/implementation-matrix.md` and `docs/regression-qa-matrix.md` | New IDs only |
| Run backend test suite and Playwright suite | Read-only validation |
| Run gate check commands | All grep/ast gate checks |

---

## Mandatory Checkpoints (Human Review Required)

The agent **must pause and present results** at the following points:

| Checkpoint | Trigger | What to Present |
|---|---|---|
| Section gate | Before marking an entire BP3 section `[DONE]` | Test suite counts, any failing tests, gate check output |
| RC-3 gate execution | Before writing the RC-3 entry in `current-phase-status.md` | Full gate results table (all 12 gates) |
| Alembic migration | Before applying a migration to a non-test DB | Migration script content, affected tables |
| Live trading guard change | Any proposed change to `live_execution_service.py` or `LIVE_TRADING_ENABLED` | Full diff and rationale |
| Prompt adaptation apply | Any call to `POST /prompt-adaptations/apply` in production | Proposed prompt text, old vs new diff, win-rate data driving the change |
| Dependency addition | Any new entry in `pyproject.toml` or `package.json` | Package name, version, purpose, security note |

---

## Execution Order (Build Plan 3)

The agent works through `docs/build-plan-3.md` in the recommended execution order:

```
Phase 10 (Sections 1–3):
  BP3-01.01 → BP3-01.02 → BP3-02.01 → BP3-02.02 → BP3-02.03 → BP3-03.01 → BP3-03.02
  [Checkpoint: Section 1–3 gate review]

Phase 11 (Sections 4–5):
  BP3-04.01 → BP3-04.02 → BP3-04.03 → BP3-04.04 → BP3-04.05 → BP3-05.01 → BP3-05.02 → BP3-05.03
  [Checkpoint: Section 4–5 gate review]

Phase 12 (Sections 6–7):
  BP3-06.01 → BP3-06.02 → BP3-06.03 → BP3-06.04 → BP3-06.05 → BP3-07.01 → BP3-07.02 → BP3-07.03
  [Checkpoint: Section 6–7 gate review]

Phase 13 (Section 8 — Gate Hardening):
  BP3-08.01 → BP3-08.02 → BP3-08.03 → BP3-08.04 → BP3-08.05
  [Checkpoint: RC-3 gate results — human confirms release candidate]
```

UI steps (WEB-P13–WEB-P17) may be deferred to the end of each phase if backend delivery
is the current priority. The agent decides this autonomously.

---

## Anti-Drift Enforcement (Autonomous)

Before marking any step `[DONE]`, the agent **automatically runs the relevant gate checks**:

| Step type | Auto-checks run |
|---|---|
| Any new TSX file | Gate 3 (hex literal scan) |
| Any new worker | Gate 9 (BaseWorker subclass check) |
| Any auto-paper path | Gate 10 (risk gate call chain trace) |
| Any PromptVersion write | Gate 11 (no in-place update assertion) |
| Any Polygon-touching worker | Gate 12 (raw HTTP call scan) |
| Any new impl row | Gate 1 (matrix row present before DONE) |
| Any new feature | Gate 2 (QA ID linked before DONE) |

If a gate check fails, the agent fixes the violation in the same step before marking `[DONE]`.
It does not skip gates or defer violations to a later step.

---

## Decision Rules (No Human Input Needed)

| Decision | Rule |
|---|---|
| Which assets to seed in the universe | Use the 20 listed in BP3-01.01 exactly |
| Default auto-paper position cap | `AUTO_PAPER_MAX_OPEN_POSITIONS=5` |
| Performance stats minimum samples before context injection | `min_samples=10` |
| Adaptation trigger threshold | win rate < 40% with ≥ 20 samples |
| Sweep interval | Every 4 hours (configurable via env, default 4h) |
| Close worker interval | Daily at 22:00 UTC |
| LLM mock for tests | Use existing `MockLLMProvider` pattern from `tests/evals/` |
| New QA IDs | Increment from QA-226 upward |
| New impl IDs | Follow existing prefix conventions (API-S16, API-W09, etc.) |
| Error handling for missing Polygon key | Log warning, skip asset for this sweep, continue |
| Error handling for failed risk evaluation | Log error, skip opportunity, continue |

---

## What Requires Owner Input (Cannot Be Auto-Resolved)

- Adding a **new external service or API** not already in the architecture (e.g. a new broker)
- Changing the **IBKR live execution path** from disabled to enabled
- Changing **risk rule thresholds** in `risk-rules.md`
- Deciding to **cancel or skip** a build plan step entirely
- Any change that would cause a currently-passing test to **permanently fail by design**
- Setting a real `POLYGON_API_KEY` or `OPENAI_API_KEY` in a production environment

---

## Status Tracking Convention

The agent updates `docs/build-plan-3.md` step statuses using this format:

```
[IN-PROGRESS] — started YYYY-MM-DD
[DONE] YYYY-MM-DD — <one line summary of what was built and what test count confirms it>
```

At the end of each phase, the agent adds an entry to `docs/current-phase-status.md` with
test suite counts and a summary of what was shipped.

---

*This charter is in force from 2026-04-24 until superseded by a Build Plan 4 charter.*
*Owner: Ants | Agent: GitHub Copilot (Claude Sonnet 4.6)*
