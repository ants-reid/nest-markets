// MH-148-B-UI — Broker submit decisions API client (read-only).
//
// Wraps GET /broker/submit-decisions/recent (MH-148-B). The audit table is
// empty until the future MH-148-C writer is wired (paired with MH-147); this
// client and the cockpit page that consumes it are pure read surfaces.

import { apiRequest } from "./core";

export interface BrokerSubmitDecisionRow {
  id: string;
  created_at: string | null;
  signal_id: string | null;
  intent: string;
  would_block: boolean;
  blocked_reason_code: string | null;
  blocked_reason_text: string | null;
  preflight_json: Record<string, unknown> | null;
}

export interface BrokerSubmitDecisionsResponse {
  count: number;
  limit: number;
  filters: {
    intent: string | null;
    would_block: boolean | null;
  };
  advisory: string;
  items: BrokerSubmitDecisionRow[];
}

export interface BrokerSubmitDecisionsQuery {
  limit?: number;
  intent?: string | null;
  wouldBlock?: boolean | null;
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
  const qs = params.toString();
  const path = qs
    ? `/broker/submit-decisions/recent?${qs}`
    : "/broker/submit-decisions/recent";
  return apiRequest<BrokerSubmitDecisionsResponse>(path, { method: "GET" });
}
