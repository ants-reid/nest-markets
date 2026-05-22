import { apiRequest } from "./core";

export type CockpitTradeCloseLabel =
  | "target_hit"
  | "stop_hit"
  | "manual_close"
  | "timeout_or_stale"
  | "validation_close"
  | "risk_close"
  | "unknown";

export type CockpitTradeCloseOutcomeMatch = "matched" | "mismatched" | "unknown";

export interface CockpitTradeCloseSummary {
  headline: string;
  total_closed_trades: number;
  known_close_labels: number;
  unknown_close_labels: number;
  profitable_trades: number;
  losing_trades: number;
  flat_trades: number;
  setup_matched: number;
  setup_mismatched: number;
  setup_unknown: number;
}

export interface CockpitTradeCloseExplanation {
  id: string;
  paper_order_id: string | null;
  position_id: string | null;
  symbol: string;
  opened_at: string | null;
  closed_at: string | null;
  status: string;
  close_label: CockpitTradeCloseLabel;
  close_reason: string | null;
  result_summary: string;
  realized_pnl: number | null;
  outcome_match: CockpitTradeCloseOutcomeMatch;
  evidence: string[];
  missing_data: string[];
  learning_note: string;
  is_actionable: false;
}

export interface CockpitTradeCloseExplanationsResponse {
  generated_at: string;
  mode: "paper";
  summary: CockpitTradeCloseSummary;
  explanations: CockpitTradeCloseExplanation[];
  limitations: string[];
  recommended_review_actions: string[];
}

export async function getCockpitTradeCloseExplanations(): Promise<CockpitTradeCloseExplanationsResponse> {
  return apiRequest<CockpitTradeCloseExplanationsResponse>("/cockpit/trade-close-explanations", {
    method: "GET",
  });
}
