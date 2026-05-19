# Auto-Paper History Operator Guide

This guide explains the backend read-only auto-paper history endpoints and the adjacent readiness endpoint from an operator point of view. These endpoints are inspection, export, and readiness-review surfaces around the retained auto-paper run log and current paper safety posture. They do not enable trading, do not modify retention, and do not change worker execution behavior.

## Endpoint set

The current auto-paper history and readiness review surface consists of five endpoints under `/market-data`:

1. `GET /market-data/auto-paper/history`
   Returns the filtered retained run entries, newest first.
2. `GET /market-data/auto-paper/history/summary`
   Returns aggregate totals over the same filtered history slice.
3. `GET /market-data/auto-paper/history/retention`
   Returns read-only metadata about the retained history window and retention trend.
4. `GET /market-data/auto-paper/history/export`
   Returns one read-only export bundle containing filter metadata, filtered entries, and the matching filtered summary.
5. `GET /market-data/auto-paper/readiness`
  Returns one read-only readiness contract that combines the current broker control posture, broker health posture, scheduler state, shared paper preflight posture, and recent auto-paper history posture.

All five endpoints are backend inspection surfaces only.

## Contract reference policy

This runbook explains the endpoint contracts in operator terms, but the exact serialized payload snapshots are anchored in the route tests so documentation examples do not drift.

Canonical contract snapshot references:

- `/market-data/auto-paper/history`
  `apps/api/tests/test_market_data_route.py::test_get_auto_paper_history_contract_snapshots_key_fields`
- `/market-data/auto-paper/history/summary`
  `apps/api/tests/test_market_data_route.py::test_get_auto_paper_history_summary_contract_snapshots_key_fields`
- `/market-data/auto-paper/history/retention`
  `apps/api/tests/test_market_data_route.py::test_get_auto_paper_history_retention_contract_snapshots_key_fields`
- `/market-data/auto-paper/history/export`
  `apps/api/tests/test_market_data_route.py::test_export_auto_paper_history_contract_snapshots_key_fields`
- `/market-data/auto-paper/readiness`
  `apps/api/tests/test_market_data_route.py::test_get_auto_paper_readiness_contract_snapshots_key_fields`

Use this runbook for field meaning and operator reading. Use the contract tests above when you need the exact pinned payload examples.

## Naming map

Use the following names consistently across route discussion, runbook sections, and contract references:

| Route path | Route function | Preferred runbook label | Canonical contract test |
|-----------|----------------|-------------------------|-------------------------|
| `/market-data/auto-paper/history` | `get_auto_paper_history` | `History readback route` | `test_get_auto_paper_history_contract_snapshots_key_fields` |
| `/market-data/auto-paper/history/summary` | `get_auto_paper_history_summary` | `Summary readback route` | `test_get_auto_paper_history_summary_contract_snapshots_key_fields` |
| `/market-data/auto-paper/history/retention` | `get_auto_paper_history_retention` | `Retention metadata route` | `test_get_auto_paper_history_retention_contract_snapshots_key_fields` |
| `/market-data/auto-paper/history/export` | `export_auto_paper_history` | `Export bundle route` | `test_export_auto_paper_history_contract_snapshots_key_fields` |
| `/market-data/auto-paper/readiness` | `get_auto_paper_readiness` | `Readiness route` | `test_get_auto_paper_readiness_contract_snapshots_key_fields` |

Naming guidance:

- Use `readback` for the history and summary routes because they return retained inspection data.
- Use `retention metadata` for the retention route because it describes the retained log window, not individual runs.
- Use `export bundle` for the export route because the payload combines filters, summary, and entries.
- Use `readiness route` for the readiness endpoint because it summarizes whether the current backend posture is safe enough for a future enablement review without changing execution behavior.
- Preserve the exact function and test names above when linking to implementation or contract coverage.

## Readiness route

`GET /market-data/auto-paper/readiness` returns one read-only contract for the current auto-paper safety posture.

### Query parameters

- None. This endpoint describes the current backend safety posture as a single composed review surface.

### Response contract

The readiness response currently includes:

- `status`
- `ready_for_auto_submit`
- `blocking_reasons`
- `warning_reasons`
- `broker_control`
- `broker_health`
- `scheduler`
- `shared_paper_preflight`
- `recent_history`

### Contract snapshot reference

Exact pinned payload example:

- `apps/api/tests/test_market_data_route.py::test_get_auto_paper_readiness_contract_snapshots_key_fields`

### Operator reading

