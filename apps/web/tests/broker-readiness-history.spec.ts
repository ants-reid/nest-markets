import { readFile } from "node:fs/promises";

import { expect, test } from "@playwright/test";

import {
  DAILY_PNL_RESPONSE,
  MULTI_ENTRY_PROVENANCE_RESPONSE,
  PAPER_CONTROL_RESPONSE,
  PAPER_READY_HEALTH,
  installBrokerMocks,
} from "./broker-test-helpers";

test("MH-52: readiness checklist derives ready and advisory items from existing state", async ({ page }) => {
  await installBrokerMocks(
    page,
    PAPER_READY_HEALTH,
    PAPER_CONTROL_RESPONSE,
    { entries: [] },
    {
      dailyPnlResponse: DAILY_PNL_RESPONSE,
      dryRunResponse: {
        status: "ready",
        mode_guard_ok: true,
        request_valid: true,
        estimated_notional: 1851,
        issues: [],
        warnings: [],
        preflight_context: {
          cash_balance: 50000,
          buying_power: 100000,
          open_position_count: 0,
          current_symbol_exposure: 0,
          estimated_post_trade_symbol_exposure: 1851,
          current_total_exposure: 0,
          estimated_post_trade_total_exposure: 1851,
          daily_pnl: -342.5,
          daily_loss: 342.5,
          risk_limit_snapshot: null,
        },
        broker_mode: {
          broker: "ibkr",
          mode: "paper",
          live_execution_enabled: false,
          paper_trading_enabled: true,
        },
      },
    },
    MULTI_ENTRY_PROVENANCE_RESPONSE,
  );

  await page.goto("/broker");

  await expect(page.getByTestId("broker-readiness-panel")).toBeVisible();
  await expect(page.getByTestId("broker-readiness-count")).toContainText("7/8 ready");
  await expect(page.getByTestId("broker-readiness-item-paper-mode")).toContainText("Ready");
  await expect(page.getByTestId("broker-readiness-item-live-blocked")).toContainText("Ready");
  await expect(page.getByTestId("broker-readiness-item-auto-locked")).toContainText("Ready");
  await expect(page.getByTestId("broker-readiness-item-daily-pnl-context")).toContainText("Ready");
  await expect(page.getByTestId("broker-readiness-item-preflight-context")).toContainText("Advisory");
  await expect(page.getByTestId("broker-readiness-item-preflight-context")).toContainText("Run a dry run to populate advisory preflight context.");

  await page.getByTestId("broker-submit-dry-run").click();

  await expect(page.getByTestId("broker-readiness-count")).toContainText("8/8 ready");
  await expect(page.getByTestId("broker-readiness-item-preflight-context")).toContainText("Ready");
  await expect(page.getByTestId("broker-readiness-item-preflight-context")).toContainText("Dry run status: READY.");
});

test("MH-52: readiness checklist surfaces missing broker readiness items when state is unavailable", async ({ page }) => {
  await installBrokerMocks(
    page,
    null,
    null,
    { entries: [] },
    {
      dailyPnlResponse: null,
    },
    { entries: [], returned: 0, account_id: "DU123456", broker_mode: null },
  );

  await page.goto("/broker");

  await expect(page.getByTestId("broker-readiness-panel")).toBeVisible();
  await expect(page.getByTestId("broker-readiness-item-portfolio-snapshot")).toContainText("Ready");
  await expect(page.getByTestId("broker-readiness-item-paper-mode")).toContainText("Missing");
  await expect(page.getByTestId("broker-readiness-item-gateway")).toContainText("Missing");
  await expect(page.getByTestId("broker-readiness-item-manual-paper-submit")).toContainText("Missing");
  await expect(page.getByTestId("broker-readiness-item-daily-pnl-context")).toContainText("Missing");
  await expect(page.getByTestId("broker-readiness-item-preflight-context")).toContainText("Advisory");
});

// ── MH-53: Readiness Checklist Export / Copy Summary ───────────────────────

test("MH-53: readiness summary can be exported as JSON", async ({ page }) => {
  await installBrokerMocks(
    page,
    PAPER_READY_HEALTH,
    PAPER_CONTROL_RESPONSE,
    { entries: [] },
    {
      dailyPnlResponse: DAILY_PNL_RESPONSE,
    },
    MULTI_ENTRY_PROVENANCE_RESPONSE,
  );

  await page.goto("/broker");

  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByTestId("broker-readiness-export-json").click(),
  ]);

  await expect(download.suggestedFilename()).toMatch(/broker-readiness-\d+\.json/);

  const downloadPath = await download.path();
  expect(downloadPath).not.toBeNull();
  const text = await readFile(downloadPath as string, "utf-8");
  const payload = JSON.parse(text);
  expect(payload.total_count).toBe(8);
  expect(Array.isArray(payload.items)).toBeTruthy();
  expect(payload.items).toHaveLength(8);
  expect(payload.items[0]).toHaveProperty("id");
  expect(payload.items[0]).toHaveProperty("status");
});

test("MH-53: readiness summary copy action provides user feedback", async ({ page, context, browserName }) => {
  if (browserName !== "webkit") {
    await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  }

  await installBrokerMocks(
    page,
    PAPER_READY_HEALTH,
    PAPER_CONTROL_RESPONSE,
    { entries: [] },
    {
      dailyPnlResponse: DAILY_PNL_RESPONSE,
    },
    MULTI_ENTRY_PROVENANCE_RESPONSE,
  );

  await page.goto("/broker");
  await page.getByTestId("broker-readiness-copy-summary").click();
  await expect(page.getByTestId("broker-readiness-copy-state")).toContainText(/Copied readiness summary\.|Clipboard unavailable\./);
});

test("MH-53: readiness print summary action triggers browser print", async ({ page }) => {
  await page.addInitScript(() => {
    (window as Window & { __printCalls?: number }).__printCalls = 0;
    const originalPrint = window.print.bind(window);
    window.print = () => {
      (window as Window & { __printCalls?: number }).__printCalls = ((window as Window & { __printCalls?: number }).__printCalls ?? 0) + 1;
      return originalPrint();
    };
  });

  await installBrokerMocks(
    page,
    PAPER_READY_HEALTH,
    PAPER_CONTROL_RESPONSE,
    { entries: [] },
    {
      dailyPnlResponse: DAILY_PNL_RESPONSE,
    },
    MULTI_ENTRY_PROVENANCE_RESPONSE,
  );

  await page.goto("/broker");
  await page.getByTestId("broker-readiness-print-summary").click();

  const printCalls = await page.evaluate(() => (window as Window & { __printCalls?: number }).__printCalls ?? 0);
  expect(printCalls).toBe(1);
});

// ── MH-54: Broker Readiness History Snapshots ──────────────────────────────

test("MH-54: readiness snapshot can be saved locally and shown in history", async ({ page }) => {
  await installBrokerMocks(
    page,
    PAPER_READY_HEALTH,
    PAPER_CONTROL_RESPONSE,
    { entries: [] },
    {
      dailyPnlResponse: DAILY_PNL_RESPONSE,
    },
    MULTI_ENTRY_PROVENANCE_RESPONSE,
  );

  await page.goto("/broker");

  await expect(page.getByTestId("broker-readiness-history-empty")).toContainText("No local readiness snapshots saved yet.");
  await expect(page.getByTestId("broker-readiness-history-count")).toContainText("0 saved");

  await page.getByTestId("broker-readiness-save-snapshot").click();

  await expect(page.getByTestId("broker-readiness-history-count")).toContainText("1 saved");
  await expect(page.getByTestId("broker-readiness-history-item")).toHaveCount(1);
  await expect(page.getByTestId("broker-readiness-history-item").first()).toContainText("Broker readiness summary");

  const stored = await page.evaluate(() => window.localStorage.getItem("mh-broker-readiness-history"));
  expect(stored).not.toBeNull();
  const parsed = JSON.parse(stored as string);
  expect(Array.isArray(parsed)).toBeTruthy();
  expect(parsed).toHaveLength(1);
  expect(parsed[0]).toHaveProperty("captured_at");
  expect(parsed[0]).toHaveProperty("items");
});

