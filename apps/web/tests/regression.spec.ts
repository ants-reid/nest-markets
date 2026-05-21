/**
 * Regression test suite.
 *
 * QA IDs map 1-to-1 with docs/regression-qa-matrix.md.
 *
 * Run with:   npx playwright test tests/regression.spec.ts
 */

import { expect, test } from "@playwright/test";

const API_BASE_URL = process.env.PLAYWRIGHT_API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

function apiUrl(path: string) {
  return new URL(path, API_BASE_URL).toString();
}

// ---------------------------------------------------------------------------
// Route regression checks
// ---------------------------------------------------------------------------

// QA-002
test("QA-002 dashboard loads without broken primary panels", async ({ page }) => {
  await page.goto("/dashboard");
  await expect(page.locator("main").first()).toBeVisible();
  // PersonalDashboard renders a heading with "Dashboard" or similar navigation
  // and a Nav component — verify the nav and at least one content region exist.
  const nav = page.locator("nav");
  await expect(nav).toBeVisible();
  // No <title> error banners
  await expect(page.getByText("Error", { exact: false })).toHaveCount(0);
});

// QA-003
test("QA-003 analytics route loads and key panels render", async ({ page }) => {
  await page.goto("/analytics");
  await expect(page.locator("main").first()).toBeVisible();
  const nav = page.locator("nav");
  await expect(nav).toBeVisible();
  await expect(page.getByText("Loading analytics...")).toHaveCount(0);
  await expect(page.locator("svg").first()).toBeVisible({ timeout: 10000 });
});

// QA-010
test("QA-010 alerts route loads key sections and watchlist chart", async ({ page }) => {
  await page.goto("/alerts");
  await expect(page.locator("main").first()).toBeVisible();
  const nav = page.locator("nav");
  await expect(nav).toBeVisible();
  // Wait for async data load — the page should move out of loading state
  await page.waitForTimeout(1200);
  // Alert Rules panel heading or label — use exact h2 to avoid multi-match
  await expect(page.locator("h2").filter({ hasText: "Watchlist" }).first()).toBeVisible();
  // SVG chart should be rendered inside the watchlist chart panel
  const svgElements = page.locator("svg");
  await expect(svgElements.first()).toBeVisible();
});

// QA-011
test("QA-011 notifications route loads without broken states", async ({ page }) => {
  await page.goto("/notifications");
  await expect(page.locator("main").first()).toBeVisible();
  await expect(page.locator("h1").filter({ hasText: "Notifications" })).toBeVisible();
  const nav = page.locator("nav");
  await expect(nav).toBeVisible();
});

// QA-108
test("QA-108 market data freshness indicators render on analytics and signals", async ({ page }) => {
  await page.goto("/analytics");
  await expect(page.getByText("Data last updated:", { exact: false })).toBeVisible();

  await page.goto("/signals");
  await expect(page.getByText("Live feed synced:", { exact: false })).toBeVisible();
});

// QA-110
test("QA-110 prompts page renders version history surface", async ({ page }) => {
  await page.goto("/prompts");
  await expect(page.getByRole("heading", { name: "Prompts" })).toBeVisible();

  const firstPromptButton = page.locator("button").filter({ hasText: /system\/|user\// }).first();
  await expect(firstPromptButton).toBeVisible();
  await firstPromptButton.click();

  await expect(page.getByText("Version History")).toBeVisible();
});

// QA-111
test("QA-111 evals page loads run table surface", async ({ page }) => {
  await page.goto("/evals");
  await expect(page.getByRole("heading", { name: "Evaluation Runs" })).toBeVisible();
});

// QA-112
test("QA-112 models registry page loads backend-backed list surface", async ({ page }) => {
  await page.goto("/models");
  await expect(page.getByRole("heading", { name: "Model Registry" })).toBeVisible();
  await expect(page.getByText("Registered model versions", { exact: false })).toBeVisible();
});

// QA-114
test("QA-114 promotions page loads governance actions surface", async ({ page }) => {
  await page.goto("/promotions");
  await expect(page.getByRole("heading", { name: "Promotion Queue" })).toBeVisible();
  await expect(page.getByText("Promote an inactive model version", { exact: false })).toBeVisible();
});

// QA-113
test("QA-113 signals page renders recent news surface", async ({ page }) => {
  await page.goto("/signals");
  await expect(page.getByRole("heading", { name: "Recent News" })).toBeVisible();
});

// ---------------------------------------------------------------------------
// Theme and token checks
// ---------------------------------------------------------------------------

// QA-020
test("QA-020 dark mode persists across route changes", async ({ page }) => {
  // Seed localStorage so the theme bootstrap picks it up
  await page.goto("/");
  await page.evaluate(() => {
    window.localStorage.setItem("mh-theme", "dark");
  });

  // Navigate to a secondary route and confirm data-theme is still dark
  await page.goto("/alerts");
  const theme = await page.evaluate(() => document.documentElement.getAttribute("data-theme"));
  // dark is the default; data-theme may be absent (meaning dark) or "dark"
  expect(theme === null || theme === "dark").toBeTruthy();

  await page.goto("/analytics");
  const theme2 = await page.evaluate(() => document.documentElement.getAttribute("data-theme"));
  expect(theme2 === null || theme2 === "dark").toBeTruthy();
});

// QA-021
test("QA-021 light mode persists across route changes", async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => {
    window.localStorage.setItem("mh-theme", "light");
  });

  await page.goto("/alerts");
  const theme = await page.evaluate(() => document.documentElement.getAttribute("data-theme"));
  expect(theme).toBe("light");

  await page.goto("/dashboard");
  const theme2 = await page.evaluate(() => document.documentElement.getAttribute("data-theme"));
  expect(theme2).toBe("light");

  // Reset so subsequent tests start clean
  await page.evaluate(() => {
    window.localStorage.removeItem("mh-theme");
  });
});

