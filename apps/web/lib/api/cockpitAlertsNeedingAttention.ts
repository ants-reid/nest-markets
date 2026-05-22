import { apiRequest } from "./core";

export type CockpitAttentionPriority = "high" | "medium" | "low" | "unknown";
export type CockpitAttentionSource =
  | "alert"
  | "incident"
  | "monitor"
  | "risk"
  | "trading_halt"
  | "notification"
  | "paper"
  | "unknown";
export type CockpitAttentionType =
  | "active_alert"
  | "unresolved_incident"
  | "monitor_degraded"
  | "stale_data"
  | "risk_attention"
  | "trading_halt"
  | "missing_context";

export interface CockpitAttentionSummary {
  headline: string;
  total_items: number;
  high_priority: number;
  medium_priority: number;
  low_priority: number;
  unknown_priority: number;
  active_alerts: number;
  unresolved_incidents: number;
  monitor_degraded: number;
  stale_data: number;
  risk_attention: number;
  trading_halt: number;
  missing_context: number;
}

export interface CockpitAttentionItem {
  id: string;
  source: CockpitAttentionSource;
  title: string;
  message: string;
  priority: CockpitAttentionPriority;
  status: string;
  detected_at: string | null;
  attention_type: CockpitAttentionType;
  evidence: string[];
  missing_data: string[];
  recommended_review_action: string;
  is_actionable: false;
}

export interface CockpitAttentionGroup {
  group: string;
  count: number;
  item_ids: string[];
}

export interface CockpitAlertsNeedingAttentionResponse {
  generated_at: string;
  mode: "paper";
  summary: CockpitAttentionSummary;
  attention_items: CockpitAttentionItem[];
  grouped_by_priority: CockpitAttentionGroup[];
  grouped_by_source: CockpitAttentionGroup[];
  monitor_notes: string[];
  risk_notes: string[];
  limitations: string[];
  recommended_review_actions: string[];
}

export async function getCockpitAlertsNeedingAttention(): Promise<CockpitAlertsNeedingAttentionResponse> {
  return apiRequest<CockpitAlertsNeedingAttentionResponse>("/cockpit/alerts-needing-attention", {
    method: "GET",
  });
}
