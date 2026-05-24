// Read-only broker submit decision timeline client.
//
// Wraps GET /broker/submit-decisions/recent and exposes the UI-safe timeline
// fields needed by the cockpit history surface. This client never submits,
// cancels, retries, or mutates broker state.

import { apiRequest } from "./core";

export interface BrokerSubmitDecisionRow {
  id: string;
  created_at: string | null;
  signal_id: string | null;
  intent: string;
  would_block: boolean;
  blocked_reason_code: string | null;
  blocked_reason_text: string | null;
  decision_status: string | null;
  allowed_to_submit: boolean | null;
  decision_reason: string | null;
  source: string | null;
  submit_gate: string | null;
  broker_order_id: string | null;
  correlation_id: string | null;
  recommendation_id: string | null;
  route_check_reference: string | null;
  dry_run_reference: string | null;
  execution_mode: string | null;
  account_mode: string | null;
  risk_profile_id: string | null;
  risk_block_reason: string | null;
  execution_source: string | null;
  serious_paper_source: string | null;
  canonical_paper_route: string | null;
  broker_account_mode: string | null;
  live_state: string | null;
  request_summary: {
    ticker: string | null;
    side: string | null;
    quantity: number | null;
    order_type: string | null;
    limit_price: number | null;
    stop_price: number | null;
  } | null;
  warnings: Array<{
    code: string | null;
    message: string | null;
    source: string | null;
    classification: string | null;
    severity: string | null;
  }>;
  blocked_reasons: Array<{
    code: string | null;
    message: string | null;
    source: string | null;
    classification: string | null;
    severity: string | null;
  }>;
  preflight_json: Record<string, unknown> | null;
}

export interface BrokerSubmitDecisionsResponse {
  count: number;
  limit: number;
  filters: {
    intent: string | null;
    would_block: boolean | null;
    source: string | null;
    decision_status: string | null;
    correlation_id: string | null;
    recommendation_id: string | null;
  };
  advisory: string;
  items: BrokerSubmitDecisionRow[];
}

export interface BrokerSubmitDecisionsQuery {
  limit?: number;
  intent?: string | null;
  wouldBlock?: boolean | null;
  source?: string | null;
  decisionStatus?: string | null;
  correlationId?: string | null;
  recommendationId?: string | null;
}

export async function getRecentBrokerSubmitDecisions(
  query: BrokerSubmitDecisionsQuery = {},
): Promise<BrokerSubmitDecisionsResponse> {
  const params = new URLSearchParams();
  if (query.limit !== undefined) {
    params.set("limit", String(query.limit));
  }
  if (query.intent != null && query.intent !== "") {
    params.set("intent", query.intent);
  }
  if (query.wouldBlock !== undefined && query.wouldBlock !== null) {
    params.set("would_block", query.wouldBlock ? "true" : "false");
  }
  if (query.source != null && query.source !== "") {
    params.set("source", query.source);
  }
  if (query.decisionStatus != null && query.decisionStatus !== "") {
    params.set("decision_status", query.decisionStatus);
  }
  if (query.correlationId != null && query.correlationId !== "") {
    params.set("correlation_id", query.correlationId);
  }
  if (query.recommendationId != null && query.recommendationId !== "") {
    params.set("recommendation_id", query.recommendationId);
  }
  const qs = params.toString();
  const path = qs
    ? `/broker/submit-decisions/recent?${qs}`
    : "/broker/submit-decisions/recent";
  return apiRequest<BrokerSubmitDecisionsResponse>(path, { method: "GET" });
}
