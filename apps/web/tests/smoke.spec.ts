import { expect, test } from "@playwright/test";

const API_BASE_URL = process.env.PLAYWRIGHT_API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

function apiUrl(path: string) {
  return new URL(path, API_BASE_URL).toString();
}

function buildCockpitModeState() {
  return {
    current_mode: "learning",
    selectable_modes: ["learning", "manual", "auto_paper"],
    locked_modes: ["assisted_live", "live", "auto_live"],
    modes: [
      {
        id: "learning",
        label: "Learning",
        status: "active",
        selectable: true,
        locked: false,
        reason: "No orders are placed. This mode is for learning, explanations, and observation only.",
        risk_note: "Risk first: no paper or live orders are submitted from Learning mode.",
        allowed_actions: ["Read explanations and market context"],
        blocked_actions: ["Paper order automation", "Live broker submission"],
        safety_gates: ["No order path is enabled by mode selection"],
      },
      {
        id: "manual",
        label: "Manual",
        status: "available",
        selectable: true,
        locked: false,
        reason: "Nothing is submitted unless the operator explicitly chooses to act.",
        risk_note: "Risk first: recommendations stay advisory until a human reviews and confirms the next step.",
        allowed_actions: ["Review recommendations and reasoning"],
        blocked_actions: ["Automatic paper trading", "Real-money submission"],
        safety_gates: ["Existing trading_control_service rules still apply"],
      },
      {
        id: "auto_paper",
        label: "Auto Paper",
        status: "available",
        selectable: true,
        locked: false,
        reason: "Simulation only. This mode signals paper-only operator intent and keeps real money out of scope.",
        risk_note: "Risk first: selecting Auto Paper does not enable live trading and does not bypass paper-boundary checks.",
        allowed_actions: ["View auto-paper readiness and status surfaces"],
        blocked_actions: ["Real broker order routing", "Auto live trading"],
        safety_gates: ["Backend live flags remain false"],
      },
      {
        id: "assisted_live",
        label: "Assisted Live",
        status: "locked",
        selectable: false,
        locked: true,
        reason: "Locked until a future live-readiness checklist, per-trade approval flow, and explicit unlock phase exist.",
        risk_note: "Risk first: assisted live stays unavailable because current protections are not sufficient for real-money routing.",
        allowed_actions: ["Review future product direction only"],
        blocked_actions: ["Mode selection", "Live order submission"],
        safety_gates: ["Rejected server-side if requested"],
      },
      {
        id: "live",
        label: "Live / Real Money",
        status: "locked",
        selectable: false,
        locked: true,
        reason: "Locked until future live arming, emergency-stop, and release-checklist phases are complete.",
        risk_note: "Risk first: real-money trading remains blocked even if a client edits the frontend.",
        allowed_actions: ["Review future product direction only"],
        blocked_actions: ["Mode selection", "Real-money trading"],
        safety_gates: ["live_trading_enabled remains false"],
      },
      {
        id: "auto_live",
        label: "Auto Live",
        status: "locked",
        selectable: false,
        locked: true,
        reason: "Locked until long paper evidence, positive expectancy review, safety sign-off, and explicit unlock exist.",
        risk_note: "Risk first: auto live is intentionally blocked because the current build does not permit automated real-money execution.",
        allowed_actions: ["Review future product direction only"],
        blocked_actions: ["Mode selection", "Automatic live trading"],
        safety_gates: ["auto_live_enabled remains false"],
      },
    ],
    global_safety_state: {
      live_trading_enabled: false,
      auto_live_enabled: false,
      real_money_enabled: false,
      paper_order_submission_allowed: true,
      live_order_submission_allowed: false,
      auto_trading_allowed: false,
      emergency_stop_active: false,
      trading_mode: "paper",
      execution_control: "manual",
      arming_state: "armed",
      reasons: [],
    },
    live_trading_enabled: false,
    auto_live_enabled: false,
    real_money_enabled: false,
    notes: [
      "Mode selection is advisory and does not replace backend trading guards.",
      "Live and real-money modes stay blocked in this phase even if a client submits them directly.",
    ],
  };
}

