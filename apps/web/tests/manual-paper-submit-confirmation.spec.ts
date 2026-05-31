import { expect, test } from "@playwright/test";

const API_BASE_URL = process.env.PLAYWRIGHT_API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
const API_ORIGIN = new URL(API_BASE_URL).origin;

type MockRouteResponse = {
  status: number;
  contentType: string;
  body: string;
};

function isApiRequest(requestUrl: string, pathname: string): boolean {
  const url = new URL(requestUrl);
  return url.origin === API_ORIGIN && url.pathname === pathname;
}

async function routeRecommendationEvidence(
  page: import("@playwright/test").Page,
  recommendationId: string,
  options: {
    recommendationBody?: Record<string, unknown>;
    routeCheckBody?: Record<string, unknown>;
    dryRunBody?: Record<string, unknown>;
  } = {},
) {
  const nowIso = new Date().toISOString();

  await page.route("**/paper/recommendations/*", async (route) => {
    const requestUrl = new URL(route.request().url());
    const expectedPath = `/paper/recommendations/${recommendationId}`;

    if (requestUrl.pathname !== expectedPath) {
      await route.continue();
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: recommendationId,
        signal_id: null,
        model_version_id: null,
        ticker: "NVDA",
        side: "BUY",
        quantity: 3,
        order_type: "MARKET",
        limit_price: null,
        confidence: null,
        risk_score: 0.18,
        estimated_notional: 300,
        rationale: "Read-only confirmation test fixture.",
        status: "approved",
        created_at: nowIso,
        reviewed_at: nowIso,
        reviewed_by: "operator",
        review_notes: "Approved for guarded paper review.",
        executed_at: null,
        paper_order_ids: null,
        ...options.recommendationBody,
      }),
    });
  });

  await page.route("**/paper/recommendations/**/serious-paper-route-check*", async (route) => {
    const requestUrl = new URL(route.request().url());
    const expectedPath = `/paper/recommendations/${recommendationId}/serious-paper-route-check`;

    if (requestUrl.pathname !== expectedPath) {
      await route.continue();
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        recommendation_id: recommendationId,
        recommendation_status: "approved",
        ticker: "NVDA",
        side: "BUY",
        quantity: 3,
        order_type: "MARKET",
        limit_price: null,
        estimated_notional: 300,
        risk_score: 0.18,
        route_check_status: "eligible",
        resolved_route: "/broker/orders",
        resolved_execution_source: "ibkr_paper",
        execution_source: "recommendation_route_check",
        serious_paper_source: "ibkr_paper",
        is_canonical_paper: true,
        broker_account_mode: "paper",
        live_state: "ibkr_live_locked",
        would_block: false,
        blocked_reason: null,
        missing_data: [],
        next_required_action: "Review the dedicated guarded confirmation surface before any later manual paper step.",
        is_submit: false,
        workers_allowed_to_submit: false,
        live_trading_enabled: false,
        canonical_paper_route: "/broker/orders",
        broker_mode: {
          broker: "ibkr",
          mode: "paper",
          live_execution_enabled: false,
          paper_trading_enabled: true,
        },
        ...options.routeCheckBody,
      }),
    });
  });

  await page.route("**/paper/recommendations/**/broker-dry-run-preview*", async (route) => {
    const requestUrl = new URL(route.request().url());
    const expectedPath = `/paper/recommendations/${recommendationId}/broker-dry-run-preview`;

    if (requestUrl.pathname !== expectedPath) {
      await route.continue();
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        recommendation_id: recommendationId,
        recommendation_status: "approved",
        ticker: "NVDA",
        side: "BUY",
        quantity: 3,
        order_type: "MARKET",
        limit_price: null,
        estimated_notional: 300,
        risk_score: 0.18,
        route_check_status: "eligible",
        dry_run_status: "ready",
        dry_run_only: true,
        dry_run_executed: true,
        allowed_to_submit: true,
        resolved_route: "/broker/orders",
        resolved_execution_source: "ibkr_paper",
        dry_run_execution_source: "broker_dry_run",
        balance_source: "ibkr_paper",
        fees_source: "pending_broker_report",
        fills_source: "pending_broker_fill",
        positions_source: "ibkr_paper",
        serious_paper_source: "ibkr_paper",
        is_canonical_paper: true,
        broker_account_mode: "paper",
        live_state: "ibkr_live_locked",
        would_block: false,
        blocked_reason: null,
        missing_data: [],
        next_required_action: "Review the final guarded confirmation design surface. No submit control is enabled in this phase.",
        is_submit: false,
        workers_allowed_to_submit: false,
        live_trading_enabled: false,
        canonical_paper_route: "/broker/orders",
        broker_mode: {
          broker: "ibkr",
          mode: "paper",
          live_execution_enabled: false,
          paper_trading_enabled: true,
        },
        mode_guard_ok: true,
        request_valid: true,
        issues: [],
        warnings: [],
        preflight_decision: {
          decision_status: "allowed",
          submit_gate: "not_applied",
          advisory_count: 0,
          would_block_count: 0,
          blocking_count: 0,
          advisory_items: [],
          would_block_items: [],
          blocking_items: [],
        },
        preflight_context: null,
        paper_path_note: "Dry-run validates the canonical IBKR paper submit path without placing an order.",
        ...options.dryRunBody,
      }),
    });
  });
}

