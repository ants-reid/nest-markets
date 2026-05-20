import { expect, test, type Request } from "@playwright/test";

import {
  ACCOUNT_RESPONSE,
  DAILY_PNL_RESPONSE,
  PAPER_CONTROL_RESPONSE,
  PAPER_READY_HEALTH,
  RICH_DRY_RUN_RESPONSE,
  installBrokerMocks,
} from "./broker-test-helpers";

function isBrokerApiRequest(request: Request) {
  const url = new URL(request.url());
  return !request.isNavigationRequest() && url.pathname.startsWith("/broker/");
}

test("MH-33: manual submit flow runs dry-run then submits order", async ({ page }) => {
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
  });

  await page.goto("/broker");

  await page.getByTestId("broker-submit-order-type").selectOption("LIMIT");
  await page.getByTestId("broker-submit-limit-price").fill("181.25");
  await page.getByTestId("broker-submit-quantity").fill("12");

  await page.getByTestId("broker-submit-dry-run").click();
  await expect(page.getByTestId("broker-submit-dry-run-result")).toContainText("READY");

  // MH-34: confirmation step before submit
  await page.getByTestId("broker-submit-order").click();
  await expect(page.getByTestId("broker-submit-confirm-panel")).toBeVisible();
  await expect(page.getByTestId("broker-submit-confirm-panel")).toContainText("BUY 12");

  await page.getByTestId("broker-submit-confirm").click();
  await expect(page.getByTestId("broker-submit-success")).toContainText("Order submitted");
});

test("MH-33: submit blocked if dry-run not ready", async ({ page }) => {
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
    { entries: [] },
    {
      dryRunResponse: {
        status: "invalid",
        mode_guard_ok: true,
        request_valid: false,
        estimated_notional: null,
        issues: [{ code: "invalid_quantity", message: "Quantity must be > 0" }],
        broker_mode: {
          broker: "ibkr",
          mode: "paper",
          live_execution_enabled: false,
          paper_trading_enabled: true,
        },
      },
      submitResponse: {
        broker_order_id: "SHOULD-NOT-HAPPEN",
        status: "SUBMITTED",
        filled_price: null,
        filled_quantity: null,
        error_message: null,
        broker_mode: {
          broker: "ibkr",
          mode: "paper",
          live_execution_enabled: false,
          paper_trading_enabled: true,
        },
      },
    },
  );

  await page.goto("/broker");
  // Use a valid quantity so client-side validation passes; server returns invalid dry-run
  await page.getByTestId("broker-submit-quantity").fill("1");
  await page.getByTestId("broker-submit-dry-run").click();
  await expect(page.getByTestId("broker-submit-dry-run-result")).toContainText("INVALID");

  await page.getByTestId("broker-submit-order").click();
  await expect(page.getByTestId("broker-submit-error")).toContainText("Run a successful dry run before submitting.");
});

// ── MH-34 tests ───────────────────────────────────────────────────────────────
test("MH-34: dry-run blocked by client validation when ticker is empty", async ({ page }) => {
  await installBrokerMocks(page, PAPER_READY_HEALTH);
  await page.goto("/broker");

  await page.getByTestId("broker-submit-ticker").fill("");
  await page.getByTestId("broker-submit-dry-run").click();

  await expect(page.getByTestId("broker-submit-ticker-error")).toContainText("Symbol is required");
  await expect(page.getByTestId("broker-submit-dry-run-result")).not.toBeVisible();
});

test("MH-34: dry-run blocked by client validation when quantity is zero", async ({ page }) => {
  await installBrokerMocks(page, PAPER_READY_HEALTH);
  await page.goto("/broker");

  await page.getByTestId("broker-submit-quantity").fill("0");
  await page.getByTestId("broker-submit-dry-run").click();

  await expect(page.getByTestId("broker-submit-quantity-error")).toContainText("Quantity must be a positive whole number");
  await expect(page.getByTestId("broker-submit-dry-run-result")).not.toBeVisible();
});

