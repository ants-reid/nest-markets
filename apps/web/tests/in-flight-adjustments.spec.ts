import { expect, test } from "@playwright/test";

const API_BASE_URL = process.env.PLAYWRIGHT_API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
const API_ORIGIN = new URL(API_BASE_URL).origin;

function apiUrl(path: string) {
  return new URL(path, API_BASE_URL).toString();
}

function isApiRequest(requestUrl: string, pathname: string): boolean {
  const url = new URL(requestUrl);
  return url.origin === API_ORIGIN && url.pathname === pathname;
}

type MockRouteResponse = {
  status: number;
  contentType: string;
  body: string;
};

async function routeRecommendationRouteChecks(
  page: import("@playwright/test").Page,
  responses: Record<string, MockRouteResponse>,
) {
  await page.route("**/paper/recommendations/**/serious-paper-route-check*", async (route) => {
    const requestUrl = new URL(route.request().url());

    if (requestUrl.pathname !== `/paper/recommendations/${requestUrl.pathname.split("/")[3]}/serious-paper-route-check`) {
      await route.continue();
      return;
    }

    const parts = requestUrl.pathname.split("/");
    const recommendationId = parts[3];
    const response = recommendationId ? responses[recommendationId] : undefined;

    if (!response) {
      await route.continue();
      return;
    }

    await route.fulfill(response);
  });
}

async function routeRecommendationDryRunPreviews(
  page: import("@playwright/test").Page,
  responses: Record<string, MockRouteResponse>,
) {
  await page.route("**/paper/recommendations/**/broker-dry-run-preview*", async (route) => {
    const requestUrl = new URL(route.request().url());

    if (requestUrl.pathname !== `/paper/recommendations/${requestUrl.pathname.split("/")[3]}/broker-dry-run-preview`) {
      await route.continue();
      return;
    }

    const parts = requestUrl.pathname.split("/");
    const recommendationId = parts[3];
    const response = recommendationId ? responses[recommendationId] : undefined;

    if (!response) {
      await route.continue();
      return;
    }

    await route.fulfill(response);
  });
}

function buildInFlightReport(overrides: Record<string, unknown> = {}) {
  return {
    generated_at: "2026-05-22T20:15:00+00:00",
    mode: "paper",
    summary: {
      headline: "Read-only in-flight paper adjustments watchlist for operator review.",
      total_items: 3,
      open_positions: 1,
      open_orders: 1,
      active_recommendations: 1,
      watch_only: 0,
      review_required: 2,
      high_attention: 1,
    },
    items: [
      {
        id: "position-1",
        item_type: "paper_position",
        symbol: "AAPL",
        asset_id: "asset-aapl",
        asset_name: "Apple Inc.",
        asset_detail_path: "/asset-cards/asset-aapl",
        has_asset_context: true,
        status: "open",
        opened_at: "2026-05-22T18:00:00+00:00",
        created_at: "2026-05-22T18:00:00+00:00",
        current_state_summary: "AAPL long qty=1 entry=189.5",
        attention_level: "high",
        adjustment_label: "risk_attention",
        reason: "Linked risk decision is not approved and needs operator review.",
        evidence: ["position_status=open", "risk_decision=rejected"],
        missing_data: [],
        recommended_review_action: "Review risk notes before next paper check.",
        is_actionable: false,
      },
      {
        id: "order-1",
        item_type: "paper_order",
        symbol: "AAPL",
        asset_id: null,
        asset_name: null,
        asset_detail_path: null,
        has_asset_context: false,
        status: "accepted",
        opened_at: null,
        created_at: "2026-05-22T19:55:00+00:00",
        current_state_summary: "AAPL buy qty=1 type=limit",
        attention_level: "medium",
        adjustment_label: "review_required",
        reason: "Order requires review.",
        evidence: ["order_status=accepted"],
        missing_data: [],
        recommended_review_action: "Review order lifecycle context.",
        is_actionable: false,
      },
      {
        id: "recommendation-1",
        item_type: "paper_recommendation",
        symbol: "NVDA",
        asset_id: "asset-nvda",
        asset_name: "NVIDIA Corp.",
        asset_detail_path: "/asset-cards/asset-nvda",
        has_asset_context: true,
        status: "approved",
        opened_at: null,
        created_at: "2026-05-22T20:05:00+00:00",
        current_state_summary: "NVDA BUY qty=3 order_type=MARKET",
        attention_level: "medium",
        adjustment_label: "review_required",
        reason: "Recommendation is awaiting operator route-check before guarded broker paper review.",
        evidence: ["recommendation_status=approved", "paper_review=manual_required"],
        missing_data: [],
        recommended_review_action: "Review the recommendation route-check before guarded broker dry-run.",
        is_actionable: false,
      },
    ],
    monitor_notes: [
      {
        title: "Feed degraded",
        detail: "Primary feed stalled.",
        severity: "critical",
        created_at: "2026-05-22T19:45:00+00:00",
      },
    ],
    risk_notes: ["Risk decision rejected for abc: spread_too_wide."],
    limitations: [],
    recommended_review_actions: [
      "Start with high-attention items, then review medium-priority items.",
    ],
    ...overrides,
  };
}

async function mockInFlightReport(
  page: import("@playwright/test").Page,
  payload = buildInFlightReport(),
) {
  await page.route("**/cockpit/in-flight-adjustments*", async (route) => {
    const request = route.request();
    const requestUrl = new URL(request.url());

    if (
      request.resourceType() !== "fetch" ||
      requestUrl.pathname !== "/cockpit/in-flight-adjustments"
    ) {
      await route.continue();
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(payload),
    });
  });

  await routeRecommendationRouteChecks(page, {
    "recommendation-1": {
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        recommendation_id: "recommendation-1",
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
        next_required_action: "Run POST /broker/orders/dry-run for the intended order, then submit through POST /broker/orders only if the paper preflight remains acceptable.",
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
    },
  });

  await routeRecommendationDryRunPreviews(page, {
    "recommendation-1": {
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        recommendation_id: "recommendation-1",
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
        next_required_action: "Review this guarded broker dry-run preview, then use the existing POST /broker/orders manual paper submit path only if the operator still accepts the preflight findings.",
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
        preflight_context: {
          cash_balance: null,
          buying_power: null,
          open_position_count: null,
          current_symbol_exposure: null,
          estimated_post_trade_symbol_exposure: null,
          current_total_exposure: null,
          estimated_post_trade_total_exposure: null,
          daily_pnl: null,
          daily_loss: null,
          risk_limit_snapshot: null,
        },
        paper_path_note: "Dry-run validates the IBKR paper submit path without placing an order.",
      }),
    },
  });
}