async function mockInFlightReport(page: import("@playwright/test").Page, recommendationId: string) {
  await page.route("**/cockpit/in-flight-adjustments*", async (route) => {
    const requestUrl = new URL(route.request().url());

    if (!isApiRequest(requestUrl.toString(), "/cockpit/in-flight-adjustments")) {
      await route.continue();
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        generated_at: "2026-05-24T09:15:00+00:00",
        mode: "paper",
        summary: {
          headline: "Read-only in-flight paper adjustments watchlist for operator review.",
          total_items: 1,
          open_positions: 0,
          open_orders: 0,
          active_recommendations: 1,
          watch_only: 0,
          review_required: 1,
          high_attention: 0,
        },
        items: [
          {
            id: recommendationId,
            item_type: "paper_recommendation",
            symbol: "NVDA",
            asset_id: "asset-nvda",
            asset_name: "NVIDIA Corp.",
            asset_detail_path: "/asset-cards/asset-nvda",
            has_asset_context: true,
            status: "approved",
            opened_at: null,
            created_at: "2026-05-24T09:00:00+00:00",
            current_state_summary: "NVDA BUY qty=3 order_type=MARKET",
            attention_level: "medium",
            adjustment_label: "review_required",
            reason: "Recommendation is awaiting operator route-check before guarded broker paper review.",
            evidence: ["recommendation_status=approved"],
            missing_data: [],
            recommended_review_action: "Review the recommendation route-check before guarded broker dry-run.",
            is_actionable: false,
          },
        ],
        monitor_notes: [],
        risk_notes: [],
        limitations: [],
        recommended_review_actions: ["Review the route-check before opening the confirmation design surface."],
      }),
    });
  });
}