test("MH-54: readiness history persists across reloads", async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem(
      "mh-broker-readiness-history",
      JSON.stringify([
        {
          id: "seeded-history-1",
          captured_at: "2026-04-29T12:00:00Z",
          ready_count: 6,
          total_count: 8,
          summary_text: "Broker readiness summary: 6/8 ready",
          items: [],
        },
      ]),
    );
  });

  await installBrokerMocks(
    page,
    PAPER_READY_HEALTH,
    PAPER_CONTROL_RESPONSE,
    { entries: [] },
    {
      dailyPnlResponse: DAILY_PNL_RESPONSE,
    },
    MULTI_ENTRY_PROVENANCE_RESPONSE,
  );

  await page.goto("/broker");

  await expect(page.getByTestId("broker-readiness-history-count")).toContainText("1 saved");
  await expect(page.getByTestId("broker-readiness-history-item")).toHaveCount(1);
  await expect(page.getByTestId("broker-readiness-history-item").first()).toContainText("6/8 ready");

  await page.reload();

  await expect(page.getByTestId("broker-readiness-history-count")).toContainText("1 saved");
  await expect(page.getByTestId("broker-readiness-history-item")).toHaveCount(1);
});

// ── MH-55: Broker Readiness History Export + Clear Controls ────────────────

test("MH-55: saved readiness history can be exported as JSON and CSV", async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem(
      "mh-broker-readiness-history",
      JSON.stringify([
        {
          id: "seeded-history-1",
          captured_at: "2026-04-29T12:00:00Z",
          ready_count: 6,
          total_count: 8,
          summary_text: "Broker readiness summary: 6/8 ready\nREADY - Portfolio snapshot loaded: 0 open positions loaded.",
          items: [],
        },
      ]),
    );
  });

  await installBrokerMocks(
    page,
    PAPER_READY_HEALTH,
    PAPER_CONTROL_RESPONSE,
    { entries: [] },
    {
      dailyPnlResponse: DAILY_PNL_RESPONSE,
    },
    MULTI_ENTRY_PROVENANCE_RESPONSE,
  );

  await page.goto("/broker");

  const [jsonDownload] = await Promise.all([
    page.waitForEvent("download"),
    page.getByTestId("broker-readiness-history-export-json").click(),
  ]);
  const jsonPath = await jsonDownload.path();
  expect(jsonPath).not.toBeNull();
  const jsonText = await readFile(jsonPath as string, "utf-8");
  const jsonPayload = JSON.parse(jsonText);
  expect(jsonPayload.snapshot_count).toBe(1);
  expect(jsonPayload.snapshots[0].id).toBe("seeded-history-1");

  const [csvDownload] = await Promise.all([
    page.waitForEvent("download"),
    page.getByTestId("broker-readiness-history-export-csv").click(),
  ]);
  const csvPath = await csvDownload.path();
  expect(csvPath).not.toBeNull();
  const csvText = await readFile(csvPath as string, "utf-8");
  expect(csvText).toContain("captured_at,ready_count,total_count,summary_text");
  expect(csvText).toContain("seeded-history-1");
  expect(csvText).toContain("Broker readiness summary: 6/8 ready");
});

test("MH-55: selected readiness snapshot summary can be copied", async ({ page, context, browserName }) => {
  if (browserName !== "webkit") {
    await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  }

  await page.addInitScript(() => {
    window.localStorage.setItem(
      "mh-broker-readiness-history",
      JSON.stringify([
        {
          id: "seeded-history-1",
          captured_at: "2026-04-29T12:00:00Z",
          ready_count: 6,
          total_count: 8,
          summary_text: "Broker readiness summary: 6/8 ready",
          items: [],
        },
        {
          id: "seeded-history-2",
          captured_at: "2026-04-29T13:00:00Z",
          ready_count: 7,
          total_count: 8,
          summary_text: "Broker readiness summary: 7/8 ready",
          items: [],
        },
      ]),
    );
  });

  await installBrokerMocks(
    page,
    PAPER_READY_HEALTH,
    PAPER_CONTROL_RESPONSE,
    { entries: [] },
    {
      dailyPnlResponse: DAILY_PNL_RESPONSE,
    },
    MULTI_ENTRY_PROVENANCE_RESPONSE,
  );

  await page.goto("/broker");
  await page.getByTestId("broker-readiness-history-item").nth(1).click();
  await page.getByTestId("broker-readiness-history-copy-selected").click();
  await expect(page.getByTestId("broker-readiness-history-copy-state")).toContainText(/Copied selected readiness snapshot\.|Clipboard unavailable\./);
});

test("MH-55: readiness history can be cleared with confirmation", async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem(
      "mh-broker-readiness-history",
      JSON.stringify([
        {
          id: "seeded-history-1",
          captured_at: "2026-04-29T12:00:00Z",
          ready_count: 6,
          total_count: 8,
          summary_text: "Broker readiness summary: 6/8 ready",
          items: [],
        },
      ]),
    );
  });

  await installBrokerMocks(
    page,
    PAPER_READY_HEALTH,
    PAPER_CONTROL_RESPONSE,
    { entries: [] },
    {
      dailyPnlResponse: DAILY_PNL_RESPONSE,
    },
    MULTI_ENTRY_PROVENANCE_RESPONSE,
  );

  await page.goto("/broker");

  await page.getByTestId("broker-readiness-history-clear").click();
  await expect(page.getByTestId("broker-readiness-history-clear-confirm")).toBeVisible();

  await page.getByTestId("broker-readiness-history-clear-confirm-no").click();
  await expect(page.getByTestId("broker-readiness-history-count")).toContainText("1 saved");

  await page.getByTestId("broker-readiness-history-clear").click();
  await page.getByTestId("broker-readiness-history-clear-confirm-yes").click();

  await expect(page.getByTestId("broker-readiness-history-count")).toContainText("0 saved");
  await expect(page.getByTestId("broker-readiness-history-empty")).toContainText("No local readiness snapshots saved yet.");

  const stored = await page.evaluate(() => window.localStorage.getItem("mh-broker-readiness-history"));
  expect(stored).toBe("[]");
});

// ── MH-56: Broker Readiness History Compare View ───────────────────────────

