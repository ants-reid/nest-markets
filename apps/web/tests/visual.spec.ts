import { test, expect } from "@playwright/test";

const FIXED_NOW_ISO = "2026-05-21T03:00:00.000Z";
const API_BASE_URL = process.env.PLAYWRIGHT_API_BASE_URL ?? "http://127.0.0.1:8000";

const VIEWPORTS = [
  { name: "mobile", width: 390, height: 844 },
  { name: "tablet", width: 768, height: 1024 },
  { name: "desktop", width: 1024, height: 768 },
];

const PAGES = [
  { name: "dashboard", url: "/" },
  { name: "analytics", url: "/analytics" },
  { name: "execution", url: "/execution" },
  { name: "performance", url: "/performance" },
  { name: "assets", url: "/assets" },
  { name: "opportunities", url: "/opportunities" },
  { name: "alerts", url: "/alerts" },
  { name: "notifications", url: "/notifications" },
];

const STABLE_EXECUTIONS = [
  {
    execution_id: "11111111-1111-4111-8111-111111111111",
    status: "submitted",
    asset: "EURUSD",
    timeframe: "1h",
    side: "buy",
    qty: 2,
    notional: 1200,
    stop_price: 1.078,
    target_price: 1.092,
    fill_price: 1.084,
    reason: null,
  },
  {
    execution_id: "22222222-2222-4222-8222-222222222222",
    status: "filled",
    asset: "XAUUSD",
    timeframe: "4h",
    side: "sell",
    qty: 1,
    notional: 1800,
    stop_price: 2360,
    target_price: 2285,
    fill_price: 2325,
    reason: null,
  },
  {
    execution_id: "33333333-3333-4333-8333-333333333333",
    status: "rejected",
    asset: "NZDUSD",
    timeframe: "1d",
    side: "buy",
    qty: 3,
    notional: 950,
    stop_price: 0.588,
    target_price: 0.612,
    fill_price: 0.601,
    reason: "risk_gate",
  },
  {
    execution_id: "44444444-4444-4444-8444-444444444444",
    status: "closed",
    asset: "GBPUSD",
    timeframe: "1h",
    side: "buy",
    qty: 2,
    notional: 1430,
    stop_price: 1.261,
    target_price: 1.279,
    fill_price: 1.268,
    reason: null,
  },
  {
    execution_id: "55555555-5555-4555-8555-555555555555",
    status: "new",
    asset: "USDJPY",
    timeframe: "15m",
    side: "sell",
    qty: 1,
    notional: 1100,
    stop_price: 157.2,
    target_price: 154.8,
    fill_price: 156.3,
    reason: null,
  },
];

const STABLE_ACTIVE_ALERTS = [
  {
    alert_id: "alert-2001",
    rule_id: "rule-3001",
    execution_id: "33333333-3333-4333-8333-333333333333",
    asset: "NZDUSD",
    status: "open",
    message: "Risk gate rejection still requires operator review.",
    level: "warning",
  },
  {
    alert_id: "alert-2002",
    rule_id: "rule-3002",
    execution_id: "22222222-2222-4222-8222-222222222222",
    asset: "XAUUSD",
    status: "open",
    message: "Gold short position has crossed the volatility watch threshold.",
    level: "info",
  },
];

const STABLE_ALERT_RULES = [
  {
    rule_id: "rule-3001",
    asset: "NZDUSD",
    condition: "Reject on risk-gate failure",
    status: "active",
    created_at: "2026-05-20T10:00:00Z",
    updated_at: "2026-05-20T10:15:00Z",
    snoozed_until: null,
  },
  {
    rule_id: "rule-3002",
    asset: "XAUUSD",
    condition: "Alert when volatility rises above baseline",
    status: "active",
    created_at: "2026-05-20T11:00:00Z",
    updated_at: "2026-05-20T11:10:00Z",
    snoozed_until: null,
  },
  {
    rule_id: "rule-3003",
    asset: "EURUSD",
    condition: "Notify when execution stays submitted > 30m",
    status: "active",
    created_at: "2026-05-20T12:00:00Z",
    updated_at: "2026-05-20T12:05:00Z",
    snoozed_until: null,
  },
];