test("manual paper submit confirmation requires explicit final confirmation before calling /broker/orders", async ({ page }) => {
  const recommendationId = "recommendation-1";
  let brokerOrdersCalls = 0;
  let executionPaperCalls = 0;
  let capturedPayload: Record<string, unknown> | null = null;

  await routeRecommendationEvidence(page, recommendationId);
  await page.route("**/execution/paper", async (route) => {
    executionPaperCalls += 1;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({}) });
  });
  await page.route("**/broker/orders", async (route) => {
    if (new URL(route.request().url()).pathname !== "/broker/orders") {
      await route.continue();
      return;
    }

    brokerOrdersCalls += 1;
    capturedPayload = route.request().postDataJSON() as Record<string, unknown>;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        broker_order_id: "PAPER-123",
        status: "SUBMITTED",
        filled_price: null,
        filled_quantity: null,
        error_message: null,
        broker_mode: {
          broker: "ibkr",
          mode: "paper",
          live_execution_enabled: false,
          paper_trading_enabled: true,
        },
        execution_source: "ibkr_paper",
        balance_source: "ibkr_paper",
        fees_source: "ibkr_reported",
        fills_source: "ibkr_paper",
        positions_source: "ibkr_paper",
        serious_paper_source: "ibkr_paper",
        is_canonical_paper: true,
        canonical_paper_route: "/broker/orders",
        broker_account_mode: "paper",
        live_state: "ibkr_live_locked",
        paper_path_note: "IBKR paper is the canonical serious paper trading path.",
      }),
    });
  });

  await page.goto(`/cockpit/manual-paper-submit-confirmation?recommendationId=${recommendationId}&symbol=NVDA`);

  const submitButton = page.getByTestId("manual-paper-submit-button");
  const confirmationCheckbox = page.getByTestId("manual-paper-submit-confirmation-checkbox");

  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-page")).toBeVisible();
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-status")).toContainText(/paper_only_confirmation_control/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-surface-status-grid")).toContainText(/submit_enabled_nowfalse/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-surface-status-grid")).toContainText(/final_confirmation_checkedfalse/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-future-route")).toContainText(/future_submit_route\/broker\/orders/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-wording-preview")).toContainText(/i understand this is an ibkr paper order only/i);
  await expect(submitButton).toBeDisabled();
  expect(brokerOrdersCalls).toBe(0);

  await confirmationCheckbox.check();

  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-surface-status-grid")).toContainText(/submit_enabled_nowtrue/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-surface-status-grid")).toContainText(/final_confirmation_checkedtrue/i);
  await expect(submitButton).toBeEnabled();
  await expect(page.getByRole("button", { name: /trade now|auto submit|approve live|one-click execute|live submit|buy now|sell now|execute now/i })).toHaveCount(0);

  await submitButton.click();

  await expect(page.getByTestId("manual-paper-submit-success-state")).toContainText(/paper order submitted/i);
  await expect(page.getByTestId("manual-paper-submit-success-state")).toContainText(/PAPER-123/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-surface-status-grid")).toContainText(/order_submittedtrue/i);
  expect(brokerOrdersCalls).toBe(1);
  expect(executionPaperCalls).toBe(0);
  expect(capturedPayload).not.toBeNull();
  expect(capturedPayload?.ticker).toBe("NVDA");
  expect(capturedPayload?.side).toBe("BUY");
  expect(capturedPayload?.quantity).toBe(3);
  expect(capturedPayload?.order_type).toBe("MARKET");
  expect(capturedPayload?.tif).toBe("DAY");
  expect(capturedPayload?.account_mode).toBe("paper");
  expect(capturedPayload?.execution_source).toBe("ibkr_paper");
  expect(capturedPayload?.route_check_reference).toBe("recommendation_route_check:eligible");
  expect(capturedPayload?.dry_run_reference).toBe("broker_dry_run:allowed");
  expect(typeof capturedPayload?.client_order_id).toBe("string");
  expect(capturedPayload?.client_order_id).toBe(capturedPayload?.submit_decision_correlation_id);

  const outcomeView = page.getByTestId("manual-paper-submit-outcome-view");
  await expect(outcomeView).toBeVisible();
  await expect(outcomeView).toHaveAttribute("data-outcome-status", "allowed");
  await expect(page.getByTestId("manual-paper-submit-outcome-status")).toContainText(/paper submit allowed/i);
  await expect(page.getByTestId("manual-paper-submit-outcome-paper-only-badge")).toBeVisible();
  await expect(page.getByTestId("manual-paper-submit-outcome-live-locked-badge")).toContainText(/live remains locked/i);
  await expect(page.getByTestId("manual-paper-submit-outcome-workers-badge")).toContainText(/workers cannot submit/i);
  await expect(page.getByTestId("manual-paper-submit-outcome-no-live-order-badge")).toContainText(/no live order was placed/i);
  await expect(page.getByTestId("manual-paper-submit-outcome-attempt-details")).toContainText(/NVDA/);
  await expect(page.getByTestId("manual-paper-submit-outcome-attempt-details")).toContainText(/BUY/);
  await expect(page.getByTestId("manual-paper-submit-outcome-attempt-details")).toContainText(/MARKET/);
  await expect(page.getByTestId("manual-paper-submit-outcome-attempt-details")).toContainText(/DAY/);
  await expect(page.getByTestId("manual-paper-submit-outcome-recommendation-id")).toContainText(recommendationId);
  await expect(page.getByTestId("manual-paper-submit-outcome-correlation-id")).toContainText(/manual_paper_submit_/i);
  await expect(page.getByTestId("manual-paper-submit-outcome-guard-result")).toContainText(/broker_mode/i);
  await expect(page.getByTestId("manual-paper-submit-outcome-guard-result")).toContainText(/preflight_decision_status/i);
  await expect(page.getByTestId("manual-paper-submit-outcome-guard-result")).toContainText(/response_status/i);
  await expect(page.getByTestId("manual-paper-submit-outcome-guard-result")).toContainText(/PAPER-123/);
  await expect(page.getByTestId("manual-paper-submit-outcome-guard-result")).toContainText(/live_execution_enabledfalse/i);
  const timelineLink = page.getByTestId("manual-paper-submit-outcome-timeline-href");
  await expect(timelineLink).toContainText(/view full submit decision timeline/i);
  await expect(timelineLink).toHaveAttribute(
    "href",
    new RegExp(`^/cockpit/audit/broker-submit-decisions\\?correlation_id=manual_paper_submit_[a-z0-9_]+&recommendation_id=${recommendationId}$`),
  );
  await expect(page.getByTestId("manual-paper-submit-outcome-next-step")).toContainText(/review timeline and monitor paper account/i);
  await expect(page.getByTestId("manual-paper-submit-outcome-next-step")).toContainText(/no automatic resubmission will occur/i);
  await expect(page.getByRole("button", { name: /trade now|auto submit|approve live|one-click execute|live submit|buy now|sell now|execute now/i })).toHaveCount(0);

  // Confirm no second submit occurs automatically after the outcome view renders.
  await page.waitForTimeout(150);
  expect(brokerOrdersCalls).toBe(1);
});

