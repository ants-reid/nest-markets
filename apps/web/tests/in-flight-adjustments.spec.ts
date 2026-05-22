import { expect, test } from "@playwright/test";

function buildInFlightReport(overrides: Record<string, unknown> = {}) {
  return {
    generated_at: "2026-05-22T20:15:00+00:00",
    mode: "paper",
    summary: {
      headline: "Read-only in-flight paper adjustments watchlist for operator review.",
      total_items: 2,
      open_positions: 1,
      open_orders: 1,
      active_recommendations: 0,
      watch_only: 0,
      review_required: 1,
      high_attention: 1,
    },
    items: [
      {
        id: "position-1",
        item_type: "paper_position",
        symbol: "AAPL",
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
  await page.addInitScript((mockPayload) => {
    const originalFetch = window.fetch.bind(window);
    window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string"
        ? input
        : input instanceof Request
          ? input.url
          : input.toString();

      if (url.includes("/cockpit/in-flight-adjustments")) {
        return new Response(JSON.stringify(mockPayload), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }

      return originalFetch(input, init);
    };
  }, payload);
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
  await expect(page.getByRole("button", { name: /place|close|modify|execute/i })).toHaveCount(0);
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
  await page.addInitScript(() => {
    const originalFetch = window.fetch.bind(window);
    window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string"
        ? input
        : input instanceof Request
          ? input.url
          : input.toString();

      if (url.includes("/cockpit/in-flight-adjustments")) {
        return new Response("backend unavailable", {
          status: 500,
          headers: { "Content-Type": "text/plain" },
        });
      }

      return originalFetch(input, init);
    };
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