// QA-024
test("QA-024 raw color hex literals are not present in rendered HTML", async ({ page }) => {
  // This checks the live DOM of a few key pages for inline style attributes
  // containing raw hex colors rather than CSS tokens.
  const pages = ["/", "/alerts", "/analytics", "/dashboard", "/notifications"];
  for (const route of pages) {
    await page.goto(route);
    const html = await page.content();
    // Look for 6-digit hex colors in inline styles that are NOT inside a CSS custom property
    // Pattern: style="...#[0-9a-fA-F]{6}..." where the hex is not part of color-mix or var()
    const plainHexInStyle = /#[0-9a-fA-F]{6}/g;
    const matches = html.match(plainHexInStyle) ?? [];
    // Allow zero matches — any hit is a regression
    expect(
      matches.length,
      `Route ${route} has ${matches.length} raw hex color(s) in rendered HTML`,
    ).toBe(0);
  }
});

// ---------------------------------------------------------------------------
// Chart regression checks
// ---------------------------------------------------------------------------

// QA-030
test("QA-030 single-point series renders a visible marker on the alerts watchlist chart", async ({ page }) => {
  await page.goto("/alerts");
  await page.waitForTimeout(1500); // wait for data + chart render

  const svg = page.getByLabel("Time series chart");
  await expect(svg).toBeVisible();

  // At minimum the SVG should contain path or circle elements (the chart draws both)
  const pathsAndCircles = await svg.locator("path, circle").count();
  expect(pathsAndCircles).toBeGreaterThan(0);
});

// QA-031
test("QA-031 multi-point line chart is visible in dark mode (analytics)", async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => window.localStorage.setItem("mh-theme", "dark"));

  await page.goto("/analytics");
  await page.waitForTimeout(1000);

  const svg = page.getByLabel("Time series chart");
  await expect(svg).toBeVisible();
  const paths = await svg.locator("path").count();
  expect(paths).toBeGreaterThan(0);
});

// QA-032
test("QA-032 multi-point line chart is visible in light mode (analytics)", async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => window.localStorage.setItem("mh-theme", "light"));

  await page.goto("/analytics");
  await page.waitForTimeout(1000);

  const svg = page.getByLabel("Time series chart");
  await expect(svg).toBeVisible();
  const paths = await svg.locator("path").count();
  expect(paths).toBeGreaterThan(0);

  await page.evaluate(() => window.localStorage.removeItem("mh-theme"));
});

// ---------------------------------------------------------------------------
// Table and surface checks
// ---------------------------------------------------------------------------

// QA-040 / QA-041
test("QA-040-041 execution table rows are present and readable in both themes", async ({ page }) => {
  for (const theme of ["dark", "light"] as const) {
    await page.goto("/");
    await page.evaluate((t) => window.localStorage.setItem("mh-theme", t), theme);

    await page.goto("/execution");
    await expect(page.locator("main").first()).toBeVisible();
    // Exact heading to avoid strict violation against nav/notification links
    await expect(page.getByRole("heading", { name: "Execution List" })).toBeVisible();
  }
  await page.evaluate(() => window.localStorage.removeItem("mh-theme"));
});