test("MH-56: compare view shows before vs after counts and changed readiness items", async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem(
      "mh-broker-readiness-history",
      JSON.stringify([
        {
          id: "latest-history",
          captured_at: "2026-04-29T14:00:00Z",
          ready_count: 7,
          total_count: 8,
          summary_text: "Broker readiness summary: 7/8 ready",
          items: [
            { id: "portfolio-snapshot", label: "Portfolio snapshot loaded", status: "ready", detail: "0 open positions loaded." },
            { id: "paper-mode", label: "Paper broker mode confirmed", status: "ready", detail: "Account DU123456 checked against broker paper-mode health." },
            { id: "gateway", label: "Gateway reachable", status: "ready", detail: "http://127.0.0.1:4002" },
            { id: "manual-paper-submit", label: "Manual paper submission available", status: "ready", detail: "Paper mode · Manual control." },
            { id: "live-blocked", label: "Live submission remains blocked", status: "ready", detail: "Live order submission blocked." },
            { id: "auto-locked", label: "Auto trading remains locked", status: "ready", detail: "Auto trading locked." },
            { id: "daily-pnl-context", label: "Daily P&L context available", status: "ready", detail: "3 snapshots loaded for today." },
            { id: "preflight-context", label: "Preflight advisory reviewed", status: "advisory", detail: "Run a dry run to populate advisory preflight context." },
          ],
        },
        {
          id: "older-history",
          captured_at: "2026-04-29T13:00:00Z",
          ready_count: 5,
          total_count: 8,
          summary_text: "Broker readiness summary: 5/8 ready",
          items: [
            { id: "portfolio-snapshot", label: "Portfolio snapshot loaded", status: "ready", detail: "0 open positions loaded." },
            { id: "paper-mode", label: "Paper broker mode confirmed", status: "ready", detail: "Account DU123456 checked against broker paper-mode health." },
            { id: "gateway", label: "Gateway reachable", status: "missing", detail: "Gateway health check failed." },
            { id: "manual-paper-submit", label: "Manual paper submission available", status: "ready", detail: "Paper mode · Manual control." },
            { id: "live-blocked", label: "Live submission remains blocked", status: "ready", detail: "Live order submission blocked." },
            { id: "auto-locked", label: "Auto trading remains locked", status: "ready", detail: "Auto trading locked." },
            { id: "daily-pnl-context", label: "Daily P&L context available", status: "advisory", detail: "No daily P&L snapshots available yet." },
            { id: "preflight-context", label: "Preflight advisory reviewed", status: "missing", detail: "Dry run invalid." },
          ],
        },
      ]),
    );
  });

  await installBrokerMocks(
    page,
    PAPER_READY_HEALTH,
    PAPER_CONTROL_RESPONSE,
    { entries: [] },
    {
      dailyPnlResponse: DAILY_PNL_RESPONSE,
    },
    MULTI_ENTRY_PROVENANCE_RESPONSE,
  );

  await page.goto("/broker");
  await expect(page.getByTestId("broker-readiness-compare-range")).toContainText("Select an older saved snapshot");

  await page.getByTestId("broker-readiness-history-item").nth(1).click();

  await expect(page.getByTestId("broker-readiness-compare-ready-count")).toContainText("5 -> 7");
  await expect(page.getByTestId("broker-readiness-compare-advisory-count")).toContainText("1 -> 1");
  await expect(page.getByTestId("broker-readiness-compare-missing-count")).toContainText("2 -> 0");
  await expect(page.getByTestId("broker-readiness-compare-change-item")).toHaveCount(3);
  await expect(page.getByTestId("broker-readiness-compare-panel")).toContainText("Gateway reachable");
  await expect(page.getByTestId("broker-readiness-compare-panel")).toContainText("Daily P&L context available");
  await expect(page.getByTestId("broker-readiness-compare-panel")).toContainText("Preflight advisory reviewed");
  await expect(page.getByTestId("broker-readiness-compare-change-improved")).toHaveCount(3);
});

test("MH-56: compare view highlights regressions when latest snapshot is worse", async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem(
      "mh-broker-readiness-history",
      JSON.stringify([
        {
          id: "latest-history",
          captured_at: "2026-04-29T14:00:00Z",
          ready_count: 5,
          total_count: 8,
          summary_text: "Broker readiness summary: 5/8 ready",
          items: [
            { id: "portfolio-snapshot", label: "Portfolio snapshot loaded", status: "ready", detail: "0 open positions loaded." },
            { id: "paper-mode", label: "Paper broker mode confirmed", status: "ready", detail: "Account DU123456 checked against broker paper-mode health." },
            { id: "gateway", label: "Gateway reachable", status: "missing", detail: "Gateway health check failed." },
            { id: "manual-paper-submit", label: "Manual paper submission available", status: "ready", detail: "Paper mode · Manual control." },
            { id: "live-blocked", label: "Live submission remains blocked", status: "ready", detail: "Live order submission blocked." },
            { id: "auto-locked", label: "Auto trading remains locked", status: "ready", detail: "Auto trading locked." },
            { id: "daily-pnl-context", label: "Daily P&L context available", status: "missing", detail: "Daily P&L context is unavailable." },
            { id: "preflight-context", label: "Preflight advisory reviewed", status: "advisory", detail: "Run a dry run to populate advisory preflight context." },
          ],
        },
        {
          id: "older-history",
          captured_at: "2026-04-29T13:00:00Z",
          ready_count: 7,
          total_count: 8,
          summary_text: "Broker readiness summary: 7/8 ready",
          items: [
            { id: "portfolio-snapshot", label: "Portfolio snapshot loaded", status: "ready", detail: "0 open positions loaded." },
            { id: "paper-mode", label: "Paper broker mode confirmed", status: "ready", detail: "Account DU123456 checked against broker paper-mode health." },
            { id: "gateway", label: "Gateway reachable", status: "ready", detail: "http://127.0.0.1:4002" },
            { id: "manual-paper-submit", label: "Manual paper submission available", status: "ready", detail: "Paper mode · Manual control." },
            { id: "live-blocked", label: "Live submission remains blocked", status: "ready", detail: "Live order submission blocked." },
            { id: "auto-locked", label: "Auto trading remains locked", status: "ready", detail: "Auto trading locked." },
            { id: "daily-pnl-context", label: "Daily P&L context available", status: "ready", detail: "3 snapshots loaded for today." },
            { id: "preflight-context", label: "Preflight advisory reviewed", status: "advisory", detail: "Run a dry run to populate advisory preflight context." },
          ],
        },
      ]),
    );
  });

  await installBrokerMocks(
    page,
    PAPER_READY_HEALTH,
    PAPER_CONTROL_RESPONSE,
    { entries: [] },
    {
      dailyPnlResponse: DAILY_PNL_RESPONSE,
    },
    MULTI_ENTRY_PROVENANCE_RESPONSE,
  );

  await page.goto("/broker");
  await page.getByTestId("broker-readiness-history-item").nth(1).click();

  await expect(page.getByTestId("broker-readiness-compare-ready-count")).toContainText("7 -> 5");
  await expect(page.getByTestId("broker-readiness-compare-missing-count")).toContainText("0 -> 2");
  await expect(page.getByTestId("broker-readiness-compare-change-regressed")).toHaveCount(2);
  await expect(page.getByTestId("broker-readiness-compare-panel")).toContainText("Gateway reachable");
  await expect(page.getByTestId("broker-readiness-compare-panel")).toContainText("Daily P&L context available");
});

// ── MH-57: Broker Readiness Timeline Mini Chart ────────────────────────────

