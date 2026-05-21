import { expect, test } from "@playwright/test";

function buildModeState(currentMode: string = "auto_paper") {
  return {
    current_mode: currentMode,
    selectable_modes: ["learning", "manual", "auto_paper"],
    locked_modes: ["assisted_live", "live", "auto_live"],
    modes: [
      {
        id: "learning",
        label: "Learning",
        status: currentMode === "learning" ? "active" : "available",
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
        status: currentMode === "manual" ? "active" : "available",
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
        status: currentMode === "auto_paper" ? "active" : "available",
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
        reason: "Locked until a future live-readiness checklist exists.",
        risk_note: "Risk first: assisted live stays unavailable.",
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
        reason: "Locked until future live phases are complete.",
        risk_note: "Risk first: real-money trading remains blocked.",
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
        reason: "Locked until long paper evidence and safety sign-off exist.",
        risk_note: "Risk first: auto live is intentionally blocked.",
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

function buildAutoPaperStatus() {
  return {
    advisory:
      "Auto-paper status card is read-only. It surfaces the current drift-lock posture and does not enable, arm, or change any trading control.",
    mode: "auto_paper",
    auto_paper_selectable: true,
    auto_paper_active: true,
    auto_paper_armed: true,
    live_trading_locked: true,
    auto_live_locked: true,
    posture: "warning",
    headline: "Auto Paper requires review before the next cycle",
    subline: "Risk gates still apply and live trading remains locked.",
    last_check_at: "2025-01-02T03:04:05Z",
    last_action_at: "2025-01-02T03:14:05Z",
    last_decision: "blocked",
    last_block_reason: "Risk gates blocked the latest Auto Paper run.",
    open_paper_positions_count: 2,
    max_open_paper_positions: 5,
    risk_gate_summary: [
      {
        label: "Paper submission gate",
        status: "passing",
        detail: "Paper submission remains inside backend trading-control rules.",
      },
      {
        label: "Emergency stop",
        status: "passing",
        detail: "Emergency stop halts all Auto Paper activity when active.",
      },
      {
        label: "Open paper position cap",
        status: "passing",
        detail: "2/5 open Auto Paper positions.",
      },
    ],
    safety_notes: [
      "Auto Paper can simulate trades only.",
      "No real money orders can be placed from this mode.",
      "Live trading remains locked.",
      "Auto-live remains locked.",
    ],
    operator_next_action:
      "Review the latest block reason: Risk gates blocked the latest Auto Paper run.",
    enforcement: {
      auto_paper_enforcement_enabled: false,
      auto_trading_enabled: false,
      live_trading_enabled: false,
      live_order_submission_allowed: false,
    },
    trading_control: {
      trading_mode: "paper",
      execution_control: "manual",
      arming_state: "armed",
      auto_trading_allowed: false,
      paper_order_submission_allowed: true,
      live_order_submission_allowed: false,
      emergency_stop_active: false,
      reasons: [],
    },
    latest_run: {
      worker_name: "auto_paper_test",
      status: "ok",
      message: "auto_paper_trader: 0 positions opened, 1 risk-blocked",
      started_at: "2025-01-02T03:04:05Z",
      finished_at: "2025-01-02T03:05:05Z",
      source: "scheduled",
      outcome_counts: {
        accepted_count: 0,
        rejected_count: 0,
        cancelled_count: 0,
        blocked_count: 1,
        risk_blocked_count: 1,
        gate_blocked_count: 0,
        skipped_cap_count: 0,
      },
    },
    latest_paper_order: {
      order_type: "auto_paper",
      status: "queued",
      side: "buy",
      direction: "long",
      qty: 1.25,
      notional: 1250,
      submitted_at: "2025-01-02T03:14:05Z",
      signal_id: null,
      asset_id: null,
      broker_order_id: null,
    },
    run_log_summary: {
      current_entry_count: 4,
      max_entries: 200,
      utilization_pct: 2,
      near_capacity: false,
      retention_status: "ok",
      latest_started_at: "2025-01-02T03:04:05Z",
    },
    links: {
      readiness: "/market-data/auto-paper/readiness",
      scheduler: "/market-data/auto-paper/scheduler/status",
      worker_run_log: "/monitor/worker-run-log/overview",
      broker_control: "/broker/control",
      broker_health: "/broker/health",
    },
  };
}

async function mockCockpitSurfaces(page: import("@playwright/test").Page) {
  await page.route("**/cockpit/mode", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(buildModeState()),
    });
  });

  await page.route("**/cockpit/auto-paper/status", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(buildAutoPaperStatus()),
    });
  });
}

test("auto paper status page shows simulation-only safety and operator guidance", async ({ page }) => {
  await mockCockpitSurfaces(page);

  await page.goto("/cockpit/auto-paper-status");
  await page.waitForLoadState("domcontentloaded");

  await expect(page.getByTestId("auto-paper-status-page")).toBeVisible();
  await expect(page.getByTestId("auto-paper-lock-notice")).toContainText(/simulation only/i);
  await expect(page.getByTestId("auto-paper-lock-notice")).toContainText(/live trading remains locked/i);
  await expect(page.getByTestId("auto-paper-state-summary")).toContainText(/blocked/i);
  await expect(page.getByTestId("auto-paper-next-action")).toContainText(/review the latest block reason/i);
  await expect(page.getByText(/simulated size/i)).toBeVisible();
});

test("cockpit hub shows concise auto paper summary", async ({ page }) => {
  await mockCockpitSurfaces(page);

  await page.goto("/cockpit");
  await page.waitForLoadState("domcontentloaded");

  await expect(page.getByTestId("cockpit-auto-paper-summary")).toContainText(/auto paper requires review/i);
  await expect(page.getByTestId("cockpit-auto-paper-summary")).toContainText(/simulation only/i);
  await expect(page.getByTestId("cockpit-auto-paper-summary")).toContainText(/blocked/i);
});

test("auto paper status page has no horizontal overflow at 390px", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockCockpitSurfaces(page);

  await page.goto("/cockpit/auto-paper-status");
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