test("home page shows dashboard surface", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "What Needs Attention Now" })).toBeVisible();
});

test("performance page loads without errors", async ({ page }) => {
  await page.goto("/performance");
  await expect(page.locator("main").first()).toBeVisible();
  await expect(page.getByRole("heading", { name: /performance/i })).toBeVisible();
});

test("assets page loads table", async ({ page }) => {
  await page.goto("/assets");
  await expect(page.locator("main").first()).toBeVisible();
  await expect(page.getByRole("heading", { name: /asset universe/i })).toBeVisible();
});

test("opportunities page loads table", async ({ page }) => {
  await page.goto("/opportunities");
  await expect(page.locator("main").first()).toBeVisible();
  await expect(page.getByRole("heading", { name: /opportunities/i })).toBeVisible();
});

test("notifications page loads", async ({ page }) => {
  await page.goto("/notifications");
  await expect(page.locator("main").first()).toBeVisible();
  await expect(page.getByRole("heading", { name: /notifications/i }).first()).toBeVisible();
});

test("alerts page loads watchlist surface", async ({ page }) => {
  await page.goto("/alerts");
  await expect(page.locator("main").first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Alerts & Watchlist" })).toBeVisible();
});

test("data centre page loads with read-only heading", async ({ page }) => {
  await page.goto("/data-centre");
  await expect(page.locator("main").first()).toBeVisible();
  await expect(page.getByRole("heading", { name: /data centre/i })).toBeVisible();
  await expect(page.getByText(/run mh-02 imports before expecting full coverage/i)).toBeVisible();
  await expect(page.getByRole("button", { name: /start import job/i })).toBeVisible();
  await expect(page.getByRole("button", { name: /start quality recalculation job/i })).toBeVisible();
});

test("strategy lab page loads route and research review sections", async ({ page }) => {
  await page.goto("/strategy-lab");
  await expect(page.locator("main").first()).toBeVisible();
  await expect(page.getByRole("heading", { name: /strategy lab/i })).toBeVisible();
  await expect(page.getByTestId("strategy-lab-banner")).toBeVisible();
  await expect(page.getByTestId("strategy-lab-summary-strip")).toBeVisible();
  await expect(page.getByTestId("strategy-lab-density-toggle")).toBeVisible();
  await expect(page.getByTestId("strategy-lab-runs-section")).toBeVisible();
  await expect(page.getByTestId("strategy-lab-results-section")).toBeVisible();
  await expect(page.getByTestId("strategy-lab-result-drilldown-section")).toBeVisible();
  await expect(page.getByTestId("strategy-lab-report-actions")).toBeVisible();
  await expect(page.getByTestId("strategy-lab-report-preview")).toBeVisible();
});

test("strategy lab sidebar and research-only safety content render", async ({ page }) => {
  await page.goto("/strategy-lab");
  await expect(page.getByRole("link", { name: "Strategy Lab" })).toBeVisible();
  await expect(page.getByTestId("strategy-lab-safety-section")).toBeVisible();
  await expect(page.getByText(/not approved for paper or live trading/i)).toBeVisible();
});

test("strategy lab cost, quality, and walk-forward sections render", async ({ page }) => {
  await page.goto("/strategy-lab");
  await expect(page.getByTestId("strategy-lab-cost-model-section")).toBeVisible();
  await expect(page.getByTestId("strategy-lab-quality-section")).toBeVisible();
  await expect(page.getByTestId("strategy-lab-walk-forward-section")).toBeVisible();
  await expect(page.getByTestId("strategy-lab-ai-report-section")).toBeVisible();
});

test("workflow submit renders result", async ({ page }) => {
  await page.goto("/workflow");
  await page.getByRole("button", { name: "Run live workflow" }).click();
  await expect(page.getByText("Workflow State")).toBeVisible();
});

test("signals page loads live feed surfaces", async ({ page }) => {
  await page.goto("/signals");
  await expect(page.getByRole("heading", { name: "Live Signal Feed" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Recent News" })).toBeVisible();
});

test("risk submit renders payload", async ({ page }) => {
  await page.goto("/risk");
  await page.getByRole("button", { name: "Evaluate risk" }).click();
  await expect(page.getByText(/APPROVED|DENIED/).first()).toBeVisible();
});

test("approvals submit renders payload", async ({ page }) => {
  await page.goto("/approvals");
  await page.getByRole("button", { name: "Create approval request" }).click();
  await expect(page.getByText('"request_id"')).toBeVisible();
});

test("execution page loads execution list", async ({ page }) => {
  await page.goto("/execution");
  await expect(page.getByRole("heading", { name: "Execution List" })).toBeVisible();
});

test("live execution guard returns disabled sentinel via API", async ({ request }) => {
  const response = await request.post(apiUrl("/execution/live"), {
    data: {
      asset: "AAPL",
      side: "buy",
      qty: 1,
      notional: 150,
      stop_price: 145,
      target_price: 160,
    },
  });

  const body = (await response.json()) as { reason: string };
  expect(body.reason).toBe("live_execution_disabled_in_mvp");
});

test("data quality review page loads heading and filter bar", async ({ page }) => {
  await page.goto("/data-quality");
  await page.waitForLoadState("domcontentloaded");
  await expect(page.getByRole("heading", { name: /data quality review/i })).toBeVisible();
  await expect(page.getByTestId("dq-filter-bar")).toBeVisible();
});

test("data quality outlier list panel renders", async ({ page }) => {
  await page.goto("/data-quality");
  await page.waitForLoadState("domcontentloaded");
  await expect(page.getByTestId("dq-outlier-list")).toBeVisible();
});

test("data quality detail panel shows empty state when no row selected", async ({ page }) => {
  await page.goto("/data-quality");
  await page.waitForLoadState("domcontentloaded");
  await expect(page.getByTestId("dq-detail-panel")).toBeVisible();
  await expect(page.getByText(/select an item to review/i)).toBeVisible();
});

test("data quality filter bar has asset, provider, timeframe inputs", async ({ page }) => {
  await page.goto("/data-quality");
  await page.waitForLoadState("domcontentloaded");
  await expect(page.getByTestId("dq-filter-asset")).toBeVisible();
  await expect(page.getByTestId("dq-filter-provider")).toBeVisible();
  await expect(page.getByTestId("dq-filter-timeframe")).toBeVisible();
});

test("feed monitor page loads heading and filter controls", async ({ page }) => {
  await page.goto("/monitor/feeds");
  await page.waitForLoadState("domcontentloaded");
  await expect(page.getByRole("heading", { name: /feed monitor/i })).toBeVisible();
  await expect(page.locator('section[aria-label="Feed monitor filters"]')).toBeVisible();
  await expect(page.getByRole("button", { name: /refresh/i })).toBeVisible();
  await expect(page.getByText(/drift lock active/i)).toBeVisible();
});

test("cockpit page loads mode selector and locked live modes", async ({ page }) => {
  await page.route("**/cockpit/mode", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(buildCockpitModeState()),
    });
  });

  await page.goto("/cockpit");
  await page.waitForLoadState("domcontentloaded");
  await expect(page.getByRole("heading", { name: "Cockpit", exact: true })).toBeVisible();
  await expect(page.getByTestId("cockpit-mode-selector")).toBeVisible();
  await expect(page.getByTestId("cockpit-current-mode-summary")).toContainText(/learning/i);
  await expect(page.getByText(/risk first: mode selection changes operator intent only/i)).toBeVisible();
  await expect(page.getByTestId("cockpit-select-assisted_live")).toBeDisabled();
  await expect(page.getByTestId("cockpit-select-live")).toBeDisabled();
  await expect(page.getByTestId("cockpit-select-auto_live")).toBeDisabled();
});