// MH-COCKPIT-13-B — Auto-paper status card API client (read-only).

import { apiRequest } from "./core";

export interface AutoPaperStatusEnforcement {
  auto_paper_enforcement_enabled: boolean;
  auto_trading_enabled: boolean;
  live_trading_enabled: boolean;
  live_order_submission_allowed: boolean;
}

export interface AutoPaperStatusTradingControl {
  trading_mode: string;
  execution_control: string;
  arming_state: string;
  auto_trading_allowed: boolean;
  paper_order_submission_allowed: boolean;
  live_order_submission_allowed: boolean;
  emergency_stop_active: boolean;
  reasons: string[];
}

export interface AutoPaperStatusLatestRun {
  worker_name: string;
  status: string;
  message: string;
  started_at: string;
  finished_at: string;
  source: string;
  outcome_counts: Record<string, number> | null;
}

export interface AutoPaperStatusRunLogSummary {
  current_entry_count: number;
  max_entries: number;
  utilization_pct: number;
  near_capacity: boolean;
  retention_status: string | null;
  latest_started_at: string | null;
}

export type AutoPaperStatusPosture = "ok" | "warning" | "blocked";

export type AutoPaperLastDecision =
  | "accepted"
  | "blocked"
  | "skipped"
  | "errored"
  | "unknown";

export interface AutoPaperStatusRiskGateItem {
  label: string;
  status: "passing" | "warning" | "blocked";
  detail: string;
}

export interface AutoPaperStatusLatestPaperOrder {
  order_type: string | null;
  status: string | null;
  side: string | null;
  direction: string | null;
  qty: number | null;
  notional: number | null;
  submitted_at: string | null;
  signal_id: string | null;
  asset_id: string | null;
  broker_order_id: number | string | null;
  ibkr_status?: string | null;
}

export interface AutoPaperCandidateQueueItem {
  signal_id: string;
  asset: string;
  provider_name: string;
  signal_status: string;
  signal_score: number | null;
  confidence: number | null;
  composite_score: number | null;
  scan_ts: string | null;
  age_minutes: number | null;
  age_bucket: string;
  stale_manual_seed: boolean;
  duplicate_symbol_candidate: boolean;
}

export interface AutoPaperCandidateQueue {
  recency_hours: number;
  min_signal_score: number;
  eligible_count: number;
  top_candidates: AutoPaperCandidateQueueItem[];
  selection_explanation: string;
}

export interface AutoPaperQueueHygiene {
  stale_manual_seed_count: number;
  duplicate_symbol_candidate_count: number;
  already_submitted_count: number;
  allowlist_blocked_count: number;
  cap_blocked: boolean;
  controlled_gate_blocked: boolean;
  age_bucket_counts: Record<string, number>;
  cleanup_recommendations: string[];
}

export interface AutoPaperControlledGateDecision {
  allowed: boolean;
  blocking_gate: string | null;
  reason: string | null;
}

export interface AutoPaperControlledGateSnapshot {
  auto_paper_enabled: boolean;
  broker_provider: string;
  broker_mode: string;
  tws_enabled: boolean;
  live_execution_enabled: boolean;
  max_orders_per_run: number;
  max_orders_per_day: number;
  max_notional_usd: number;
  symbol_allowlist: string[];
  order_type: string;
  limit_price: number;
  require_tws: boolean;
  background_scheduler_enabled: boolean;
  minutes_between_runs: number;
  kill_on_error_count: number;
  kill_on_reject_rate: number;
  orders_today: number;
  kill_switch_active: boolean;
}

export interface AutoPaperControlledGate {
  decision: AutoPaperControlledGateDecision;
  snapshot: AutoPaperControlledGateSnapshot;
}

export interface AutoPaperStatusCard {
  advisory: string;
  mode: string;
  auto_paper_selectable: boolean;
  auto_paper_active: boolean;
  auto_paper_armed: boolean;
  live_trading_locked: boolean;
  auto_live_locked: boolean;
  posture: AutoPaperStatusPosture;
  headline: string;
  subline: string;
  last_check_at: string | null;
  last_action_at: string | null;
  last_decision: AutoPaperLastDecision;
  last_block_reason: string | null;
  open_paper_positions_count: number;
  max_open_paper_positions: number;
  risk_gate_summary: AutoPaperStatusRiskGateItem[];
  safety_notes: string[];
  operator_next_action: string;
  enforcement: AutoPaperStatusEnforcement;
  trading_control: AutoPaperStatusTradingControl;
  latest_run: AutoPaperStatusLatestRun | null;
  latest_paper_order: AutoPaperStatusLatestPaperOrder | null;
  candidate_queue?: AutoPaperCandidateQueue;
  queue_hygiene?: AutoPaperQueueHygiene;
  run_log_summary: AutoPaperStatusRunLogSummary;
  links: Record<string, string>;
  controlled_gate?: AutoPaperControlledGate;
}

export async function getAutoPaperStatusCard(): Promise<AutoPaperStatusCard> {
  return apiRequest<AutoPaperStatusCard>("/cockpit/auto-paper/status", {
    method: "GET",
  });
}

export interface AutoPaperRunResult {
  worker_name: string;
  status: string;
  message: string;
  started_at: string;
  finished_at: string;
}

export async function runAutoPaperOnce(): Promise<AutoPaperRunResult> {
  return apiRequest<AutoPaperRunResult>(
    "/market-data/auto-paper/run?source=manual",
    { method: "POST" },
  );
}

export interface AutoPaperKillSwitchState {
  kill_switch_active: boolean;
  profile_name: string | null;
  profile_is_active: string | null;
}

export async function getAutoPaperKillSwitch(): Promise<AutoPaperKillSwitchState> {
  return apiRequest<AutoPaperKillSwitchState>(
    "/market-data/auto-paper/kill-switch",
    { method: "GET" },
  );
}

export async function activateAutoPaperKillSwitch(): Promise<AutoPaperKillSwitchState> {
  return apiRequest<AutoPaperKillSwitchState>(
    "/market-data/auto-paper/kill-switch/activate",
    { method: "POST" },
  );
}

export async function deactivateAutoPaperKillSwitch(): Promise<AutoPaperKillSwitchState> {
  return apiRequest<AutoPaperKillSwitchState>(
    "/market-data/auto-paper/kill-switch/deactivate",
    { method: "POST" },
  );
}