test("manual paper submit confirmation surface renders safe missing-context state without recommendation id", async ({ page }) => {
  let brokerOrdersCalls = 0;

  await page.route("**/broker/orders", async (route) => {
    brokerOrdersCalls += 1;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({}) });
  });

  await page.goto("/cockpit/manual-paper-submit-confirmation");

  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-page")).toBeVisible();
  await expect(page.getByText(/no recommendation id was provided/i)).toBeVisible();
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-surface-status-grid")).toContainText(/route_check_statusmissing_context/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-surface-status-grid")).toContainText(/dry_run_statusmissing_context/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-payload-freshness-review")).toContainText(/payload_freshness_statusrerun_route_check_required/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-payload-freshness-review")).toContainText(/rerun_route_check/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-missing-context-triage")).toContainText(/missing_context_triage_statusmissing_route_check/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-missing-context-triage")).toContainText(/route-check evidence has not been loaded yet/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-missing-context-triage")).toContainText(/guarded broker dry-run evidence has not been loaded yet/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-missing-context-triage")).toContainText(/broker account mode is unavailable until route-check loads/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-review-statuses")).toContainText(/review-chain status is unavailable until recommendation context is loaded/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-context-gaps")).toContainText(/recommendation_id/i);
  await expect(page.getByTestId("manual-paper-submit-button")).toBeDisabled();
  expect(brokerOrdersCalls).toBe(0);
});