const STABLE_NOTIFICATIONS = [
  {
    notification_id: "note-4001",
    alert_id: "alert-2001",
    rule_id: "rule-3001",
    execution_id: "33333333-3333-4333-8333-333333333333",
    asset: "NZDUSD",
    status: "rejected",
    message: "Review the rejected NZDUSD execution before the next batch run.",
    level: "warning",
    is_read: false,
    read_at: null,
  },
  {
    notification_id: "note-4002",
    alert_id: "alert-2002",
    rule_id: "rule-3002",
    execution_id: "22222222-2222-4222-8222-222222222222",
    asset: "XAUUSD",
    status: "filled",
    message: "XAUUSD remains within the monitored volatility band.",
    level: "info",
    is_read: true,
    read_at: "2026-05-20T13:45:00Z",
  },
  {
    notification_id: "note-4003",
    alert_id: "alert-2003",
    rule_id: "rule-3003",
    execution_id: "11111111-1111-4111-8111-111111111111",
    asset: "EURUSD",
    status: "submitted",
    message: "EURUSD submitted order is still waiting for confirmation.",
    level: "warning",
    is_read: false,
    read_at: null,
  },
];

const STABLE_RUN_HISTORY = [
  {
    worker_name: "auto-paper",
    status: "success",
    message: "Processed 2 opportunities into the paper queue.",
    started_at: "2026-05-21T02:15:00Z",
    finished_at: "2026-05-21T02:15:12Z",
    source: "scheduled",
  },
  {
    worker_name: "auto-paper",
    status: "success",
    message: "No new actionable signals in this cadence.",
    started_at: "2026-05-21T01:45:00Z",
    finished_at: "2026-05-21T01:45:05Z",
    source: "scheduled",
  },
];

const STABLE_KILL_SWITCH = {
  kill_switch_active: false,
  profile_name: "paper-default",
  profile_is_active: "true",
};

const STABLE_ASSETS = {
  total: 5,
  items: [
    {
      id: "asset-5001",
      symbol: "EURUSD",
      name: "Euro / US Dollar",
      asset_class: "fx",
      base_currency: "EUR",
      quote_currency: "USD",
      exchange: "IDEALPRO",
      sector: null,
      industry: null,
      is_active: true,
    },
    {
      id: "asset-5002",
      symbol: "GBPUSD",
      name: "British Pound / US Dollar",
      asset_class: "fx",
      base_currency: "GBP",
      quote_currency: "USD",
      exchange: "IDEALPRO",
      sector: null,
      industry: null,
      is_active: true,
    },
    {
      id: "asset-5003",
      symbol: "USDJPY",
      name: "US Dollar / Japanese Yen",
      asset_class: "fx",
      base_currency: "USD",
      quote_currency: "JPY",
      exchange: "IDEALPRO",
      sector: null,
      industry: null,
      is_active: true,
    },
    {
      id: "asset-5004",
      symbol: "XAUUSD",
      name: "Gold Spot",
      asset_class: "commodity_proxy",
      base_currency: "XAU",
      quote_currency: "USD",
      exchange: "OTC",
      sector: null,
      industry: null,
      is_active: true,
    },
    {
      id: "asset-5005",
      symbol: "SPY",
      name: "SPDR S&P 500 ETF",
      asset_class: "etf",
      base_currency: "USD",
      quote_currency: "USD",
      exchange: "ARCA",
      sector: null,
      industry: null,
      is_active: false,
    },
  ],
};

function corsHeaders() {
  return {
    "access-control-allow-origin": "*",
    "access-control-allow-methods": "GET,POST,PUT,PATCH,DELETE,OPTIONS",
    "access-control-allow-headers": "Content-Type, Authorization",
  };
}

async function fulfillJson(route: Parameters<Parameters<typeof test>[0]>[0]["route"], body: unknown) {
  await route.fulfill({
    status: 200,
    contentType: "application/json",
    headers: corsHeaders(),
    body: JSON.stringify(body),
  });
}

async function installStableClientState(pw: Parameters<Parameters<typeof test>[0]>[0]["page"]) {
  await pw.addInitScript(({ fixedNowIso }) => {
    const fixedNow = new Date(fixedNowIso).valueOf();
    const NativeDate = Date;

    class FixedDate extends NativeDate {
      constructor(...args: ConstructorParameters<typeof Date>) {
        super(args.length === 0 ? fixedNow : args[0] as string | number | Date);
      }

      static now() {
        return fixedNow;
      }

      static parse(value: string) {
        return NativeDate.parse(value);
      }

      static UTC(...args: Parameters<typeof NativeDate.UTC>) {
        return NativeDate.UTC(...args);
      }
    }

    Object.setPrototypeOf(FixedDate, NativeDate);
    // @ts-expect-error test-only Date override
    window.Date = FixedDate;

    window.localStorage.clear();
    window.localStorage.setItem("mh-theme", "dark");
    window.localStorage.setItem(
      "dashboard:autoPaperSettings:v2",
      JSON.stringify({ autoEnabled: false, intervalMinutes: 15 }),
    );
    window.localStorage.removeItem("dashboard:autoPaperNextRunAt:v1");
    window.localStorage.setItem("dashboard:globalExecutionMode:v1", "paper");
  }, { fixedNowIso: FIXED_NOW_ISO });
}

