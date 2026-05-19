// MH-COCKPIT-06-B — Cockpit notifications-digest API client (read-only).

import { apiRequest } from "./core";

export type DigestSeverity = "info" | "warn" | "error" | "critical";

export interface NotificationsDigestRow {
  id: string;
  severity: string;
  code: string;
  title: string;
  source: string;
  created_at: string | null;
  occurred_at: string | null;
}

export interface NotificationsDigestSnapshot {
  as_of_utc: string;
  window_start_utc: string;
  hours: number;
  min_severity: string;
  limit: number;
  advisory: string;
  totals: {
    incidents: number;
    by_severity: Record<string, number>;
    by_source: Record<string, number>;
  };
  attention_count: number;
  highest_severity: string;
  attention: NotificationsDigestRow[];
}

export interface NotificationsDigestQuery {
  hours?: number;
  minSeverity?: DigestSeverity;
  limit?: number;
}

export async function getNotificationsDigest(
  query: NotificationsDigestQuery = {},
): Promise<NotificationsDigestSnapshot> {
  const params = new URLSearchParams();
  if (query.hours !== undefined) params.set("hours", String(query.hours));
  if (query.minSeverity) params.set("min_severity", query.minSeverity);
  if (query.limit !== undefined) params.set("limit", String(query.limit));
  const qs = params.toString();
  const path = qs
    ? `/cockpit/notifications/digest?${qs}`
    : "/cockpit/notifications/digest";
  return apiRequest<NotificationsDigestSnapshot>(path, { method: "GET" });
}
