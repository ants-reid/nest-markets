import { apiRequest } from "./core";

export type CockpitInFlightItemType = "paper_position" | "paper_order" | "paper_recommendation" | "unknown";
export type CockpitInFlightAttentionLevel = "low" | "medium" | "high" | "unknown";
export type CockpitInFlightAdjustmentLabel =
  | "watch_only"
  | "review_required"
  | "stale_data"
  | "risk_attention"
  | "missing_context"
  | "monitor_issue"
  | "unknown";

export interface CockpitInFlightSummary {
  headline: string;
  total_items: number;
  open_positions: number;
  open_orders: number;
  active_recommendations: number;
  watch_only: number;
  review_required: number;
  high_attention: number;
}

export interface CockpitInFlightItem {
  id: string;
  item_type: CockpitInFlightItemType;
  symbol: string;
  asset_id: string | null;
  asset_name: string | null;
  asset_detail_path: string | null;
  has_asset_context: boolean;
  status: string;
  opened_at: string | null;
  created_at: string | null;
  current_state_summary: string;
  attention_level: CockpitInFlightAttentionLevel;
  adjustment_label: CockpitInFlightAdjustmentLabel;
  reason: string;
  evidence: string[];
  missing_data: string[];
  recommended_review_action: string;
  is_actionable: false;
}

export interface CockpitInFlightNote {
  title: string;
  detail: string;
  severity: string;
  created_at: string | null;
}

export interface CockpitInFlightAdjustmentsResponse {
  generated_at: string;
  mode: "paper";
  summary: CockpitInFlightSummary;
  items: CockpitInFlightItem[];
  monitor_notes: CockpitInFlightNote[];
  risk_notes: string[];
  limitations: string[];
  recommended_review_actions: string[];
}

export async function getCockpitInFlightAdjustments(): Promise<CockpitInFlightAdjustmentsResponse> {
  return apiRequest<CockpitInFlightAdjustmentsResponse>("/cockpit/in-flight-adjustments", {
    method: "GET",
  });
}
