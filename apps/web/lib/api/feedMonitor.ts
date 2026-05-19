import { apiRequest } from "./core";

export type FeedMonitorStatus = "ok" | "degraded" | "down" | "unknown" | "error";
export type FeedMonitorCategory = "feeds_in" | "feeds_out" | "runtime";

export interface FeedMonitorRow {
  id: string;
  name: string;
  category: FeedMonitorCategory;
  kind: string;
  status: FeedMonitorStatus;
  configured: boolean | null;
  runtime_reachable: boolean | null;
  detail: string | null;
  action: string | null;
  checked_at: string | null;
  latency_ms: number | null;
  target: string | null;
  tags: string[];
  extra: Record<string, unknown>;
}

export interface FeedMonitorSummary {
  total: number;
  configured: number;
  runtime_reachable: number;
  issue_count: number;
  by_status: Partial<Record<FeedMonitorStatus, number>>;
  by_category: Partial<Record<FeedMonitorCategory, number>>;
}

export interface FeedMonitorResponse {
  overall: FeedMonitorStatus;
  advisory: string;
  as_of_utc: string;
  summary: FeedMonitorSummary;
  next_actions: string[];
  rows: FeedMonitorRow[];
}

export async function getFeedMonitor(): Promise<FeedMonitorResponse> {
  return apiRequest<FeedMonitorResponse>("/monitor/feeds", { method: "GET" });
}