test("In-Flight Adjustments route renders summary and paper read-only wording", async ({ page }) => {
  await mockInFlightReport(page);

  await page.goto("/cockpit/in-flight-adjustments");
  await page.waitForLoadState("domcontentloaded");

  await expect(page.getByTestId("cockpit-in-flight-adjustments-page")).toBeVisible();
  await expect(page.getByRole("heading", { name: /in-flight adjustments/i })).toBeVisible();
  await expect(page.getByTestId("cockpit-in-flight-paper-mode")).toContainText(/paper mode only/i);
  await expect(page.getByTestId("cockpit-in-flight-summary-cards")).toContainText(/in-flight items/i);
  await expect(page.getByTestId("cockpit-in-flight-item-list")).toContainText(/AAPL/);
  await expect(page.getByTestId("cockpit-in-flight-item-list")).toContainText(/NVDA/);
  await expect(page.getByRole("link", { name: /view asset context/i }).first()).toHaveAttribute("href", "/asset-cards/asset-aapl");
  await expect(page.getByText(/asset context unavailable/i)).toBeVisible();
  await expect(page.getByRole("button", { name: /place|close|modify|execute/i })).toHaveCount(0);
  await expect(page.getByRole("button", { name: /buy|sell|approve live|auto submit|trade now/i })).toHaveCount(0);
});

test("In-Flight Adjustments recommendation route-check renders eligible review state", async ({ page }) => {
  await mockInFlightReport(page);

  await page.goto("/cockpit/in-flight-adjustments");
  await page.waitForLoadState("domcontentloaded");

  await page.getByTestId("recommendation-route-check-trigger-recommendation-1").click();

  await expect(page.getByTestId("recommendation-route-check-status-recommendation-1")).toContainText(/eligible/i);
  await expect(page.getByTestId("recommendation-route-check-summary-recommendation-1")).toContainText(
    /ready for guarded ibkr paper dry-run\/manual review/i,
  );
  await expect(page.getByTestId("recommendation-route-check-panel-recommendation-1")).toContainText(
    /workers allowed to submit/i,
  );
  await expect(page.getByTestId("recommendation-route-check-panel-recommendation-1")).toContainText(
    /live trading enabled/i,
  );
  await expect(page.getByTestId("recommendation-route-check-panel-recommendation-1")).toContainText(
    /no/i,
  );
  await expect(page.getByRole("link", { name: /open guarded broker dry-run/i })).toHaveAttribute(
    "href",
    "/broker#broker-execution",
  );
  await expect(page.getByRole("link", { name: /view manual paper route/i })).toHaveAttribute(
    "href",
    "/broker#broker-execution",
  );
  await expect(page.getByTestId("recommendation-dry-run-preview-trigger-recommendation-1")).toBeVisible();
  await expect(page.getByTestId("recommendation-submit-readiness-status-recommendation-1")).toContainText(
    /dry-run required/i,
  );
  await expect(page.getByTestId("recommendation-submit-readiness-summary-recommendation-1")).toContainText(
    /readiness only, no order submitted/i,
  );
  await expect(page.getByTestId("recommendation-submit-readiness-recommendation-1")).toContainText(
    /live remains locked/i,
  );
  await expect(page.getByTestId("recommendation-submit-readiness-recommendation-1")).toContainText(
    /workers cannot submit/i,
  );
  await expect(page.getByTestId("recommendation-submit-handoff-status-recommendation-1")).toContainText(
    /dry-run required first/i,
  );
  await expect(page.getByTestId("recommendation-submit-handoff-summary-recommendation-1")).toContainText(
    /handoff review only, no order submitted/i,
  );
  await expect(page.getByTestId("recommendation-submit-handoff-recommendation-1")).toContainText(
    /future manual submit route/i,
  );
  await expect(page.getByTestId("recommendation-submit-handoff-recommendation-1")).toContainText(
    /not available/i,
  );
  await expect(page.getByTestId("recommendation-submit-handoff-recommendation-1")).toContainText(
    /no order submitted/i,
  );
  await expect(page.getByTestId("recommendation-submit-audit-package-status-recommendation-1")).toContainText(
    /dry-run required first/i,
  );
  await expect(page.getByTestId("recommendation-submit-audit-package-summary-recommendation-1")).toContainText(
    /audit package only, no order submitted/i,
  );
  await expect(page.getByTestId("recommendation-submit-audit-package-recommendation-1")).toContainText(
    /manual paper submit audit package/i,
  );
  await expect(page.getByTestId("recommendation-submit-audit-package-recommendation-1")).toContainText(
    /future \/broker\/orders payload preview fields/i,
  );
  await expect(page.getByTestId("recommendation-submit-audit-package-recommendation-1")).toContainText(
    /not available/i,
  );
  await expect(page.getByTestId("recommendation-submit-audit-package-recommendation-1")).toContainText(
    /no order submitted: yes/i,
  );
  await expect(page.getByTestId("recommendation-submit-approval-package-status-recommendation-1")).toContainText(
    /dry-run required first/i,
  );
  await expect(page.getByTestId("recommendation-submit-approval-package-summary-recommendation-1")).toContainText(
    /approval package only, no order submitted/i,
  );
  await expect(page.getByTestId("recommendation-submit-approval-package-recommendation-1")).toContainText(
    /future manual approval requirements/i,
  );
  await expect(page.getByTestId("recommendation-submit-approval-package-recommendation-1")).toContainText(
    /not available/i,
  );
  await expect(page.getByTestId("recommendation-submit-approval-package-recommendation-1")).toContainText(
    /no order submitted: yes/i,
  );
  await expect(page.getByTestId("recommendation-submit-preflight-contract-status-recommendation-1")).toContainText(
    /dry-run required first/i,
  );
  await expect(page.getByTestId("recommendation-submit-preflight-contract-summary-recommendation-1")).toContainText(
    /preflight contract only, no order submitted/i,
  );
  await expect(page.getByTestId("recommendation-submit-preflight-contract-recommendation-1")).toContainText(
    /submit-time rerun requirements/i,
  );
  await expect(page.getByTestId("recommendation-submit-preflight-contract-recommendation-1")).toContainText(
    /future manual submit route/i,
  );
  await expect(page.getByTestId("recommendation-submit-preflight-contract-recommendation-1")).toContainText(
    /not available/i,
  );
  await expect(page.getByTestId("recommendation-submit-preflight-contract-recommendation-1")).toContainText(
    /submitted order/i,
  );
  await expect(page.getByTestId("recommendation-submit-decision-review-status-recommendation-1")).toContainText(
    /dry-run required first/i,
  );
  await expect(page.getByTestId("recommendation-submit-decision-review-summary-recommendation-1")).toContainText(
    /no decision written and no order submitted/i,
  );
  await expect(page.getByTestId("recommendation-submit-decision-review-recommendation-1")).toContainText(
    /future sourcemanual_paper_submit/i,
  );
  await expect(page.getByTestId("recommendation-submit-decision-review-recommendation-1")).toContainText(
    /decision_write_performed_nowfalse/i,
  );
  await expect(page.getByTestId("recommendation-submit-decision-review-recommendation-1")).toContainText(
    /submitted_orderfalse/i,
  );
  await expect(page.getByTestId("recommendation-submit-decision-review-recommendation-1")).toContainText(
    /submit_preflight_decision_required: yes/i,
  );
  await expect(page.getByTestId("recommendation-submit-decision-review-recommendation-1")).toContainText(
    /submit_attempt_decision_required: yes/i,
  );
  await expect(page.getByTestId("recommendation-submit-decision-review-recommendation-1")).toContainText(
    /no submit button is available here/i,
  );
  await expect(page.getByTestId("recommendation-operator-action-review-status-recommendation-1")).toContainText(
    /dry-run required first/i,
  );
  await expect(page.getByTestId("recommendation-operator-action-review-summary-recommendation-1")).toContainText(
    /action review only, no order submitted/i,
  );
  await expect(page.getByTestId("recommendation-operator-action-review-recommendation-1")).toContainText(
    /future_action_namemanual_ibkr_paper_submit/i,
  );
  await expect(page.getByTestId("recommendation-operator-action-review-recommendation-1")).toContainText(
    /action_available_nowfalse/i,
  );
  await expect(page.getByTestId("recommendation-operator-action-review-recommendation-1")).toContainText(
    /decision_write_performed_nowfalse/i,
  );
  await expect(page.getByTestId("recommendation-operator-action-review-recommendation-1")).toContainText(
    /future_action_enabled_now: false/i,
  );
  await expect(page.getByTestId("recommendation-operator-action-review-recommendation-1")).toContainText(
    /future_action_route: not available/i,
  );
  await expect(page.getByTestId("recommendation-operator-action-review-recommendation-1")).toContainText(
    /future_action_requires_operator_confirmation: true/i,
  );
  await expect(page.getByTestId("recommendation-operator-action-review-recommendation-1")).toContainText(
    /future_action_requires_submit_time_rechecks: true/i,
  );
  await expect(page.getByTestId("recommendation-operator-action-review-recommendation-1")).toContainText(
    /future_action_requires_decision_persistence: true/i,
  );
  await expect(page.getByTestId("recommendation-operator-action-review-recommendation-1")).toContainText(
    /no submit button is available here/i,
  );
  await expect(page.getByTestId("recommendation-final-guarded-submit-interaction-spec-status-recommendation-1")).toContainText(
    /dry-run required first/i,
  );
  await expect(page.getByTestId("recommendation-final-guarded-submit-interaction-spec-summary-recommendation-1")).toContainText(
    /interaction spec only, no order submitted/i,
  );
  await expect(page.getByTestId("recommendation-final-guarded-submit-interaction-spec-recommendation-1")).toContainText(
    /future_interaction_namemanual_ibkr_paper_submit/i,
  );
  await expect(page.getByTestId("recommendation-final-guarded-submit-interaction-spec-recommendation-1")).toContainText(
    /future_interaction_route: not available/i,
  );
  await expect(page.getByTestId("recommendation-final-guarded-submit-interaction-spec-recommendation-1")).toContainText(
    /action_available_nowfalse/i,
  );
  await expect(page.getByTestId("recommendation-final-guarded-submit-interaction-spec-recommendation-1")).toContainText(
    /decision_write_performed_nowfalse/i,
  );
  await expect(page.getByTestId("recommendation-final-guarded-submit-interaction-spec-recommendation-1")).toContainText(
    /submitted_orderfalse/i,
  );
  await expect(page.getByTestId("recommendation-final-guarded-submit-interaction-spec-recommendation-1")).toContainText(
    /submit_time_checks_rerun_latertrue/i,
  );
  await expect(page.getByTestId("recommendation-final-guarded-submit-interaction-spec-recommendation-1")).toContainText(
    /no submit button is available here/i,
  );
});

