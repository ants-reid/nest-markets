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

export interface AutoPaperStatusCard {
  advisory: string;
  posture: AutoPaperStatusPosture;
  headline: string;
  subline: string;
  enforcement: AutoPaperStatusEnforcement;
  trading_control: AutoPaperStatusTradingControl;
  latest_run: AutoPaperStatusLatestRun | null;
  run_log_summary: AutoPaperStatusRunLogSummary;
  links: Record<string, string>;
}

export async function getAutoPaperStatusCard(): Promise<AutoPaperStatusCard> {
  return apiRequest<AutoPaperStatusCard>("/cockpit/auto-paper/status", {
    method: "GET",
  });
}
