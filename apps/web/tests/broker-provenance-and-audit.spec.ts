import { readFile } from "node:fs/promises";

import { expect, test } from "@playwright/test";

import {
  MULTI_ENTRY_PROVENANCE_RESPONSE,
  NORMALIZED_TRADE_PROVENANCE_RESPONSE,
  PAPER_CONTROL_RESPONSE,
  PAPER_READY_HEALTH,
  installBrokerMocks,
} from "./broker-test-helpers";

test("MH-32: broker audit panel renders recent events", async ({ page }) => {
  await installBrokerMocks(
    page,
    {
      status: "paper_ready",
      mode_guard_ok: true,
      gateway_reachable: true,
      gateway_url: "https://localhost:5001/v1/api",
      account_id: "DUP153837",
      account_is_paper: true,
      broker_mode: {
        broker: "ibkr",
        mode: "paper",
        live_execution_enabled: false,
        paper_trading_enabled: true,
      },
    },
    PAPER_CONTROL_RESPONSE,
    {
      entries: [
        {
          ts: "2026-04-28T10:00:00Z",
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
          ts: "2026-04-28T10:01:00Z",
          event: "broker_order_event",
          action: "submit",
          ticker: "AAPL",
          side: "BUY",
          quantity: 10,
          status: "SUBMITTED",
          broker_order_id: "PAPER-123",
          reason: null,
          dry_run: false,
          issues: [],
        },
      ],
    },
  );

  await page.goto("/broker");
  await expect(page.getByTestId("broker-audit-panel")).toBeVisible();
  await expect(page.getByTestId("broker-audit-count")).toContainText("2 events");
  await expect(page.getByTestId("broker-audit-row")).toHaveCount(2);
  await expect(page.getByTestId("broker-audit-panel")).toContainText("PAPER-123");
  await expect(page.getByTestId("broker-audit-panel")).toContainText("Dry Run");
});

test("MH-32: broker audit panel shows empty state", async ({ page }) => {
  await installBrokerMocks(page, {
    status: "paper_ready",
    mode_guard_ok: true,
    gateway_reachable: true,
    gateway_url: "https://localhost:5001/v1/api",
    account_id: "DUP153837",
    account_is_paper: true,
    broker_mode: {
      broker: "ibkr",
      mode: "paper",
      live_execution_enabled: false,
      paper_trading_enabled: true,
    },
  }, PAPER_CONTROL_RESPONSE, { entries: [] });

  await page.goto("/broker");
  await expect(page.getByTestId("broker-audit-panel")).toContainText("No broker order audit events yet.");
});

test("MH-32: broker audit panel shows unavailable state", async ({ page }) => {
  await installBrokerMocks(
    page,
    {
      status: "paper_ready",
      mode_guard_ok: true,
      gateway_reachable: true,
      gateway_url: "https://localhost:5001/v1/api",
      account_id: "DUP153837",
      account_is_paper: true,
      broker_mode: {
        broker: "ibkr",
        mode: "paper",
        live_execution_enabled: false,
        paper_trading_enabled: true,
      },
    },
    PAPER_CONTROL_RESPONSE,
    null,
  );

  await page.goto("/broker");
  await expect(page.getByTestId("broker-audit-panel")).toContainText("Audit trail unavailable.");
});
test("MH-48: normalized trade provenance panel renders broker trade event rows", async ({ page }) => {
  await installBrokerMocks(
    page,
    PAPER_READY_HEALTH,
    PAPER_CONTROL_RESPONSE,
    { entries: [] },
    undefined,
    NORMALIZED_TRADE_PROVENANCE_RESPONSE,
  );

  await page.goto("/broker");

  await expect(page.getByTestId("broker-trade-provenance-panel")).toBeVisible();
  await expect(page.getByTestId("broker-trade-provenance-count")).toContainText("1 events");
  await expect(page.getByTestId("broker-trade-provenance-row")).toHaveCount(1);
  await expect(page.getByTestId("broker-trade-provenance-panel")).toContainText("fp-abc-123");
  await expect(page.getByTestId("broker-trade-provenance-panel")).toContainText("AAPL");
  await expect(page.getByTestId("broker-trade-provenance-panel")).toContainText("BUY");
  await expect(page.getByTestId("broker-trade-provenance-panel")).toContainText("broker_account_trades");
});

