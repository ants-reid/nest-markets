// MH-COCKPIT-01-B — Markets snapshot API client (read-only).

import { apiRequest } from "./core";

export interface MarketSnapshotItem {
  code: string;
  label: string;
  timezone: string;
  is_open: boolean;
  local_time: string;
  open_time: string;
  close_time: string;
  open_weekdays: number[];
  notes: string;
}

export interface MarketSnapshotResponse {
  as_of_utc: string;
  advisory: string;
  markets: MarketSnapshotItem[];
}

export async function getMarketsSnapshot(): Promise<MarketSnapshotResponse> {
  return apiRequest<MarketSnapshotResponse>("/markets/snapshot", { method: "GET" });
}
