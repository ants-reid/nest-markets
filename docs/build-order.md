# Build Order

Date: 2026-04-23

## Control Note

This file now serves two purposes:

1. preserve the intended build sequence
2. record where the current repository has moved ahead, drifted, or remains incomplete

For operational tracking, use these linked control docs:

- `docs/catch-up-action-plan.md`
- `docs/implementation-matrix.md`
- `docs/regression-qa-matrix.md`

## Phase 1
- config
- logging
- app bootstrap
- db base
- db session
- health route

Current status: complete

## Phase 2
- database models
- migrations
- seed assets

Current status: likely implemented, still needs a full audit against models and migrations

## Phase 3
- indicators
- feature engine

Current status: complete and documented

## Phase 4
- LLM provider interface
- OpenAI provider
- prompt loading
- schema loading

Current status: complete and documented

## Phase 5
- signal service
- risk service
- risk profiles
- execution mode router

Current status: substantially implemented and in active use

## Phase 6
- paper execution service
- approval workflow
- live execution scaffold

Current status: partially to substantially implemented; real paper execution, approvals, and live-disabled scaffold exist, but the phase needs a canonical completion summary

## Phase 7
- workers
- schedules
- sync jobs

Current status: not evident from current repo audit; must be explicitly documented as implemented or not started

## Phase 8
- frontend dashboard

Current status: exceeded original scope; the frontend is now a multi-route application shell, not just a dashboard

## Phase 9
- evals
- prompt versioning pages
- regression tests

Current status: partial; smoke tests exist, but broad regression coverage and prompt-versioning surfaces were not verified in this audit

## Rule
Only build one phase at a time.
Do not jump ahead.
Do not add live trading in MVP.

## Current Catch-Up Rule

The repository has already moved ahead of the original strict sequence. Until drift is recovered, use this order:

1. `WS-01` source-of-truth inventory
2. `WS-02` build-order reconciliation
3. `WS-03` architecture audit
4. `WS-04` theme and token governance
5. `WS-05` regression baseline
6. `WS-06` new-feature integration review
7. `WS-07` release gates

No major new surface area should be added until those workstreams are materially advanced.
