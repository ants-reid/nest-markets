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
) {
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
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-review-statuses")).toContainText(/review-chain status is unavailable until recommendation context is loaded/i);
  await expect(page.getByTestId("cockpit-manual-paper-submit-confirmation-context-gaps")).toContainText(/recommendation_id/i);
  await expect(page.getByTestId("manual-paper-submit-disabled-button")).toBeDisabled();
  expect(brokerOrdersCalls).toBe(0);
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