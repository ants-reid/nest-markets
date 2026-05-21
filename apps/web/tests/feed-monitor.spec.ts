import { expect, test } from "@playwright/test";

const FEED_MONITOR_PATH = "/monitor/feeds";

function isFeedMonitorApiRequest(request: import("@playwright/test").Request) {
  const url = new URL(request.url());
  return !request.isNavigationRequest() && url.pathname === FEED_MONITOR_PATH;
}

function feedMonitorApiUrl() {
  return `**${FEED_MONITOR_PATH}`;
}

function buildFeedMonitorPayload(overrides?: Partial<Record<string, unknown>>) {
  return {
    overall: "degraded",
    advisory: "Investigate non-OK feeds before enabling automation.",
    as_of_utc: "2026-05-20T08:15:00.000Z",
    summary: {
      total: 3,
      configured: 2,
      runtime_reachable: 1,
      issue_count: 2,
      by_status: { ok: 1, degraded: 1, unknown: 1 },
      by_category: { feeds_in: 1, feeds_out: 1, runtime: 1 },
    },
    next_actions: [
      "Review polygon websocket entitlement posture.",
      "Confirm IBKR gateway runtime before paper automation.",
    ],
    rows: [
      {
        id: "feed-in.polygon.websocket",
        name: "Polygon websocket",
        category: "feeds_in",
        kind: "provider",
        status: "degraded",
        configured: true,
        runtime_reachable: true,
        detail: "Heartbeat latency above monitor threshold.",
        action: "Review provider backlog before market open.",
        checked_at: "2026-05-20T08:14:30.000Z",
        latency_ms: 125.4,
        target: "wss://socket.polygon.io/stocks",
        tags: ["market-data"],
        extra: {},
      },
      {
        id: "feed-out.sec.reference",
        name: "SEC reference API",
        category: "feeds_out",
        kind: "provider",
        status: "ok",
        configured: true,
        runtime_reachable: true,
        detail: "Reference pulls healthy.",
        action: "No operator action required.",
        checked_at: "2026-05-20T08:14:10.000Z",
        latency_ms: 42.1,
        target: "https://data.sec.gov/api/xbrl/companyfacts",
        tags: ["reference"],
        extra: {},
      },
      {
        id: "runtime.ibkr_gateway",
        name: "IBKR gateway runtime",
        category: "runtime",
        kind: "runtime",
        status: "unknown",
        configured: null,
        runtime_reachable: null,
        detail: "Gateway not yet probed in this environment.",
        action: "Start or reconnect the paper gateway before any runtime checks.",
        checked_at: "2026-05-20T08:14:50.000Z",
        latency_ms: null,
        target: "paper-gateway",
        tags: ["broker"],
        extra: {},
      },
    ],
    ...overrides,
  };
}

async function mockFeedMonitor(
  page: import("@playwright/test").Page,
  options?: {
    payload?: Record<string, unknown>;
    status?: number;
    rawBody?: string;
  },
) {
  const responseStatus = options?.status ?? 200;
  await page.route(feedMonitorApiUrl(), async (route) => {
    if (!isFeedMonitorApiRequest(route.request())) {
      await route.continue();
      return;
    }

    await route.fulfill({
      status: responseStatus,
      contentType: "application/json",
      body: options?.rawBody ?? JSON.stringify(options?.payload ?? buildFeedMonitorPayload()),
    });
  });
}

test("feed monitor route loads summary, filters, and rows", async ({ page }) => {
  await mockFeedMonitor(page);

  await page.goto("/monitor/feeds");
  await page.waitForLoadState("domcontentloaded");

  const filters = page.locator('section[aria-label="Feed monitor filters"]');

  await expect(page.getByRole("heading", { name: /feed monitor/i })).toBeVisible();
  await expect(page.getByText(/read-only posture for inbound data feeds/i)).toBeVisible();
  await expect(page.getByText("Investigate non-OK feeds before enabling automation.")).toBeVisible();

  await expect(page.locator("span").filter({ hasText: /^Overall$/ })).toBeVisible();
  await expect(page.locator("span").filter({ hasText: /^Rows$/ })).toBeVisible();
  await expect(page.locator("span").filter({ hasText: /^Configured$/ })).toBeVisible();
  await expect(page.locator("span").filter({ hasText: /^Runtime reachable$/ })).toBeVisible();
  await expect(page.locator("span").filter({ hasText: /^Issues$/ })).toBeVisible();

  await expect(page.getByRole("cell", { name: /polygon websocket/i })).toBeVisible();
  await expect(page.getByRole("cell", { name: /sec reference api/i })).toBeVisible();
  await expect(page.getByRole("cell", { name: /ibkr gateway runtime/i })).toBeVisible();

  await filters.getByLabel("Category").selectOption("runtime");
  await expect(page.getByRole("cell", { name: /ibkr gateway runtime/i })).toBeVisible();
  await expect(page.getByRole("cell", { name: /polygon websocket/i })).toHaveCount(0);

  await filters.getByLabel("Category").selectOption("all");
  await filters.getByLabel("Status").selectOption("degraded");
  await expect(page.getByRole("cell", { name: /polygon websocket/i })).toBeVisible();
  await expect(page.getByRole("cell", { name: /sec reference api/i })).toHaveCount(0);

  await filters.getByLabel("Status").selectOption("all");
  await filters.getByLabel("Search").fill("gateway");
  await expect(page.getByRole("cell", { name: /ibkr gateway runtime/i })).toBeVisible();
  await expect(page.getByRole("cell", { name: /polygon websocket/i })).toHaveCount(0);
});

test("feed monitor route handles unknown and empty rows without hard crash", async ({ page }) => {
  await mockFeedMonitor(page, {
    payload: buildFeedMonitorPayload({
      overall: "unknown",
      advisory: "No runtime probes have reported yet.",
      summary: {
        total: 0,
        configured: 0,
        runtime_reachable: 0,
        issue_count: 0,
        by_status: { unknown: 0 },
        by_category: {},
      },
      next_actions: ["Wait for the next monitor cycle or refresh manually."],
      rows: [],
    }),
  });

  const consoleErrors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });

  await page.goto("/monitor/feeds");
  await page.waitForLoadState("domcontentloaded");

  await expect(page.getByRole("heading", { name: /feed monitor/i })).toBeVisible();
  await expect(page.getByText("No runtime probes have reported yet.")).toBeVisible();
  await expect(page.getByText(/no feed rows match the current filters/i)).toBeVisible();
  await expect(page.getByText(/wait for the next monitor cycle/i)).toBeVisible();
  await expect(page.getByText(/something went wrong/i)).toHaveCount(0);

  const fatalErrors = consoleErrors.filter(
    (entry) => entry.includes("Unhandled") || entry.includes("Cannot read") || entry.includes("is not a function"),
  );
  expect(fatalErrors).toHaveLength(0);
});

test("feed monitor page has no horizontal overflow at 390px", async ({ page }) => {
  test.setTimeout(45_000);
  await page.setViewportSize({ width: 390, height: 844 });
  await mockFeedMonitor(page);

  await page.goto("/monitor/feeds");
  await page.waitForLoadState("domcontentloaded");

  await expect(page.getByRole("heading", { name: /feed monitor/i })).toBeVisible();
  await expect(page.getByRole("cell", { name: /polygon websocket/i })).toBeVisible();

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
