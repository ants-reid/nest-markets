import { expect, test } from "@playwright/test";

function buildDailyScoreboard(overrides: Record<string, unknown> = {}) {
  return {
    report_date: "2026-05-22",
    generated_at: "2026-05-22T21:00:00+00:00",
    mode: "paper",
    summary: {
      headline: "Read-only daily paper-trading scoreboard for operator review.",
      day_status: "green_day",
      trades_opened_today: 2,
      trades_closed_today: 1,
      open_positions_now: 1,
    },
    performance: {
      realized_pnl_today: 12.5,
      unrealized_pnl_snapshot: 3.0,
      net_pnl_today: 15.5,
      win_count: 1,
      loss_count: 0,
      flat_count: 0,
      unknown_count: 0,
    },
    activity: {
      trades_opened_today: 2,
      trades_closed_today: 1,
      open_positions_now: 1,
    },
    open_positions: {
      count: 1,
      long_count: 1,
      short_count: 0,
    },
    closed_positions: {
      count: 1,
      wins: 1,
      losses: 0,
      flat: 0,
      unknown: 0,
    },
    top_contributors: {
      count: 2,
      items: [
        {
          symbol: "AAPL",
          realized_pnl: 12.5,
          contribution_label: "positive",
          evidence: ["realized_pnl_sum_by_symbol"],
        },
        {
          symbol: "MSFT",
          realized_pnl: -2.0,
          contribution_label: "negative",
          evidence: ["realized_pnl_sum_by_symbol"],
        },
      ],
    },
    risk_and_monitor_notes: [
      {
        label: "monitor_attention",
        title: "Feed degraded",
        detail: "Primary feed stalled.",
        severity: "critical",
        created_at: "2026-05-22T20:30:00+00:00",
      },
    ],
    review_priorities: [
      "Review monitor/feed incidents first before interpreting scoreboard performance.",
      "Review top positive and negative contributors to compare setup quality and exit behavior.",
    ],
    limitations: [],
    ...overrides,
  };
}

async function mockDailyScoreboard(
  page: import("@playwright/test").Page,
  payload = buildDailyScoreboard(),
) {
  await page.addInitScript((mockPayload) => {
    const originalFetch = window.fetch.bind(window);
    window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string"
        ? input
        : input instanceof Request
          ? input.url
          : input.toString();

      if (url.includes("/cockpit/daily-scoreboard")) {
        return new Response(JSON.stringify(mockPayload), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }

      return originalFetch(input, init);
    };
  }, payload);
}

test("Daily scoreboard route renders summary cards and paper read-only wording", async ({ page }) => {
  await mockDailyScoreboard(page);

  await page.goto("/cockpit/daily-scoreboard");
  await page.waitForLoadState("domcontentloaded");

  await expect(page.getByTestId("cockpit-daily-scoreboard-page")).toBeVisible();
  await expect(page.getByRole("heading", { name: /daily scoreboard/i })).toBeVisible();
  await expect(page.getByTestId("cockpit-daily-paper-mode")).toContainText(/paper mode only/i);
  await expect(page.getByTestId("cockpit-daily-summary-cards")).toContainText(/trades opened today/i);
  await expect(page.getByTestId("cockpit-daily-top-contributors")).toContainText(/AAPL/);
  await expect(page.getByTestId("cockpit-daily-notes-panels")).toContainText(/feed degraded/i);
  await expect(page.getByRole("button", { name: /place|close|modify|approve|execute|submit/i })).toHaveCount(0);
});

test("Daily scoreboard empty state renders safely", async ({ page }) => {
  await mockDailyScoreboard(
    page,
    buildDailyScoreboard({
      summary: {
        headline: "Read-only daily paper-trading scoreboard for operator review.",
        day_status: "unknown",
        trades_opened_today: 0,
        trades_closed_today: 0,
        open_positions_now: 0,
      },
      performance: {
        realized_pnl_today: 0,
        unrealized_pnl_snapshot: 0,
        net_pnl_today: 0,
        win_count: 0,
        loss_count: 0,
        flat_count: 0,
        unknown_count: 0,
      },
      activity: {
        trades_opened_today: 0,
        trades_closed_today: 0,
        open_positions_now: 0,
      },
      open_positions: {
        count: 0,
        long_count: 0,
        short_count: 0,
      },
      closed_positions: {
        count: 0,
        wins: 0,
        losses: 0,
        flat: 0,
        unknown: 0,
      },
      top_contributors: {
        count: 0,
        items: [],
      },
      risk_and_monitor_notes: [],
      review_priorities: ["No urgent scoreboard review priorities were detected; maintain current paper safeguards."],
      limitations: ["No closed paper positions were found for today."],
    }),
  );

  await page.goto("/cockpit/daily-scoreboard");
  await page.waitForLoadState("domcontentloaded");

  await expect(page.getByText(/no paper scoreboard activity yet/i)).toBeVisible();
});

test("Daily scoreboard unknown metrics render safely", async ({ page }) => {
  await mockDailyScoreboard(
    page,
    buildDailyScoreboard({
      summary: {
        headline: "Read-only daily paper-trading scoreboard for operator review.",
        day_status: "data_incomplete",
        trades_opened_today: 1,
        trades_closed_today: 1,
        open_positions_now: 1,
      },
      performance: {
        realized_pnl_today: null,
        unrealized_pnl_snapshot: null,
        net_pnl_today: null,
        win_count: null,
        loss_count: null,
        flat_count: null,
        unknown_count: 1,
      },
      top_contributors: {
        count: 1,
        items: [
          {
            symbol: "AAPL",
            realized_pnl: null,
            contribution_label: "unknown",
            evidence: ["realized_pnl_missing"],
          },
        ],
      },
      limitations: ["Realized paper P&L is incomplete because one or more closed positions lack realized_pnl."],
    }),
  );

  await page.goto("/cockpit/daily-scoreboard");
  await page.waitForLoadState("domcontentloaded");

  await expect(page.getByText(/unknown/i).first()).toBeVisible();
  await expect(page.getByText(/realized paper p&l is incomplete/i)).toBeVisible();
});

test("Daily scoreboard shows safe error state", async ({ page }) => {
  await page.addInitScript(() => {
    const originalFetch = window.fetch.bind(window);
    window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string"
        ? input
        : input instanceof Request
          ? input.url
          : input.toString();

      if (url.includes("/cockpit/daily-scoreboard")) {
        return new Response("backend unavailable", {
          status: 500,
          headers: { "Content-Type": "text/plain" },
        });
      }

      return originalFetch(input, init);
    };
  });

  await page.goto("/cockpit/daily-scoreboard");
  await page.waitForLoadState("domcontentloaded");

  await expect(page.getByText(/daily scoreboard unavailable/i)).toBeVisible();
  await expect(page.getByText(/backend unavailable/i)).toBeVisible();
});

test("cockpit/daily-scoreboard has no horizontal overflow at 390px", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockDailyScoreboard(page);

  await page.goto("/cockpit/daily-scoreboard");
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
