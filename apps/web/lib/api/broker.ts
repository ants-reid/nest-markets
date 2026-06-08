import { apiRequest } from "./core";

export interface BrokerModeInfo {
  broker: string;
  mode: string;
  live_execution_enabled: boolean;
  paper_trading_enabled: boolean;
}

export type BrokerHealthStatus =
  | "paper_ready"
  | "paper_config_only"
  | "live_ready"
  | "live_config_only"
  | "misconfigured";

export interface BrokerHealth {
  status: BrokerHealthStatus;
  mode_guard_ok: boolean;
  gateway_reachable: boolean;
  gateway_url: string;
  account_id: string;
  account_is_paper: boolean;
  broker_mode: BrokerModeInfo;
  broker_readiness?: {
    overall_status: "green" | "yellow" | "red";
    last_checked_at: string;
    items: Array<{
      key: string;
      label: string;
      status: "green" | "yellow" | "red";
      reason: string;
      suggested_action: string;
    }>;
  };
}

export async function getBrokerHealth(): Promise<BrokerHealth> {
  return apiRequest<BrokerHealth>("/broker/health", { method: "GET" });
}

export interface BrokerTradingControl {
  trading_mode: string;
  execution_control: string;
  arming_state: string;
  live_order_submission_allowed: boolean;
  paper_order_submission_allowed: boolean;
  auto_trading_allowed: boolean;
  emergency_stop_active: boolean;
  reasons: string[];
}

export async function getBrokerControl(): Promise<BrokerTradingControl> {
  return apiRequest<BrokerTradingControl>("/broker/control", { method: "GET" });
}

export interface BrokerOrderAuditEntry {
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
}

export interface BrokerOrderAuditTrail {
  entries: BrokerOrderAuditEntry[];
}

export async function getBrokerOrderAudit(limit = 20): Promise<BrokerOrderAuditTrail> {
  return apiRequest<BrokerOrderAuditTrail>(`/broker/orders/audit?limit=${limit}`, { method: "GET" });
}

export interface NormalizedBrokerTradeEvent {
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
}

export interface BrokerTradeEventAuditTrail {
  entries: NormalizedBrokerTradeEvent[];
  returned: number;
  account_id: string | null;
  broker_mode: BrokerModeInfo | null;
}

export async function getNormalizedBrokerTrades(limit = 100): Promise<BrokerTradeEventAuditTrail> {
  return apiRequest<BrokerTradeEventAuditTrail>(`/broker/trades/normalized?limit=${limit}`, { method: "GET" });
}

export interface BrokerOrderRequest {
  ticker: string;
  side: "BUY" | "SELL";
  quantity: number;
  order_type: "MARKET" | "LIMIT" | "STOP" | "STOP_LIMIT" | "TRAIL";
  limit_price?: number;
  stop_price?: number;
  tif?: string;
  outside_rth?: boolean;
  client_order_id?: string;
}

export interface BrokerOrderResult {
  broker_order_id: string;
  status: string;
  filled_price: number | null;
  filled_quantity: number | null;
  error_message: string | null;
  broker_mode: BrokerModeInfo | null;
}

export interface BrokerOrderDryRunIssue {
  code: string;
  message: string;
  severity?: string | null;
  source?: string | null;
  enforcement_enabled?: boolean | null;
}

export interface BrokerOrderPreflightDecisionItem {
  code: string;
  message: string;
  severity?: string | null;
  source?: string | null;
  enforcement_enabled: boolean;
  classification: string;
}

export interface BrokerOrderDryRunPreflightDecision {
  decision_status: string;
  submit_gate: string;
  advisory_count: number;
  would_block_count: number;
  blocking_count: number;
  advisory_items: BrokerOrderPreflightDecisionItem[];
  would_block_items: BrokerOrderPreflightDecisionItem[];
  blocking_items: BrokerOrderPreflightDecisionItem[];
}

export interface RiskLimitSnapshot {
  scope: string | null;
  trading_mode: string | null;
  max_order_notional: number | null;
  daily_loss_limit_amount: number | null;
  daily_loss_limit_pct: number | null;
  max_open_positions: number | null;
  max_total_exposure: number | null;
  max_symbol_exposure: number | null;
  max_trades_per_day: number | null;
  min_cash_buffer: number | null;
}

