// MH-158-B — Worker run log overview API client (read-only).

import { apiRequest } from "./core";

export interface WorkerRunLogRetention {
  storage_backend: string;
  trim_on_append: boolean;
  max_entries: number;
  current_entry_count: number;
  entries_remaining: number;
  utilization_pct: number;
  warning_threshold_pct: number;
  near_capacity: boolean;
  retention_status: string;
  retention_warning: string | null;
  retained_span_hours: number | null;
  average_entries_per_day: number | null;
  estimated_days_until_capacity: number | null;
  retention_trend_status: string;
  log_exists: boolean;
  oldest_started_at: string | null;
  latest_started_at: string | null;
}

export interface WorkerRunEntry {
  worker_name: string;
  status: string;
  message: string;
  started_at: string;
  finished_at: string;
  source: string;
  outcome_counts: Record<string, number> | null;
}

export interface WorkerRunLogOverview {
  advisory: string;
  limit: number;
  retention: WorkerRunLogRetention;
  totals: {
    returned: number;
    by_status: Record<string, number>;
    by_source: Record<string, number>;
  };
  entries: WorkerRunEntry[];
}

export async function getWorkerRunLogOverview(
  limit = 20,
): Promise<WorkerRunLogOverview> {
  const path = `/monitor/worker-run-log/overview?limit=${encodeURIComponent(String(limit))}`;
  return apiRequest<WorkerRunLogOverview>(path, { method: "GET" });
}
