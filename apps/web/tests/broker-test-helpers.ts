import { type Page } from "@playwright/test";

type BrokerHealthPayload = {
  status: "paper_ready" | "paper_config_only" | "live_ready" | "live_config_only" | "misconfigured";
  mode_guard_ok: boolean;
  gateway_reachable: boolean;
  gateway_url: string;
  account_id: string;
  account_is_paper: boolean;
  broker_mode: {
    broker: string;
    mode: string;
    live_execution_enabled: boolean;
    paper_trading_enabled: boolean;
  };
};

type BrokerControlPayload = {
  trading_mode: string;
  execution_control: string;
  arming_state: string;
  live_order_submission_allowed: boolean;
  paper_order_submission_allowed: boolean;
  auto_trading_allowed: boolean;
  emergency_stop_active: boolean;
  reasons: string[];
};

type BrokerAuditPayload = {
  entries: Array<{
    ts: string;
    event: string;
    action: string;
    ticker: string;
    side: string;
    quantity: number | null;
    status: string;
    broker_order_id: string | null;
    reason: string | null;
    dry_run: boolean;
    issues: Array<{ code?: string; message?: string }>;
  }>;
};

type BrokerTradeProvenancePayload = {
  entries: Array<{
    event_fingerprint: string;
    external_trade_id: string | null;
    broker_order_id: string | null;
    symbol: string | null;
    side: string | null;
    quantity: number | null;
    fill_price: number | null;
    commission: number | null;
    net_amount: number | null;
    realized_pnl: number | null;
    trade_ts: string | null;
    source: string;
    account_id: string | null;
    broker_provider: string;
    created_at: string;
  }>;
  returned: number;
  account_id: string | null;
  broker_mode: {
    broker: string;
    mode: string;
    live_execution_enabled: boolean;
    paper_trading_enabled: boolean;
  } | null;
};

export const ACCOUNT_RESPONSE = {
  net_liquidation: 100000,
  cash_balance: 50000,
  buying_power: 100000,
  currency: "USD",
  excess_liquidity: 45000,
  margin: 5000,
  unrealized_pnl: 1200,
  broker_mode: {
    broker: "ibkr",
    mode: "paper",
    live_execution_enabled: false,
    paper_trading_enabled: true,
  },
};

const POSITIONS_RESPONSE: unknown[] = [];

export const PAPER_CONTROL_RESPONSE: BrokerControlPayload = {
  trading_mode: "paper",
  execution_control: "manual",
  arming_state: "armed",
  live_order_submission_allowed: false,
  paper_order_submission_allowed: true,
  auto_trading_allowed: false,
  emergency_stop_active: false,
  reasons: [],
};

type BrokerOrderMocks = {
  dryRunResponse?: unknown | null;
  submitResponse?: unknown | null;
  dailyPnlResponse?: unknown | null;
};

export async function installBrokerMocks(
  page: Page,
  healthPayload: BrokerHealthPayload | null,
  controlPayload: BrokerControlPayload | null = PAPER_CONTROL_RESPONSE,
  auditPayload: BrokerAuditPayload | null = { entries: [] },
  orderMocks: BrokerOrderMocks = {
    dryRunResponse: {
      status: "ready",
      mode_guard_ok: true,
      request_valid: true,
      estimated_notional: 1805,
      issues: [],
      warnings: [],
      preflight_context: null,
      broker_mode: {
        broker: "ibkr",
        mode: "paper",
        live_execution_enabled: false,
        paper_trading_enabled: true,
      },
    },
    submitResponse: {
      broker_order_id: "PAPER-TEST-1",
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
  provenancePayload: BrokerTradeProvenancePayload | null = {
    entries: [],
    returned: 0,
    account_id: "DU123456",
    broker_mode: {
      broker: "ibkr",
      mode: "paper",
      live_execution_enabled: false,
      paper_trading_enabled: true,
    },
  },
) {
  await page.route("http://127.0.0.1:8000/broker/**", async (route) => {
    const url = new URL(route.request().url());

    if (url.pathname === "/broker/account") {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(ACCOUNT_RESPONSE) });
      return;
    }

    if (url.pathname === "/broker/positions") {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(POSITIONS_RESPONSE) });
      return;
    }

    if (url.pathname === "/broker/health") {
      if (healthPayload === null) {
        await route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ detail: "error" }) });
      } else {
        await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(healthPayload) });
      }
      return;
    }

    if (url.pathname === "/broker/control") {
      if (controlPayload === null) {
        await route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ detail: "error" }) });
      } else {
        await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(controlPayload) });
      }
      return;
    }

    if (url.pathname === "/broker/orders/audit") {
      if (auditPayload === null) {
        await route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ detail: "error" }) });
      } else {
        await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(auditPayload) });
      }
      return;
    }

    if (url.pathname === "/broker/trades/normalized") {
      if (provenancePayload === null) {
        await route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ detail: "error" }) });
      } else {
        await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(provenancePayload) });
      }
      return;
    }

    if (url.pathname === "/broker/orders/dry-run") {
      if (orderMocks.dryRunResponse === null) {
        await route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ detail: "error" }) });
      } else {
        await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(orderMocks.dryRunResponse) });
      }
      return;
    }

    if (url.pathname === "/broker/orders" && route.request().method() === "POST") {
      if (orderMocks.submitResponse === null) {
        await route.fulfill({ status: 403, contentType: "application/json", body: JSON.stringify({ detail: "blocked" }) });
      } else {
        await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(orderMocks.submitResponse) });
      }
      return;
    }

    if (url.pathname === "/broker/daily-pnl") {
      const payload = orderMocks.dailyPnlResponse;
      if (payload === null) {
        await route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ detail: "error" }) });
      } else if (payload === undefined) {
        // Default: no snapshots (empty state)
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            date: new Date().toISOString().slice(0, 10),
            daily_pnl: null,
            daily_loss: null,
            closed_pnl: null,
            open_pnl: null,
            total_pnl: null,
            latest_snapshot_ts: null,
            snapshot_count: 0,
            source: "pnl_snapshots",
            note: "No snapshots today",
          }),
        });
      } else {
        await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(payload) });
      }
      return;
    }

    await route.continue();
  });
}
export const PAPER_READY_HEALTH: BrokerHealthPayload = {
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
};