test("In-Flight Adjustments recommendation dry-run preview renders safe broker review details", async ({ page }) => {
  await mockInFlightReport(page);

  await page.goto("/cockpit/in-flight-adjustments");
  await page.waitForLoadState("domcontentloaded");

  await page.getByTestId("recommendation-route-check-trigger-recommendation-1").click();
  await page.getByTestId("recommendation-dry-run-preview-trigger-recommendation-1").click();

  await expect(page.getByTestId("recommendation-dry-run-preview-status-recommendation-1")).toContainText(/ready/i);
  await expect(page.getByTestId("recommendation-dry-run-preview-summary-recommendation-1")).toContainText(
    /no order submitted/i,
  );
  await expect(page.getByTestId("recommendation-dry-run-preview-recommendation-1")).toContainText(
    /broker_dry_run/i,
  );
  await expect(page.getByTestId("recommendation-dry-run-preview-recommendation-1")).toContainText(
    /allowed to submit/i,
  );
  await expect(page.getByTestId("recommendation-dry-run-preview-recommendation-1")).toContainText(
    /dry-run validates the ibkr paper submit path without placing an order/i,
  );
  await expect(page.getByTestId("recommendation-submit-readiness-status-recommendation-1")).toContainText(
    /ready for future manual paper submit/i,
  );
  await expect(page.getByTestId("recommendation-submit-readiness-summary-recommendation-1")).toContainText(
    /ready for future manual paper handoff/i,
  );
  await expect(page.getByTestId("recommendation-submit-readiness-recommendation-1")).toContainText(
    /no submit control is present: yes/i,
  );
  await expect(page.getByTestId("recommendation-submit-handoff-status-recommendation-1")).toContainText(
    /ready for future manual handoff/i,
  );
  await expect(page.getByTestId("recommendation-submit-handoff-summary-recommendation-1")).toContainText(
    /future manual paper submit would still use guarded \/broker\/orders/i,
  );
  await expect(page.getByTestId("recommendation-submit-handoff-recommendation-1")).toContainText(
    /future manual submit route/i,
  );
  await expect(page.getByTestId("recommendation-submit-handoff-recommendation-1")).toContainText(
    /\/broker\/orders/i,
  );
  await expect(page.getByTestId("recommendation-submit-handoff-recommendation-1")).toContainText(
    /no order submitted: yes/i,
  );
  await expect(page.getByTestId("recommendation-submit-audit-package-status-recommendation-1")).toContainText(
    /package ready for future manual review/i,
  );
  await expect(page.getByTestId("recommendation-submit-audit-package-summary-recommendation-1")).toContainText(
    /future guarded manual paper submit step/i,
  );
  await expect(page.getByTestId("recommendation-submit-audit-package-recommendation-1")).toContainText(
    /resolved future route/i,
  );
  await expect(page.getByTestId("recommendation-submit-audit-package-recommendation-1")).toContainText(
    /\/broker\/orders/i,
  );
  await expect(page.getByTestId("recommendation-submit-audit-package-recommendation-1")).toContainText(
    /account_mode: required · ready · paper/i,
  );
  await expect(page.getByTestId("recommendation-submit-audit-package-recommendation-1")).toContainText(
    /broker submit decision reference: not surfaced before a future guarded submit step/i,
  );
  await expect(page.getByTestId("recommendation-submit-audit-package-recommendation-1")).toContainText(
    /no order submitted: yes/i,
  );
  await expect(page.getByTestId("recommendation-submit-approval-package-status-recommendation-1")).toContainText(
    /approval package ready for future manual review/i,
  );
  await expect(page.getByTestId("recommendation-submit-approval-package-summary-recommendation-1")).toContainText(
    /approval-style package is ready for operator review/i,
  );
  await expect(page.getByTestId("recommendation-submit-approval-package-recommendation-1")).toContainText(
    /future manual submit route/i,
  );
  await expect(page.getByTestId("recommendation-submit-approval-package-recommendation-1")).toContainText(
    /\/broker\/orders/i,
  );
  await expect(page.getByTestId("recommendation-submit-approval-package-recommendation-1")).toContainText(
    /submit-time preflight required: yes/i,
  );
  await expect(page.getByTestId("recommendation-submit-approval-package-recommendation-1")).toContainText(
    /submit-time decision persistence required: yes/i,
  );
  await expect(page.getByTestId("recommendation-submit-approval-package-recommendation-1")).toContainText(
    /operator_manual_review_required: required later/i,
  );
  await expect(page.getByTestId("recommendation-submit-preflight-contract-status-recommendation-1")).toContainText(
    /preflight contract ready for future manual step/i,
  );
  await expect(page.getByTestId("recommendation-submit-preflight-contract-summary-recommendation-1")).toContainText(
    /final pre-submit checklist is ready for operator review/i,
  );
  await expect(page.getByTestId("recommendation-submit-preflight-contract-recommendation-1")).toContainText(
    /future manual submit route/i,
  );
  await expect(page.getByTestId("recommendation-submit-preflight-contract-recommendation-1")).toContainText(
    /\/broker\/orders/i,
  );
  await expect(page.getByTestId("recommendation-submit-preflight-contract-recommendation-1")).toContainText(
    /decision logging requirements/i,
  );
  await expect(page.getByTestId("recommendation-submit-preflight-contract-recommendation-1")).toContainText(
    /source label rechecks/i,
  );
  await expect(page.getByTestId("recommendation-submit-preflight-contract-recommendation-1")).toContainText(
    /operator_confirmation_required: required later/i,
  );
  await expect(page.getByTestId("recommendation-future-manual-submit-design-review-recommendation-1")).toContainText(
    /future manual submit design review/i,
  );
  await expect(page.getByTestId("recommendation-future-manual-submit-design-review-status-recommendation-1")).toContainText(
    /design only, not enabled/i,
  );
  await expect(page.getByTestId("recommendation-future-manual-submit-design-review-summary-recommendation-1")).toContainText(
    /design only, not enabled/i,
  );
  await expect(page.getByTestId("recommendation-future-manual-submit-design-review-recommendation-1")).toContainText(
    /future submit route/i,
  );
  await expect(page.getByTestId("recommendation-future-manual-submit-design-review-recommendation-1")).toContainText(
    /\/broker\/orders/i,
  );
  await expect(page.getByTestId("recommendation-future-manual-submit-design-review-recommendation-1")).toContainText(
    /future submit statusdesign_only_not_enabled/i,
  );
  await expect(page.getByTestId("recommendation-future-manual-submit-design-review-recommendation-1")).toContainText(
    /final_operator_confirmation_requiredtrue/i,
  );
  await expect(page.getByTestId("recommendation-future-manual-submit-design-review-recommendation-1")).toContainText(
    /submit_time_preflight_rerun_requiredtrue/i,
  );
  await expect(page.getByTestId("recommendation-future-manual-submit-design-review-recommendation-1")).toContainText(
    /submit_time_decision_persistence_requiredtrue/i,
  );
  await expect(page.getByTestId("recommendation-future-manual-submit-design-review-recommendation-1")).toContainText(
    /submit_time_live_lock_recheck_requiredtrue/i,
  );
  await expect(page.getByTestId("recommendation-future-manual-submit-design-review-recommendation-1")).toContainText(
    /submit_time_worker_submit_allowedfalse/i,
  );
  await expect(page.getByTestId("recommendation-future-manual-submit-design-review-recommendation-1")).toContainText(
    /submit_button_availablefalse/i,
  );
  await expect(page.getByTestId("recommendation-future-manual-submit-design-review-recommendation-1")).toContainText(
    /order_submittedfalse/i,
  );
  await expect(page.getByTestId("recommendation-future-manual-submit-design-review-recommendation-1")).toContainText(
    /enabled_in_this_phasefalse/i,
  );
  await expect(page.getByTestId("recommendation-future-manual-submit-design-review-recommendation-1")).toContainText(
    /decision logging would be required/i,
  );
  await expect(page.getByTestId("recommendation-future-manual-submit-design-review-recommendation-1")).toContainText(
    /submit-time checks would rerun/i,
  );
  await expect(page.getByTestId("recommendation-future-manual-submit-design-review-recommendation-1")).toContainText(
    /live remains locked/i,
  );
  await expect(page.getByTestId("recommendation-future-manual-submit-design-review-recommendation-1")).toContainText(
    /workers cannot submit/i,
  );
  await expect(page.getByTestId("recommendation-submit-decision-review-status-recommendation-1")).toContainText(
    /ready for future decision review/i,
  );
  await expect(page.getByTestId("recommendation-submit-decision-review-summary-recommendation-1")).toContainText(
    /no decision written and no order submitted/i,
  );
  await expect(page.getByTestId("recommendation-submit-decision-review-recommendation-1")).toContainText(
    /decision persistence owner/i,
  );
  await expect(page.getByTestId("recommendation-submit-decision-review-recommendation-1")).toContainText(
    /manual_paper_submit/i,
  );
  await expect(page.getByTestId("recommendation-submit-decision-review-recommendation-1")).toContainText(
    /decision_write_performed_nowfalse/i,
  );
  await expect(page.getByTestId("recommendation-submit-decision-review-recommendation-1")).toContainText(
    /review_onlytrue/i,
  );
  await expect(page.getByTestId("recommendation-submit-decision-review-recommendation-1")).toContainText(
    /submit_preflight_decision_required: yes/i,
  );
  await expect(page.getByTestId("recommendation-submit-decision-review-recommendation-1")).toContainText(
    /submit_attempt_decision_required: yes/i,
  );
  await expect(page.getByTestId("recommendation-submit-decision-review-recommendation-1")).toContainText(
    /blocked_attempt_decision_required_if_any_guard_blocks: yes/i,
  );
  await expect(page.getByTestId("recommendation-submit-decision-review-recommendation-1")).toContainText(
    /live_locked_attempt_record_required_if_live_mode: yes/i,
  );
  await expect(page.getByTestId("recommendation-submit-decision-review-recommendation-1")).toContainText(
    /dry_run_decision_referenceavailable from source=dry_run/i,
  );
  await expect(page.getByTestId("recommendation-submit-decision-review-recommendation-1")).toContainText(
    /live trading remains locked/i,
  );
  await expect(page.getByTestId("recommendation-submit-decision-review-recommendation-1")).toContainText(
    /workers cannot submit/i,
  );
  await expect(page.getByTestId("recommendation-operator-action-review-status-recommendation-1")).toContainText(
    /action review ready for future manual step/i,
  );
  await expect(page.getByTestId("recommendation-operator-action-review-summary-recommendation-1")).toContainText(
    /action review only, no order submitted/i,
  );
  await expect(page.getByTestId("recommendation-operator-action-review-recommendation-1")).toContainText(
    /future_action_namemanual_ibkr_paper_submit/i,
  );
  await expect(page.getByTestId("recommendation-operator-action-review-recommendation-1")).toContainText(
    /future_action_route\/broker\/orders/i,
  );
  await expect(page.getByTestId("recommendation-operator-action-review-recommendation-1")).toContainText(
    /action_available_nowfalse/i,
  );
  await expect(page.getByTestId("recommendation-operator-action-review-recommendation-1")).toContainText(
    /action_review_onlytrue/i,
  );
  await expect(page.getByTestId("recommendation-operator-action-review-recommendation-1")).toContainText(
    /decision_write_performed_nowfalse/i,
  );
  await expect(page.getByTestId("recommendation-operator-action-review-recommendation-1")).toContainText(
    /future_action_worker_allowed: false/i,
  );
  await expect(page.getByTestId("recommendation-operator-action-review-recommendation-1")).toContainText(
    /future_action_live_allowed: false/i,
  );
  await expect(page.getByTestId("recommendation-operator-action-review-recommendation-1")).toContainText(
    /submit_preflight_decision_required: yes/i,
  );
  await expect(page.getByTestId("recommendation-operator-action-review-recommendation-1")).toContainText(
    /submit_attempt_decision_required: yes/i,
  );
  await expect(page.getByTestId("recommendation-operator-action-review-recommendation-1")).toContainText(
    /no submit button is available here/i,
  );
  await expect(page.getByTestId("recommendation-operator-action-review-recommendation-1")).toContainText(
    /live trading remains locked/i,
  );
  await expect(page.getByTestId("recommendation-operator-action-review-recommendation-1")).toContainText(
    /workers cannot submit/i,
  );
  await expect(page.getByTestId("recommendation-final-guarded-submit-interaction-spec-status-recommendation-1")).toContainText(
    /interaction spec ready for future phase/i,
  );
  await expect(page.getByTestId("recommendation-final-guarded-submit-interaction-spec-summary-recommendation-1")).toContainText(
    /interaction spec only, no order submitted/i,
  );
  await expect(page.getByTestId("recommendation-final-guarded-submit-interaction-spec-recommendation-1")).toContainText(
    /final_guarded_submit_interaction_spec_statusinteraction_spec_ready_for_future_phase/i,
  );
  await expect(page.getByTestId("recommendation-final-guarded-submit-interaction-spec-recommendation-1")).toContainText(
    /future_interaction_namemanual_ibkr_paper_submit/i,
  );
  await expect(page.getByTestId("recommendation-final-guarded-submit-interaction-spec-recommendation-1")).toContainText(
    /future_interaction_route\/broker\/orders/i,
  );
  await expect(page.getByTestId("recommendation-final-guarded-submit-interaction-spec-recommendation-1")).toContainText(
    /action_available_nowfalse/i,
  );
  await expect(page.getByTestId("recommendation-final-guarded-submit-interaction-spec-recommendation-1")).toContainText(
    /interaction_spec_review_onlytrue/i,
  );
  await expect(page.getByTestId("recommendation-final-guarded-submit-interaction-spec-recommendation-1")).toContainText(
    /decision_write_performed_nowfalse/i,
  );
  await expect(page.getByTestId("recommendation-final-guarded-submit-interaction-spec-recommendation-1")).toContainText(
    /submitted_orderfalse/i,
  );
  await expect(page.getByTestId("recommendation-final-guarded-submit-interaction-spec-recommendation-1")).toContainText(
    /submit_time_checks_rerun_latertrue/i,
  );
  await expect(page.getByTestId("recommendation-final-guarded-submit-interaction-spec-recommendation-1")).toContainText(
    /future_interaction_route_guarded_broker_orders: yes/i,
  );
  await expect(page.getByTestId("recommendation-final-guarded-submit-interaction-spec-recommendation-1")).toContainText(
    /operator_action_review_ready: yes/i,
  );
  await expect(page.getByTestId("recommendation-final-guarded-submit-interaction-spec-recommendation-1")).toContainText(
    /submit_preflight_decision_required: yes/i,
  );
  await expect(page.getByTestId("recommendation-final-guarded-submit-interaction-spec-recommendation-1")).toContainText(
    /submit_attempt_decision_required: yes/i,
  );
  await expect(page.getByTestId("recommendation-final-guarded-submit-interaction-spec-recommendation-1")).toContainText(
    /submit-time checks would rerun later/i,
  );
  await expect(page.getByTestId("recommendation-final-guarded-submit-interaction-spec-recommendation-1")).toContainText(
    /live trading remains locked/i,
  );
  await expect(page.getByTestId("recommendation-final-guarded-submit-interaction-spec-recommendation-1")).toContainText(
    /workers cannot submit/i,
  );
  await expect(page.getByRole("button", { name: /submit order|execute|buy|sell|approve live|auto submit|trade now/i })).toHaveCount(0);
  await expect(page.getByRole("button", { name: /write decision|record decision/i })).toHaveCount(0);
});

