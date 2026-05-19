import { expect, test } from "@playwright/test";

import {
  DAILY_PNL_RESPONSE,
  MULTI_ENTRY_PROVENANCE_RESPONSE,
  PAPER_CONTROL_RESPONSE,
  PAPER_READY_HEALTH,
  installBrokerMocks,
} from "./broker-test-helpers";

test("MH-29: broker health panel shows paper_ready status", async ({ page }) => {
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
  await expect(page.getByTestId("broker-health-panel")).toBeVisible();
  await expect(page.getByTestId("broker-health-panel")).toHaveAttribute("data-health-status", "paper_ready");
  await expect(page.getByText("Paper Ready")).toBeVisible();
  await expect(page.getByTestId("broker-health-mode-guard")).toContainText("Mode Guard");
  await expect(page.getByTestId("broker-health-gateway")).toContainText("Gateway");
  await expect(page.getByTestId("broker-health-account")).toContainText("Account DUP153837");
  await expect(page.getByTestId("broker-health-gateway-url")).toContainText("https://localhost:5001/v1/api");
});

test("MH-29: broker health panel shows paper_config_only when gateway is down", async ({ page }) => {
  await installBrokerMocks(page, {
    status: "paper_config_only",
    mode_guard_ok: true,
    gateway_reachable: false,
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
  await expect(page.getByTestId("broker-health-panel")).toHaveAttribute("data-health-status", "paper_config_only");
  await expect(page.getByText("Config Only")).toBeVisible();
  await expect(page.getByTestId("broker-health-gateway")).toContainText("Gateway");
});

test("MH-29: broker health panel shows misconfigured for live-mode settings", async ({ page }) => {
  await installBrokerMocks(page, {
    status: "misconfigured",
    mode_guard_ok: false,
    gateway_reachable: true,
    gateway_url: "https://localhost:5001/v1/api",
    account_id: "U1234567",
    account_is_paper: false,
    broker_mode: {
      broker: "ibkr",
      mode: "live",
      live_execution_enabled: true,
      paper_trading_enabled: false,
    },
  });

  await page.goto("/broker");
  await expect(page.getByTestId("broker-health-panel")).toHaveAttribute("data-health-status", "misconfigured");
  await expect(page.getByText("Misconfigured")).toBeVisible();
  await expect(page.getByTestId("broker-health-account")).toContainText("Account U1234567");
});

test("MH-29: broker health panel shows fallback when health API is unavailable", async ({ page }) => {
  await installBrokerMocks(page, null);

  await page.goto("/broker");
  await expect(page.getByTestId("broker-health-panel")).toHaveAttribute("data-health-status", "error");
  await expect(page.getByText("Health check unavailable")).toBeVisible();
});
test("MH-37: trading control panel renders paper mode state", async ({ page }) => {
  await installBrokerMocks(page, PAPER_READY_HEALTH, PAPER_CONTROL_RESPONSE);

  await page.goto("/broker");

  await expect(page.getByTestId("broker-control-panel")).toBeVisible();
  await expect(page.getByTestId("broker-control-trading-mode")).toContainText("Paper");
  await expect(page.getByTestId("broker-control-execution-control")).toContainText("Manual");
  await expect(page.getByTestId("broker-control-arming-state")).toContainText("Armed");
  await expect(page.getByTestId("broker-control-summary-paper")).toContainText("Paper mode active, IBKR paper orders only.");
  await expect(page.getByTestId("broker-control-live-blocked-note")).toContainText("Live order submission blocked.");
  await expect(page.getByTestId("broker-control-auto-locked-note")).toContainText("Auto trading locked.");
});

test("MH-37: trading control panel shows live configured but locked wording", async ({ page }) => {
  await installBrokerMocks(
    page,
    {
      status: "live_ready",
      mode_guard_ok: true,
      gateway_reachable: true,
      gateway_url: "https://localhost:5001/v1/api",
      account_id: "U1234567",
      account_is_paper: false,
      broker_mode: {
        broker: "ibkr",
        mode: "live",
        live_execution_enabled: true,
        paper_trading_enabled: false,
      },
    },
    {
      trading_mode: "live",
      execution_control: "manual",
      arming_state: "disarmed",
      live_order_submission_allowed: false,
      paper_order_submission_allowed: false,
      auto_trading_allowed: false,
      emergency_stop_active: false,
      reasons: [
        "live_order_submission_blocked_until_future_arming_risk_and_emergency_stop_gates",
      ],
    },
  );

  await page.goto("/broker");

  await expect(page.getByTestId("broker-control-badge")).toContainText("Live Configured");
  await expect(page.getByTestId("broker-control-summary-live")).toContainText(
    "Live mode configured, live execution remains locked until future arming gates are enabled.",
  );
  await expect(page.getByTestId("broker-control-live-submit")).toContainText("Blocked");
  await expect(page.getByTestId("broker-control-reasons")).toContainText("Live Order Submission Blocked Until Future Arming Risk And Emergency Stop Gates");
});

test("MH-37: trading control unavailable state does not break broker page", async ({ page }) => {
  await installBrokerMocks(page, PAPER_READY_HEALTH, null);

  await page.goto("/broker");

  await expect(page.getByTestId("broker-control-unavailable")).toContainText("Trading control unavailable");
  await expect(page.getByTestId("broker-manual-submit-panel")).toBeVisible();
});

test("MH-37: broker page exposes no live or auto toggle buttons", async ({ page }) => {
  await installBrokerMocks(page, PAPER_READY_HEALTH, PAPER_CONTROL_RESPONSE);

  await page.goto("/broker");

  await expect(page.getByRole("button", { name: /switch to live/i })).toHaveCount(0);
  await expect(page.getByRole("button", { name: /enable auto/i })).toHaveCount(0);
  await expect(page.getByRole("button", { name: /live mode/i })).toHaveCount(0);
  await expect(page.getByRole("button", { name: /auto trading/i })).toHaveCount(0);
});
test("MH-51: broker review page exposes grouped section navigation", async ({ page }) => {
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

  await expect(page.getByTestId("broker-section-nav")).toBeVisible();
  await expect(page.getByTestId("broker-overview-section")).toBeVisible();
  await expect(page.getByTestId("broker-execution-section")).toBeVisible();
  await expect(page.getByTestId("broker-review-section")).toBeVisible();
  await expect(page.getByRole("link", { name: "Overview" })).toHaveAttribute("href", "#broker-overview");
  await expect(page.getByRole("link", { name: "Manual Review" })).toHaveAttribute("href", "#broker-execution");
  await expect(page.getByRole("link", { name: "Provenance" })).toHaveAttribute("href", "#broker-provenance");
  await expect(page.getByRole("link", { name: "Audit" })).toHaveAttribute("href", "#broker-audit");
});

test("MH-51: existing broker safety copy remains visible after layout polish", async ({ page }) => {
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
        broker_mode: {
          broker: "ibkr",
          mode: "paper",
          live_execution_enabled: false,
          paper_trading_enabled: true,
        },
        advisory_context: {
          account_id: "DU123456",
          account_currency: "USD",
          daily_pnl: -342.5,
          daily_loss: 342.5,
          estimated_post_trade_position: 10,
          estimated_post_trade_exposure: 1851,
          current_position_qty: 0,
          buying_power: 100000,
          net_liquidation: 100000,
          excess_liquidity: 45000,
          risk_limit_snapshot: null,
          warnings: [],
        },
      },
    },
    MULTI_ENTRY_PROVENANCE_RESPONSE,
  );

  await page.goto("/broker");

  await expect(page.getByTestId("broker-manual-submit-panel")).toContainText("Dry run is required before submit");
  await page.getByTestId("broker-submit-dry-run").click();
  await expect(page.getByTestId("broker-dry-run-advisory-note")).toContainText("Advisory only. Context is based on the currently active broker account.");
  await expect(page.getByTestId("broker-control-live-blocked-note")).toContainText("Live order submission blocked.");
  await expect(page.getByTestId("broker-control-auto-locked-note")).toContainText("Auto trading locked.");
});

// ── MH-52: Broker Readiness Checklist Panel ────────────────────────────────