- `status=blocked` means at least one current backend gate would still stop a future auto-paper enablement review. In the current phase, `auto_trading_disabled_by_trading_control` is expected and keeps the surface blocked by default.
- `status=warning` means there are no current hard blocking reasons in the composed contract, but there are advisory reasons that should be reviewed before treating the posture as clean.
- `status=ready` means the composed readiness contract found no current blocking or warning reasons. This does not enable automation by itself; it only means the reviewed backend posture is currently clean.
- `ready_for_auto_submit` reflects whether the composed contract found any blocking reasons. It is narrower than execution enablement and should be read together with `status` and the reason arrays.
- `blocking_reasons` lists the hard reasons the current posture is still not clean enough for auto submission. Treat these as the primary operator triage list.
- `warning_reasons` lists advisory issues such as fragmented or immature operational posture. These do not flip the contract into a hard block unless a separate blocking reason is also present.
- `broker_control` is the env-backed trading control posture. Use it to confirm whether auto trading is globally disabled, whether paper mode is active, and whether any emergency stop posture is visible.
- `broker_health` is the underlying broker connectivity and mode-coherence posture. Use it to confirm that the gateway is reachable, the configured account still looks like a paper account, and the broker mode metadata is coherent.
- `scheduler` shows whether the scheduled auto-paper worker is running, paused, missing, or unavailable. A paused or missing scheduler means scheduled automation is not currently in a runnable posture even if other fields look healthy.
- `shared_paper_preflight` reflects the existing paper submit dry-run seam, not auto enablement by itself. Use it to understand whether the shared broker preflight posture is clean, advisory-only, or already showing findings that would matter once the auto gate is revisited.
- `recent_history` ties readiness back to observed worker posture. Use `latest_run` for the newest retained run, `summary` for the current retained slice totals, and `retention` for log-window health and capacity trend.

### Operator notes

- This endpoint is a composed review surface. It does not change scheduler state, does not submit orders, and does not bypass the hard auto-trading gate.
- Read `blocking_reasons` first, then `warning_reasons`, then the supporting posture sections that explain why those reasons are present.
- Treat `shared_paper_preflight` as the shared paper broker-submit posture and `recent_history` as the observed auto-paper run posture. They are related, but they answer different operator questions.

## Shared filters

The history, summary, and export endpoints share the same filter seam.

Available query parameters:

- `limit`
  Caps the number of returned retained entries. The backend clamps this to the retained history cap.
- `source`
  Filters to `manual` or `scheduled` auto-paper runs.
- `outcome`
  Filters to runs containing `accepted`, `rejected`, `cancelled`, or `blocked` outcomes.
- `started_after`
  Filters to runs starting on or after the given ISO-8601 timestamp.
- `started_before`
  Filters to runs starting on or before the given ISO-8601 timestamp.

Practical reading:

- Use the same filters across `history`, `summary`, and `export` when you need one consistent review slice.
- `retention` does not accept these filters because it describes the whole retained log window, not one filtered subset.

## History readback route

`GET /market-data/auto-paper/history` returns individual retained run entries.

### Query parameters

- `limit`
  Requested retained row count. The backend clamps the value to the retained history cap.
- `source`
  Optional filter for `manual` or `scheduled` rows only.
- `outcome`
  Optional filter for rows containing `accepted`, `rejected`, `cancelled`, or `blocked` outcomes.
- `started_after`
  Optional ISO-8601 lower bound for `started_at`.
- `started_before`
  Optional ISO-8601 upper bound for `started_at`.

### Response contract

Each entry includes:

- `worker_name`
- `status`
- `message`
- `started_at`
- `finished_at`
- `source`
- `outcome_counts`

`outcome_counts` is the structured interpretation of the run result. It currently includes:

- `accepted_count`
- `rejected_count`
- `cancelled_count`
- `blocked_count`
- `risk_blocked_count`
- `gate_blocked_count`
- `skipped_cap_count`
- `legacy_broker_rejected_count`

### Contract snapshot reference

Exact pinned payload example:

- `apps/api/tests/test_market_data_route.py::test_get_auto_paper_history_contract_snapshots_key_fields`

### Operator notes

- Rows are returned newest first.
- `status` reflects the worker result status, while `outcome_counts` breaks down the structured execution outcomes inside that run.
- `message` remains useful as operator-readable context, but contract-safe downstream consumers should prefer `outcome_counts` for counts.

Use the history readback route for row-level inspection of individual manual or scheduled auto-paper runs.
For concrete call patterns, use the matching examples in `Common operator usage examples`.

## Summary readback route

`GET /market-data/auto-paper/history/summary` returns aggregate totals over the same filtered history slice.

### Query parameters

- `limit`
  Requested retained row count used to build the summary slice.
