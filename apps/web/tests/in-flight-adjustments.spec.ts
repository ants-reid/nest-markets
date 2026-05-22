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

    if (requestUrl.origin !== API_ORIGIN) {
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
    if (!isApiRequest(route.request().url(), "/cockpit/in-flight-adjustments")) {
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
});

test("In-Flight Adjustments recommendation route-check renders blocked and missing-context states", async ({ page }) => {
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

  await page.goto("/cockpit/in-flight-adjustments");
  await page.waitForLoadState("domcontentloaded");

  await page.getByTestId("recommendation-route-check-trigger-recommendation-live-blocked").click();
  await expect(page.getByTestId("recommendation-route-check-status-recommendation-live-blocked")).toContainText(/blocked/i);
  await expect(page.getByTestId("recommendation-route-check-panel-recommendation-live-blocked")).toContainText(/live submit remains locked/i);
  await expect(page.getByRole("link", { name: /open guarded broker dry-run/i })).toHaveCount(0);

  await page.getByTestId("recommendation-route-check-trigger-recommendation-missing-context").click();
  await expect(page.getByTestId("recommendation-route-check-status-recommendation-missing-context")).toContainText(/missing context/i);
  await expect(page.getByTestId("recommendation-route-check-panel-recommendation-missing-context")).toContainText(/operator approval is required/i);
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

test("cockpit/in-flight-adjustments expanded recommendation route-check has no horizontal overflow at 390px", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockInFlightReport(page);

  await page.goto("/cockpit/in-flight-adjustments");
  await page.waitForLoadState("domcontentloaded");
  await page.getByTestId("recommendation-route-check-trigger-recommendation-1").click();
  await expect(page.getByTestId("recommendation-route-check-summary-recommendation-1")).toBeVisible();

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
