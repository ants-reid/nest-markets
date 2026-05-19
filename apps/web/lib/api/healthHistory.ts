// MH-MON-08-B — Health history API client (read-only).

import { apiRequest } from "./core";

export interface HealthHistoryBucket {
  bucket_start: string;
  counts: Record<string, number>;
  total: number;
}

export interface HealthHistoryLastEntry {
  severity: string;
  code: string;
  title: string;
  created_at: string;
}

export interface HealthHistorySnapshot {
  as_of_utc: string;
  window_start_utc: string;
  hours: number;
  bucket_minutes: number;
  filters: { source: string | null };
  advisory: string;
  totals: {
    by_severity: Record<string, number>;
    by_source: Record<string, number>;
    incidents: number;
  };
  last_per_source: Record<string, HealthHistoryLastEntry>;
  timeseries: HealthHistoryBucket[];
}

export interface HealthHistoryQuery {
  hours?: number;
  bucketMinutes?: number;
  source?: string;
}

export async function getHealthHistory(
  query: HealthHistoryQuery = {},
): Promise<HealthHistorySnapshot> {
  const params = new URLSearchParams();
  if (query.hours !== undefined) params.set("hours", String(query.hours));
  if (query.bucketMinutes !== undefined) {
    params.set("bucket_minutes", String(query.bucketMinutes));
  }
  if (query.source) params.set("source", query.source);
  const qs = params.toString();
  const path = qs ? `/monitor/health-history?${qs}` : "/monitor/health-history";
  return apiRequest<HealthHistorySnapshot>(path, { method: "GET" });
}