- `source`
  Optional filter for `manual` or `scheduled` rows only.
- `outcome`
  Optional filter for rows containing `accepted`, `rejected`, `cancelled`, or `blocked` outcomes.
- `started_after`
  Optional ISO-8601 lower bound for `started_at`.
- `started_before`
  Optional ISO-8601 upper bound for `started_at`.

### Response contract

The summary currently includes:

- `total_runs`
- `manual_run_count`
- `scheduled_run_count`
- `success_run_count`
- `error_run_count`
- `accepted_total`
- `rejected_total`
- `cancelled_total`
- `blocked_total`
- `risk_blocked_total`
- `gate_blocked_total`
- `latest_run_started_at`

### Contract snapshot reference

Exact pinned payload example:

- `apps/api/tests/test_market_data_route.py::test_get_auto_paper_history_summary_contract_snapshots_key_fields`

### Operator notes

- The summary is computed from the same filtered row set as the history endpoint, not from a separate aggregate store.
- `latest_run_started_at` is the newest retained row inside the filtered slice.
- `blocked_total` can include multiple blocked reasons; use `risk_blocked_total` and `gate_blocked_total` when you need the more specific breakdown.

Use the summary readback route for a compact view of how a filtered slice is behaving without reading every retained entry.
For concrete call patterns, reuse the matching filter examples in `Common operator usage examples`.

## Retention metadata route

`GET /market-data/auto-paper/history/retention` returns metadata about the retained run-log window itself.

### Query parameters

- None. This endpoint describes the full retained log window, not a filtered subset.

### Response contract

The retention response currently includes:

- storage information such as `storage_backend`, `trim_on_append`, and `max_entries`
- current occupancy information such as `current_entry_count`, `entries_remaining`, and `utilization_pct`
- advisory fields such as `warning_threshold_pct`, `near_capacity`, `retention_status`, and `retention_warning`
- retained-window timestamps such as `oldest_started_at` and `latest_started_at`
- read-only trend fields such as `retained_span_hours`, `average_entries_per_day`, `estimated_days_until_capacity`, and `retention_trend_status`

### Contract snapshot reference

Exact pinned payload example:

- `apps/api/tests/test_market_data_route.py::test_get_auto_paper_history_retention_contract_snapshots_key_fields`

Operational reading:

- `near_capacity` means the retained log is approaching the configured cap.
- `retention_warning` is advisory text only.
- `retention_trend_status=insufficient_data` means there is not enough retained history to derive a useful growth estimate yet.
- `estimated_days_until_capacity` is an estimate derived from already retained timestamps and retained count. It does not trigger pruning or deletion.

### Operator notes

- `current_entry_count` and `entries_remaining` describe the currently retained file-backed window only.
- `near_capacity` and `retention_status` are advisory posture signals, not controls.
- Trend fields are read-only estimates derived from the retained window and should be treated as operational guidance, not scheduling guarantees.

Use the retention metadata route to understand how much history is currently retained and whether the retained window is trending toward the cap.

## Export bundle route

`GET /market-data/auto-paper/history/export` returns one read-only export bundle for a filtered history slice.

### Query parameters

- `limit`
  Requested retained row count. The backend clamps the value to the retained history cap and echoes the normalized value in `filters.limit`.
- `source`
  Optional filter for `manual` or `scheduled` rows only.
- `outcome`
  Optional filter for rows containing `accepted`, `rejected`, `cancelled`, or `blocked` outcomes.
- `started_after`
  Optional ISO-8601 lower bound for `started_at`.
- `started_before`
  Optional ISO-8601 upper bound for `started_at`.

### Response contract

The export bundle includes:

- `exported_at`
- `filters`
- `summary`
- `entries`

`filters` echoes the applied filter set after backend normalization. This is useful when an export artifact is shared and the receiver needs to know exactly what slice was requested.

`summary` matches the same aggregation logic used by `GET /market-data/auto-paper/history/summary`.

`entries` matches the same filtered entry logic used by `GET /market-data/auto-paper/history`.

### Contract snapshot reference

Exact pinned payload example:

- `apps/api/tests/test_market_data_route.py::test_export_auto_paper_history_contract_snapshots_key_fields`

### Operator notes

- `filters` is part of the contract and should be preserved when sharing an export artifact, because it records the exact slice that was requested.
- `summary` and `entries` are aligned to the same filtered slice, so they should reconcile without additional post-processing.
- `exported_at` records when the bundle was produced, not when the underlying runs occurred.

Use the export bundle route when you want one portable payload that combines row-level detail and aggregate totals for the same filtered slice.
For concrete call patterns, use the export examples in `Common operator usage examples`.