test("MH-34: dry-run blocked by client validation when limit price is missing", async ({ page }) => {
  await installBrokerMocks(page, PAPER_READY_HEALTH);
  await page.goto("/broker");

  await page.getByTestId("broker-submit-order-type").selectOption("LIMIT");
  // leave limit price empty
  await page.getByTestId("broker-submit-dry-run").click();

  await expect(page.getByTestId("broker-submit-limit-price-error")).toContainText("Limit price must be > 0");
  await expect(page.getByTestId("broker-submit-dry-run-result")).not.toBeVisible();
});

test("MH-34: dry-run issues shown inline when server returns invalid", async ({ page }) => {
  await installBrokerMocks(
    page,
    PAPER_READY_HEALTH,
    PAPER_CONTROL_RESPONSE,
    { entries: [] },
    {
      dryRunResponse: {
        status: "invalid",
        mode_guard_ok: false,
        request_valid: true,
        estimated_notional: null,
        issues: [
          { code: "mode_guard_fail", message: "Broker is not in paper mode" },
          { code: "account_mismatch", message: "Account is not a paper account" },
        ],
        broker_mode: {
          broker: "ibkr",
          mode: "live",
          live_execution_enabled: true,
          paper_trading_enabled: false,
        },
      },
    },
  );

  await page.goto("/broker");
  await page.getByTestId("broker-submit-dry-run").click();

  await expect(page.getByTestId("broker-submit-dry-run-result")).toContainText("INVALID");
  await expect(page.getByTestId("broker-submit-dry-run-issues")).toBeVisible();
  await expect(page.getByTestId("broker-submit-dry-run-issues")).toContainText("Broker is not in paper mode");
  await expect(page.getByTestId("broker-submit-dry-run-issues")).toContainText("Account is not a paper account");
});

test("MH-34: confirmation step can be cancelled before submit", async ({ page }) => {
  await installBrokerMocks(page, PAPER_READY_HEALTH);
  await page.goto("/broker");

  await page.getByTestId("broker-submit-dry-run").click();
  await expect(page.getByTestId("broker-submit-dry-run-result")).toContainText("READY");

  await page.getByTestId("broker-submit-order").click();
  await expect(page.getByTestId("broker-submit-confirm-panel")).toBeVisible();

  await page.getByTestId("broker-submit-cancel").click();
  await expect(page.getByTestId("broker-submit-confirm-panel")).not.toBeVisible();
  await expect(page.getByTestId("broker-submit-order")).toBeVisible();
  await expect(page.getByTestId("broker-submit-success")).not.toBeVisible();
});

test("MH-34: form resets after successful submit", async ({ page }) => {
  await installBrokerMocks(page, PAPER_READY_HEALTH);
  await page.goto("/broker");

  await page.getByTestId("broker-submit-ticker").fill("TSLA");
  await page.getByTestId("broker-submit-quantity").fill("5");

  await page.getByTestId("broker-submit-dry-run").click();
  await expect(page.getByTestId("broker-submit-dry-run-result")).toContainText("READY");

  await page.getByTestId("broker-submit-order").click();
  await page.getByTestId("broker-submit-confirm").click();
  await expect(page.getByTestId("broker-submit-success")).toContainText("Order submitted");

  // Form fields should be reset to empty; dry-run result cleared
  await expect(page.getByTestId("broker-submit-ticker")).toHaveValue("");
  await expect(page.getByTestId("broker-submit-quantity")).toHaveValue("");
  await expect(page.getByTestId("broker-submit-dry-run-result")).not.toBeVisible();
});

