import { expect, test } from "@playwright/test";

const API_BASE_URL = process.env.PLAYWRIGHT_API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

function apiUrl(path: string) {
  return new URL(path, API_BASE_URL).toString();
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