## Recommended operator review flow

For a normal retained-history backend review pass, use the routes in this order.

If the review starts from composed readiness posture rather than a known retained slice, start with the readiness route and then use the readiness examples, scenarios, and checklist below to choose the next drill-down route before returning to this default history-first flow.

### Step 1: Start with history readback

Call `GET /market-data/auto-paper/history` first.

Use it to answer:

- What individual runs are in the retained window?
- Were the runs manual or scheduled?
- Which runs contain accepted, rejected, cancelled, or blocked outcomes?
- Which specific rows deserve closer inspection?

Recommended practice:

- Start with the narrowest useful filter set.
- Filter by `source`, `outcome`, or started-at bounds before widening the slice.
- Use row-level `message` and `outcome_counts` together when triaging individual runs.

### Step 2: Confirm the slice with summary readback

Call `GET /market-data/auto-paper/history/summary` with the same filters used for history.

Use it to answer:

- How many runs are in the same filtered slice?
- Are errors or blocked outcomes concentrated in that slice?
- Do the aggregate totals reconcile with the rows you just inspected?

Recommended practice:

- Reuse the exact same filters from Step 1.
- Treat the summary as the aggregate view of the same retained rows, not as a separate source.
- If the totals do not match operator expectations, return to Step 1 and refine the filter set.

### Step 3: Check retention posture separately

Call `GET /market-data/auto-paper/history/retention` after you understand the filtered slice.

Use it to answer:

- How much of the run-log window is currently retained?
- Is the retained history near the configured cap?
- Is the retained window trending toward capacity?

Recommended practice:

- Treat retention as whole-log posture, not as a filtered-slice tool.
- Review `near_capacity`, `retention_status`, and `retention_warning` together.
- Use trend fields as operational guidance only; they do not trigger pruning or deletion.

### Step 4: Export the reviewed slice for handoff

Call `GET /market-data/auto-paper/history/export` last when you need a portable review artifact.

Use it to answer:

- Can the exact filtered slice be handed off without rebuilding it manually?
- Does the export preserve both the row-level entries and their aggregate totals?
- Are the applied filters recorded clearly enough for another operator to reproduce the same slice?

Recommended practice:

- Export only after the history and summary slice looks correct.
- Preserve the `filters` block with the export so the slice provenance stays clear.
- Use the export bundle when you need one payload for handoff, audit review, or offline inspection.

### Flow summary

Use the routes in this sequence when the review is history-first rather than readiness-first:

1. `History readback route` for row-level triage.
2. `Summary readback route` for aggregate confirmation of the same slice.
3. `Retention metadata route` for whole-log retention posture.
4. `Export bundle route` for portable handoff of the reviewed slice.

## Common operator usage examples

Use these examples as starting points for common backend review tasks.

These examples are the preferred operator call references in this runbook. The route sections above define the contract and field meaning; this section holds the practical request patterns so examples stay in one place.

### Latest retained history

Use this when you want the newest retained run entries without any additional filtering.

```text
GET /market-data/auto-paper/history?limit=20
```

### Filtered manual-only history

Use this when you want to inspect only manual runs inside a specific time window.

```text
GET /market-data/auto-paper/history?source=manual&started_after=2026-04-30T00:00:00+00:00&started_before=2026-04-30T23:59:59+00:00
```

### Filtered scheduled-only history

Use this when you want to inspect only scheduled runs for the same retained period.

```text
GET /market-data/auto-paper/history?source=scheduled&started_after=2026-04-30T00:00:00+00:00&started_before=2026-04-30T23:59:59+00:00
```

### Blocked-only review

Use this when you want to isolate runs containing blocked outcomes before drilling into the specific row-level details.

```text
GET /market-data/auto-paper/history?outcome=blocked&started_after=2026-04-30T00:00:00+00:00
```

### Summary for the same filter set

Use this immediately after a filtered history call when you want aggregate confirmation for the same review slice.

```text
GET /market-data/auto-paper/history/summary?outcome=blocked&started_after=2026-04-30T00:00:00+00:00
```

### Retention check

Use this when you want the current whole-log retention posture before deciding whether the retained window is sufficient for review.

```text
GET /market-data/auto-paper/history/retention
```

### Export bundle for handoff

Use this after validating the history and summary slice when you want one portable payload for another operator or offline review.

```text
GET /market-data/auto-paper/history/export?outcome=blocked&started_after=2026-04-30T00:00:00+00:00&limit=100
```

### Readiness check for the current blocked posture

Use this when you want the current composed auto-paper readiness posture and expect the hard auto-trading block to still be present.