test("manual paper submit confirmation payload freshness review fails closed when timestamps are missing", async ({ page }) => {
  const recommendationId = "recommendation-missing-timestamps";

  await routeRecommendationEvidence(page, recommendationId, {
    recommendationBody: {
      created_at: null,
      reviewed_at: null,
    },
  });

  await page.goto(`/cockpit/manual-paper-submit-confirmation?recommendationId=${recommendationId}&symbol=NVDA`);

  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-payload-freshness-review")).toContainText(/payload_freshness_statusmissing_timestamps/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-payload-freshness-review")).toContainText(/missing_freshness_fields/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-payload-freshness-review")).toContainText(/recommendation.created_at/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-payload-freshness-review")).toContainText(/recommendation.reviewed_at/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-payload-freshness-review")).toContainText(/missing timestamps prevent freshness confirmation/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-missing-context-triage")).toContainText(/missing_context_triage_statusmissing_freshness_evidence/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-missing-context-triage")).toContainText(/missing freshness field: recommendation.created_at/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-missing-context-triage")).toContainText(/missing freshness field: recommendation.reviewed_at/i);
  await expect(page.getByTestId("manual-paper-submit-button")).toBeDisabled();
});

test("manual paper submit confirmation payload freshness review requires a rerun when dry-run evidence is missing", async ({ page }) => {
  const recommendationId = "recommendation-missing-dry-run";

  await routeRecommendationEvidence(page, recommendationId, {
    routeCheckBody: {
      next_required_action: "Run the guarded dry-run preview again before any future manual paper step.",
    },
    dryRunBody: {
      dry_run_status: "missing_context",
      dry_run_only: true,
      dry_run_executed: false,
      allowed_to_submit: false,
      resolved_route: null,
      resolved_execution_source: null,
      dry_run_execution_source: null,
      balance_source: null,
      fees_source: null,
      fills_source: null,
      positions_source: null,
      would_block: true,
      blocked_reason: null,
      next_required_action: "Run the guarded dry-run preview again before any future manual paper step.",
      preflight_decision: null,
      paper_path_note: "Guarded dry-run preview has not been executed yet.",
    },
  });

  await page.goto(`/cockpit/manual-paper-submit-confirmation?recommendationId=${recommendationId}&symbol=NVDA`);

  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-payload-freshness-review")).toContainText(/payload_freshness_statusrerun_dry_run_required/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-payload-freshness-review")).toContainText(/guarded dry-run/i);
  await expect(page.getByTestId("manual-paper-submit-gate-failures")).toContainText(/guarded broker dry-run must remain ready/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-missing-context-triage")).toContainText(/guarded broker dry-run/i);
  await expect(page.getByTestId("manual-paper-submit-button")).toBeDisabled();
});

test("manual paper submit confirmation freshness fails closed when recommendation review evidence is stale", async ({ page }) => {
  const recommendationId = "recommendation-stale-review";
  let brokerOrdersCalls = 0;

  await routeRecommendationEvidence(page, recommendationId, {
    recommendationBody: {
      created_at: "2024-01-01T00:00:00.000Z",
      reviewed_at: "2024-01-01T00:05:00.000Z",
    },
  });
  await page.route("**/broker/orders", async (route) => {
    brokerOrdersCalls += 1;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({}) });
  });

  await page.goto(`/cockpit/manual-paper-submit-confirmation?recommendationId=${recommendationId}&symbol=NVDA`);

  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-payload-freshness-review")).toContainText(/payload_freshness_statusstale_evidence/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-payload-freshness-review")).toContainText(/recommendation payload review timestamp is outside the current freshness window/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-payload-freshness-review")).toContainText(/upstream state has drifted or the reviewed evidence is stale/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-missing-context-triage")).toContainText(/missing_context_triage_statusstale_evidence/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-missing-context-triage")).toContainText(/stale evidence blocks future manual review/i);
  await expect(page.getByTestId("manual-paper-submit-button")).toBeDisabled();
  expect(brokerOrdersCalls).toBe(0);
});