export interface DryRunPreflightContext {
  cash_balance: number | null;
  buying_power: number | null;
  open_position_count: number | null;
  current_symbol_exposure: number | null;
  estimated_post_trade_symbol_exposure: number | null;
  current_total_exposure: number | null;
  estimated_post_trade_total_exposure: number | null;
  daily_pnl: number | null;
  daily_loss: number | null;
  risk_limit_snapshot: RiskLimitSnapshot | null;
}

export interface BrokerOrderDryRunResult {
  status: "ready" | "invalid" | "blocked";
  mode_guard_ok: boolean;
  request_valid: boolean;
  estimated_notional: number | null;
  issues: BrokerOrderDryRunIssue[];
  warnings: BrokerOrderDryRunIssue[];
  preflight_decision: BrokerOrderDryRunPreflightDecision;
  preflight_context: DryRunPreflightContext | null;
  broker_mode: BrokerModeInfo;
  execution_source: string;
  balance_source: string;
  fees_source: string;
  fills_source: string;
  positions_source: string;
  serious_paper_source: string;
  is_canonical_paper: boolean;
  canonical_paper_route: string;
  broker_account_mode: string;
  live_state: string;
  paper_path_note: string;
}

export interface BrokerOrderDryRunRequest extends BrokerOrderRequest {
  /** Optional advisory portfolio context — never affects dry-run status */
  cash_balance?: number;
  buying_power?: number;
  open_position_count?: number;
  current_symbol_exposure?: number;
  current_total_exposure?: number;
  daily_pnl?: number;
  daily_loss?: number;
}

export async function dryRunBrokerOrder(payload: BrokerOrderDryRunRequest): Promise<BrokerOrderDryRunResult> {
  return apiRequest<BrokerOrderDryRunResult>("/broker/orders/dry-run", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function submitBrokerOrder(payload: BrokerOrderRequest): Promise<BrokerOrderResult> {
  return apiRequest<BrokerOrderResult>("/broker/orders", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export interface BrokerAccountInfo {
  net_liquidation: number;
  cash_balance: number;
  buying_power: number;
  currency: string;
  excess_liquidity: number;
  margin: number;
  unrealized_pnl: number;
}

export interface BrokerPosition {
  conid: number;
  ticker: string;
  side: string;
  quantity: number;
  avg_cost: number;
  market_price: number | null;
  market_value: number | null;
  unrealized_pnl: number | null;
  asset_class: string;
  currency: string;
}

export async function getBrokerAccount(): Promise<BrokerAccountInfo> {
  return apiRequest<BrokerAccountInfo>("/broker/account", { method: "GET" });
}

export async function getBrokerPositions(): Promise<BrokerPosition[]> {
  return apiRequest<BrokerPosition[]>("/broker/positions", { method: "GET" });
}

/** Daily P&L summary from pnl_snapshots (MH-43 backend, MH-44 frontend). */
export interface BrokerDailyPnl {
  date: string;
  daily_pnl: number | null;
  daily_loss: number | null;
  closed_pnl: number | null;
  open_pnl: number | null;
  total_pnl: number | null;
  latest_snapshot_ts: string | null;
  snapshot_count: number;
  source: string;
  note: string | null;
}

export async function getDailyPnl(): Promise<BrokerDailyPnl> {
  return apiRequest<BrokerDailyPnl>("/broker/daily-pnl", { method: "GET" });
}

export interface AutoPaperSchedulerStatus {
  job_id: string;
  next_run_time: string | null;
  state: "running" | "paused" | "missing" | "scheduler_unavailable";
}

export async function getAutoPaperSchedulerStatus(): Promise<AutoPaperSchedulerStatus> {
  return apiRequest<AutoPaperSchedulerStatus>("/market-data/auto-paper/scheduler/status", { method: "GET" });
}

export async function pauseAutoPaperScheduler(): Promise<AutoPaperSchedulerStatus> {
  return apiRequest<AutoPaperSchedulerStatus>("/market-data/auto-paper/scheduler/pause", { method: "POST" });
}

export async function resumeAutoPaperScheduler(): Promise<AutoPaperSchedulerStatus> {
  return apiRequest<AutoPaperSchedulerStatus>("/market-data/auto-paper/scheduler/resume", { method: "POST" });
}