```text
GET /market-data/auto-paper/readiness
```

Use the readiness route section for field meaning, then use the readiness scenarios and checklist below to choose the next drill-down route.

### Readiness check for a warning-only posture

Use this when you want to confirm that the composed readiness contract can be advisory-only even when there are no hard blocking reasons in the current snapshot.

```text
GET /market-data/auto-paper/readiness
```

Use the readiness route section for field meaning, then use the readiness scenarios and checklist below to decide whether the next drill-down should be history, retention, scheduler posture, or shared preflight posture.

### Readiness check when the scheduler is disabled or unavailable

Use this when you want to verify whether scheduled auto-paper execution is currently paused, missing, or unavailable even before reviewing recent run history.

```text
GET /market-data/auto-paper/readiness
```

Use this as the readiness-first call, then move to the scheduler-specific scenario below if scheduler posture is the active concern.

### Readiness check for retention near-capacity posture

Use this when you want the composed readiness route to tell you whether retained history health is becoming part of the operator review concern.

```text
GET /market-data/auto-paper/readiness
```

Use this as the composed starting point, then move to retention drill-down only if the readiness payload suggests retained-window health is the active issue.

### Readiness check for recent blocked history posture

Use this when you want to understand whether recent retained runs already show a blocked pattern before reviewing row-level history directly.

```text
GET /market-data/auto-paper/readiness
```

Use this as the composed starting point, then move to history and summary drill-down only if the readiness payload suggests blocked retained runs are part of the current posture.

### Example usage sequence

For a blocked-outcome investigation, a typical route sequence is:

1. `GET /market-data/auto-paper/history?outcome=blocked&started_after=2026-04-30T00:00:00+00:00`
2. `GET /market-data/auto-paper/history/summary?outcome=blocked&started_after=2026-04-30T00:00:00+00:00`
3. `GET /market-data/auto-paper/history/retention`
4. `GET /market-data/auto-paper/history/export?outcome=blocked&started_after=2026-04-30T00:00:00+00:00&limit=100`

For a readiness-first investigation, a typical route sequence is:

1. `GET /market-data/auto-paper/readiness`
2. Inspect `blocking_reasons` and `warning_reasons`.
3. If scheduler posture is implicated, inspect `scheduler.state` and then follow the scheduler-specific status surface if needed.
4. If recent blocked history is implicated, call `GET /market-data/auto-paper/history?outcome=blocked&started_after=2026-04-30T00:00:00+00:00`.
5. If retention posture is implicated, call `GET /market-data/auto-paper/history/retention`.

## Common review scenarios

Use these scenarios when the operator already knows the review goal and wants the shortest practical route sequence.

### Scenario: readiness route shows blocking reasons

Goal:

- Start from the composed readiness surface and decide whether the current blocked posture is driven by recent blocked history that needs deeper inspection.

Suggested route sequence:

1. `GET /market-data/auto-paper/readiness`
2. Read `blocking_reasons` first.
3. Inspect `recent_history.latest_run` and `recent_history.summary`.
4. If blocked behavior appears in the retained slice, call `GET /market-data/auto-paper/history?outcome=blocked&started_after=2026-04-30T00:00:00+00:00`.
5. Call `GET /market-data/auto-paper/history/summary?outcome=blocked&started_after=2026-04-30T00:00:00+00:00` to confirm the aggregate blocked posture for the same slice.

Operator reading:

- Treat `blocking_reasons` as the first triage signal.
- Use the readiness route to confirm whether the current block is only the expected global auto-trading block or whether recent retained blocked runs also justify deeper history review.
- Move to history and summary only after the readiness contract indicates that recent retained outcomes are part of the current blocked posture.

### Scenario: readiness route shows warning reasons

Goal:

- Start from the composed readiness surface and decide whether the current advisory posture is primarily a retained-history issue or a retention-health issue.

Suggested route sequence:

1. `GET /market-data/auto-paper/readiness`
2. Read `warning_reasons` first.
3. Inspect `recent_history.summary` and `recent_history.retention`.
4. If the warning suggests thin or immature recent history, call `GET /market-data/auto-paper/history?started_after=2026-04-30T00:00:00+00:00`.
5. If the warning suggests retained-window health, call `GET /market-data/auto-paper/history/retention`.

Operator reading:

- Use `warning_reasons` to decide whether the next drill-down should be row-level history or whole-log retention posture.
- Treat readiness warnings as advisory review signals, not as execution controls.
- Use the readiness contract to narrow the next drill-down call instead of opening every review route immediately.

### Scenario: readiness route shows scheduler posture problems