test("manual paper submit confirmation renders a safe blocked state when /broker/orders returns structured 403", async ({ page }) => {
  const recommendationId = "recommendation-blocked-submit";
  let brokerOrdersCalls = 0;

  await routeRecommendationEvidence(page, recommendationId);
  await page.route("**/broker/orders", async (route) => {
    if (new URL(route.request().url()).pathname !== "/broker/orders") {
      await route.continue();
      return;
    }

    brokerOrdersCalls += 1;
    await route.fulfill({
      status: 403,
      contentType: "application/json",
      body: JSON.stringify({
        detail: {
          code: "paper_preflight_blocked",
          message: "Paper order submission blocked by preflight checks.",
          decision_status: "would_block",
          submit_gate: "blocked",
          blocking_reasons: [
            { code: "max_order_notional_exceeded", message: "Order notional exceeds the active paper risk limit." },
          ],
        },
      }),
    });
  });

  await page.goto(`/cockpit/manual-paper-submit-confirmation?recommendationId=${recommendationId}&symbol=NVDA`);
  await page.getByTestId("manual-paper-submit-confirmation-checkbox").check();
  await page.getByTestId("manual-paper-submit-button").click();

  await expect(page.getByTestId("manual-paper-submit-error-state")).toContainText(/paper submit blocked/i);
  await expect(page.getByTestId("manual-paper-submit-error-state")).toContainText(/submit_gate=blocked/i);
  await expect(page.getByTestId("manual-paper-submit-error-state")).toContainText(/decision_status=would_block/i);
  await expect(page.getByTestId("manual-paper-submit-error-state")).toContainText(/order notional exceeds the active paper risk limit/i);
  expect(brokerOrdersCalls).toBe(1);

  const outcomeView = page.getByTestId("manual-paper-submit-outcome-view");
  await expect(outcomeView).toBeVisible();
  await expect(outcomeView).toHaveAttribute("data-outcome-status", "blocked");
  await expect(page.getByTestId("manual-paper-submit-outcome-status")).toContainText(/paper submit blocked/i);
  await expect(page.getByTestId("manual-paper-submit-outcome-live-locked-badge")).toContainText(/live remains locked/i);
  await expect(page.getByTestId("manual-paper-submit-outcome-workers-badge")).toContainText(/workers cannot submit/i);
  await expect(page.getByTestId("manual-paper-submit-outcome-no-live-order-badge")).toContainText(/no live order was placed/i);
  await expect(page.getByTestId("manual-paper-submit-outcome-blocked-reasons")).toContainText(/order notional exceeds the active paper risk limit/i);
  await expect(page.getByTestId("manual-paper-submit-outcome-guard-result")).toContainText(/submit_gate/i);
  await expect(page.getByTestId("manual-paper-submit-outcome-guard-result")).toContainText(/response_decision_status/i);
  await expect(page.getByTestId("manual-paper-submit-outcome-recommendation-id")).toContainText(recommendationId);
  await expect(page.getByTestId("manual-paper-submit-outcome-timeline-href")).toHaveAttribute(
    "href",
    new RegExp(`^/cockpit/audit/broker-submit-decisions\\?correlation_id=manual_paper_submit_[a-z0-9_]+&recommendation_id=${recommendationId}$`),
  );
  await expect(page.getByTestId("manual-paper-submit-outcome-next-step")).toContainText(/resolve blockers and rerun review/i);
  await expect(page.getByTestId("manual-paper-submit-outcome-next-step")).toContainText(/rerun the dry-run before any further paper submit attempt/i);

  // Ensure no auto-resubmit is triggered after the outcome view renders.
  await page.waitForTimeout(150);
  expect(brokerOrdersCalls).toBe(1);
});

