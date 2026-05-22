import { expect, test } from "@playwright/test";

function buildAttentionPayload(overrides: Record<string, unknown> = {}) {
  return {
    generated_at: "2026-05-22T23:10:00+00:00",
    mode: "paper",
    summary: {
      headline: "Read-only paper attention queue for alerts, incidents, monitor health, and risk context.",
      total_items: 3,
      high_priority: 1,
      medium_priority: 2,
      low_priority: 0,
      unknown_priority: 0,
      active_alerts: 1,
      unresolved_incidents: 1,
      monitor_degraded: 1,
      stale_data: 0,
      risk_attention: 0,
      trading_halt: 0,
      missing_context: 0,
    },
    attention_items: [
      {
        id: "alert:a1",
        source: "alert",
        title: "Active alert for AAPL",
        message: "AAPL execution was rejected.",
        asset_id: "asset-aapl",
        asset_symbol: "AAPL",
        asset_name: "Apple Inc.",
        asset_detail_path: "/asset-cards/asset-aapl",
        has_asset_context: true,
        priority: "high",
        status: "rejected",
        detected_at: null,
        attention_type: "active_alert",
        evidence: ["rule_id:x", "execution_id:y"],
        missing_data: ["detected_at unavailable in active alert record"],
        recommended_review_action: "Review related paper execution context and risk notes before taking any manual next step.",
        is_actionable: false,
      },
      {
        id: "incident:i1",
        source: "incident",
        title: "Worker failure",
        message: "Worker loop failed",
        asset_id: null,
        asset_symbol: null,
        asset_name: null,
        asset_detail_path: null,
        has_asset_context: false,
        priority: "medium",
        status: "observed",
        detected_at: "2026-05-22T23:00:00+00:00",
        attention_type: "unresolved_incident",
        evidence: ["severity:error", "source:worker"],
        missing_data: [],
        recommended_review_action: "Cross-check this incident with monitor and risk summaries; keep this surface read-only.",
        is_actionable: false,
      },
      {
        id: "monitor:feeds_in.polygon_provider",
        source: "monitor",
        title: "Monitor status down: feeds_in.polygon_provider",
        message: "Probe failed",
        asset_id: null,
        asset_symbol: null,
        asset_name: null,
        asset_detail_path: null,
        has_asset_context: false,
        priority: "medium",
        status: "down",
        detected_at: "2026-05-22T23:02:00+00:00",
        attention_type: "monitor_degraded",
        evidence: ["probe:feeds_in.polygon_provider"],
        missing_data: [],
        recommended_review_action: "Review monitor probe diagnostics and confirm feed/provider stability.",
        is_actionable: false,
      },
    ],
    grouped_by_priority: [
      { group: "high", count: 1, item_ids: ["alert:a1"] },
      { group: "medium", count: 2, item_ids: ["incident:i1", "monitor:feeds_in.polygon_provider"] },
    ],
    grouped_by_source: [
      { group: "alert", count: 1, item_ids: ["alert:a1"] },
      { group: "incident", count: 1, item_ids: ["incident:i1"] },
      { group: "monitor", count: 1, item_ids: ["monitor:feeds_in.polygon_provider"] },
    ],
    monitor_notes: ["feeds_in.polygon_provider down"],
    risk_notes: ["Risk limits are configured for future enforcement but are not yet wired into broker submission."],
    limitations: [],
    recommended_review_actions: ["Start with high-priority items, then work through medium-priority monitor and risk notes."],
    ...overrides,
  };
}

async function mockAttentionReport(
  page: import("@playwright/test").Page,
  payload = buildAttentionPayload(),
) {
  await page.addInitScript((mockPayload) => {
    const originalFetch = window.fetch.bind(window);
    window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string"
        ? input
        : input instanceof Request
          ? input.url
          : input.toString();

      if (url.includes("/cockpit/alerts-needing-attention")) {
        return new Response(JSON.stringify(mockPayload), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }

      return originalFetch(input, init);
    };
  }, payload);
}

test("Alerts needing attention route renders summary and read-only wording", async ({ page }) => {
  await mockAttentionReport(page);

  await page.goto("/cockpit/alerts-needing-attention");
  await page.waitForLoadState("domcontentloaded");

  await expect(page.getByTestId("cockpit-alerts-needing-attention-page")).toBeVisible();
  await expect(page.getByRole("heading", { name: /alerts needing attention/i })).toBeVisible();
  await expect(page.getByTestId("cockpit-alerts-paper-mode")).toContainText(/paper mode only/i);
  await expect(page.getByTestId("cockpit-alerts-summary-cards")).toContainText(/attention items/i);
  await expect(page.getByTestId("cockpit-alerts-items")).toContainText(/active alert for AAPL/i);
  await expect(page.getByRole("link", { name: /view asset context/i }).first()).toHaveAttribute("href", "/asset-cards/asset-aapl");
  await expect(page.getByText(/asset context unavailable/i)).toBeVisible();
  await expect(page.getByRole("button", { name: /acknowledge|resolve|execute|close|modify|approve/i })).toHaveCount(0);
});

test("Alerts needing attention empty state renders safely", async ({ page }) => {
  await mockAttentionReport(
    page,
    buildAttentionPayload({
      summary: {
        headline: "Read-only paper attention queue for alerts, incidents, monitor health, and risk context.",
        total_items: 0,
        high_priority: 0,
        medium_priority: 0,
        low_priority: 0,
        unknown_priority: 0,
        active_alerts: 0,
        unresolved_incidents: 0,
        monitor_degraded: 0,
        stale_data: 0,
        risk_attention: 0,
        trading_halt: 0,
        missing_context: 0,
      },
      attention_items: [],
      grouped_by_priority: [],
      grouped_by_source: [],
      monitor_notes: [],
      risk_notes: [],
      limitations: ["No attention items were found from current paper, monitor, risk, and incident sources."],
      recommended_review_actions: ["Use this page for read-focused triage only."],
    }),
  );

  await page.goto("/cockpit/alerts-needing-attention");
  await page.waitForLoadState("domcontentloaded");

  await expect(page.getByText(/no active attention items/i)).toBeVisible();
  await expect(page.getByText(/no attention items were found/i)).toBeVisible();
});

test("Alerts needing attention shows safe error state", async ({ page }) => {
  await page.addInitScript(() => {
    const originalFetch = window.fetch.bind(window);
    window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string"
        ? input
        : input instanceof Request
          ? input.url
          : input.toString();

      if (url.includes("/cockpit/alerts-needing-attention")) {
        return new Response("backend unavailable", {
          status: 500,
          headers: { "Content-Type": "text/plain" },
        });
      }

      return originalFetch(input, init);
    };
  });

  await page.goto("/cockpit/alerts-needing-attention");
  await page.waitForLoadState("domcontentloaded");

  await expect(page.getByText(/alerts needing attention unavailable/i)).toBeVisible();
  await expect(page.getByText(/backend unavailable/i)).toBeVisible();
});

test("cockpit/alerts-needing-attention has no horizontal overflow at 390px", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockAttentionReport(page);

  await page.goto("/cockpit/alerts-needing-attention");
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