Goal:

- Confirm whether the current readiness concern is scheduler-specific before drilling into recent run outcomes.

Suggested route sequence:

1. `GET /market-data/auto-paper/readiness`
2. Inspect `scheduler.state`.
3. If the scheduler is `paused`, `missing`, or `scheduler_unavailable`, treat the scheduler posture as the current review focus.
4. Follow with the scheduler-specific backend surface if direct scheduler confirmation is needed.
5. Return to history readback only if recent retained run posture is also needed for context.

Operator reading:

- A scheduler warning is primarily a scheduler-state issue, not a retained-history issue.
- Use the readiness route to confirm scheduler posture first, then drill down only if the scheduler state needs direct operational follow-up.
- Do not assume a scheduler posture warning implies rejected, cancelled, or blocked retained run outcomes without checking `recent_history` separately.

### Scenario: readiness route shows shared preflight warnings

Goal:

- Determine whether the current advisory posture is coming from the shared paper broker-submit seam rather than recent run history.

Suggested route sequence:

1. `GET /market-data/auto-paper/readiness`
2. Inspect `shared_paper_preflight.status` and `shared_paper_preflight.preflight_decision`.
3. Read the `would_block_items` or `blocking_items` inside the preflight decision.
4. Cross-check `broker_control` and `broker_health` to confirm the broader broker posture around the same warning.
5. Use history or retention drill-down only if the readiness payload also suggests recent run or retention posture problems.

Operator reading:

- Treat shared preflight findings as paper broker-submit posture signals, not as direct evidence of recent retained run outcomes.
- Use the preflight decision items to identify whether the warning is exposure-related, mode-related, or otherwise broker-submit specific.
- Keep the drill-down centered on the readiness payload unless a separate retained-history or retention signal also appears.

### Scenario: blocked-by-risk review

Goal:

- Determine whether blocked outcomes are being driven by the risk gate specifically.

Suggested route sequence:

1. `GET /market-data/auto-paper/history?outcome=blocked&started_after=2026-04-30T00:00:00+00:00`
2. Inspect `outcome_counts.risk_blocked_count` on the returned rows.
3. `GET /market-data/auto-paper/history/summary?outcome=blocked&started_after=2026-04-30T00:00:00+00:00`
4. Compare `risk_blocked_total` against `blocked_total`.
5. `GET /market-data/auto-paper/history/export?outcome=blocked&started_after=2026-04-30T00:00:00+00:00&limit=100` if the slice needs handoff.

Operator reading:

- If `risk_blocked_total` is the dominant share of `blocked_total`, treat the slice as primarily risk-blocked.
- Use row-level `message` alongside `risk_blocked_count` when investigating why a specific run was blocked.

### Scenario: blocked-by-gate review

Goal:

- Determine whether blocked outcomes are being driven by the broker or automation gate rather than risk.

Suggested route sequence:

1. `GET /market-data/auto-paper/history?outcome=blocked&started_after=2026-04-30T00:00:00+00:00`
2. Inspect `outcome_counts.gate_blocked_count` on the returned rows.
3. `GET /market-data/auto-paper/history/summary?outcome=blocked&started_after=2026-04-30T00:00:00+00:00`
4. Compare `gate_blocked_total` against `blocked_total`.
5. `GET /market-data/auto-paper/history/export?outcome=blocked&started_after=2026-04-30T00:00:00+00:00&limit=100` if another operator needs the same reviewed slice.

Operator reading:

- If `gate_blocked_total` is the dominant share of `blocked_total`, treat the slice as primarily gate-blocked.
- Review `source` on the rows to see whether the gate issue is concentrated in manual or scheduled runs.

### Scenario: rejected broker outcome review

Goal:

- Review runs where broker-facing outcomes were rejected rather than accepted.

Suggested route sequence:

1. `GET /market-data/auto-paper/history?outcome=rejected&started_after=2026-04-30T00:00:00+00:00`
2. Inspect row-level `rejected_count` and `message` for the affected runs.
3. `GET /market-data/auto-paper/history/summary?outcome=rejected&started_after=2026-04-30T00:00:00+00:00`
4. Confirm the aggregate `rejected_total` for the same slice.
5. Export the slice if the rejected outcomes need offline review or handoff.

Operator reading:

- Use rejected-outcome review when a run completed but did not produce accepted broker results.
- Check whether the rejected slice is concentrated in one `source` or time window before widening scope.

### Scenario: cancelled broker outcome review

Goal:

- Review runs where broker-facing outcomes were cancelled instead of accepted.

Suggested route sequence:

1. `GET /market-data/auto-paper/history?outcome=cancelled&started_after=2026-04-30T00:00:00+00:00`
2. Inspect row-level `cancelled_count` and `message` for the retained runs.
3. `GET /market-data/auto-paper/history/summary?outcome=cancelled&started_after=2026-04-30T00:00:00+00:00`
4. Confirm the aggregate `cancelled_total` for the same slice.
5. Export the slice if the cancelled-outcome review needs to be shared.

Operator reading:

- Use cancelled-outcome review when execution was not accepted and the retained rows show cancellation-specific outcomes.
- Compare the cancelled slice with rejected or blocked slices if operator expectations do not match the observed totals.

### Scenario: scheduled run review

Goal:

- Review only scheduled auto-paper executions over a defined retained window.

Suggested route sequence:

1. `GET /market-data/auto-paper/history?source=scheduled&started_after=2026-04-30T00:00:00+00:00&started_before=2026-04-30T23:59:59+00:00`
2. Inspect row-level outcomes for the scheduled slice.
3. `GET /market-data/auto-paper/history/summary?source=scheduled&started_after=2026-04-30T00:00:00+00:00&started_before=2026-04-30T23:59:59+00:00`
4. Confirm the aggregate scheduled totals.
5. Export the slice if scheduled-run review needs handoff.

Operator reading:

- Scheduled review is useful when the operator wants to separate background execution behavior from manual trigger behavior.
- Use the same time bounds across history, summary, and export so the scheduled slice stays consistent.

### Scenario: retention near-capacity review

Goal:

- Review whether the retained run-log window is nearing the configured cap and whether action or handoff is needed.

Suggested route sequence:

1. `GET /market-data/auto-paper/history/retention`
2. Inspect `near_capacity`, `retention_status`, `entries_remaining`, and `retention_warning`.
3. Inspect `retained_span_hours`, `average_entries_per_day`, and `estimated_days_until_capacity`.
4. Optionally run a matching history or export review if another operator needs the current retained slice as context.

Operator reading:

- Treat `near_capacity` as an advisory review signal, not as a control.
- Use `estimated_days_until_capacity` as guidance only; it does not change retention behavior by itself.

## Final operator review checklist

Use this checklist at the end of an auto-paper history review to make sure the review is complete and the handoff is clear.

### Readiness-first checks

- Before using `GET /market-data/auto-paper/readiness`, confirm whether the review goal is overall readiness triage or a known row-level history investigation.
- Start with the readiness route when the operator does not yet know whether the current concern is blocking posture, warning posture, scheduler posture, preflight posture, or retained-history posture.
- Read `ready_for_auto_submit` together with `status`; do not treat `ready_for_auto_submit` as an enablement control by itself.
- If `ready_for_auto_submit=false`, review `blocking_reasons` before opening history, summary, retention, or scheduler drill-down routes.
- If `status=warning`, review `warning_reasons` before deciding whether the next drill-down should be history, retention, scheduler posture, or shared preflight posture.

### Readiness drill-down checklist

- When `blocking_reasons` are present, inspect `recent_history.latest_run` and `recent_history.summary` before opening history readback.
- When `warning_reasons` suggest retained-history posture, drill down into `History readback route` or `Summary readback route`.
- When `warning_reasons` suggest retained-window health, drill down into `Retention metadata route`.
- When scheduler posture is implicated, inspect `scheduler.state` first and treat scheduler follow-up as separate from retained-history review.
- When shared preflight warnings are implicated, inspect `shared_paper_preflight.preflight_decision` together with `broker_control` and `broker_health` before opening history or retention routes.
- Choose only the narrowest next route that explains the current readiness signal instead of opening every review route at once.

### Before-review checks

- Confirm the review goal before selecting filters: blocked, rejected, cancelled, scheduled, or retention posture.
- If the review starts from readiness rather than a known retained slice, confirm that the first question is about composed posture rather than row-level outcomes.
- Confirm the time window you intend to inspect before calling history or summary routes.
- Decide whether the review needs a source-specific slice (`manual` or `scheduled`) before widening scope.
- Confirm whether the review is row-level triage, aggregate confirmation, retention posture review, or handoff preparation.

### During-review checks

- If the review started from readiness, confirm whether `blocking_reasons` or `warning_reasons` actually justify opening a follow-up route.
- Re-check whether `ready_for_auto_submit` and `status` tell the same story as the underlying posture sections before drawing conclusions.
- Start with `History readback route` and verify the returned rows match the intended filter set.
- Reuse the same filters on `Summary readback route` and confirm the aggregate totals reconcile with the inspected rows.
- Use `Retention metadata route` separately to understand whole-log posture instead of treating it as a filtered-slice tool.
- Check whether row-level `message` and structured `outcome_counts` tell the same story before drawing conclusions.
- Confirm whether the relevant behavior is concentrated by `source`, by outcome type, or by time window before escalating.