test("In-Flight Adjustments recommendation preflight contract shows approval package required when approval package is not ready", async ({ page }) => {
  await mockInFlightReport(page);

  await page.unroute("**/paper/recommendations/**/broker-dry-run-preview*");
  await routeRecommendationDryRunPreviews(page, {
    "recommendation-1": {
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        recommendation_id: "recommendation-1",
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
        allowed_to_submit: false,
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
        next_required_action: "Review approval evidence before considering any future guarded manual paper submit handoff.",
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
        preflight_context: {
          cash_balance: null,
          buying_power: null,
          open_position_count: null,
          current_symbol_exposure: null,
          estimated_post_trade_symbol_exposure: null,
          current_total_exposure: null,
          estimated_post_trade_total_exposure: null,
          daily_pnl: null,
          daily_loss: null,
          risk_limit_snapshot: null,
        },
        paper_path_note: "Dry-run validates the IBKR paper submit path without placing an order.",
      }),
    },
  });

  await page.goto("/cockpit/in-flight-adjustments");
  await page.waitForLoadState("domcontentloaded");

  await page.getByTestId("recommendation-route-check-trigger-recommendation-1").click();
  await page.getByTestId("recommendation-dry-run-preview-trigger-recommendation-1").click();

  await expect(page.getByTestId("recommendation-submit-audit-package-status-recommendation-1")).toContainText(
    /package ready for future manual review/i,
  );
  await expect(page.getByTestId("recommendation-submit-approval-package-status-recommendation-1")).toContainText(
    /approval not available/i,
  );
  await expect(page.getByTestId("recommendation-submit-preflight-contract-status-recommendation-1")).toContainText(
    /approval package required first/i,
  );
  await expect(page.getByTestId("recommendation-submit-preflight-contract-recommendation-1")).toContainText(
    /operator confirmations required later/i,
  );
  await expect(page.getByTestId("recommendation-submit-preflight-contract-recommendation-1")).toContainText(
    /no submit control present: yes/i,
  );
  await expect(page.getByTestId("recommendation-submit-decision-review-status-recommendation-1")).toContainText(
    /approval package required first/i,
  );
  await expect(page.getByTestId("recommendation-submit-decision-review-recommendation-1")).toContainText(
    /the future decision trail depends on the approval package being ready first/i,
  );
  await expect(page.getByTestId("recommendation-operator-action-review-status-recommendation-1")).toContainText(
    /approval package required first/i,
  );
  await expect(page.getByTestId("recommendation-operator-action-review-recommendation-1")).toContainText(
    /final operator approval evidence is still missing/i,
  );
  await expect(page.getByRole("button", { name: /submit order|execute|buy|sell|approve live|auto submit|trade now/i })).toHaveCount(0);
});

