// MH-NEWS-08-A2-UI — News-in-decision audit log API client (read-only).
//
// Wraps GET /news-in-decision-log/recent (MH-NEWS-08-A2). The audit table
// is empty until the future MH-NEWS-08-B writer is wired (paired with
// MH-NEWS-04). This client and the cockpit page that consumes it are pure
// read surfaces.

import { apiRequest } from "./core";

export interface NewsInDecisionLogRow {
  id: string;
  created_at: string | null;
  decision_kind: string;
  decision_id: string | null;
  signal_id: string | null;
  llm_request_log_id: string | null;
  news_article_id: string | null;
  news_item_id: string | null;
  evidence_class: string;
  headline_snapshot: string | null;
  source_snapshot: string | null;
  url_snapshot: string | null;
  published_at_snapshot: string | null;
  context_json: Record<string, unknown> | null;
}

export interface NewsInDecisionLogResponse {
  count: number;
  limit: number;
  filters: {
    decision_kind: string | null;
    signal_id: string | null;
    news_article_id: string | null;
  };
  advisory: string;
  items: NewsInDecisionLogRow[];
}

export interface NewsInDecisionLogQuery {
  limit?: number;
  decisionKind?: string | null;
  signalId?: string | null;
  newsArticleId?: string | null;
}

export async function getRecentNewsInDecisionLog(
  query: NewsInDecisionLogQuery = {},
): Promise<NewsInDecisionLogResponse> {
  const params = new URLSearchParams();
  if (query.limit !== undefined) {
    params.set("limit", String(query.limit));
  }
  if (query.decisionKind != null && query.decisionKind !== "") {
    params.set("decision_kind", query.decisionKind);
  }
  if (query.signalId != null && query.signalId !== "") {
    params.set("signal_id", query.signalId);
  }
  if (query.newsArticleId != null && query.newsArticleId !== "") {
    params.set("news_article_id", query.newsArticleId);
  }
  const qs = params.toString();
  const path = qs
    ? `/news-in-decision-log/recent?${qs}`
    : "/news-in-decision-log/recent";
  return apiRequest<NewsInDecisionLogResponse>(path, { method: "GET" });
}