test("MH-48: normalized trade provenance panel shows empty state", async ({ page }) => {
  await installBrokerMocks(page, PAPER_READY_HEALTH, PAPER_CONTROL_RESPONSE, { entries: [] });
  await page.goto("/broker");
  await expect(page.getByTestId("broker-trade-provenance-panel")).toContainText("No normalized trade events yet.");
});

test("MH-48: normalized trade provenance panel shows unavailable state", async ({ page }) => {
  await installBrokerMocks(page, PAPER_READY_HEALTH, PAPER_CONTROL_RESPONSE, { entries: [] }, undefined, null);
  await page.goto("/broker");
  await expect(page.getByTestId("broker-trade-provenance-panel")).toContainText("Normalized trade provenance unavailable.");
});

test("MH-49: provenance filter bar is visible when entries exist", async ({ page }) => {
  await installBrokerMocks(
    page,
    PAPER_READY_HEALTH,
    PAPER_CONTROL_RESPONSE,
    { entries: [] },
    undefined,
    MULTI_ENTRY_PROVENANCE_RESPONSE,
  );
  await page.goto("/broker");
  await expect(page.getByTestId("broker-trade-provenance-filters")).toBeVisible();
  await expect(page.getByTestId("broker-trade-provenance-filter-symbol")).toBeVisible();
  await expect(page.getByTestId("broker-trade-provenance-filter-source")).toBeVisible();
  await expect(page.getByTestId("broker-trade-provenance-filter-account")).toBeVisible();
  await expect(page.getByTestId("broker-trade-provenance-filter-pnl-only")).toBeVisible();
});

test("MH-49: symbol filter hides non-matching rows", async ({ page }) => {
  await installBrokerMocks(
    page,
    PAPER_READY_HEALTH,
    PAPER_CONTROL_RESPONSE,
    { entries: [] },
    undefined,
    MULTI_ENTRY_PROVENANCE_RESPONSE,
  );
  await page.goto("/broker");

  await expect(page.getByTestId("broker-trade-provenance-row")).toHaveCount(3);

  await page.getByTestId("broker-trade-provenance-filter-symbol").fill("AAPL");

  await expect(page.getByTestId("broker-trade-provenance-row")).toHaveCount(1);
  await expect(page.getByTestId("broker-trade-provenance-panel")).toContainText("AAPL");
  await expect(page.getByTestId("broker-trade-provenance-panel")).not.toContainText("MSFT");
  await expect(page.getByTestId("broker-trade-provenance-panel")).not.toContainText("TSLA");
});

test("MH-49: source filter hides non-matching rows", async ({ page }) => {
  await installBrokerMocks(
    page,
    PAPER_READY_HEALTH,
    PAPER_CONTROL_RESPONSE,
    { entries: [] },
    undefined,
    MULTI_ENTRY_PROVENANCE_RESPONSE,
  );
  await page.goto("/broker");

  await page.getByTestId("broker-trade-provenance-filter-source").fill("manual_entry");

  await expect(page.getByTestId("broker-trade-provenance-row")).toHaveCount(1);
  await expect(page.getByTestId("broker-trade-provenance-panel")).toContainText("TSLA");
});

test("MH-49: account filter hides non-matching rows", async ({ page }) => {
  await installBrokerMocks(
    page,
    PAPER_READY_HEALTH,
    PAPER_CONTROL_RESPONSE,
    { entries: [] },
    undefined,
    MULTI_ENTRY_PROVENANCE_RESPONSE,
  );
  await page.goto("/broker");

  await page.getByTestId("broker-trade-provenance-filter-account").fill("DU999999");

  await expect(page.getByTestId("broker-trade-provenance-row")).toHaveCount(1);
  await expect(page.getByTestId("broker-trade-provenance-panel")).toContainText("TSLA");
});