test("manual paper submit outcome view renders a safe failed state when /broker/orders fails with a generic 500", async ({ page }) => {
  const recommendationId = "recommendation-failed-submit";
  let brokerOrdersCalls = 0;

  await routeRecommendationEvidence(page, recommendationId);
  await page.route("**/broker/orders", async (route) => {
    if (new URL(route.request().url()).pathname !== "/broker/orders") {
      await route.continue();
      return;
    }

    brokerOrdersCalls += 1;
    await route.fulfill({
      status: 500,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Upstream broker gateway unavailable." }),
    });
  });

  await page.goto(`/cockpit/manual-paper-submit-confirmation?recommendationId=${recommendationId}&symbol=NVDA`);
  await page.getByTestId("manual-paper-submit-confirmation-checkbox").check();
  await page.getByTestId("manual-paper-submit-button").click();

  await expect(page.getByTestId("manual-paper-submit-error-state")).toContainText(/paper submit failed/i);
  expect(brokerOrdersCalls).toBe(1);

  const outcomeView = page.getByTestId("manual-paper-submit-outcome-view");
  await expect(outcomeView).toBeVisible();
  await expect(outcomeView).toHaveAttribute("data-outcome-status", "failed");
  await expect(page.getByTestId("manual-paper-submit-outcome-status")).toContainText(/paper submit failed/i);
  await expect(page.getByTestId("manual-paper-submit-outcome-live-locked-badge")).toContainText(/live remains locked/i);
  await expect(page.getByTestId("manual-paper-submit-outcome-workers-badge")).toContainText(/workers cannot submit/i);
  await expect(page.getByTestId("manual-paper-submit-outcome-no-live-order-badge")).toContainText(/no live order was placed/i);
  await expect(page.getByTestId("manual-paper-submit-outcome-warning")).toBeVisible();
  await expect(page.getByTestId("manual-paper-submit-outcome-timeline-href")).toHaveAttribute(
    "href",
    new RegExp(`^/cockpit/audit/broker-submit-decisions\\?correlation_id=manual_paper_submit_[a-z0-9_]+&recommendation_id=${recommendationId}$`),
  );
  await expect(page.getByTestId("manual-paper-submit-outcome-next-step")).toContainText(/check broker\/api status and timeline before retry/i);
  await expect(page.getByTestId("manual-paper-submit-outcome-next-step")).toContainText(/no automatic resubmission will occur/i);
  await expect(page.getByRole("button", { name: /trade now|auto submit|approve live|one-click execute|live submit|buy now|sell now|execute now/i })).toHaveCount(0);

  // No secret-like fields like api keys, tokens, or passwords should appear in the outcome view.
  await expect(outcomeView).not.toContainText(/api[_-]?key/i);
  await expect(outcomeView).not.toContainText(/secret/i);
  await expect(outcomeView).not.toContainText(/password/i);
  await expect(outcomeView).not.toContainText(/bearer/i);

  await page.waitForTimeout(150);
  expect(brokerOrdersCalls).toBe(1);
});

test("manual paper submit confirmation triage groups payload, source-label, broker-mode, and blocking issues", async ({ page }) => {
  const recommendationId = "recommendation-triage-blocked";

  await routeRecommendationEvidence(page, recommendationId, {
    recommendationBody: {
      order_type: "LIMIT",
      limit_price: null,
    },
    routeCheckBody: {
      order_type: "LIMIT",
      limit_price: null,
      route_check_status: "blocked",
      blocked_reason: "Live broker mode must be reset before paper review can continue.",
      execution_source: "unexpected_source",
      serious_paper_source: "ibkr_live",
      canonical_paper_route: "/broker/live-orders",
      broker_account_mode: "live",
      live_trading_enabled: true,
      workers_allowed_to_submit: true,
      broker_mode: {
        broker: "ibkr",
        mode: "live",
        live_execution_enabled: true,
        paper_trading_enabled: false,
      },
    },
    dryRunBody: {
      order_type: "LIMIT",
      limit_price: null,
      dry_run_execution_source: "unexpected_source",
      serious_paper_source: "ibkr_live",
      canonical_paper_route: "/broker/live-orders",
      broker_account_mode: "live",
      live_trading_enabled: true,
      workers_allowed_to_submit: true,
      broker_mode: {
        broker: "ibkr",
        mode: "live",
        live_execution_enabled: true,
        paper_trading_enabled: false,
      },
    },
  });

  await page.goto(`/cockpit/manual-paper-submit-confirmation?recommendationId=${recommendationId}&symbol=NVDA`);

  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-missing-context-triage")).toContainText(/missing_context_triage_statusblocked_by_review/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-missing-context-triage")).toContainText(/payload/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-missing-context-triage")).toContainText(/limit_price/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-missing-context-triage")).toContainText(/source labels \/ broker mode/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-missing-context-triage")).toContainText(/route-check execution_source is unexpected_source/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-missing-context-triage")).toContainText(/broker mode is missing, unknown, or no longer coherently paper/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-missing-context-triage")).toContainText(/live trading is no longer locked/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-missing-context-triage")).toContainText(/workers would be allowed to submit/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-missing-context-triage")).toContainText(/blocking reasons/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-missing-context-triage")).toContainText(/live broker mode must be reset before paper review can continue/i);
  await expect(page.getByTestId("manual-paper-submit-button")).toBeDisabled();
});