test("In-Flight Adjustments recommendation handoff review shows readiness required when dry-run finished but readiness is not ready", async ({ page }) => {
  await mockInFlightReport(page);

  await page.unroute("**/paper/recommendations/**/broker-dry-run-preview*");
  await routeRecommendationDryRunPreviews(page, {
    "recommendation-1": {
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        recommendation_id: "recommendation-1",
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
        allowed_to_submit: false,
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
        next_required_action: "Review the readiness evidence before considering any future manual paper handoff.",
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
          decision_status: "unknown",
          submit_gate: "not_applied",
          advisory_count: 0,
          would_block_count: 0,
          blocking_count: 0,
          advisory_items: [],
          would_block_items: [],
          blocking_items: [],
        },
        preflight_context: {
          cash_balance: null,
          buying_power: null,
          open_position_count: null,
          current_symbol_exposure: null,
          estimated_post_trade_symbol_exposure: null,
          current_total_exposure: null,
          estimated_post_trade_total_exposure: null,
          daily_pnl: null,
          daily_loss: null,
          risk_limit_snapshot: null,
        },
        paper_path_note: "Dry-run validates the IBKR paper submit path without placing an order.",
      }),
    },
  });

  await page.goto("/cockpit/in-flight-adjustments");
  await page.waitForLoadState("domcontentloaded");

  await page.getByTestId("recommendation-route-check-trigger-recommendation-1").click();
  await page.getByTestId("recommendation-dry-run-preview-trigger-recommendation-1").click();

  await expect(page.getByTestId("recommendation-submit-handoff-status-recommendation-1")).toContainText(
    /readiness review required/i,
  );
  await expect(page.getByTestId("recommendation-submit-handoff-summary-recommendation-1")).toContainText(
    /handoff review only, no order submitted/i,
  );
  await expect(page.getByTestId("recommendation-submit-handoff-recommendation-1")).toContainText(
    /future manual submit route/i,
  );
  await expect(page.getByTestId("recommendation-submit-handoff-recommendation-1")).toContainText(
    /not available/i,
  );
  await expect(page.getByTestId("recommendation-submit-audit-package-status-recommendation-1")).toContainText(
    /readiness review required/i,
  );
  await expect(page.getByTestId("recommendation-submit-audit-package-summary-recommendation-1")).toContainText(
    /audit package only, no order submitted/i,
  );
  await expect(page.getByTestId("recommendation-submit-audit-package-recommendation-1")).toContainText(
    /resolved future route/i,
  );
  await expect(page.getByTestId("recommendation-submit-audit-package-recommendation-1")).toContainText(
    /not available/i,
  );
  await expect(page.getByTestId("recommendation-submit-approval-package-status-recommendation-1")).toContainText(
    /readiness review required/i,
  );
  await expect(page.getByTestId("recommendation-submit-approval-package-summary-recommendation-1")).toContainText(
    /approval package only, no order submitted/i,
  );
  await expect(page.getByTestId("recommendation-submit-preflight-contract-status-recommendation-1")).toContainText(
    /readiness review required/i,
  );
  await expect(page.getByTestId("recommendation-submit-preflight-contract-summary-recommendation-1")).toContainText(
    /preflight contract only, no order submitted/i,
  );
  await expect(page.getByRole("button", { name: /submit order|execute|buy|sell|approve live|auto submit|trade now/i })).toHaveCount(0);
});