test("MH-49: P&L present filter hides rows without realized_pnl", async ({ page }) => {
  await installBrokerMocks(
    page,
    PAPER_READY_HEALTH,
    PAPER_CONTROL_RESPONSE,
    { entries: [] },
    undefined,
    MULTI_ENTRY_PROVENANCE_RESPONSE,
  );
  await page.goto("/broker");

  await expect(page.getByTestId("broker-trade-provenance-row")).toHaveCount(3);

  await page.getByTestId("broker-trade-provenance-filter-pnl-only").check();

  // MSFT has realized_pnl: null, should be hidden
  await expect(page.getByTestId("broker-trade-provenance-row")).toHaveCount(2);
  await expect(page.getByTestId("broker-trade-provenance-panel")).not.toContainText("MSFT");
});

test("MH-49: filtered-empty message shown when no rows match filter", async ({ page }) => {
  await installBrokerMocks(
    page,
    PAPER_READY_HEALTH,
    PAPER_CONTROL_RESPONSE,
    { entries: [] },
    undefined,
    MULTI_ENTRY_PROVENANCE_RESPONSE,
  );
  await page.goto("/broker");

  await page.getByTestId("broker-trade-provenance-filter-symbol").fill("ZZZZZ");

  await expect(page.getByTestId("broker-trade-provenance-row")).toHaveCount(0);
  await expect(page.getByTestId("broker-trade-provenance-filtered-empty")).toContainText("No events match the current filters.");
});

test("MH-49: clicking a provenance row opens event detail drawer", async ({ page }) => {
  await installBrokerMocks(
    page,
    PAPER_READY_HEALTH,
    PAPER_CONTROL_RESPONSE,
    { entries: [] },
    undefined,
    NORMALIZED_TRADE_PROVENANCE_RESPONSE,
  );
  await page.goto("/broker");

  await expect(page.getByTestId("broker-trade-provenance-drawer")).not.toBeVisible();

  await page.getByTestId("broker-trade-provenance-row").first().click();

  await expect(page.getByTestId("broker-trade-provenance-drawer")).toBeVisible();
  await expect(page.getByTestId("broker-trade-provenance-drawer-fingerprint")).toContainText("fp-abc-123");
  await expect(page.getByTestId("broker-trade-provenance-drawer")).toContainText("AAPL");
  await expect(page.getByTestId("broker-trade-provenance-drawer")).toContainText("BUY");
  await expect(page.getByTestId("broker-trade-provenance-drawer")).toContainText("broker_account_trades");
  await expect(page.getByTestId("broker-trade-provenance-drawer")).toContainText("DU123456");
});

test("MH-49: event detail drawer can be closed via close button", async ({ page }) => {
  await installBrokerMocks(
    page,
    PAPER_READY_HEALTH,
    PAPER_CONTROL_RESPONSE,
    { entries: [] },
    undefined,
    NORMALIZED_TRADE_PROVENANCE_RESPONSE,
  );
  await page.goto("/broker");

  await page.getByTestId("broker-trade-provenance-row").first().click();
  await expect(page.getByTestId("broker-trade-provenance-drawer")).toBeVisible();

  await page.getByTestId("broker-trade-provenance-drawer-close").click();
  await expect(page.getByTestId("broker-trade-provenance-drawer")).not.toBeVisible();
});

test("MH-49: event detail drawer can be dismissed by clicking overlay", async ({ page }) => {
  await installBrokerMocks(
    page,
    PAPER_READY_HEALTH,
    PAPER_CONTROL_RESPONSE,
    { entries: [] },
    undefined,
    NORMALIZED_TRADE_PROVENANCE_RESPONSE,
  );
  await page.goto("/broker");

  await page.getByTestId("broker-trade-provenance-row").first().click();
  await expect(page.getByTestId("broker-trade-provenance-drawer")).toBeVisible();

  await page.getByTestId("broker-trade-provenance-drawer-overlay").click({ position: { x: 10, y: 10 } });
  await expect(page.getByTestId("broker-trade-provenance-drawer")).not.toBeVisible();
});

test("MH-49: no submit changes added", async ({ page }) => {
  await installBrokerMocks(page, PAPER_READY_HEALTH, PAPER_CONTROL_RESPONSE, { entries: [] }, undefined, MULTI_ENTRY_PROVENANCE_RESPONSE);
  await page.goto("/broker");
  await expect(page.getByTestId("broker-trade-provenance-drawer")).not.toBeVisible();
  // Drawer has no submit/action buttons
  await page.getByTestId("broker-trade-provenance-row").first().click();
  await expect(page.getByTestId("broker-trade-provenance-drawer")).toBeVisible();
  await expect(page.getByTestId("broker-trade-provenance-drawer").getByRole("button", { name: /submit|trade|buy|sell|execute/i })).toHaveCount(0);
});

