import { expect, test } from "@playwright/test";

const API_BASE_URL = process.env.PLAYWRIGHT_API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
const API_ORIGIN = new URL(API_BASE_URL).origin;

test("broker submit decision timeline renders read-only decision history", async ({ page }) => {
  let brokerSubmitCalls = 0;

  await page.route("**/broker/orders", async (route) => {
    brokerSubmitCalls += 1;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ ok: true }),
    });
  });

  await page.route("**/broker/submit-decisions/recent*", async (route) => {
    const requestUrl = new URL(route.request().url());
    if (requestUrl.origin !== API_ORIGIN || requestUrl.pathname !== "/broker/submit-decisions/recent") {
      await route.continue();
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        count: 2,
        limit: 25,
        filters: {
          intent: null,
          would_block: null,
          source: null,
          decision_status: null,
          correlation_id: null,
          recommendation_id: null,
        },
        advisory:
          "Audit feed for persisted broker preflight and submit decisions. Rows are append-only and emitted by safety enforcement paths.",
        items: [
          {
            id: "7998b807-7301-4d8d-b95c-0a0bc2497cd5",
            created_at: "2026-05-24T10:15:00+00:00",
            signal_id: null,
            intent: "manual",
            would_block: true,
            blocked_reason_code: "max_order_notional_exceeded",
            blocked_reason_text: "Order notional exceeds active paper limit.",
            decision_status: "would_block",
            allowed_to_submit: false,
            decision_reason: "Order notional exceeds active paper limit.",
            source: "submit_preflight",
            submit_gate: "blocked",
            broker_order_id: null,
            correlation_id: "manual_paper_submit_corr_1",
            recommendation_id: "53dbd3e2-57b0-4a4a-a889-7e3e98f0f3cb",
            route_check_reference: "recommendation_route_check:eligible",
            dry_run_reference: "broker_dry_run:would_block",
            execution_mode: "ibkr_paper",
            account_mode: "paper",
            risk_profile_id: null,
            risk_block_reason: null,
            execution_source: "ibkr_paper",
            serious_paper_source: "ibkr_paper",
            canonical_paper_route: "/broker/orders",
            broker_account_mode: "paper",
            live_state: "ibkr_live_locked",
            request_summary: {
              ticker: "AAPL",
              side: "BUY",
              quantity: 10,
              order_type: "LIMIT",
              limit_price: 180.5,
              stop_price: null,
            },
            warnings: [],
            blocked_reasons: [
              {
                code: "max_order_notional_exceeded",
                message: "Order notional exceeds active paper limit.",
                source: "risk",
                classification: "would_block",
                severity: "warning",
              },
            ],
            preflight_json: {},
          },
          {
            id: "7d8d5648-b334-4285-b7d4-2e8da072ed7d",
            created_at: "2026-05-24T10:18:00+00:00",
            signal_id: null,
            intent: "manual",
            would_block: false,
            blocked_reason_code: null,
            blocked_reason_text: null,
            decision_status: "allowed",
            allowed_to_submit: true,
            decision_reason: "preflight_allowed",
            source: "submit_attempt",
            submit_gate: "allowed",
            broker_order_id: "PAPER-123",
            correlation_id: "manual_paper_submit_corr_1",
            recommendation_id: "53dbd3e2-57b0-4a4a-a889-7e3e98f0f3cb",
            route_check_reference: "recommendation_route_check:eligible",
            dry_run_reference: "broker_dry_run:allowed",
            execution_mode: "ibkr_paper",
            account_mode: "paper",
            risk_profile_id: null,
            risk_block_reason: null,
            execution_source: "ibkr_paper",
            serious_paper_source: "ibkr_paper",
            canonical_paper_route: "/broker/orders",
            broker_account_mode: "paper",
            live_state: "ibkr_live_locked",
            request_summary: {
              ticker: "AAPL",
              side: "BUY",
              quantity: 10,
              order_type: "LIMIT",
              limit_price: 180.5,
              stop_price: null,
            },
            warnings: [
              {
                code: "spread_warn",
                message: "Spread is elevated but still advisory.",
                source: "risk",
                classification: "advisory",
                severity: "warning",
              },
            ],
            blocked_reasons: [],
            preflight_json: {},
          },
        ],
      }),
    });
  });

  await page.goto("/cockpit/audit/broker-submit-decisions");
  await page.waitForLoadState("domcontentloaded");

  await expect(page.getByTestId("broker-submit-decisions-timeline-page")).toBeVisible();
  await expect(page.getByRole("heading", { name: /broker submit decision timeline/i })).toBeVisible();
  await expect(page.getByTestId("broker-submit-decisions-summary")).toContainText(/visible rows/i);
  await expect(page.getByTestId("broker-submit-decisions-summary")).toContainText(/would-block rows/i);
  await expect(page.getByTestId("broker-submit-decisions-item-list")).toContainText(/submit_preflight/i);
  await expect(page.getByTestId("broker-submit-decisions-item-list")).toContainText(/submit_attempt/i);
  await expect(page.getByTestId("broker-submit-decisions-item-list")).toContainText(/manual_paper_submit_corr_1/i);
  await expect(page.getByTestId("broker-submit-decisions-item-list")).toContainText(/53dbd3e2-57b0-4a4a-a889-7e3e98f0f3cb/i);
  await expect(page.getByTestId("broker-submit-decisions-item-list")).toContainText(/PAPER-123/i);
  await expect(page.getByRole("button", { name: /submit|approve|retry|rerun|execute/i })).toHaveCount(0);
  await expect(page.getByRole("button", { name: /^refresh$/i })).toHaveCount(1);
  expect(brokerSubmitCalls).toBe(0);
});