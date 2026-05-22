import { expect, test } from "@playwright/test";

function buildTradeCloseReport(overrides: Record<string, unknown> = {}) {
  return {
    generated_at: "2026-05-22T20:15:00+00:00",
    mode: "paper",
    summary: {
      headline: "Read-only close reasoning for recently closed paper trades.",
      total_closed_trades: 2,
      known_close_labels: 2,
      unknown_close_labels: 0,
      profitable_trades: 1,
      losing_trades: 1,
      flat_trades: 0,
      setup_matched: 1,
      setup_mismatched: 1,
      setup_unknown: 0,
    },
    explanations: [
      {
        id: "position-1",
        paper_order_id: "order-1",
        position_id: "position-1",
        symbol: "AAPL",
        opened_at: "2026-05-22T18:00:00+00:00",
        closed_at: "2026-05-22T19:10:00+00:00",
        status: "closed",
        close_label: "target_hit",
        close_reason: "target_hit",
        result_summary: "Closed near target with positive realized P&L.",
        realized_pnl: 12.5,
        outcome_match: "matched",
        evidence: ["close_reason=target_hit", "realized_pnl=12.5"],
        missing_data: [],
        learning_note: "Target exits continue to align with signal direction.",
        is_actionable: false,
      },
      {
        id: "position-2",
        paper_order_id: "order-2",
        position_id: "position-2",
        symbol: "MSFT",
        opened_at: "2026-05-22T17:00:00+00:00",
        closed_at: "2026-05-22T19:20:00+00:00",
        status: "closed",
        close_label: "stop_hit",
        close_reason: "stop_hit",
        result_summary: "Closed near stop with negative realized P&L.",
        realized_pnl: -4.25,
        outcome_match: "mismatched",
        evidence: ["close_reason=stop_hit", "realized_pnl=-4.25"],
        missing_data: ["signal_outcome unavailable"],
        learning_note: "Review stop placement consistency for similar entries.",
        is_actionable: false,
      },
    ],
    limitations: [],
    recommended_review_actions: [
      "Review unknown or conflicting close labels before the next paper session.",
    ],
    ...overrides,
  };
}

async function mockTradeCloseReport(
  page: import("@playwright/test").Page,
  payload = buildTradeCloseReport(),
) {
  await page.addInitScript((mockPayload) => {
    const originalFetch = window.fetch.bind(window);
    window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string"
        ? input
        : input instanceof Request
          ? input.url
          : input.toString();

      if (url.includes("/cockpit/trade-close-explanations")) {
        return new Response(JSON.stringify(mockPayload), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }

      return originalFetch(input, init);
    };
  }, payload);
}

test("Trade-close explanations route renders summary and paper read-only wording", async ({ page }) => {
  await mockTradeCloseReport(page);

  await page.goto("/cockpit/trade-close-explanations");
  await page.waitForLoadState("domcontentloaded");

  await expect(page.getByTestId("cockpit-trade-close-explanations-page")).toBeVisible();
  await expect(page.getByRole("heading", { name: /trade-close explanations/i })).toBeVisible();
  await expect(page.getByTestId("cockpit-trade-close-paper-mode")).toContainText(/paper mode only/i);
  await expect(page.getByTestId("cockpit-trade-close-summary-cards")).toContainText(/closed trades/i);
  await expect(page.getByTestId("cockpit-trade-close-explanation-list")).toContainText(/AAPL/);
  await expect(page.getByRole("button", { name: /place|close|modify|execute|submit/i })).toHaveCount(0);
});

test("Trade-close explanations empty state renders safely", async ({ page }) => {
  await mockTradeCloseReport(
    page,
    buildTradeCloseReport({
      summary: {
        headline: "Read-only close reasoning for recently closed paper trades.",
        total_closed_trades: 0,
        known_close_labels: 0,
        unknown_close_labels: 0,
        profitable_trades: 0,
        losing_trades: 0,
        flat_trades: 0,
        setup_matched: 0,
        setup_mismatched: 0,
        setup_unknown: 0,
      },
      explanations: [],
      limitations: ["No recently closed paper trades were found in persisted data."],
      recommended_review_actions: ["No immediate review action is required."],
    }),
  );

  await page.goto("/cockpit/trade-close-explanations");
  await page.waitForLoadState("domcontentloaded");

  await expect(page.getByText(/no closed paper trades yet/i)).toBeVisible();
});

test("Trade-close explanations shows safe error state", async ({ page }) => {
  await page.addInitScript(() => {
    const originalFetch = window.fetch.bind(window);
    window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string"
        ? input
        : input instanceof Request
          ? input.url
          : input.toString();

      if (url.includes("/cockpit/trade-close-explanations")) {
        return new Response("backend unavailable", {
          status: 500,
          headers: { "Content-Type": "text/plain" },
        });
      }

      return originalFetch(input, init);
    };
  });

  await page.goto("/cockpit/trade-close-explanations");
  await page.waitForLoadState("domcontentloaded");

  await expect(page.getByText(/trade-close explanations unavailable/i)).toBeVisible();
  await expect(page.getByText(/backend unavailable/i)).toBeVisible();
});

test("cockpit/trade-close-explanations has no horizontal overflow at 390px", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockTradeCloseReport(page);

  await page.goto("/cockpit/trade-close-explanations");
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
