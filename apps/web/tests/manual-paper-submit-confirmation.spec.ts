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

test("manual paper submit confirmation surface stays design-only and never calls /broker/orders", async ({ page }) => {
  const recommendationId = "recommendation-1";
  let brokerOrdersCalls = 0;

  await routeRecommendationEvidence(page, recommendationId);
  await page.route("**/broker/orders", async (route) => {
    brokerOrdersCalls += 1;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({}) });
  });

  await page.goto(`/cockpit/manual-paper-submit-confirmation?recommendationId=${recommendationId}&symbol=NVDA`);

  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-page")).toBeVisible();
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-status")).toContainText(/design_only_not_enabled/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-surface-status-grid")).toContainText(/submit_enabled_nowfalse/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-surface-status-grid")).toContainText(/order_submittedfalse/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-surface-status-grid")).toContainText(/live_trading_enabledfalse/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-surface-status-grid")).toContainText(/workers_allowed_to_submitfalse/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-surface-status-grid")).toContainText(/route_check_statuseligible/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-surface-status-grid")).toContainText(/dry_run_statusready/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-surface-status-grid")).toContainText(/readiness_statusready_for_future_manual_paper_submit/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-surface-status-grid")).toContainText(/handoff_statushandoff_ready_for_future_manual_step/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-surface-status-grid")).toContainText(/audit_package_statuspackage_ready_for_future_manual_review/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-surface-status-grid")).toContainText(/approval_package_statusapproval_package_ready_for_future_manual_review/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-surface-status-grid")).toContainText(/preflight_contract_statuspreflight_contract_ready_for_future_manual_step/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-future-route")).toContainText(/future_submit_route\/broker\/orders/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-review-statuses")).toContainText(/read-only confirmation preview/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-review-statuses")).toContainText(/submit-decision review status/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-review-statuses")).toContainText(/operator action review status/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-review-statuses")).toContainText(/final interaction spec status/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-payload-freshness-review")).toContainText(/payload freshness review/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-payload-freshness-review")).toContainText(/payload_freshness_statusfreshness_ready_for_future_manual_review/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-payload-freshness-review")).toContainText(/recommendation_payload_freshtrue/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-payload-freshness-review")).toContainText(/route_check_freshtrue/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-payload-freshness-review")).toContainText(/dry_run_freshtrue/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-payload-freshness-review")).toContainText(/approval_package_freshtrue/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-payload-freshness-review")).toContainText(/preflight_contract_freshtrue/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-payload-freshness-review")).toContainText(/submit_enabled_nowfalse/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-payload-freshness-review")).toContainText(/order_submittedfalse/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-payload-freshness-review")).toContainText(/live_trading_enabledfalse/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-payload-freshness-review")).toContainText(/workers_allowed_to_submitfalse/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-payload-freshness-review")).toContainText(/submit remains disabled in this phase/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-payload-freshness-review")).toContainText(/future manual paper submit would require fresh route-check and dry-run evidence/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-payload-freshness-review")).toContainText(/live trading still locked/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-payload-freshness-review")).toContainText(/workers still non-submitting/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-missing-context-triage")).toContainText(/missing-context triage/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-missing-context-triage")).toContainText(/missing_context_triage_statustriage_clear_for_future_review/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-missing-context-triage")).toContainText(/submit_enabled_nowfalse/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-missing-context-triage")).toContainText(/order_submittedfalse/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-missing-context-triage")).toContainText(/live_trading_enabledfalse/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-missing-context-triage")).toContainText(/workers_allowed_to_submitfalse/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-missing-context-triage")).toContainText(/triage is clear for future review/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-rerun-checklist")).toContainText(/submit-time checks will rerun/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-decision-persistence")).toContainText(/submit_preflight decision before submit/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-wording-preview")).toContainText(/i understand this is an ibkr paper order only/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-context-gaps")).toContainText(/no missing context is currently surfaced/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-context-gaps")).toContainText(/no blocking reasons are currently surfaced/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-context-gaps")).toContainText(/no warnings are currently surfaced/i);
  await expect(page.getByTestId("manual-paper-submit-disabled-button")).toBeDisabled();
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-page")).toContainText(/submit not enabled in this phase/i);
  await expect(page.getByRole("button", { name: /trade now|auto submit|approve live|one-click execute|live submit|buy now|sell now|execute now|submit order now/i })).toHaveCount(0);
  expect(brokerOrdersCalls).toBe(0);
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
  await expect(page.getByTestId("manual-paper-submit-disabled-button")).toBeDisabled();
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
  await expect(page.getByTestId("manual-paper-submit-disabled-button")).toBeDisabled();
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
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-payload-freshness-review")).toContainText(/future manual paper submit would require a fresh guarded broker dry-run preview first/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-missing-context-triage")).toContainText(/missing_context_triage_statusmissing_dry_run/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-missing-context-triage")).toContainText(/guarded broker dry-run must be rerun before future manual review/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-missing-context-triage")).toContainText(/rerun_required/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-missing-context-triage")).toContainText(/guarded dry-run/i);
  await expect(page.getByTestId("manual-paper-submit-disabled-button")).toBeDisabled();
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
  await expect(page.getByTestId("manual-paper-submit-disabled-button")).toBeDisabled();
});

test("in-flight review chain links to the dedicated confirmation design surface without adding execution", async ({ page }) => {
  const recommendationId = "recommendation-1";

  await mockInFlightReport(page, recommendationId);
  await routeRecommendationEvidence(page, recommendationId);

  await page.goto("/cockpit/in-flight-adjustments");
  await page.getByTestId(`recommendation-route-check-trigger-${recommendationId}`).click();
  await page.getByTestId(`recommendation-dry-run-preview-trigger-${recommendationId}`).click();

  const confirmationLink = page.getByRole("link", { name: /manual ibkr paper submit confirmation/i }).first();
  await expect(confirmationLink).toBeVisible();
  await confirmationLink.click();

  await expect(page).toHaveURL(new RegExp(`/cockpit/manual-paper-submit-confirmation\\?recommendationId=${recommendationId}`));
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-page")).toContainText(/paper only/i);
  await expect(page.getByTestId("manual-paper-submit-disabled-button")).toBeDisabled();
});