function requiresStableVisualHarness(pageName: string) {
  return pageName === "dashboard" || pageName === "assets";
}

async function installStableVisualMocks(
  pw: Parameters<Parameters<typeof test>[0]>[0]["page"],
  pageName: string,
) {
  if (pageName !== "dashboard" && pageName !== "assets") {
    return;
  }

  await pw.route(`${API_BASE_URL}/**`, async (route) => {
    const request = route.request();
    const url = new URL(request.url());

    if (request.method() === "OPTIONS") {
      await route.fulfill({ status: 200, headers: corsHeaders() });
      return;
    }

    if (url.pathname === "/health") {
      await fulfillJson(route, { status: "ok" });
      return;
    }

    if (pageName === "dashboard") {
      if (url.pathname === "/execution/paper") {
        await fulfillJson(route, STABLE_EXECUTIONS);
        return;
      }
      if (/^\/execution\/paper\/[^/]+\/journal$/.test(url.pathname)) {
        await route.fulfill({
          status: 404,
          headers: corsHeaders(),
          body: "",
        });
        return;
      }
      if (url.pathname === "/approvals/alerts/active") {
        await fulfillJson(route, STABLE_ACTIVE_ALERTS);
        return;
      }
      if (url.pathname === "/approvals/alerts/notifications") {
        await fulfillJson(route, STABLE_NOTIFICATIONS);
        return;
      }
      if (url.pathname === "/approvals/alerts/rules") {
        await fulfillJson(route, STABLE_ALERT_RULES);
        return;
      }
      if (url.pathname === "/market-data/auto-paper/history") {
        await fulfillJson(route, STABLE_RUN_HISTORY);
        return;
      }
      if (url.pathname === "/market-data/auto-paper/kill-switch") {
        await fulfillJson(route, STABLE_KILL_SWITCH);
        return;
      }
    }

    if (pageName === "assets" && url.pathname === "/assets") {
      await fulfillJson(route, STABLE_ASSETS);
      return;
    }

    await route.continue();
  });
}

async function waitForVisualReady(
  pw: Parameters<Parameters<typeof test>[0]>[0]["page"],
  pageName: string,
) {
  if (pageName === "dashboard") {
    await pw.locator('[data-rs="dashboard-split"]').first().waitFor({ state: "visible" });
    await pw.getByText("Loading personal dashboard...").waitFor({ state: "hidden" });
    await pw.getByText("Loading notifications...").waitFor({ state: "hidden" });
    return;
  }

  if (pageName === "assets") {
    await pw.getByRole("heading", { name: "Asset Universe" }).waitFor({ state: "visible" });
    await pw.getByText("Loading assets…").waitFor({ state: "hidden" });
    await pw.locator("table").first().waitFor({ state: "visible" });
  }
}

for (const viewport of VIEWPORTS) {
  test.describe(`Visual regression — ${viewport.name} (${viewport.width}px)`, () => {
    test.use({ viewport: { width: viewport.width, height: viewport.height } });

    for (const page of PAGES) {
      test(`${page.name} — dark theme`, async ({ page: pw }) => {
        if (requiresStableVisualHarness(page.name)) {
          await installStableClientState(pw);
        }
        await installStableVisualMocks(pw, page.name);
        await pw.goto(page.url);
        await pw.waitForLoadState("networkidle");
        await waitForVisualReady(pw, page.name);
        await pw.waitForTimeout(500);
        await expect(pw).toHaveScreenshot(`${page.name}-${viewport.name}-dark.png`, {
          fullPage: true,
          maxDiffPixelRatio: 0.02,
        });
      });

      test(`${page.name} — light theme`, async ({ page: pw }) => {
        if (requiresStableVisualHarness(page.name)) {
          await installStableClientState(pw);
        }
        await installStableVisualMocks(pw, page.name);
        await pw.goto(page.url);
        await pw.waitForLoadState("networkidle");
        await waitForVisualReady(pw, page.name);
        await pw.waitForTimeout(500);
        await pw.evaluate(() => {
          document.documentElement.setAttribute("data-theme", "light");
        });
        await expect(pw).toHaveScreenshot(`${page.name}-${viewport.name}-light.png`, {
          fullPage: true,
          maxDiffPixelRatio: 0.02,
        });
      });
    }
  });
}
