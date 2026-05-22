import { expect, test } from "@playwright/test";

function buildEodReport(overrides: Record<string, unknown> = {}) {
  return {
    report_date: "2026-05-22",
    generated_at: "2026-05-22T20:15:00+00:00",
    mode: "paper",
    summary: {
      headline: "Paper-mode end-of-day recap for operator review.",
      opened_today: 2,
      closed_today: 1,
      open_positions_now: 1,
      alerts_needing_attention: 1,
      lessons_available: 1,
    },
    paper_activity: {
      opened_today: 2,
      closed_today: 1,
      current_open_positions: 1,
    },
    pnl: {
      realized_day: 12.5,
      unrealized_snapshot: 4.25,
      realized_basis: "closed_positions_today",
      unrealized_basis: "open_positions_snapshot",
    },
    open_positions: {
      count: 1,
      items: [
        {
          asset_symbol: "AAPL",
          side: "long",
          qty: 1,
          opened_at: "2026-05-22T18:00:00+00:00",
          unrealized_pnl: 4.25,
        },
      ],
    },
    closed_positions: {
      count: 1,
      wins: 1,
      losses: 0,
      flat: 0,
      unknown: 0,
      best_trade: {
        asset_symbol: "AAPL",
        side: "long",
        opened_at: "2026-05-22T15:00:00+00:00",
        closed_at: "2026-05-22T17:00:00+00:00",
        realized_pnl: 12.5,
        close_reason: "target_hit",
      },
      worst_trade: {
        asset_symbol: "AAPL",
        side: "long",
        opened_at: "2026-05-22T15:00:00+00:00",
        closed_at: "2026-05-22T17:00:00+00:00",
        realized_pnl: 12.5,
        close_reason: "target_hit",
      },
      items: [],
    },
    alerts_or_incidents: [
      {
        severity: "critical",
        code: "monitor.feed_down",
        title: "Feed degraded",
        source: "monitor",
        created_at: "2026-05-22T18:30:00+00:00",
        detail: "Primary feed stalled.",
      },
    ],
    monitor_notes: [
      {
        title: "Feed degraded",
        detail: "Primary feed stalled.",
        severity: "critical",
        created_at: "2026-05-22T18:30:00+00:00",
      },
    ],
    lessons: [
      {
        title: "Directional accuracy",
        detail: "1/1 closed outcomes matched the predicted direction today.",
        evidence_count: 1,
      },
    ],
    recommended_actions: [
      "Review the highest-severity incidents in Cockpit Notifications before the next paper session.",
    ],
    limitations: [],
    ...overrides,
  };
}

async function mockEodReport(page: import("@playwright/test").Page, payload = buildEodReport()) {
  await page.addInitScript((mockPayload) => {
    const originalFetch = window.fetch.bind(window);
    window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string"
        ? input
        : input instanceof Request
          ? input.url
          : input.toString();

      if (url.includes("/cockpit/eod-report")) {
        return new Response(JSON.stringify(mockPayload), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }

      return originalFetch(input, init);
    };
  }, payload);
}

test("End-of-Day report renders summary cards and paper-only wording", async ({ page }) => {
  await mockEodReport(page);

  await page.goto("/cockpit/eod-report");
  await page.waitForLoadState("domcontentloaded");

  await expect(page.getByTestId("cockpit-eod-report-page")).toBeVisible();
  await expect(page.getByRole("heading", { name: /end-of-day report/i })).toBeVisible();
  await expect(page.getByTestId("cockpit-eod-paper-mode")).toContainText(/paper mode only/i);
  await expect(page.getByTestId("cockpit-eod-summary-cards")).toContainText(/paper trades opened/i);
  await expect(page.getByTestId("cockpit-eod-summary-cards")).toContainText(/needs attention/i);
  await expect(page.getByText(/review execution/i)).toBeVisible();
  await expect(page.getByRole("button", { name: /place order|close position|submit/i })).toHaveCount(0);
});

test("EOD report empty state renders safely", async ({ page }) => {
  await mockEodReport(page, buildEodReport({
    summary: {
      headline: "Paper-mode end-of-day recap for operator review.",
      opened_today: 0,
      closed_today: 0,
      open_positions_now: 0,
      alerts_needing_attention: 0,
      lessons_available: 0,
    },
    paper_activity: {
      opened_today: 0,
      closed_today: 0,
      current_open_positions: 0,
    },
    pnl: {
      realized_day: 0,
      unrealized_snapshot: 0,
      realized_basis: "closed_positions_today",
      unrealized_basis: "open_positions_snapshot",
    },
    open_positions: { count: 0, items: [] },
    closed_positions: {
      count: 0,
      wins: 0,
      losses: 0,
      flat: 0,
      unknown: 0,
      best_trade: null,
      worst_trade: null,
      items: [],
    },
    alerts_or_incidents: [],
    monitor_notes: [],
    lessons: [],
    recommended_actions: ["No urgent EOD issues detected."],
    limitations: ["No closed signal outcomes were available for today, so lessons are limited."],
  }));

  await page.goto("/cockpit/eod-report");
  await page.waitForLoadState("domcontentloaded");

  await expect(page.getByText(/no paper activity recorded yet/i)).toBeVisible();
  await expect(page.getByText(/counts remain at zero/i)).toBeVisible();
});

test("EOD report shows a safe error state", async ({ page }) => {
  await page.addInitScript(() => {
    const originalFetch = window.fetch.bind(window);
    window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string"
        ? input
        : input instanceof Request
          ? input.url
          : input.toString();

      if (url.includes("/cockpit/eod-report")) {
        return new Response("backend unavailable", {
          status: 500,
          headers: { "Content-Type": "text/plain" },
        });
      }

      return originalFetch(input, init);
    };
  });

  await page.goto("/cockpit/eod-report");
  await page.waitForLoadState("domcontentloaded");

  await expect(page.getByText(/eod report unavailable/i)).toBeVisible();
  await expect(page.getByText(/backend unavailable/i)).toBeVisible();
});

test("cockpit/eod-report has no horizontal overflow at 390px", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockEodReport(page);

  await page.goto("/cockpit/eod-report");
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