test("MH-42: dry-run sends advisory context when account/positions are loaded", async ({ page }) => {
  let capturedBody: unknown = null;

  await page.route("**/broker/**", async (route) => {
    if (!isBrokerApiRequest(route.request())) {
      await route.continue();
      return;
    }

    const url = new URL(route.request().url());
    if (url.pathname === "/broker/account") {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(ACCOUNT_RESPONSE) });
      return;
    }
    if (url.pathname === "/broker/positions") {
      await route.fulfill({
        status: 200, contentType: "application/json",
        body: JSON.stringify([
          { conid: 1, ticker: "TSLA", side: "BUY", quantity: 5, avg_cost: 200, market_price: 210, market_value: 1050, unrealized_pnl: 50, asset_class: "STK", currency: "USD" },
        ]),
      });
      return;
    }
    if (url.pathname === "/broker/health") {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ ...PAPER_READY_HEALTH }) });
      return;
    }
    if (url.pathname === "/broker/control") {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(PAPER_CONTROL_RESPONSE) });
      return;
    }
    if (url.pathname === "/broker/orders/audit") {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ entries: [] }) });
      return;
    }
    if (url.pathname === "/broker/orders/dry-run") {
      capturedBody = JSON.parse(route.request().postData() ?? "{}");
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(RICH_DRY_RUN_RESPONSE) });
      return;
    }
    await route.continue();
  });

  await page.goto("/broker");
  await page.getByTestId("broker-submit-dry-run").click();
  await expect(page.getByTestId("broker-submit-dry-run-result")).toContainText("READY");

  // Account context should be sent
  expect(capturedBody).not.toBeNull();
  const body = capturedBody as Record<string, unknown>;
  expect(body["cash_balance"]).toBe(50000);
  expect(body["buying_power"]).toBe(100000);
  expect(typeof body["open_position_count"]).toBe("number");
  expect(typeof body["current_total_exposure"]).toBe("number");
});

test("MH-42: dry-run result displays estimated notional in preflight context panel", async ({ page }) => {
  await installBrokerMocks(page, PAPER_READY_HEALTH, PAPER_CONTROL_RESPONSE, { entries: [] }, {
    dryRunResponse: RICH_DRY_RUN_RESPONSE,
  });

  await page.goto("/broker");
  await page.getByTestId("broker-submit-dry-run").click();

  await expect(page.getByTestId("broker-submit-dry-run-result")).toContainText("READY");
  await expect(page.getByTestId("broker-preflight-context-panel")).toBeVisible();
  await expect(page.getByTestId("broker-preflight-estimated-notional")).toContainText("1,805");
});

test("MH-42: dry-run result displays post-trade exposure estimates", async ({ page }) => {
  await installBrokerMocks(page, PAPER_READY_HEALTH, PAPER_CONTROL_RESPONSE, { entries: [] }, {
    dryRunResponse: RICH_DRY_RUN_RESPONSE,
  });

  await page.goto("/broker");
  await page.getByTestId("broker-submit-dry-run").click();

  await expect(page.getByTestId("broker-preflight-context-panel")).toBeVisible();
  await expect(page.getByTestId("broker-preflight-post-trade-symbol-exposure")).toContainText("3,805");
  await expect(page.getByTestId("broker-preflight-post-trade-total-exposure")).toContainText("13,805");
});

test("MH-42: dry-run result displays risk-limit snapshot", async ({ page }) => {
  await installBrokerMocks(page, PAPER_READY_HEALTH, PAPER_CONTROL_RESPONSE, { entries: [] }, {
    dryRunResponse: RICH_DRY_RUN_RESPONSE,
  });

  await page.goto("/broker");
  await page.getByTestId("broker-submit-dry-run").click();

  await expect(page.getByTestId("broker-preflight-risk-snapshot")).toBeVisible();
  await expect(page.getByTestId("broker-preflight-risk-snapshot")).toContainText("10,000");
  await expect(page.getByTestId("broker-preflight-risk-snapshot")).toContainText("50,000");
});

