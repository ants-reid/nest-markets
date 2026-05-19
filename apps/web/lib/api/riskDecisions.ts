// MH-RISK-AUDIT-A-UI — Risk-decisions audit API client (read-only).
//
// Wraps GET /risk-decisions/recent (MH-RISK-AUDIT-A). Unlike the other
// audit endpoints shipped this bucket, the underlying table is already
// populated by the deterministic risk evaluator, so the response
// generally returns real rows.

import { apiRequest } from "./core";

export interface RiskDecisionRow {
  id: string;
  created_at: string | null;
  timestamp: string | null;
  signal_id: string | null;
  approved: string;
  blocking_rule: string | null;
  block_reason_code: string | null;
  risk_profile_id: string | null;
  position_risk_pct: number | null;
  notional_allowed: number | null;
  correlation_bucket: string | null;
  spread_ok: boolean | null;
  session_ok: boolean | null;
  drawdown_ok: boolean | null;
  cooldown_ok: boolean | null;
  kill_switch_active: boolean | null;
  blocked_reasons_json: unknown;
}

export interface RiskDecisionsResponse {
  count: number;
  limit: number;
  filters: {
    approved: string | null;
    signal_id: string | null;
    block_reason_code: string | null;
  };
  advisory: string;
  items: RiskDecisionRow[];
}

export interface RiskDecisionsQuery {
  limit?: number;
  approved?: string | null;
  signalId?: string | null;
  blockReasonCode?: string | null;
}

export async function getRecentRiskDecisions(
  query: RiskDecisionsQuery = {},
): Promise<RiskDecisionsResponse> {
  const params = new URLSearchParams();
  if (query.limit !== undefined) {
    params.set("limit", String(query.limit));
  }
  if (query.approved != null && query.approved !== "") {
    params.set("approved", query.approved);
  }
  if (query.signalId != null && query.signalId !== "") {
    params.set("signal_id", query.signalId);
  }
  if (query.blockReasonCode != null && query.blockReasonCode !== "") {
    params.set("block_reason_code", query.blockReasonCode);
  }
  const qs = params.toString();
  const path = qs ? `/risk-decisions/recent?${qs}` : "/risk-decisions/recent";
  return apiRequest<RiskDecisionsResponse>(path, { method: "GET" });
}