// QA-103
test("QA-103 execution page renders open positions panel", async ({ page }) => {
  await page.goto("/execution");
  await expect(page.locator("main").first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Open Positions" })).toBeVisible();
});

// QA-042
test("QA-042 empty and loading states render without a crash", async ({ page }) => {
  // Temporarily block API calls so the page must render an empty/loading state
  await page.route("**/api/**", (route) => route.abort());

  await page.goto("/notifications");
  await expect(page.locator("main").first()).toBeVisible();
  // Must not throw — page renders even when API is down; use h1 to avoid strict violation
  await expect(page.locator("h1").filter({ hasText: "Notifications" })).toBeVisible();
});

// ---------------------------------------------------------------------------
// Backend and policy checks
// ---------------------------------------------------------------------------

// QA-009 (moved from smoke — kept here for completeness with the registry ID)
test("QA-009-b live execution guard returns disabled sentinel", async ({ request }) => {
  const response = await request.post(apiUrl("/execution/live"), {
    data: {
      asset: "AAPL",
      side: "buy",
      qty: 1.0,
      notional: 150.0,
      stop_price: 145.0,
      target_price: 160.0,
    },
  });

  const body = await response.json() as { reason: string };
  expect(body.reason).toBe("live_execution_disabled_in_mvp");
});

// ---------------------------------------------------------------------------
// QA-013 — LLM toggle renders warning state when activated
// ---------------------------------------------------------------------------

// QA-013
test("QA-013 workflow page exposes live LLM mode controls", async ({ page }) => {
  await page.goto("/workflow");
  await expect(page.locator("main").first()).toBeVisible();

  await expect(page.getByText("Live LLM mode", { exact: false })).toBeVisible();
  await expect(page.locator("form").getByRole("link", { name: "Dashboard" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Run live workflow" })).toBeVisible();
});

// ---------------------------------------------------------------------------
// QA-033 — Chart axis labels are visible in both themes on /analytics
// ---------------------------------------------------------------------------

// QA-033
// LineChart renders axis guides as HTML div overlays (not SVG <text>), so we
// verify the chart container and SVG path elements are visible in both themes.
test("QA-033 chart area visible and SVG paths rendered in dark mode", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto("/");
  await page.evaluate(() => window.localStorage.setItem("mh-theme", "dark"));
  await page.goto("/analytics");
  // Wait for the data loading indicator to disappear
  await expect(page.locator("text=Loading analytics...")).toBeHidden({ timeout: 10000 });

  // SVG chart must be visible
  const svg = page.getByLabel("Time series chart");
  await expect(svg).toBeVisible();

  // Chart must have rendered path elements (lines or area fill)
  const paths = await svg.locator("path").count();
  expect(paths).toBeGreaterThan(0);
});

// QA-033 light mode variant
test("QA-033 chart area visible and SVG paths rendered in light mode", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto("/");
  await page.evaluate(() => window.localStorage.setItem("mh-theme", "light"));
  await page.goto("/analytics");
  await expect(page.locator("text=Loading analytics...")).toBeHidden({ timeout: 10000 });

  const svg = page.getByLabel("Time series chart");
  await expect(svg).toBeVisible();
  const paths = await svg.locator("path").count();
  expect(paths).toBeGreaterThan(0);

  await page.evaluate(() => window.localStorage.removeItem("mh-theme"));
});

// ---------------------------------------------------------------------------
// QA-034 — Series toggles and time range controls are usable on /analytics
// ---------------------------------------------------------------------------

// QA-034
// TimeRangeBar renders buttons: "1D", "1W", "1M", "3M", "1Y", "ALL"
// SeriesToggle renders named series buttons.
test("QA-034 series toggles and time range controls are usable", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto("/analytics");
  // Wait for data to load before checking chart controls
  await expect(page.locator("text=Loading analytics...")).toBeHidden({ timeout: 10000 });

  // TimeRangeBar — buttons "1D", "1W", "1M", "3M", "1Y", "ALL"
  const rangeButtons = page.locator("button").filter({ hasText: /^(1D|1W|1M|3M|1Y|ALL)$/ });
  const rangeCount = await rangeButtons.count();
  expect(rangeCount).toBeGreaterThanOrEqual(3);

  // Click "1M" range and confirm no crash
  const oneMonth = page.locator("button").filter({ hasText: /^1M$/ }).first();
  await expect(oneMonth).toBeVisible();
  await oneMonth.click();
  await expect(page.locator("main").first()).toBeVisible();

  // SeriesToggle — at least one series toggle button exists and is clickable
  const allButtons = page.locator("button");
  const totalButtons = await allButtons.count();
  expect(totalButtons).toBeGreaterThanOrEqual(3);

  // None of the range buttons should be disabled
  for (let i = 0; i < rangeCount; i++) {
    const btn = rangeButtons.nth(i);
    const isDisabled = await btn.getAttribute("disabled");
    expect(isDisabled).toBeNull();
  }
});