export const NORMALIZED_TRADE_PROVENANCE_RESPONSE: BrokerTradeProvenancePayload = {
  returned: 1,
  account_id: "DU123456",
  broker_mode: {
    broker: "ibkr",
    mode: "paper",
    live_execution_enabled: false,
    paper_trading_enabled: true,
  },
  entries: [
    {
      event_fingerprint: "fp-abc-123",
      external_trade_id: "T-1001",
      broker_order_id: "1001",
      symbol: "AAPL",
      side: "BUY",
      quantity: 10,
      fill_price: 185.1,
      commission: 1,
      net_amount: 1850,
      realized_pnl: 5,
      trade_ts: "2026-04-28T12:00:00Z",
      source: "broker_account_trades",
      account_id: "DU123456",
      broker_provider: "ibkr",
      created_at: "2026-04-28T12:00:01Z",
    },
  ],
};

export const RICH_DRY_RUN_RESPONSE = {
  status: "ready",
  mode_guard_ok: true,
  request_valid: true,
  estimated_notional: 1805.0,
  issues: [],
  warnings: [
    {
      code: "max_order_notional_configured",
      message: "Max order notional is configured for future enforcement and is evaluated here as advisory only.",
      severity: "warning",
      source: "risk_limits",
      enforcement_enabled: false,
    },
  ],
  preflight_context: {
    cash_balance: 50000.0,
    buying_power: 80000.0,
    open_position_count: 3,
    current_symbol_exposure: 2000.0,
    estimated_post_trade_symbol_exposure: 3805.0,
    current_total_exposure: 12000.0,
    estimated_post_trade_total_exposure: 13805.0,
    daily_pnl: 250.0,
    daily_loss: null,
    risk_limit_snapshot: {
      scope: "global",
      trading_mode: "paper",
      max_order_notional: 10000.0,
      max_total_exposure: 50000.0,
      max_symbol_exposure: null,
      daily_loss_limit_amount: null,
      daily_loss_limit_pct: null,
      max_open_positions: null,
      max_trades_per_day: null,
      min_cash_buffer: null,
    },
  },
  broker_mode: {
    broker: "ibkr",
    mode: "paper",
    live_execution_enabled: false,
    paper_trading_enabled: true,
  },
};

export const DAILY_PNL_RESPONSE = {
  date: new Date().toISOString().slice(0, 10),
  daily_pnl: -342.5,
  daily_loss: 342.5,
  closed_pnl: -200.0,
  open_pnl: -142.5,
  total_pnl: -342.5,
  latest_snapshot_ts: new Date().toISOString(),
  snapshot_count: 3,
  source: "pnl_snapshots",
  note: null,
};

export const MULTI_ENTRY_PROVENANCE_RESPONSE: BrokerTradeProvenancePayload = {
  returned: 3,
  account_id: "DU123456",
  broker_mode: {
    broker: "ibkr",
    mode: "paper",
    live_execution_enabled: false,
    paper_trading_enabled: true,
  },
  entries: [
    {
      event_fingerprint: "fp-abc-001",
      external_trade_id: "T-2001",
      broker_order_id: "2001",
      symbol: "AAPL",
      side: "BUY",
      quantity: 10,
      fill_price: 185.1,
      commission: 1,
      net_amount: 1850,
      realized_pnl: 5,
      trade_ts: "2026-04-28T12:00:00Z",
      source: "broker_account_trades",
      account_id: "DU123456",
      broker_provider: "ibkr",
      created_at: "2026-04-28T12:00:01Z",
    },
    {
      event_fingerprint: "fp-abc-002",
      external_trade_id: "T-2002",
      broker_order_id: "2002",
      symbol: "MSFT",
      side: "SELL",
      quantity: 5,
      fill_price: 310.0,
      commission: 1,
      net_amount: 1550,
      realized_pnl: null,
      trade_ts: "2026-04-28T13:00:00Z",
      source: "broker_account_trades",
      account_id: "DU123456",
      broker_provider: "ibkr",
      created_at: "2026-04-28T13:00:01Z",
    },
    {
      event_fingerprint: "fp-abc-003",
      external_trade_id: "T-2003",
      broker_order_id: "2003",
      symbol: "TSLA",
      side: "BUY",
      quantity: 2,
      fill_price: 200.0,
      commission: 0.5,
      net_amount: 400,
      realized_pnl: -10,
      trade_ts: "2026-04-28T14:00:00Z",
      source: "manual_entry",
      account_id: "DU999999",
      broker_provider: "ibkr",
      created_at: "2026-04-28T14:00:01Z",
    },
  ],
};