test("MH-42: warnings are displayed separately from issues in preflight panel", async ({ page }) => {
  await installBrokerMocks(page, PAPER_READY_HEALTH, PAPER_CONTROL_RESPONSE, { entries: [] }, {
    dryRunResponse: {
      ...RICH_DRY_RUN_RESPONSE,
      issues: [{ code: "invalid_quantity", message: "Quantity must be > 0" }],
      status: "invalid",
      request_valid: false,
    },
  });

  await page.goto("/broker");
  await page.getByTestId("broker-submit-quantity").fill("1");
  await page.getByTestId("broker-submit-dry-run").click();

  await expect(page.getByTestId("broker-submit-dry-run-result")).toContainText("INVALID");
  await expect(page.getByTestId("broker-submit-dry-run-issues")).toBeVisible();
  await expect(page.getByTestId("broker-submit-dry-run-issues")).toContainText("Quantity must be > 0");

  // Warnings appear in preflight panel, separate from issues
  await expect(page.getByTestId("broker-preflight-warnings")).toBeVisible();
  await expect(page.getByTestId("broker-preflight-warning-item")).toHaveCount(RICH_DRY_RUN_RESPONSE.warnings.length);
  await expect(page.getByTestId("broker-submit-dry-run-issues")).not.toContainText("max_order_notional");
});

test("MH-42: warning-only dry-run still leaves submit path available after confirmation", async ({ page }) => {
  await installBrokerMocks(page, PAPER_READY_HEALTH, PAPER_CONTROL_RESPONSE, { entries: [] }, {
    dryRunResponse: RICH_DRY_RUN_RESPONSE,
    submitResponse: {
      broker_order_id: "PAPER-42-TEST",
      status: "SUBMITTED",
      filled_price: null,
      filled_quantity: null,
      error_message: null,
      broker_mode: { broker: "ibkr", mode: "paper", live_execution_enabled: false, paper_trading_enabled: true },
    },
  });

  await page.goto("/broker");
  await page.getByTestId("broker-submit-dry-run").click();

  await expect(page.getByTestId("broker-submit-dry-run-result")).toContainText("READY");
  // Warnings are present but do not block submit
  await expect(page.getByTestId("broker-preflight-warnings")).toBeVisible();

  await page.getByTestId("broker-submit-order").click();
  await expect(page.getByTestId("broker-submit-confirm-panel")).toBeVisible();
  await page.getByTestId("broker-submit-confirm").click();
  await expect(page.getByTestId("broker-submit-success")).toContainText("Order submitted");
});

test("MH-42: invalid dry-run issues still block submit", async ({ page }) => {
  await installBrokerMocks(page, PAPER_READY_HEALTH, PAPER_CONTROL_RESPONSE, { entries: [] }, {
    dryRunResponse: {
      status: "invalid",
      mode_guard_ok: true,
      request_valid: false,
      estimated_notional: null,
      issues: [{ code: "invalid_quantity", message: "Quantity must be > 0" }],
      warnings: [],
      preflight_context: null,
      broker_mode: { broker: "ibkr", mode: "paper", live_execution_enabled: false, paper_trading_enabled: true },
    },
  });

  await page.goto("/broker");
  await page.getByTestId("broker-submit-quantity").fill("1");
  await page.getByTestId("broker-submit-dry-run").click();
  await expect(page.getByTestId("broker-submit-dry-run-result")).toContainText("INVALID");

  await page.getByTestId("broker-submit-order").click();
  await expect(page.getByTestId("broker-submit-error")).toContainText("Run a successful dry run before submitting.");
});

test("MH-42: no live toggle added in MH-42", async ({ page }) => {
  await installBrokerMocks(page, PAPER_READY_HEALTH, PAPER_CONTROL_RESPONSE);
  await page.goto("/broker");

  await expect(page.getByRole("button", { name: /switch to live/i })).toHaveCount(0);
  await expect(page.getByRole("button", { name: /enable live/i })).toHaveCount(0);
  await expect(page.getByRole("button", { name: /live mode/i })).toHaveCount(0);
});