### Escalation criteria

- Escalate when row-level history and filtered summary totals do not reconcile for the intended slice.
- Escalate when blocked outcomes are persistent and the retained slice shows a dominant `risk_blocked_total` or `gate_blocked_total` pattern that needs follow-up.
- Escalate when rejected or cancelled outcomes persist across the same source or time window and the pattern is no longer isolated.
- Escalate when `near_capacity` is true and the retained window appears too narrow for the needed operator review or handoff context.
- Escalate when the retained history window no longer provides enough context to explain the current review scenario.

### Export and handoff checklist

- Decide whether export or handoff is necessary only after the readiness route and any chosen drill-down route agree on the current posture.
- Do not export from readiness alone when the actual handoff question is still row-level blocked history, rejected outcomes, cancelled outcomes, or retention posture; use the matching drill-down route first.
- Export only after the history slice and matching summary slice are confirmed.
- Preserve the `filters` block so another operator can reproduce the same reviewed slice.
- If the review began with readiness, include whether the handoff was driven by `blocking_reasons`, `warning_reasons`, scheduler posture, shared preflight posture, or retained-history posture.
- Include whether the slice was manual-only, scheduled-only, blocked-only, rejected-only, cancelled-only, or retention-focused.
- Include any observed dominant pattern: risk-blocked, gate-blocked, rejected, cancelled, scheduled concentration, or near-capacity retention posture.
- Include whether retention posture was reviewed separately and whether `near_capacity` affected the interpretation of the slice.
- Use the export bundle when one payload needs to carry both row-level detail and aggregate confirmation.

## Closing guidance

Use the guide in this order when you need the full operator workflow:

1. Route sections for contract meaning and field semantics.
2. Usage examples for the practical request pattern you need first.
3. Review scenarios when you need the shortest targeted drill-down path.
4. Final checklist for readiness triage, escalation, and handoff readiness.
5. Review flow when you want the default history-first route order for a retained-slice investigation.

Treat the route tests as the canonical payload-shape source and this runbook as the operator-facing guide to how those routes are used in practice.

## Maintenance triggers

Update this runbook whenever any of the following change:

- Route contract changes
  Any change to the meaning or intended usage of `/market-data/auto-paper/history`, `/summary`, `/retention`, `/export`, or `/readiness`.
- Response field changes
  Any added, removed, renamed, or reinterpreted response field in readiness, history, summary, retention, or export payloads.
- Filter changes
  Any added, removed, renamed, or behaviorally changed filter parameter used by history, summary, or export.
- Retention policy changes
  Any change to the retained history cap, trim behavior, advisory thresholds, or the way retention posture should be interpreted by operators.
- Export bundle shape changes
  Any change to `exported_at`, `filters`, `summary`, `entries`, or the expected relationship between those fields.
- Readiness composition changes
  Any change to how broker control posture, broker health posture, scheduler posture, shared paper preflight posture, or recent history posture are combined or interpreted in the readiness review flow.
- Operator workflow changes
  Any change to the recommended route order, review scenarios, escalation guidance, or handoff expectations.

Recommended update rule:

- If a backend change requires updating the route contract tests, review this runbook in the same change.
- If a backend change alters operator interpretation but not the exact payload shape, update this runbook even when the canonical contract tests do not need edits.
- If the change does not affect route meaning, readiness composition, payload shape, filters, retention posture, export semantics, or operator workflow, this runbook usually does not need an update.

## Maintainer handoff note

For future maintainers:

- The operator runbook lives at `docs/runbooks/auto-paper-history-operator-guide.md`.
- The canonical contract tests live at `apps/api/tests/test_market_data_route.py`.
- Update both the runbook and the contract tests when a backend change affects route meaning, readiness composition, payload shape, filters, retention posture, export semantics, or the operator workflow.
- Update the runbook even when the contract tests do not change if operator interpretation or review guidance changes.
- Keep this surface read-only in documentation unless the underlying backend intentionally changes; do not introduce wording that implies execution controls, live enablement, auto trading enablement, pruning controls, deletion controls, or toggles.

## What these endpoints do not do

These endpoints intentionally do not provide:

- pruning controls
- deletion controls
- execution controls
- live trading enablement
- auto trading enablement
- frontend workflow changes
- toggles for paper/live or auto/manual behavior

Treat this surface as backend inspection and export only.