test("MH-57: readiness timeline shows score trend and count-over-time details", async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem(
      "mh-broker-readiness-history",
      JSON.stringify([
        {
          id: "latest-history",
          captured_at: "2026-04-29T14:00:00Z",
          ready_count: 7,
          total_count: 8,
          summary_text: "Broker readiness summary: 7/8 ready",
          items: [
            { id: "portfolio-snapshot", label: "Portfolio snapshot loaded", status: "ready", detail: "0 open positions loaded." },
            { id: "paper-mode", label: "Paper broker mode confirmed", status: "ready", detail: "Account DU123456 checked against broker paper-mode health." },
            { id: "gateway", label: "Gateway reachable", status: "ready", detail: "http://127.0.0.1:4002" },
            { id: "manual-paper-submit", label: "Manual paper submission available", status: "ready", detail: "Paper mode · Manual control." },
            { id: "live-blocked", label: "Live submission remains blocked", status: "ready", detail: "Live order submission blocked." },
            { id: "auto-locked", label: "Auto trading remains locked", status: "ready", detail: "Auto trading locked." },
            { id: "daily-pnl-context", label: "Daily P&L context available", status: "ready", detail: "3 snapshots loaded for today." },
            { id: "preflight-context", label: "Preflight advisory reviewed", status: "advisory", detail: "Run a dry run to populate advisory preflight context." },
          ],
        },
        {
          id: "older-history",
          captured_at: "2026-04-29T13:00:00Z",
          ready_count: 5,
          total_count: 8,
          summary_text: "Broker readiness summary: 5/8 ready",
          items: [
            { id: "portfolio-snapshot", label: "Portfolio snapshot loaded", status: "ready", detail: "0 open positions loaded." },
            { id: "paper-mode", label: "Paper broker mode confirmed", status: "ready", detail: "Account DU123456 checked against broker paper-mode health." },
            { id: "gateway", label: "Gateway reachable", status: "missing", detail: "Gateway health check failed." },
            { id: "manual-paper-submit", label: "Manual paper submission available", status: "ready", detail: "Paper mode · Manual control." },
            { id: "live-blocked", label: "Live submission remains blocked", status: "ready", detail: "Live order submission blocked." },
            { id: "auto-locked", label: "Auto trading remains locked", status: "ready", detail: "Auto trading locked." },
            { id: "daily-pnl-context", label: "Daily P&L context available", status: "advisory", detail: "No daily P&L snapshots available yet." },
            { id: "preflight-context", label: "Preflight advisory reviewed", status: "missing", detail: "Dry run invalid." },
          ],
        },
      ]),
    );
  });

  await installBrokerMocks(
    page,
    PAPER_READY_HEALTH,
    PAPER_CONTROL_RESPONSE,
    { entries: [] },
    {
      dailyPnlResponse: DAILY_PNL_RESPONSE,
    },
    MULTI_ENTRY_PROVENANCE_RESPONSE,
  );

  await page.goto("/broker");
  await expect(page.getByTestId("broker-readiness-timeline-panel")).toBeVisible();
  await expect(page.getByTestId("broker-readiness-timeline-point")).toHaveCount(2);
  await expect(page.getByTestId("broker-readiness-timeline-bar")).toHaveCount(2);
  await expect(page.getByTestId("broker-readiness-timeline-detail")).toContainText("Ready: 7");
  await expect(page.getByTestId("broker-readiness-timeline-detail")).toContainText("Missing: 0");

  await page.getByTestId("broker-readiness-timeline-bar").first().click();
  await expect(page.getByTestId("broker-readiness-timeline-detail")).toContainText("Ready: 5");
  await expect(page.getByTestId("broker-readiness-timeline-detail")).toContainText("Missing: 2");
  await expect(page.getByTestId("broker-readiness-timeline-detail")).toContainText("Score: 63%");
});

test("MH-57: timeline renders visible single-point trend for one snapshot", async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem(
      "mh-broker-readiness-history",
      JSON.stringify([
        {
          id: "single-history",
          captured_at: "2026-04-29T14:00:00Z",
          ready_count: 6,
          total_count: 8,
          summary_text: "Broker readiness summary: 6/8 ready",
          items: [
            { id: "portfolio-snapshot", label: "Portfolio snapshot loaded", status: "ready", detail: "0 open positions loaded." },
            { id: "paper-mode", label: "Paper broker mode confirmed", status: "ready", detail: "Account DU123456 checked against broker paper-mode health." },
            { id: "gateway", label: "Gateway reachable", status: "ready", detail: "http://127.0.0.1:4002" },
            { id: "manual-paper-submit", label: "Manual paper submission available", status: "ready", detail: "Paper mode · Manual control." },
            { id: "live-blocked", label: "Live submission remains blocked", status: "ready", detail: "Live order submission blocked." },
            { id: "auto-locked", label: "Auto trading remains locked", status: "ready", detail: "Auto trading locked." },
            { id: "daily-pnl-context", label: "Daily P&L context available", status: "advisory", detail: "No daily P&L snapshots available yet." },
            { id: "preflight-context", label: "Preflight advisory reviewed", status: "missing", detail: "Dry run invalid." },
          ],
        },
      ]),
    );
  });

  await installBrokerMocks(
    page,
    PAPER_READY_HEALTH,
    PAPER_CONTROL_RESPONSE,
    { entries: [] },
    {
      dailyPnlResponse: DAILY_PNL_RESPONSE,
    },
    MULTI_ENTRY_PROVENANCE_RESPONSE,
  );

  await page.goto("/broker");
  await expect(page.getByTestId("broker-readiness-timeline-point")).toHaveCount(1);
  await expect(page.getByTestId("broker-readiness-timeline-line")).toBeVisible();
  await expect(page.getByTestId("broker-readiness-timeline-detail")).toContainText("Score: 75%");
});

// ── MH-58: Broker Readiness History Import ─────────────────────────────────

test("MH-58: readiness history import merges valid snapshots and deduplicates by id and timestamp", async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem(
      "mh-broker-readiness-history",
      JSON.stringify([
        {
          id: "existing-history",
          captured_at: "2026-04-29T13:00:00Z",
          ready_count: 6,
          total_count: 8,
          summary_text: "Broker readiness summary: 6/8 ready",
          items: [],
        },
      ]),
    );
  });

  await installBrokerMocks(
    page,
    PAPER_READY_HEALTH,
    PAPER_CONTROL_RESPONSE,
    { entries: [] },
    {
      dailyPnlResponse: DAILY_PNL_RESPONSE,
    },
    MULTI_ENTRY_PROVENANCE_RESPONSE,
  );

  await page.goto("/broker");

  await page.getByTestId("broker-readiness-history-import-input").setInputFiles({
    name: "readiness-history.json",
    mimeType: "application/json",
    buffer: Buffer.from(JSON.stringify({
      exported_at: "2026-04-29T15:00:00Z",
      snapshot_count: 3,
      snapshots: [
        {
          id: "existing-history",
          captured_at: "2026-04-29T13:00:00Z",
          ready_count: 6,
          total_count: 8,
          summary_text: "Broker readiness summary: 6/8 ready",
          items: [],
        },
        {
          id: "new-history-a",
          captured_at: "2026-04-29T14:00:00Z",
          ready_count: 7,
          total_count: 8,
          summary_text: "Broker readiness summary: 7/8 ready",
          items: [],
        },
        {
          id: "new-history-b",
          captured_at: "2026-04-29T14:00:00Z",
          ready_count: 5,
          total_count: 8,
          summary_text: "Broker readiness summary: 5/8 ready",
          items: [],
        },
      ],
    })),
  });

  await expect(page.getByTestId("broker-readiness-history-import-state")).toContainText("Imported 1 readiness snapshot.");
  await expect(page.getByTestId("broker-readiness-history-count")).toContainText("2 saved");
  await expect(page.getByTestId("broker-readiness-history-item")).toHaveCount(2);

  const stored = await page.evaluate(() => window.localStorage.getItem("mh-broker-readiness-history"));
  expect(stored).not.toBeNull();
  const parsed = JSON.parse(stored as string);
  expect(parsed).toHaveLength(2);
  expect(parsed[0].id).toBe("new-history-a");
  expect(parsed[1].id).toBe("existing-history");
});