// ── MH-50: Provenance Export + Reconciliation Notes ─────────────────────────

test("MH-50: export JSON downloads filtered provenance rows", async ({ page }) => {
  await installBrokerMocks(
    page,
    PAPER_READY_HEALTH,
    PAPER_CONTROL_RESPONSE,
    { entries: [] },
    undefined,
    MULTI_ENTRY_PROVENANCE_RESPONSE,
  );
  await page.goto("/broker");

  await page.getByTestId("broker-trade-provenance-filter-symbol").fill("AAPL");

  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByTestId("broker-trade-provenance-export-json").click(),
  ]);

  await expect(download.suggestedFilename()).toMatch(/broker-trade-provenance-\d+\.json/);

  const downloadPath = await download.path();
  expect(downloadPath).not.toBeNull();
  const text = await readFile(downloadPath as string, "utf-8");
  const payload = JSON.parse(text);
  expect(Array.isArray(payload.rows)).toBeTruthy();
  expect(payload.rows).toHaveLength(1);
  expect(payload.rows[0].symbol).toBe("AAPL");
  expect(payload.filters.symbol).toBe("AAPL");
});

test("MH-50: export CSV downloads filtered provenance rows", async ({ page }) => {
  await installBrokerMocks(
    page,
    PAPER_READY_HEALTH,
    PAPER_CONTROL_RESPONSE,
    { entries: [] },
    undefined,
    MULTI_ENTRY_PROVENANCE_RESPONSE,
  );
  await page.goto("/broker");

  await page.getByTestId("broker-trade-provenance-filter-source").fill("manual_entry");

  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByTestId("broker-trade-provenance-export-csv").click(),
  ]);

  await expect(download.suggestedFilename()).toMatch(/broker-trade-provenance-\d+\.csv/);

  const downloadPath = await download.path();
  expect(downloadPath).not.toBeNull();
  const text = await readFile(downloadPath as string, "utf-8");
  expect(text).toContain("event_fingerprint");
  expect(text).toContain("fp-abc-003");
  expect(text).toContain("manual_entry");
  expect(text).not.toContain("fp-abc-001");
});

test("MH-50: drawer copy action provides user feedback", async ({ page, context, browserName }) => {
  if (browserName !== "webkit") {
    await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  }

  await installBrokerMocks(
    page,
    PAPER_READY_HEALTH,
    PAPER_CONTROL_RESPONSE,
    { entries: [] },
    undefined,
    NORMALIZED_TRADE_PROVENANCE_RESPONSE,
  );
  await page.goto("/broker");

  await page.getByTestId("broker-trade-provenance-row").first().click();
  await page.getByTestId("broker-trade-provenance-drawer-copy").click();

  await expect(page.getByTestId("broker-trade-provenance-drawer-copy-state")).toContainText(/Copied\.|Clipboard unavailable\./);
});

test("MH-50: drawer shows reconciliation notes based on available fields", async ({ page }) => {
  await installBrokerMocks(
    page,
    PAPER_READY_HEALTH,
    PAPER_CONTROL_RESPONSE,
    { entries: [] },
    undefined,
    MULTI_ENTRY_PROVENANCE_RESPONSE,
  );
  await page.goto("/broker");

  await page.getByTestId("broker-trade-provenance-filter-symbol").fill("MSFT");
  await page.getByTestId("broker-trade-provenance-row").first().click();

  await expect(page.getByTestId("broker-trade-provenance-reconciliation-notes")).toBeVisible();
  await expect(page.getByTestId("broker-trade-provenance-reconciliation-notes")).toContainText("Realized P&L is missing from this event");
  await expect(page.getByTestId("broker-trade-provenance-reconciliation-notes")).toContainText("Broker/external identifiers present for reconciliation");
});

// ── MH-51: Broker Review Dashboard Polish ───────────────────────────────────