test("In-Flight Adjustments recommendation audit package shows handoff required for advisory review", async ({ page }) => {
  await mockInFlightReport(page);

  await page.unroute("**/paper/recommendations/**/broker-dry-run-preview*");
  await routeRecommendationDryRunPreviews(page, {
    "recommendation-1": {
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        recommendation_id: "recommendation-1",
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
        next_required_action: "Review advisory dry-run evidence before considering any future manual paper handoff.",
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
        warnings: [
          {
            code: "stale_position_snapshot",
            message: "Advisory only: position snapshot is older than the current recommendation review time.",
          },
        ],
        preflight_decision: {
          decision_status: "advisory",
          submit_gate: "not_applied",
          advisory_count: 1,
          would_block_count: 0,
          blocking_count: 0,
          advisory_items: [
            {
              code: "stale_position_snapshot",
              message: "Advisory only: position snapshot is older than the current recommendation review time.",
              severity: "warning",
              source: "broker_preflight_advisory_service",
              enforcement_enabled: false,
              classification: "advisory",
            },
          ],
          would_block_items: [],
          blocking_items: [],
        },
        preflight_context: {
          cash_balance: null,
          buying_power: null,
          open_position_count: null,
          current_symbol_exposure: null,
          estimated_post_trade_symbol_exposure: null,
          current_total_exposure: null,
          estimated_post_trade_total_exposure: null,
          daily_pnl: null,
          daily_loss: null,
          risk_limit_snapshot: null,
        },
        paper_path_note: "Dry-run validates the IBKR paper submit path without placing an order.",
      }),
    },
  });

  await page.goto("/cockpit/in-flight-adjustments");
  await page.waitForLoadState("domcontentloaded");

  await page.getByTestId("recommendation-route-check-trigger-recommendation-1").click();
  await page.getByTestId("recommendation-dry-run-preview-trigger-recommendation-1").click();

  await expect(page.getByTestId("recommendation-submit-readiness-status-recommendation-1")).toContainText(
    /ready for future manual paper submit/i,
  );
  await expect(page.getByTestId("recommendation-submit-handoff-status-recommendation-1")).toContainText(
    /handoff review required/i,
  );
  await expect(page.getByTestId("recommendation-submit-audit-package-status-recommendation-1")).toContainText(
    /handoff review required/i,
  );
  await expect(page.getByTestId("recommendation-submit-audit-package-recommendation-1")).toContainText(
    /advisory only: position snapshot is older than the current recommendation review time/i,
  );
  await expect(page.getByTestId("recommendation-submit-audit-package-recommendation-1")).toContainText(
    /not available/i,
  );
  await expect(page.getByTestId("recommendation-submit-approval-package-status-recommendation-1")).toContainText(
    /audit package required first/i,
  );
  await expect(page.getByTestId("recommendation-submit-approval-package-recommendation-1")).toContainText(
    /audit_package_reference/i,
  );
  await expect(page.getByTestId("recommendation-submit-approval-package-recommendation-1")).toContainText(
    /submit-time decision logging would still be required/i,
  );
  await expect(page.getByTestId("recommendation-submit-preflight-contract-status-recommendation-1")).toContainText(
    /handoff review required/i,
  );
  await expect(page.getByTestId("recommendation-submit-preflight-contract-recommendation-1")).toContainText(
    /stale-data checks/i,
  );
  await expect(page.getByRole("button", { name: /submit order|execute|buy|sell|approve live|auto submit|trade now/i })).toHaveCount(0);
});