test("MH-58: readiness history import rejects invalid snapshot shape", async ({ page }) => {
  await installBrokerMocks(
    page,
    PAPER_READY_HEALTH,
    PAPER_CONTROL_RESPONSE,
    { entries: [] },
    {
      dailyPnlResponse: DAILY_PNL_RESPONSE,
    },
    MULTI_ENTRY_PROVENANCE_RESPONSE,
  );

  await page.goto("/broker");

  await page.getByTestId("broker-readiness-history-import-input").setInputFiles({
    name: "invalid-readiness-history.json",
    mimeType: "application/json",
    buffer: Buffer.from(JSON.stringify({
      exported_at: "2026-04-29T15:00:00Z",
      snapshots: [
        {
          id: "broken-history",
          captured_at: "2026-04-29T14:00:00Z",
          ready_count: 7,
          total_count: 8,
          summary_text: "Broker readiness summary: 7/8 ready",
        },
      ],
    })),
  });

  await expect(page.getByTestId("broker-readiness-history-import-state")).toContainText("Import failed. Snapshot file format is invalid.");
  await expect(page.getByTestId("broker-readiness-history-count")).toContainText("0 saved");
});

test("MH-58: readiness history import rejects malformed JSON files", async ({ page }) => {
  await installBrokerMocks(
    page,
    PAPER_READY_HEALTH,
    PAPER_CONTROL_RESPONSE,
    { entries: [] },
    {
      dailyPnlResponse: DAILY_PNL_RESPONSE,
    },
    MULTI_ENTRY_PROVENANCE_RESPONSE,
  );

  await page.goto("/broker");

  await page.getByTestId("broker-readiness-history-import-input").setInputFiles({
    name: "malformed-readiness-history.json",
    mimeType: "application/json",
    buffer: Buffer.from("{not-json}"),
  });

  await expect(page.getByTestId("broker-readiness-history-import-state")).toContainText("Import failed. Snapshot file must be valid JSON.");
  await expect(page.getByTestId("broker-readiness-history-count")).toContainText("0 saved");
});

// ── MH-59: Broker Readiness History Backup Pack ────────────────────────────

test("MH-59: readiness backup pack export includes history, current state, provenance, and audit when loaded", async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem(
      "mh-broker-readiness-history",
      JSON.stringify([
        {
          id: "seeded-history-1",
          captured_at: "2026-04-29T12:00:00Z",
          ready_count: 6,
          total_count: 8,
          summary_text: "Broker readiness summary: 6/8 ready",
          items: [],
        },
      ]),
    );
  });

  await installBrokerMocks(
    page,
    PAPER_READY_HEALTH,
    PAPER_CONTROL_RESPONSE,
    {
      entries: [
        {
          ts: "2026-04-29T12:00:00Z",
          event: "broker_order_event",
          action: "dry_run",
          ticker: "AAPL",
          side: "BUY",
          quantity: 10,
          status: "ready",
          broker_order_id: null,
          reason: null,
          dry_run: true,
          issues: [],
        },
      ],
    },
    {
      dailyPnlResponse: DAILY_PNL_RESPONSE,
    },
    MULTI_ENTRY_PROVENANCE_RESPONSE,
  );

  await page.goto("/broker");

  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByTestId("broker-readiness-history-export-backup-pack").click(),
  ]);

  const downloadPath = await download.path();
  expect(downloadPath).not.toBeNull();
  const fileText = await readFile(downloadPath as string, "utf-8");
  const payload = JSON.parse(fileText);

  expect(payload.format).toBe("mh-broker-readiness-backup-pack-v1");
  expect(payload.snapshots).toHaveLength(1);
  expect(payload.snapshots[0].id).toBe("seeded-history-1");
  expect(payload.current_readiness.snapshot).toHaveProperty("summary_text");
  expect(payload.provenance_export.rows.length).toBeGreaterThan(0);
  expect(payload.audit_export.entries).toHaveLength(1);
});

test("MH-59: backup pack import merges snapshots from history and current readiness state", async ({ page }) => {
  await installBrokerMocks(
    page,
    PAPER_READY_HEALTH,
    PAPER_CONTROL_RESPONSE,
    { entries: [] },
    {
      dailyPnlResponse: DAILY_PNL_RESPONSE,
    },
    MULTI_ENTRY_PROVENANCE_RESPONSE,
  );

  await page.goto("/broker");

  await page.getByTestId("broker-readiness-history-import-input").setInputFiles({
    name: "backup-pack.json",
    mimeType: "application/json",
    buffer: Buffer.from(JSON.stringify({
      format: "mh-broker-readiness-backup-pack-v1",
      exported_at: "2026-04-29T15:00:00Z",
      snapshots: [
        {
          id: "backup-history-1",
          captured_at: "2026-04-29T13:00:00Z",
          ready_count: 6,
          total_count: 8,
          summary_text: "Broker readiness summary: 6/8 ready",
          items: [],
        },
      ],
      current_readiness: {
        snapshot: {
          id: "backup-current-1",
          captured_at: "2026-04-29T14:00:00Z",
          ready_count: 7,
          total_count: 8,
          summary_text: "Broker readiness summary: 7/8 ready",
          items: [],
        },
      },
      provenance_export: {
        exported_at: "2026-04-29T15:00:00Z",
        rows: [],
      },
      audit_export: {
        exported_at: "2026-04-29T15:00:00Z",
        entries: [],
      },
    })),
  });

  await expect(page.getByTestId("broker-readiness-history-import-state")).toContainText("Imported 2 readiness snapshots from backup pack.");
  await expect(page.getByTestId("broker-readiness-history-count")).toContainText("2 saved");
  await expect(page.getByTestId("broker-readiness-history-item")).toHaveCount(2);

  const stored = await page.evaluate(() => window.localStorage.getItem("mh-broker-readiness-history"));
  expect(stored).not.toBeNull();
  const parsed = JSON.parse(stored as string);
  expect(parsed).toHaveLength(2);
  expect(parsed[0].id).toBe("backup-current-1");
  expect(parsed[1].id).toBe("backup-history-1");
});

test("MH-59: backup pack import rejects invalid backup pack shape", async ({ page }) => {
  await installBrokerMocks(
    page,
    PAPER_READY_HEALTH,
    PAPER_CONTROL_RESPONSE,
    { entries: [] },
    {
      dailyPnlResponse: DAILY_PNL_RESPONSE,
    },
    MULTI_ENTRY_PROVENANCE_RESPONSE,
  );

  await page.goto("/broker");

  await page.getByTestId("broker-readiness-history-import-input").setInputFiles({
    name: "invalid-backup-pack.json",
    mimeType: "application/json",
    buffer: Buffer.from(JSON.stringify({
      format: "mh-broker-readiness-backup-pack-v1",
      exported_at: "2026-04-29T15:00:00Z",
      snapshots: [],
      current_readiness: {
        summary_text: "missing snapshot wrapper",
      },
    })),
  });

  await expect(page.getByTestId("broker-readiness-history-import-state")).toContainText("Import failed. Snapshot file format is invalid.");
  await expect(page.getByTestId("broker-readiness-history-count")).toContainText("0 saved");
});

// ── MH-60: Broker Local Backup Pack Viewer ─────────────────────────────────

