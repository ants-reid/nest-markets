// MH-COCKPIT-04-UI — LLM logs API client (read-only).

import { apiRequest } from "./core";

export interface LLMLogItem {
  id: string;
  created_at: string | null;
  started_at: string | null;
  provider: string;
  model_requested: string;
  model_returned: string | null;
  system_prompt_hash: string | null;
  user_prompt_hash: string | null;
  system_prompt_preview: string | null;
  user_prompt_preview: string | null;
  prompt_version_id: string | null;
  stop_reason: string | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  total_tokens: number | null;
  latency_ms: number | null;
  error_class: string | null;
  error_message: string | null;
  correlation_id: string | null;
  response_payload_preview: string | null;
}

export interface LLMLogsResponse {
  count: number;
  limit: number;
  filters: {
    provider: string | null;
    correlation_id: string | null;
    only_errors: boolean;
  };
  items: LLMLogItem[];
}

export interface LLMLogsQuery {
  limit?: number;
  provider?: string;
  correlationId?: string;
  onlyErrors?: boolean;
}

export async function getRecentLLMLogs(query: LLMLogsQuery = {}): Promise<LLMLogsResponse> {
  const params = new URLSearchParams();
  if (query.limit !== undefined) params.set("limit", String(query.limit));
  if (query.provider) params.set("provider", query.provider);
  if (query.correlationId) params.set("correlation_id", query.correlationId);
  if (query.onlyErrors) params.set("only_errors", "true");
  const qs = params.toString();
  const path = qs ? `/llm-logs/recent?${qs}` : "/llm-logs/recent";
  return apiRequest<LLMLogsResponse>(path, { method: "GET" });
}