test("In-Flight Adjustments recommendation route-check renders blocked and missing-context states", async ({ page }) => {
  let dryRunPreviewCalls = 0;
  await mockInFlightReport(page, buildInFlightReport({
    items: [
      {
        id: "recommendation-live-blocked",
        item_type: "paper_recommendation",
        symbol: "MSFT",
        asset_id: null,
        asset_name: null,
        asset_detail_path: null,
        has_asset_context: false,
        status: "approved",
        opened_at: null,
        created_at: "2026-05-22T20:07:00+00:00",
        current_state_summary: "MSFT SELL qty=5 order_type=MARKET",
        attention_level: "high",
        adjustment_label: "review_required",
        reason: "Broker mode needs review before paper route-check can proceed.",
        evidence: ["broker_mode=live"],
        missing_data: [],
        recommended_review_action: "Review broker readiness and route-check posture.",
        is_actionable: false,
      },
      {
        id: "recommendation-missing-context",
        item_type: "paper_recommendation",
        symbol: "TSLA",
        asset_id: null,
        asset_name: null,
        asset_detail_path: null,
        has_asset_context: false,
        status: "draft",
        opened_at: null,
        created_at: "2026-05-22T20:08:00+00:00",
        current_state_summary: "TSLA BUY qty=2 order_type=MARKET",
        attention_level: "medium",
        adjustment_label: "missing_context",
        reason: "Recommendation still needs operator approval.",
        evidence: ["recommendation_status=draft"],
        missing_data: ["operator approval is required before manual IBKR paper submit"],
        recommended_review_action: "Complete operator approval before paper route review.",
        is_actionable: false,
      },
    ],
    summary: {
      headline: "Read-only in-flight paper adjustments watchlist for operator review.",
      total_items: 2,
      open_positions: 0,
      open_orders: 0,
      active_recommendations: 2,
      watch_only: 0,
      review_required: 1,
      high_attention: 1,
    },
  }));

  await page.unroute("**/paper/recommendations/**/serious-paper-route-check*");
  await routeRecommendationRouteChecks(page, {
    "recommendation-live-blocked": {
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        recommendation_id: "recommendation-live-blocked",
        recommendation_status: "approved",
        ticker: "MSFT",
        side: "SELL",
        quantity: 5,
        order_type: "MARKET",
        limit_price: null,
        estimated_notional: 500,
        risk_score: 0.44,
        route_check_status: "blocked",
        resolved_route: null,
        resolved_execution_source: null,
        execution_source: "recommendation_route_check",
        serious_paper_source: "ibkr_paper",
        is_canonical_paper: false,
        broker_account_mode: "live",
        live_state: "ibkr_live_locked",
        would_block: true,
        blocked_reason: "Serious paper routing is blocked because broker mode is coherently live and live submit remains locked.",
        missing_data: [],
        next_required_action: "Restore a coherent paper broker/account mode before using the canonical serious-paper path.",
        is_submit: false,
        workers_allowed_to_submit: false,
        live_trading_enabled: false,
        canonical_paper_route: "/broker/orders",
        broker_mode: { broker: "ibkr", mode: "live", live_execution_enabled: true, paper_trading_enabled: false },
      }),
    },
    "recommendation-missing-context": {
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        recommendation_id: "recommendation-missing-context",
        recommendation_status: "draft",
        ticker: "TSLA",
        side: "BUY",
        quantity: 2,
        order_type: "MARKET",
        limit_price: null,
        estimated_notional: 200,
        risk_score: 0.21,
        route_check_status: "missing_context",
        resolved_route: null,
        resolved_execution_source: null,
        execution_source: "recommendation_route_check",
        serious_paper_source: "ibkr_paper",
        is_canonical_paper: false,
        broker_account_mode: "paper",
        live_state: "ibkr_live_locked",
        would_block: true,
        blocked_reason: null,
        missing_data: ["operator approval is required before manual IBKR paper submit"],
        next_required_action: "Complete the missing recommendation context and operator approval before attempting manual IBKR paper submit.",
        is_submit: false,
        workers_allowed_to_submit: false,
        live_trading_enabled: false,
        canonical_paper_route: "/broker/orders",
        broker_mode: { broker: "ibkr", mode: "paper", live_execution_enabled: false, paper_trading_enabled: true },
      }),
    },
  });
  await page.unroute("**/paper/recommendations/**/broker-dry-run-preview*");
  await page.route("**/paper/recommendations/**/broker-dry-run-preview*", async (route) => {
    dryRunPreviewCalls += 1;
    await route.fulfill({
      status: 500,
      contentType: "text/plain",
      body: "dry-run preview should not have been called",
    });
  });

  await page.goto("/cockpit/in-flight-adjustments");
  await page.waitForLoadState("domcontentloaded");

  await page.getByTestId("recommendation-route-check-trigger-recommendation-live-blocked").click();
  await expect(page.getByTestId("recommendation-route-check-status-recommendation-live-blocked")).toContainText(/blocked/i);
  await expect(page.getByTestId("recommendation-route-check-panel-recommendation-live-blocked")).toContainText(/live submit remains locked/i);
  await expect(page.getByTestId("recommendation-submit-readiness-status-recommendation-live-blocked")).toContainText(/blocked/i);
  await expect(page.getByTestId("recommendation-submit-handoff-status-recommendation-live-blocked")).toContainText(/blocked/i);
  await expect(page.getByTestId("recommendation-submit-audit-package-status-recommendation-live-blocked")).toContainText(/blocked/i);
  await expect(page.getByTestId("recommendation-submit-approval-package-status-recommendation-live-blocked")).toContainText(/blocked/i);
  await expect(page.getByTestId("recommendation-submit-preflight-contract-status-recommendation-live-blocked")).toContainText(/blocked/i);
  await expect(page.getByTestId("recommendation-submit-decision-review-status-recommendation-live-blocked")).toContainText(/blocked/i);
  await expect(page.getByTestId("recommendation-operator-action-review-status-recommendation-live-blocked")).toContainText(/blocked/i);
  await expect(page.getByTestId("recommendation-final-guarded-submit-interaction-spec-status-recommendation-live-blocked")).toContainText(/blocked/i);
  await expect(page.getByRole("link", { name: /open guarded broker dry-run/i })).toHaveCount(0);

  await page.getByTestId("recommendation-route-check-trigger-recommendation-missing-context").click();
  await expect(page.getByTestId("recommendation-route-check-status-recommendation-missing-context")).toContainText(/missing context/i);
  await expect(page.getByTestId("recommendation-route-check-panel-recommendation-missing-context")).toContainText(/operator approval is required/i);
  await expect(page.getByTestId("recommendation-submit-readiness-status-recommendation-missing-context")).toContainText(
    /missing context/i,
  );
  await expect(page.getByTestId("recommendation-submit-handoff-status-recommendation-missing-context")).toContainText(
    /missing context/i,
  );
  await expect(page.getByTestId("recommendation-submit-audit-package-status-recommendation-missing-context")).toContainText(
    /missing context/i,
  );
  await expect(page.getByTestId("recommendation-submit-approval-package-status-recommendation-missing-context")).toContainText(
    /missing context/i,
  );
  await expect(page.getByTestId("recommendation-submit-preflight-contract-status-recommendation-missing-context")).toContainText(
    /missing context/i,
  );
  await expect(page.getByTestId("recommendation-submit-decision-review-status-recommendation-missing-context")).toContainText(
    /missing context/i,
  );
  await expect(page.getByTestId("recommendation-operator-action-review-status-recommendation-missing-context")).toContainText(
    /missing context/i,
  );
  await expect(page.getByTestId("recommendation-final-guarded-submit-interaction-spec-status-recommendation-missing-context")).toContainText(
    /missing context/i,
  );
  expect(dryRunPreviewCalls).toBe(0);
});