test("MH-60: backup pack export shows local summary counts and metadata", async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem(
      "mh-broker-readiness-history",
      JSON.stringify([
        {
          id: "seeded-history-1",
          captured_at: "2026-04-29T12:00:00Z",
          ready_count: 6,
          total_count: 8,
          summary_text: "Broker readiness summary: 6/8 ready",
          items: [],
        },
      ]),
    );
  });

  await installBrokerMocks(
    page,
    PAPER_READY_HEALTH,
    PAPER_CONTROL_RESPONSE,
    {
      entries: [
        {
          ts: "2026-04-29T12:00:00Z",
          event: "broker_order_event",
          action: "dry_run",
          ticker: "AAPL",
          side: "BUY",
          quantity: 10,
          status: "ready",
          broker_order_id: null,
          reason: null,
          dry_run: true,
          issues: [],
        },
      ],
    },
    {
      dailyPnlResponse: DAILY_PNL_RESPONSE,
    },
    MULTI_ENTRY_PROVENANCE_RESPONSE,
  );

  await page.goto("/broker");
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByTestId("broker-readiness-history-export-backup-pack").click(),
  ]);
  expect(await download.path()).not.toBeNull();

  await expect(page.getByTestId("broker-readiness-backup-pack-summary")).toBeVisible();
  await expect(page.getByTestId("broker-readiness-backup-pack-summary-source")).toContainText("Last exported backup pack");
  await expect(page.getByTestId("broker-readiness-backup-pack-summary-snapshots")).toContainText("1");
  await expect(page.getByTestId("broker-readiness-backup-pack-summary-provenance")).toContainText("3");
  await expect(page.getByTestId("broker-readiness-backup-pack-summary-audit")).toContainText("1");
  await expect(page.getByTestId("broker-readiness-backup-pack-summary-account")).toContainText("DUP153837");
  await expect(page.getByTestId("broker-readiness-backup-pack-summary-mode")).toContainText("paper");
});

test("MH-60: backup pack import shows imported pack summary counts and metadata", async ({ page }) => {
  await installBrokerMocks(
    page,
    PAPER_READY_HEALTH,
    PAPER_CONTROL_RESPONSE,
    { entries: [] },
    {
      dailyPnlResponse: DAILY_PNL_RESPONSE,
    },
    MULTI_ENTRY_PROVENANCE_RESPONSE,
  );

  await page.goto("/broker");

  await page.getByTestId("broker-readiness-history-import-input").setInputFiles({
    name: "backup-pack-with-summary.json",
    mimeType: "application/json",
    buffer: Buffer.from(JSON.stringify({
      format: "mh-broker-readiness-backup-pack-v1",
      exported_at: "2026-04-29T15:00:00Z",
      metadata: {
        account_id: "DU999999",
        broker_mode: "paper",
      },
      snapshots: [
        {
          id: "backup-history-1",
          captured_at: "2026-04-29T13:00:00Z",
          ready_count: 6,
          total_count: 8,
          summary_text: "Broker readiness summary: 6/8 ready",
          items: [],
        },
      ],
      current_readiness: {
        snapshot: {
          id: "backup-current-1",
          captured_at: "2026-04-29T14:00:00Z",
          ready_count: 7,
          total_count: 8,
          summary_text: "Broker readiness summary: 7/8 ready",
          items: [],
        },
      },
      provenance_export: {
        exported_at: "2026-04-29T15:00:00Z",
        rows: [
          {
            event_fingerprint: "fp-1",
            external_trade_id: null,
            broker_order_id: null,
            symbol: "AAPL",
            side: "BUY",
            quantity: 10,
            fill_price: 120,
            commission: null,
            net_amount: null,
            realized_pnl: null,
            trade_ts: "2026-04-29T14:00:00Z",
            source: "broker",
            account_id: "DU999999",
            broker_provider: "ibkr",
            created_at: "2026-04-29T14:00:01Z",
          },
        ],
      },
      audit_export: {
        exported_at: "2026-04-29T15:00:00Z",
        entries: [
          {
            ts: "2026-04-29T12:00:00Z",
            event: "broker_order_event",
            action: "dry_run",
            ticker: "AAPL",
            side: "BUY",
            quantity: 10,
            status: "ready",
            broker_order_id: null,
            reason: null,
            dry_run: true,
            issues: [],
          },
        ],
      },
    })),
  });

  await expect(page.getByTestId("broker-readiness-backup-pack-summary")).toBeVisible();
  await expect(page.getByTestId("broker-readiness-backup-pack-summary-source")).toContainText("Last imported backup pack");
  await expect(page.getByTestId("broker-readiness-backup-pack-summary-snapshots")).toContainText("1");
  await expect(page.getByTestId("broker-readiness-backup-pack-summary-provenance")).toContainText("1");
  await expect(page.getByTestId("broker-readiness-backup-pack-summary-audit")).toContainText("1");
  await expect(page.getByTestId("broker-readiness-backup-pack-summary-account")).toContainText("DU999999");
  await expect(page.getByTestId("broker-readiness-backup-pack-summary-mode")).toContainText("paper");
});

// ── MH-61: Broker Local Backup Pack Detail Viewer ───────────────────────────

test("MH-61: backup pack export opens detail viewer and exports selected provenance section", async ({ page, context, browserName }) => {
  if (browserName !== "webkit") {
    await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  }

  await page.addInitScript(() => {
    window.localStorage.setItem(
      "mh-broker-readiness-history",
      JSON.stringify([
        {
          id: "seeded-history-1",
          captured_at: "2026-04-29T12:00:00Z",
          ready_count: 6,
          total_count: 8,
          summary_text: "Broker readiness summary: 6/8 ready",
          items: [],
        },
      ]),
    );
  });

  await installBrokerMocks(
    page,
    PAPER_READY_HEALTH,
    PAPER_CONTROL_RESPONSE,
    {
      entries: [
        {
          ts: "2026-04-29T12:00:00Z",
          event: "broker_order_event",
          action: "dry_run",
          ticker: "AAPL",
          side: "BUY",
          quantity: 10,
          status: "ready",
          broker_order_id: null,
          reason: null,
          dry_run: true,
          issues: [],
        },
      ],
    },
    {
      dailyPnlResponse: DAILY_PNL_RESPONSE,
    },
    MULTI_ENTRY_PROVENANCE_RESPONSE,
  );

  await page.goto("/broker");

  const [backupDownload] = await Promise.all([
    page.waitForEvent("download"),
    page.getByTestId("broker-readiness-history-export-backup-pack").click(),
  ]);
  expect(await backupDownload.path()).not.toBeNull();

  await expect(page.getByTestId("broker-readiness-backup-pack-detail")).toBeVisible();
  await expect(page.getByTestId("broker-readiness-backup-pack-current-snapshot")).toContainText("Broker readiness summary");
  await expect(page.getByTestId("broker-readiness-backup-pack-snapshot-item")).toHaveCount(1);

  await page.getByTestId("broker-readiness-backup-pack-detail-section-provenance").click();

  await expect(page.getByTestId("broker-readiness-backup-pack-detail-section-meta")).toContainText("3 provenance rows");
  await expect(page.getByTestId("broker-readiness-backup-pack-provenance-row")).toHaveCount(3);

  await page.getByTestId("broker-readiness-backup-pack-detail-copy-selected").click();
  await expect(page.getByTestId("broker-readiness-backup-pack-detail-copy-state")).toContainText(/Copied selected backup pack section\.|Clipboard unavailable\./);

  const [sectionDownload] = await Promise.all([
    page.waitForEvent("download"),
    page.getByTestId("broker-readiness-backup-pack-detail-export-selected").click(),
  ]);
  expect(await sectionDownload.suggestedFilename()).toMatch(/broker-readiness-backup-pack-provenance-\d+\.json/);

  const sectionDownloadPath = await sectionDownload.path();
  expect(sectionDownloadPath).not.toBeNull();
  const sectionText = await readFile(sectionDownloadPath as string, "utf-8");
  expect(sectionText).toContain('"section": "provenance"');
  expect(sectionText).toContain('"event_fingerprint"');
});

