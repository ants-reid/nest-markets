# MH-76 — Broker Safety Roadmap Re-Anchor

Date: 2026-04-30
Scope: backend/planning only
Status: complete

## Goal

Re-anchor the broker safety roadmap after MH-36 through MH-75 so the next implementation phases start from the actual backend safety state, not the UI visibility state.

This document does not change runtime behavior. It records what is currently active, advisory, blocked, and not yet wired, then proposes the next safe backend build order.

## Current backend safety state

### Active today

| Area | Current state | Notes |
|------|---------------|-------|
| Mode guard | Active and enforced | Broker mode consistency is enforced through the mode/trading-control guard path. Invalid paper/live combinations are rejected. |
| Manual paper submit | Active | Manual paper submit remains allowed when the environment is in a valid paper configuration. |
| Live manual submit | Blocked | Live submission is visible in state, but not armed. Submit remains blocked until later live-arming work exists. |
| Dry-run route | Active | Dry-run validates request shape and mode guard and returns `ready`, `invalid`, or `blocked`. |
| Broker audit logging | Active | Dry-run and submit events are recorded to the broker audit trail. |
| Trading control state | Active, env-backed | Trading mode, execution control, arming state, and blocked reasons are derived from env-backed control state. |

### Advisory only today

| Area | Current state | Notes |
|------|---------------|-------|
| Risk limits in dry-run | Advisory only | Dry-run collects configured risk-limit warnings and risk-limit snapshot data, but does not enforce them. |
| Trading halt in dry-run | Advisory only | Dry-run surfaces active halt state as a warning, but does not block on it. |
| Preflight context | Advisory only | Account, exposure, daily P&L, and risk snapshot values enrich dry-run output but do not change decision outcome. |
| Daily loss checks | Placeholder/advisory | The dry-run surface reports daily-loss placeholder warnings when configured, but no enforcement path exists yet. |

### Explicitly blocked today

| Area | Current state | Notes |
|------|---------------|-------|
| Auto trading | Hard blocked | `assert_auto_trading_allowed()` always blocks. No paper or live auto execution path is enabled through broker order flow. |
| Live execution | Hard blocked for submit | Live configuration can be visible, but live submit is not armed and remains blocked. |
| Casual paper/live switching | Blocked | Mixed paper/live env combinations are rejected by the mode guard. |

### Not yet wired

| Area | Current state | Notes |
|------|---------------|-------|
| Risk-limit enforcement in submit | Not wired | Risk limits exist as config/status/evaluation primitives, but submit does not enforce them. |
| Risk-limit enforcement in dry-run outcome | Not wired | Dry-run warnings do not yet become a structured blocking preflight decision. |
| Trading halt enforcement in submit | Not wired | Halt persistence and status exist, but submit does not enforce active halts. |
| Trading halt enforcement in dry-run outcome | Not wired | Dry-run reports halt warnings only; it does not block. |
| Structured preflight decision model | Not wired | There is no canonical backend decision object that separates advisory findings from hard blockers. |
| Paper auto-trading foundation | Not wired into broker order path | There is an isolated worker seam in the codebase, but no approved broker-path gating chain for paper automation yet. |
| Live manual arming | Not wired | No arming workflow or enforcement transition exists beyond the current blocked placeholder. |
| Live auto trading | Not wired | This remains much later and should not be attempted before paper automation and live manual arming are proven. |
| Paper/live toggle | Not wired and should remain deferred | A toggle is not the next safety move and should come after enforcement and arming work, not before. |

## Current backend interpretation

The backend already has the right foundation split:

1. Mode safety is enforced now.
2. Risk limits exist as configuration and evaluation primitives.
3. Trading halts exist as persistence and readback primitives.
4. Dry-run already aggregates advisory preflight information from those primitives.

The missing seam is not data collection. The missing seam is a canonical preflight decision layer that can later be reused by paper submit, then paper auto-trading, then live manual arming.