test("In-Flight Adjustments recommendation route-check shows fetch error safely", async ({ page }) => {
  await mockInFlightReport(page);

  await page.unroute("**/paper/recommendations/**/serious-paper-route-check*");
  await routeRecommendationRouteChecks(page, {
    "recommendation-1": {
      status: 503,
      contentType: "text/plain",
      body: "route-check unavailable",
    },
  });

  await page.goto("/cockpit/in-flight-adjustments");
  await page.waitForLoadState("domcontentloaded");

  await page.getByTestId("recommendation-route-check-trigger-recommendation-1").click();
  await expect(page.getByTestId("recommendation-route-check-error-recommendation-1")).toContainText(
    /route-check unavailable/i,
  );
});

test("In-Flight Adjustments recommendation dry-run preview shows fetch error safely", async ({ page }) => {
  await mockInFlightReport(page);

  await page.unroute("**/paper/recommendations/**/broker-dry-run-preview*");
  await routeRecommendationDryRunPreviews(page, {
    "recommendation-1": {
      status: 503,
      contentType: "text/plain",
      body: "dry-run preview unavailable",
    },
  });

  await page.goto("/cockpit/in-flight-adjustments");
  await page.waitForLoadState("domcontentloaded");

  await page.getByTestId("recommendation-route-check-trigger-recommendation-1").click();
  await page.getByTestId("recommendation-dry-run-preview-trigger-recommendation-1").click();
  await expect(page.getByTestId("recommendation-dry-run-preview-error-recommendation-1")).toContainText(
    /dry-run preview unavailable/i,
  );
});

test("cockpit/in-flight-adjustments expanded recommendation route-check has no horizontal overflow at 390px", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockInFlightReport(page);

  await page.goto("/cockpit/in-flight-adjustments");
  await page.waitForLoadState("domcontentloaded");
  await page.getByTestId("recommendation-route-check-trigger-recommendation-1").click();
  await page.getByTestId("recommendation-dry-run-preview-trigger-recommendation-1").click();
  await expect(page.getByTestId("recommendation-route-check-summary-recommendation-1")).toBeVisible();
  await expect(page.getByTestId("recommendation-future-manual-submit-design-review-recommendation-1")).toContainText(
    /future manual submit design review/i,
  );
  await expect(page.getByTestId("recommendation-future-manual-submit-design-review-recommendation-1")).toContainText(
    /no submit button available/i,
  );
  await expect(page.getByTestId("recommendation-submit-decision-review-recommendation-1")).toContainText(
    /guarded operator submit-decision review/i,
  );
  await expect(page.getByTestId("recommendation-submit-decision-review-recommendation-1")).toContainText(
    /no decision written/i,
  );
  await expect(page.getByTestId("recommendation-operator-action-review-recommendation-1")).toContainText(
    /guarded operator action review/i,
  );
  await expect(page.getByTestId("recommendation-operator-action-review-recommendation-1")).toContainText(
    /future action is not enabled in this phase/i,
  );
  await expect(page.getByTestId("recommendation-final-guarded-submit-interaction-spec-recommendation-1")).toContainText(
    /final guarded operator submit interaction spec/i,
  );
  await expect(page.getByTestId("recommendation-final-guarded-submit-interaction-spec-recommendation-1")).toContainText(
    /submit-time checks would rerun later/i,
  );

  const overflow = await page.evaluate(() => ({
    bodyScrollWidth: document.body.scrollWidth,
    docScrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth,
  }));

  expect(
    Math.max(overflow.bodyScrollWidth, overflow.docScrollWidth) <= overflow.innerWidth,
    `Horizontal overflow detected: body=${overflow.bodyScrollWidth}, doc=${overflow.docScrollWidth}, inner=${overflow.innerWidth}`,
  ).toBe(true);
});

test("In-Flight Adjustments empty state renders safely", async ({ page }) => {
  await mockInFlightReport(
    page,
    buildInFlightReport({
      summary: {
        headline: "Read-only in-flight paper adjustments watchlist for operator review.",
        total_items: 0,
        open_positions: 0,
        open_orders: 0,
        active_recommendations: 0,
        watch_only: 0,
        review_required: 0,
        high_attention: 0,
      },
      items: [],
      monitor_notes: [],
      risk_notes: ["No explicit rejected risk decisions were found in the recent dataset."],
      limitations: ["No in-flight paper items were found in persisted positions, orders, or recommendations."],
    }),
  );

  await page.goto("/cockpit/in-flight-adjustments");
  await page.waitForLoadState("domcontentloaded");

  await expect(page.getByText(/no in-flight paper items yet/i)).toBeVisible();
});

test("In-Flight Adjustments shows safe error state", async ({ page }) => {
  await page.route("**/cockpit/in-flight-adjustments*", async (route) => {
    if (!isApiRequest(route.request().url(), "/cockpit/in-flight-adjustments")) {
      await route.continue();
      return;
    }

    await route.fulfill({
      status: 500,
      contentType: "text/plain",
      body: "backend unavailable",
    });
  });

  await page.goto("/cockpit/in-flight-adjustments");
  await page.waitForLoadState("domcontentloaded");

  await expect(page.getByText(/in-flight adjustments unavailable/i)).toBeVisible();
  await expect(page.getByText(/backend unavailable/i)).toBeVisible();
});

test("cockpit/in-flight-adjustments has no horizontal overflow at 390px", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockInFlightReport(page);

  await page.goto("/cockpit/in-flight-adjustments");
  await page.waitForLoadState("domcontentloaded");

  const overflow = await page.evaluate(() => ({
    bodyScrollWidth: document.body.scrollWidth,
    docScrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth,
  }));

  expect(
    Math.max(overflow.bodyScrollWidth, overflow.docScrollWidth) <= overflow.innerWidth,
    `Horizontal overflow detected: body=${overflow.bodyScrollWidth}, doc=${overflow.docScrollWidth}, inner=${overflow.innerWidth}`,
  ).toBe(true);
});