test("MH-61: imported backup pack detail viewer shows snapshots and audit rows", async ({ page }) => {
  await installBrokerMocks(
    page,
    PAPER_READY_HEALTH,
    PAPER_CONTROL_RESPONSE,
    { entries: [] },
    {
      dailyPnlResponse: DAILY_PNL_RESPONSE,
    },
    MULTI_ENTRY_PROVENANCE_RESPONSE,
  );

  await page.goto("/broker");

  await page.getByTestId("broker-readiness-history-import-input").setInputFiles({
    name: "backup-pack-with-detail.json",
    mimeType: "application/json",
    buffer: Buffer.from(JSON.stringify({
      format: "mh-broker-readiness-backup-pack-v1",
      exported_at: "2026-04-29T15:00:00Z",
      metadata: {
        account_id: "DU999999",
        broker_mode: "paper",
      },
      snapshots: [
        {
          id: "backup-history-1",
          captured_at: "2026-04-29T13:00:00Z",
          ready_count: 6,
          total_count: 8,
          summary_text: "Broker readiness summary: 6/8 ready",
          items: [],
        },
      ],
      current_readiness: {
        snapshot: {
          id: "backup-current-1",
          captured_at: "2026-04-29T14:00:00Z",
          ready_count: 7,
          total_count: 8,
          summary_text: "Broker readiness summary: 7/8 ready",
          items: [],
        },
      },
      provenance_export: {
        exported_at: "2026-04-29T15:00:00Z",
        rows: [
          {
            event_fingerprint: "fp-1",
            external_trade_id: null,
            broker_order_id: null,
            symbol: "AAPL",
            side: "BUY",
            quantity: 10,
            fill_price: 120,
            commission: null,
            net_amount: null,
            realized_pnl: null,
            trade_ts: "2026-04-29T14:00:00Z",
            source: "broker",
            account_id: "DU999999",
            broker_provider: "ibkr",
            created_at: "2026-04-29T14:00:01Z",
          },
        ],
      },
      audit_export: {
        exported_at: "2026-04-29T15:00:00Z",
        entries: [
          {
            ts: "2026-04-29T12:00:00Z",
            event: "broker_order_event",
            action: "dry_run",
            ticker: "AAPL",
            side: "BUY",
            quantity: 10,
            status: "ready",
            broker_order_id: null,
            reason: null,
            dry_run: true,
            issues: [],
          },
          {
            ts: "2026-04-29T12:05:00Z",
            event: "broker_order_event",
            action: "submit",
            ticker: "MSFT",
            side: "SELL",
            quantity: 5,
            status: "accepted",
            broker_order_id: "oid-2",
            reason: null,
            dry_run: false,
            issues: [{ code: "warn", message: "manual review" }],
          },
        ],
      },
    })),
  });

  await expect(page.getByTestId("broker-readiness-backup-pack-detail")).toBeVisible();
  await expect(page.getByTestId("broker-readiness-backup-pack-current-snapshot")).toContainText("7/8 ready");
  await expect(page.getByTestId("broker-readiness-backup-pack-snapshot-item")).toHaveCount(1);

  await page.getByTestId("broker-readiness-backup-pack-detail-section-audit").click();

  await expect(page.getByTestId("broker-readiness-backup-pack-detail-section-meta")).toContainText("2 audit rows");
  await expect(page.getByTestId("broker-readiness-backup-pack-audit-row")).toHaveCount(2);
  await expect(page.getByTestId("broker-readiness-backup-pack-detail-audit")).toContainText("MSFT SELL");
});

// ── MH-62: Broker Local Backup Pack Print / Human Review Report ────────────

test("MH-62: exported backup pack shows human review report and triggers print", async ({ page }) => {
  await page.addInitScript(() => {
    (window as Window & { __printCalls?: number }).__printCalls = 0;
    const originalPrint = window.print.bind(window);
    window.print = () => {
      (window as Window & { __printCalls?: number }).__printCalls = ((window as Window & { __printCalls?: number }).__printCalls ?? 0) + 1;
      return originalPrint();
    };

    window.localStorage.setItem(
      "mh-broker-readiness-history",
      JSON.stringify([
        {
          id: "seeded-history-1",
          captured_at: "2026-04-29T12:00:00Z",
          ready_count: 6,
          total_count: 8,
          summary_text: "Broker readiness summary: 6/8 ready",
          items: [],
        },
      ]),
    );
  });

  await installBrokerMocks(
    page,
    PAPER_READY_HEALTH,
    PAPER_CONTROL_RESPONSE,
    {
      entries: [
        {
          ts: "2026-04-29T12:00:00Z",
          event: "broker_order_event",
          action: "dry_run",
          ticker: "AAPL",
          side: "BUY",
          quantity: 10,
          status: "ready",
          broker_order_id: null,
          reason: null,
          dry_run: true,
          issues: [],
        },
      ],
    },
    {
      dailyPnlResponse: DAILY_PNL_RESPONSE,
    },
    MULTI_ENTRY_PROVENANCE_RESPONSE,
  );

  await page.goto("/broker");
  await page.getByTestId("broker-readiness-history-export-backup-pack").click();

  await expect(page.getByTestId("broker-readiness-backup-pack-report")).toBeVisible();
  await expect(page.getByTestId("broker-readiness-backup-pack-report-account")).toContainText("DUP153837");
  await expect(page.getByTestId("broker-readiness-backup-pack-report-mode")).toContainText("paper");
  await expect(page.getByTestId("broker-readiness-backup-pack-report-source")).toContainText("Last exported backup pack");
  await expect(page.getByTestId("broker-readiness-backup-pack-report-readiness")).toContainText("Current baseline");
  await expect(page.getByTestId("broker-readiness-backup-pack-report-snapshots")).toContainText("1 saved snapshot");
  await expect(page.getByTestId("broker-readiness-backup-pack-report-provenance")).toContainText("3 provenance rows");
  await expect(page.getByTestId("broker-readiness-backup-pack-report-audit")).toContainText("1 audit row");

  await page.getByTestId("broker-readiness-backup-pack-report-print").click();

  const printCalls = await page.evaluate(() => (window as Window & { __printCalls?: number }).__printCalls ?? 0);
  expect(printCalls).toBe(1);
});