## Re-anchored safe sequence

The safest order remains:

1. risk and halt decision modeling first
2. paper submit enforcement second
3. emergency halt enforcement next
4. paper automation after those gates are proven
5. live manual arming later
6. live auto much later
7. toggle work last

## Recommended next implementation phases

### MH-77 — Dry-Run Enforcement Readiness

Goal:
Turn the current advisory risk/halt preflight surface into a structured backend decision model, still dry-run only.

Required output:

- a canonical preflight decision object returned by dry-run
- explicit distinction between:
  - advisory findings
  - would-block findings
  - enforcement-enabled flags
- no broker submit behavior changes yet

Constraints:

- dry-run remains non-executing
- paper submit remains behaviorally unchanged in this phase
- live submit remains blocked exactly as it is today
- auto trading remains blocked

Why first:

Because paper submit, paper auto-trading, and later live arming all need the same safety decision seam. Building that seam in dry-run first is the least risky place to define it.

### MH-78 — Paper Submit Preflight Gate

Goal:
Apply the structured preflight decision to manual paper submit only.

Required output:

- paper submit uses the same backend preflight decision logic already surfaced by dry-run
- clear blocking reasons are returned when paper submit is denied
- live submit behavior does not change beyond current blocking

Constraints:

- no auto-trading enablement
- no live manual arming
- no toggle work
- dry-run remains the preview surface for the same decision

Why second:

Because paper manual submit is the smallest real execution path. It is the right place to prove enforcement before any automation work exists.

### MH-79 — Emergency Halt Enforcement

Goal:
Make active halt state a real execution gate after the shared preflight decision exists.

Required output:

- active halt blocks paper submit
- active halt also blocks dry-run when the roadmap is ready to promote halt from advisory to enforced
- halt blocking reasons remain explicit and auditable

Constraints:

- no live enablement
- no auto-trading enablement
- no UI control expansion required for this backend phase

Why third:

Because emergency halt is a global safety override. Once decision modeling and paper submit enforcement are in place, halt can become an actual gate without inventing a separate control path.

### MH-80 — Paper Auto-Trading Foundation

Goal:
Introduce paper-only automation on top of the already-proven preflight, risk, and halt gates.

Required output:

- paper auto-trading remains isolated from live execution
- every automated paper order uses the same preflight decision path as manual paper submit
- halt and risk gates block automated paper flow before broker submission

Constraints:

- paper only
- no live arming
- no live auto
- no toggle work

Why fourth:

Because automation should consume an already-proven gate, not define one. Paper automation before risk/halt enforcement would widen execution surface prematurely.

## Deferred follow-on order

After MH-80, the next safe order should be:

1. live manual arming foundation
2. live manual submit enforcement under arming + risk + halt gates
3. live auto much later
4. paper/live toggle or broader operator controls last

## Explicit non-goals for the next phases

The following should remain out of scope until the earlier safety gates are complete:

- adding a paper/live toggle
- enabling live execution from the operator UI
- enabling live auto-trading
- bypassing the shared preflight decision for automation
- introducing separate risk logic for manual versus automated paper flow

## Implementation guidance

When MH-77 starts, use the existing `BrokerService.dry_run_order()` preflight collection path as the main insertion point for the structured decision seam. Do not fork separate decision logic into routes and services. The dry-run route should stay as a serializer/orchestrator, while the broker service should own preflight decision assembly.

When MH-78 starts, reuse that exact decision in `submit_order()` for paper mode rather than re-implementing risk or halt checks independently.

## Summary

The current backend is already in a good safety posture for the next step:

- mode guard is real and enforced
- dry-run exists and already aggregates the right advisory ingredients
- risk and halt foundations already exist
- auto trading is still blocked
- live submit is still blocked

The correct next move is not another UI phase and not a toggle. The correct next move is to convert advisory preflight into a reusable backend decision seam, enforce that seam for paper submit, then build paper automation on top of it.