test("MH-42: no auto toggle added in MH-42", async ({ page }) => {
  await installBrokerMocks(page, PAPER_READY_HEALTH, PAPER_CONTROL_RESPONSE);
  await page.goto("/broker");

  await expect(page.getByRole("button", { name: /enable auto/i })).toHaveCount(0);
  await expect(page.getByRole("button", { name: /auto trading/i })).toHaveCount(0);
  await expect(page.getByRole("button", { name: /auto mode/i })).toHaveCount(0);
});

test("MH-42: preflight panel not rendered when no preflight context returned", async ({ page }) => {
  await installBrokerMocks(page, PAPER_READY_HEALTH, PAPER_CONTROL_RESPONSE, { entries: [] }, {
    dryRunResponse: {
      status: "ready",
      mode_guard_ok: true,
      request_valid: true,
      estimated_notional: 1805,
      issues: [],
      warnings: [],
      preflight_context: null,
      broker_mode: { broker: "ibkr", mode: "paper", live_execution_enabled: false, paper_trading_enabled: true },
    },
  });

  await page.goto("/broker");
  await page.getByTestId("broker-submit-dry-run").click();
  await expect(page.getByTestId("broker-submit-dry-run-result")).toContainText("READY");
  await expect(page.getByTestId("broker-preflight-context-panel")).not.toBeVisible();
});

// ── MH-48: Normalized Trade Provenance UI ─────────────────────────────────────
test("MH-44: daily P&L strip is hidden when no snapshots available", async ({ page }) => {
  await installBrokerMocks(page, PAPER_READY_HEALTH, PAPER_CONTROL_RESPONSE);
  await page.goto("/broker");
  await expect(page.getByTestId("broker-daily-pnl-strip")).not.toBeVisible();
});

test("MH-44: daily P&L strip shows value when snapshots present", async ({ page }) => {
  await installBrokerMocks(page, PAPER_READY_HEALTH, PAPER_CONTROL_RESPONSE, { entries: [] }, {
    dailyPnlResponse: DAILY_PNL_RESPONSE,
  });
  await page.goto("/broker");
  await expect(page.getByTestId("broker-daily-pnl-strip")).toBeVisible();
  await expect(page.getByTestId("broker-daily-pnl-value")).toContainText("342");
});

test("MH-44: daily P&L strip shows loss when daily_loss > 0", async ({ page }) => {
  await installBrokerMocks(page, PAPER_READY_HEALTH, PAPER_CONTROL_RESPONSE, { entries: [] }, {
    dailyPnlResponse: DAILY_PNL_RESPONSE,
  });
  await page.goto("/broker");
  await expect(page.getByTestId("broker-daily-loss-value")).toBeVisible();
  await expect(page.getByTestId("broker-daily-loss-value")).toContainText("342");
});

test("MH-44: dry-run payload includes daily_pnl and daily_loss when data available", async ({ page }) => {
  let capturedBody: Record<string, unknown> = {};

  await installBrokerMocks(page, PAPER_READY_HEALTH, PAPER_CONTROL_RESPONSE, { entries: [] }, {
    dailyPnlResponse: DAILY_PNL_RESPONSE,
    dryRunResponse: {
      status: "ready",
      mode_guard_ok: true,
      request_valid: true,
      estimated_notional: 1805,
      issues: [],
      warnings: [],
      preflight_context: null,
      broker_mode: { broker: "ibkr", mode: "paper", live_execution_enabled: false, paper_trading_enabled: true },
    },
  });

  await page.route("**/broker/orders/dry-run", async (route) => {
    if (!isBrokerApiRequest(route.request())) {
      await route.continue();
      return;
    }

    capturedBody = JSON.parse(route.request().postData() ?? "{}") as Record<string, unknown>;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        status: "ready",
        mode_guard_ok: true,
        request_valid: true,
        estimated_notional: 1805,
        issues: [],
        warnings: [],
        preflight_context: null,
        broker_mode: { broker: "ibkr", mode: "paper", live_execution_enabled: false, paper_trading_enabled: true },
      }),
    });
  });

  await page.goto("/broker");
  await page.getByTestId("broker-submit-ticker").fill("AAPL");
  await page.getByTestId("broker-submit-quantity").fill("10");
  await page.getByTestId("broker-submit-dry-run").click();
  await expect(page.getByTestId("broker-submit-dry-run-result")).toContainText("READY");

  expect(capturedBody.daily_pnl).toBe(-342.5);
  expect(capturedBody.daily_loss).toBe(342.5);
});