test("MH-62: imported backup pack report includes generated metadata and section summaries", async ({ page }) => {
  await installBrokerMocks(
    page,
    PAPER_READY_HEALTH,
    PAPER_CONTROL_RESPONSE,
    { entries: [] },
    {
      dailyPnlResponse: DAILY_PNL_RESPONSE,
    },
    MULTI_ENTRY_PROVENANCE_RESPONSE,
  );

  await page.goto("/broker");

  await page.getByTestId("broker-readiness-history-import-input").setInputFiles({
    name: "backup-pack-human-review.json",
    mimeType: "application/json",
    buffer: Buffer.from(JSON.stringify({
      format: "mh-broker-readiness-backup-pack-v1",
      exported_at: "2026-04-29T15:00:00Z",
      metadata: {
        account_id: "DU999999",
        broker_mode: "paper",
      },
      snapshots: [
        {
          id: "backup-history-1",
          captured_at: "2026-04-29T13:00:00Z",
          ready_count: 6,
          total_count: 8,
          summary_text: "Broker readiness summary: 6/8 ready",
          items: [],
        },
        {
          id: "backup-history-2",
          captured_at: "2026-04-29T13:30:00Z",
          ready_count: 5,
          total_count: 8,
          summary_text: "Broker readiness summary: 5/8 ready",
          items: [],
        },
      ],
      current_readiness: {
        snapshot: {
          id: "backup-current-1",
          captured_at: "2026-04-29T14:00:00Z",
          ready_count: 7,
          total_count: 8,
          summary_text: "Broker readiness summary: 7/8 ready",
          items: [],
        },
      },
      provenance_export: {
        exported_at: "2026-04-29T15:00:00Z",
        rows: [
          {
            event_fingerprint: "fp-1",
            external_trade_id: null,
            broker_order_id: null,
            symbol: "AAPL",
            side: "BUY",
            quantity: 10,
            fill_price: 120,
            commission: null,
            net_amount: null,
            realized_pnl: null,
            trade_ts: "2026-04-29T14:00:00Z",
            source: "broker",
            account_id: "DU999999",
            broker_provider: "ibkr",
            created_at: "2026-04-29T14:00:01Z",
          },
          {
            event_fingerprint: "fp-2",
            external_trade_id: null,
            broker_order_id: null,
            symbol: "MSFT",
            side: "SELL",
            quantity: 5,
            fill_price: 210,
            commission: null,
            net_amount: null,
            realized_pnl: 15.5,
            trade_ts: "2026-04-29T14:05:00Z",
            source: "manual_entry",
            account_id: "DU999999",
            broker_provider: "ibkr",
            created_at: "2026-04-29T14:05:01Z",
          },
        ],
      },
      audit_export: {
        exported_at: "2026-04-29T15:00:00Z",
        entries: [
          {
            ts: "2026-04-29T12:00:00Z",
            event: "broker_order_event",
            action: "dry_run",
            ticker: "AAPL",
            side: "BUY",
            quantity: 10,
            status: "ready",
            broker_order_id: null,
            reason: null,
            dry_run: true,
            issues: [],
          },
          {
            ts: "2026-04-29T12:05:00Z",
            event: "broker_order_event",
            action: "submit",
            ticker: "MSFT",
            side: "SELL",
            quantity: 5,
            status: "accepted",
            broker_order_id: "oid-2",
            reason: null,
            dry_run: false,
            issues: [{ code: "warn", message: "manual review" }],
          },
        ],
      },
    })),
  });

  await expect(page.getByTestId("broker-readiness-backup-pack-report")).toBeVisible();
  await expect(page.getByTestId("broker-readiness-backup-pack-report-generated-at")).toContainText("Generated:");
  await expect(page.getByTestId("broker-readiness-backup-pack-report-account")).toContainText("DU999999");
  await expect(page.getByTestId("broker-readiness-backup-pack-report-mode")).toContainText("paper");
  await expect(page.getByTestId("broker-readiness-backup-pack-report-source")).toContainText("Last imported backup pack");
  await expect(page.getByTestId("broker-readiness-backup-pack-report-snapshots")).toContainText("2 saved snapshots");
  await expect(page.getByTestId("broker-readiness-backup-pack-report-provenance")).toContainText("2 provenance rows across 2 symbols");
  await expect(page.getByTestId("broker-readiness-backup-pack-report-audit")).toContainText("Dry run 1 · Submit 1 · Rows with issues 1");
});

// ── MH-63: Broker Local Backup Pack Report Export ──────────────────────────

test("MH-63: exported backup pack report can be copied and exported as markdown and text", async ({ page, context, browserName }) => {
  if (browserName !== "webkit") {
    await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  }

  await page.addInitScript(() => {
    window.localStorage.setItem(
      "mh-broker-readiness-history",
      JSON.stringify([
        {
          id: "seeded-history-1",
          captured_at: "2026-04-29T12:00:00Z",
          ready_count: 6,
          total_count: 8,
          summary_text: "Broker readiness summary: 6/8 ready",
          items: [],
        },
      ]),
    );
  });

  await installBrokerMocks(
    page,
    PAPER_READY_HEALTH,
    PAPER_CONTROL_RESPONSE,
    {
      entries: [
        {
          ts: "2026-04-29T12:00:00Z",
          event: "broker_order_event",
          action: "dry_run",
          ticker: "AAPL",
          side: "BUY",
          quantity: 10,
          status: "ready",
          broker_order_id: null,
          reason: null,
          dry_run: true,
          issues: [],
        },
      ],
    },
    {
      dailyPnlResponse: DAILY_PNL_RESPONSE,
    },
    MULTI_ENTRY_PROVENANCE_RESPONSE,
  );

  await page.goto("/broker");
  await page.getByTestId("broker-readiness-history-export-backup-pack").click();

  await page.getByTestId("broker-readiness-backup-pack-report-copy").click();
  await expect(page.getByTestId("broker-readiness-backup-pack-report-copy-state")).toContainText(/Copied full backup pack report\.|Clipboard unavailable\./);

  const [markdownDownload] = await Promise.all([
    page.waitForEvent("download"),
    page.getByTestId("broker-readiness-backup-pack-report-export-md").click(),
  ]);
  expect(await markdownDownload.suggestedFilename()).toMatch(/broker-readiness-backup-pack-report-\d+\.md/);
  const markdownPath = await markdownDownload.path();
  expect(markdownPath).not.toBeNull();
  const markdownText = await readFile(markdownPath as string, "utf-8");
  expect(markdownText).toContain("# Backup Pack Human Review Report");
  expect(markdownText).toContain("## Readiness Summary");
  expect(markdownText).toContain("Last exported backup pack");

  const [textDownload] = await Promise.all([
    page.waitForEvent("download"),
    page.getByTestId("broker-readiness-backup-pack-report-export-txt").click(),
  ]);
  expect(await textDownload.suggestedFilename()).toMatch(/broker-readiness-backup-pack-report-\d+\.txt/);
  const textPath = await textDownload.path();
  expect(textPath).not.toBeNull();
  const reportText = await readFile(textPath as string, "utf-8");
  expect(reportText).toContain("Backup Pack Human Review Report");
  expect(reportText).toContain("Account: DUP153837");
  expect(reportText).toContain("Local-only review artifact");
});

test("MH-63: imported backup pack report shows metadata footer", async ({ page }) => {
  await installBrokerMocks(
    page,
    PAPER_READY_HEALTH,
    PAPER_CONTROL_RESPONSE,
    { entries: [] },
    {
      dailyPnlResponse: DAILY_PNL_RESPONSE,
    },
    MULTI_ENTRY_PROVENANCE_RESPONSE,
  );

  await page.goto("/broker");

  await page.getByTestId("broker-readiness-history-import-input").setInputFiles({
    name: "backup-pack-report-export.json",
    mimeType: "application/json",
    buffer: Buffer.from(JSON.stringify({
      format: "mh-broker-readiness-backup-pack-v1",
      exported_at: "2026-04-29T15:00:00Z",
      metadata: {
        account_id: "DU999999",
        broker_mode: "paper",
      },
      snapshots: [],
      current_readiness: {
        snapshot: {
          id: "backup-current-1",
          captured_at: "2026-04-29T14:00:00Z",
          ready_count: 7,
          total_count: 8,
          summary_text: "Broker readiness summary: 7/8 ready",
          items: [],
        },
      },
      provenance_export: {
        exported_at: "2026-04-29T15:00:00Z",
        rows: [],
      },
      audit_export: {
        exported_at: "2026-04-29T15:00:00Z",
        entries: [],
      },
    })),
  });

  await expect(page.getByTestId("broker-readiness-backup-pack-report-footer")).toContainText("Local-only review artifact generated from mh-broker-readiness-backup-pack-v1");
});

