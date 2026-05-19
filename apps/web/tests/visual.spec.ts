import { test, expect } from "@playwright/test";

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

for (const viewport of VIEWPORTS) {
  test.describe(`Visual regression — ${viewport.name} (${viewport.width}px)`, () => {
    test.use({ viewport: { width: viewport.width, height: viewport.height } });

    for (const page of PAGES) {
      test(`${page.name} — dark theme`, async ({ page: pw }) => {
        await pw.goto(page.url);
        await pw.waitForLoadState("networkidle");
        await pw.waitForTimeout(500);
        await expect(pw).toHaveScreenshot(`${page.name}-${viewport.name}-dark.png`, {
          fullPage: true,
          maxDiffPixelRatio: 0.02,
        });
      });

      test(`${page.name} — light theme`, async ({ page: pw }) => {
        await pw.goto(page.url);
        await pw.waitForLoadState("networkidle");
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