test("manual paper submit confirmation stays disabled when live or worker safety gates drift unsafe", async ({ page }) => {
  const recommendationId = "recommendation-live-blocked";
  let brokerOrdersCalls = 0;

  await routeRecommendationEvidence(page, recommendationId, {
    routeCheckBody: {
      live_trading_enabled: true,
      workers_allowed_to_submit: true,
      broker_account_mode: "live",
      serious_paper_source: "ibkr_live",
      broker_mode: {
        broker: "ibkr",
        mode: "live",
        live_execution_enabled: true,
        paper_trading_enabled: false,
      },
    },
    dryRunBody: {
      live_trading_enabled: true,
      workers_allowed_to_submit: true,
      broker_account_mode: "live",
      serious_paper_source: "ibkr_live",
      broker_mode: {
        broker: "ibkr",
        mode: "live",
        live_execution_enabled: true,
        paper_trading_enabled: false,
      },
    },
  });
  await page.route("**/broker/orders", async (route) => {
    brokerOrdersCalls += 1;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({}) });
  });

  await page.goto(`/cockpit/manual-paper-submit-confirmation?recommendationId=${recommendationId}&symbol=NVDA`);

  await expect(page.getByTestId("manual-paper-submit-gate-failures")).toContainText(/live trading must remain locked/i);
  await expect(page.getByTestId("manual-paper-submit-gate-failures")).toContainText(/workers must remain non-submitting/i);
  await expect(page.getByTestId("manual-paper-submit-button")).toBeDisabled();
  expect(brokerOrdersCalls).toBe(0);
});

test("in-flight review chain remains navigation-only and exposes no submit control", async ({ page }) => {
  const recommendationId = "recommendation-1";
  let brokerOrdersCalls = 0;

  await mockInFlightReport(page, recommendationId);
  await routeRecommendationEvidence(page, recommendationId);
  await page.route("**/broker/orders", async (route) => {
    brokerOrdersCalls += 1;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({}) });
  });

  await page.goto("/cockpit/in-flight-adjustments");
  await expect(page.getByTestId("manual-paper-submit-button")).toHaveCount(0);
  await page.getByTestId(`recommendation-route-check-trigger-${recommendationId}`).click();
  await page.getByTestId(`recommendation-dry-run-preview-trigger-${recommendationId}`).click();

  const confirmationLink = page.getByRole("link", { name: /manual ibkr paper submit confirmation/i }).first();
  await expect(confirmationLink).toBeVisible();
  await confirmationLink.click();

  await expect(page).toHaveURL(new RegExp(`/cockpit/manual-paper-submit-confirmation\\?recommendationId=${recommendationId}`));
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-page")).toContainText(/paper only/i);
  await expect(page.getByTestId("manual-paper-submit-button")).toBeDisabled();
  expect(brokerOrdersCalls).toBe(0);
});