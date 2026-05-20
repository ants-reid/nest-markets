import { expect, test } from "@playwright/test";

function buildModeState(currentMode: string = "learning") {
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

async function mockCockpitMode(
  page: import("@playwright/test").Page,
  options?: { rejectMode?: string },
) {
  let currentMode = "learning";

  await page.route("**/cockpit/mode", async (route) => {
    const method = route.request().method();

    if (method === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(buildModeState(currentMode)),
      });
      return;
    }

    if (method === "POST") {
      const body = route.request().postDataJSON() as { requested_mode?: string };
      if (body.requested_mode === options?.rejectMode) {
        await route.fulfill({
          status: 403,
          contentType: "application/json",
          body: JSON.stringify({
            detail: {
              code: "cockpit_mode_locked",
              requested_mode: body.requested_mode,
              message: "This mode is visible for product direction only and remains locked in the current build.",
            },
          }),
        });
        return;
      }

      currentMode = body.requested_mode ?? currentMode;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(buildModeState(currentMode)),
      });
      return;
    }

    await route.continue();
  });
}

test("cockpit mode selector renders selectable and locked modes", async ({ page }) => {
  await mockCockpitMode(page);

  await page.goto("/cockpit");
  await page.waitForLoadState("domcontentloaded");

  await expect(page.getByRole("heading", { name: "Cockpit", exact: true })).toBeVisible();
  await expect(page.getByTestId("cockpit-mode-selector")).toBeVisible();
  await expect(page.getByTestId("cockpit-current-mode-summary")).toContainText(/learning/i);
  await expect(page.getByTestId("cockpit-mode-card-learning")).toContainText(/risk first/i);
  await expect(page.getByTestId("cockpit-mode-card-manual")).toContainText(/manual/i);
  await expect(page.getByTestId("cockpit-mode-card-auto_paper")).toContainText(/auto paper/i);
  await expect(page.getByTestId("cockpit-select-assisted_live")).toBeDisabled();
  await expect(page.getByTestId("cockpit-select-live")).toBeDisabled();
  await expect(page.getByTestId("cockpit-select-auto_live")).toBeDisabled();
});

test("cockpit mode selector switches between safe selectable modes", async ({ page }) => {
  await mockCockpitMode(page);

  await page.goto("/cockpit");
  await page.waitForLoadState("domcontentloaded");

  await expect(page.getByTestId("cockpit-select-manual")).toBeVisible();
  await page.getByTestId("cockpit-select-manual").click();
  await expect(page.getByTestId("cockpit-current-mode-summary")).toContainText(/manual/i);
  await expect(page.getByTestId("cockpit-mode-success")).toContainText(/manual is now the active cockpit mode/i);

  await expect(page.getByTestId("cockpit-select-auto_paper")).toBeVisible();
  await page.getByTestId("cockpit-select-auto_paper").click();
  await expect(page.getByTestId("cockpit-current-mode-summary")).toContainText(/auto paper/i);
  await expect(page.getByTestId("cockpit-mode-success")).toContainText(/auto paper is now the active cockpit mode/i);
});

test("cockpit mode selector shows a safe error when backend rejects a change", async ({ page }) => {
  await mockCockpitMode(page, { rejectMode: "manual" });

  await page.goto("/cockpit");
  await page.waitForLoadState("domcontentloaded");

  await expect(page.getByTestId("cockpit-select-manual")).toBeVisible();
  await page.getByTestId("cockpit-select-manual").click();
  await expect(page.getByTestId("cockpit-mode-error")).toContainText(/remains locked in the current build/i);
  await expect(page.getByTestId("cockpit-current-mode-summary")).toContainText(/learning/i);
});

test("cockpit page has no horizontal overflow at 390px", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockCockpitMode(page);

  await page.goto("/cockpit");
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