test("MH-44: dry-run payload omits daily_pnl when no snapshots", async ({ page }) => {
  let capturedBody: Record<string, unknown> = {};

  await page.route("**/broker/orders/dry-run", async (route) => {
    if (!isBrokerApiRequest(route.request())) {
      await route.continue();
      return;
    }

    capturedBody = JSON.parse(route.request().postData() ?? "{}") as Record<string, unknown>;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        status: "ready",
        mode_guard_ok: true,
        request_valid: true,
        estimated_notional: 1805,
        issues: [],
        warnings: [],
        preflight_context: null,
        broker_mode: { broker: "ibkr", mode: "paper", live_execution_enabled: false, paper_trading_enabled: true },
      }),
    });
  });

  await installBrokerMocks(page, PAPER_READY_HEALTH, PAPER_CONTROL_RESPONSE);
  await page.goto("/broker");
  await page.getByTestId("broker-submit-ticker").fill("AAPL");
  await page.getByTestId("broker-submit-quantity").fill("10");
  await page.getByTestId("broker-submit-dry-run").click();
  await expect(page.getByTestId("broker-submit-dry-run-result")).toContainText("READY");

  expect(capturedBody.daily_pnl).toBeUndefined();
  expect(capturedBody.daily_loss).toBeUndefined();
});

test("MH-44: preflight disclaimer mentions currently active broker account", async ({ page }) => {
  await installBrokerMocks(page, PAPER_READY_HEALTH, PAPER_CONTROL_RESPONSE, { entries: [] }, {
    dryRunResponse: {
      status: "ready",
      mode_guard_ok: true,
      request_valid: true,
      estimated_notional: 1805,
      issues: [],
      warnings: [],
      preflight_context: null,
      broker_mode: { broker: "ibkr", mode: "paper", live_execution_enabled: false, paper_trading_enabled: true },
    },
  });

  await page.goto("/broker");
  await page.getByTestId("broker-submit-dry-run").click();
  await expect(page.getByTestId("broker-submit-dry-run-result")).toContainText("READY");
  await expect(page.getByTestId("broker-dry-run-advisory-note")).toContainText("currently active broker account");
});

test("MH-44: no live toggle added", async ({ page }) => {
  await installBrokerMocks(page, PAPER_READY_HEALTH, PAPER_CONTROL_RESPONSE, { entries: [] }, {
    dailyPnlResponse: DAILY_PNL_RESPONSE,
  });
  await page.goto("/broker");
  await expect(page.getByRole("button", { name: /switch to live/i })).toHaveCount(0);
  await expect(page.getByRole("button", { name: /enable live/i })).toHaveCount(0);
});

test("MH-44: no auto toggle added", async ({ page }) => {
  await installBrokerMocks(page, PAPER_READY_HEALTH, PAPER_CONTROL_RESPONSE, { entries: [] }, {
    dailyPnlResponse: DAILY_PNL_RESPONSE,
  });
  await page.goto("/broker");
  await expect(page.getByRole("button", { name: /enable auto/i })).toHaveCount(0);
  await expect(page.getByRole("button", { name: /auto trading/i })).toHaveCount(0);
});

// ── MH-49: Provenance Filters + Event Detail Drawer ───────────────────────────
