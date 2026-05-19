# Broker Operator Guide

This guide explains the broker review page at `/broker` from an operator point of view. It is a read-only safety and review surface around the current broker session plus a guarded manual paper-order workflow.

## Page layout

The broker page is organized into four top-level review areas:

1. `Overview`
   Shows broker readiness, broker health, trading control, and current-day P&L context.
2. `Manual Review`
   Holds the manual paper order workflow, including dry-run, advisory context, and explicit confirmation before submit.
3. `Provenance`
   Shows normalized broker trade-event provenance, filters, exports, and a detail drawer for reconciliation.
4. `Audit`
   Shows recent broker order audit events for dry-runs and submits.

There is also an `Open Positions` section in the review flow showing the active account's current positions and account metrics.

## Overview section

The `Overview` section is where operators check current posture before doing anything else.

### Broker Health

The broker health card surfaces the current broker/runtime state with badges such as:

- `Paper Ready`
- `Config Only`
- `Live Config Only`
- `Live Ready`
- `Misconfigured`

It also shows three high-signal checks:

- `Mode Guard`
- `Gateway`
- `Account`

Treat this panel as visibility into current state, not as a permission control by itself. If health is unavailable, the page shows `Health check unavailable` rather than guessing.

### Trading Control

The trading control panel shows the current control posture for the active broker session:

- trading mode
- execution control
- arming state
- paper order submission status
- live order submission status
- auto trading status
- emergency stop status
- blocked reasons / safety notes

Important operator reading:

- `Paper Mode` means the current session is aligned with the paper workflow.
- `Live Configured` means live configuration is visible, not that live execution is enabled for operators.
- `Live order submission blocked.` is expected at this stage.
- `Auto trading locked.` is expected at this stage.

### Daily P&L strip

When daily P&L snapshots are available for the active account, the page shows:

- today’s P&L
- daily loss, when present
- snapshot count for the active account

If there are no snapshots, this strip is hidden rather than showing fabricated values.

## Paper/live status visibility

The broker page exposes paper/live visibility in two places:

1. `Broker Health` shows the observed runtime status and whether the current account is paper-aligned.
2. `Trading Control` shows the configured trading mode and whether paper or live submission is allowed.

Operationally, this page is still paper-first:

- it does not provide a paper/live mode toggle
- it does not provide dual paper/live panels
- it does not provide a second broker session view
- it does not convert `Live Configured` or `Live Ready` into operator permission to trade live

## Dry-run vs submit

The `Manual Paper Order Submit` panel keeps the same guarded workflow:

1. Enter symbol, side, quantity, and order type.
2. Run `Dry Run` first.
3. Review the returned advisory context and any issues/warnings.
4. Use `Submit Order` only after a successful dry-run.
5. Confirm the order in the confirmation panel before the submit request is sent.

Key distinctions:

- `Dry Run` is a pre-submit validation and context step.
- `Submit` is the actual paper order submission path.
- dry-run warnings remain advisory only
- dry-run issues can block the operator from proceeding to submit
- preflight context is informational and does not mean risk enforcement exists on submit yet

The preflight panel can show advisory values such as estimated notional, exposure, daily P&L, daily loss, and risk limit snapshots. Those fields help review the current account context, but they do not turn the page into an automated risk gate.

## Readiness checklist and local snapshots

The readiness panel summarizes current broker review posture from the loaded page state. It is intended for operator review and change tracking, not as an execution approval switch.

### Checklist meanings

- `Ready` means the relevant condition is present in the current page state.
- `Missing` means the relevant condition is absent or unavailable.
- `Advisory` means the item is informational and may need a fresh dry-run or more operator review.

The readiness score is guidance only. It should not be treated as authorization for live trading.

### Snapshot history

Operators can save the current readiness summary as a local snapshot. Snapshot history is stored in the browser only and currently keeps up to `8` snapshots.

Available history actions include:

- `Save Snapshot`
- export history as JSON
- export history as CSV
- copy the selected snapshot summary
- clear local snapshot history with confirmation
- import snapshot history from JSON

Because this history is browser-local, it should be treated as operator convenience state, not a durable system-of-record.

### Compare and timeline views

Saved snapshots support:

- before-vs-latest comparison
- changed item summaries
- regression/improvement visibility
- score timeline visualization

This is intended to help operators understand how the broker review posture changed over time.

### Backup packs

The readiness workflow can also export and import a backup pack. A backup pack can include:

- readiness snapshots
- current readiness snapshot
- provenance export rows, when available
- audit export rows, when available

Use backup packs as portable review artifacts for handoff or offline inspection. They remain documentation/review artifacts, not execution controls.

## Provenance panel

The `Normalized Trade Event Provenance` panel is a read-only reconciliation surface for normalized trade events.

It supports:

- filtering by symbol
- filtering by source
- filtering by account
- filtering to rows where realized P&L is present
- exporting the filtered result set as JSON
- exporting the filtered result set as CSV
- opening a detail drawer for a single event
- copying the selected event detail payload

The detail drawer is intended for provenance and reconciliation review. It can surface missing fields such as realized P&L, commission, or net amount, and it adds reconciliation notes based on the fields currently present.

## Audit panel

The `Recent Broker Order Audit` panel is a read-only event log for recent broker order workflow actions.

It shows entries such as:

- time
- action
- symbol
- side
- quantity
- status
- mode (`Dry Run` or `Submit`)
- broker order ID or reason

Use it to confirm what the operator workflow recently attempted or submitted. It is an inspection surface only.

## Open positions and account metrics

The positions area shows the active account’s:

- net liquidation
- cash balance
- buying power
- excess liquidity
- unrealized P&L
- open positions table

This section is for current-account review. It does not provide execution controls.

## What is not enabled yet

The broker page intentionally does **not** enable the following capabilities yet:

- live execution
- auto trading
- paper/live toggles
- auto-trading toggles
- execution arming controls from the UI
- emergency-stop controls from the UI
- backend execution changes from this page

If the page shows live-related visibility, treat that as status visibility only. The current operator workflow remains constrained to the guarded manual paper review path.

## Operator usage summary

For a normal operator pass, use the page in this order:

1. Check `Broker Health` and `Trading Control` in `Overview`.
2. Review `Today’s P&L` if it is present.
3. Review the readiness checklist.
4. Save a snapshot if you want a local checkpoint.
5. Use `Dry Run` in the manual paper order panel.
6. Review preflight context and warnings.
7. Submit only if the dry-run is successful and the manual confirmation is correct.
8. Review `Provenance` and `Audit` after the action for reconciliation.