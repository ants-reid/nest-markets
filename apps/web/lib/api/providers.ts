// MH-MON-07 — Provider Configuration view API client (read-only).

import { apiRequest } from "./core";

export type ProviderCategory = "feeds_in" | "feeds_out" | "infrastructure";

export interface ProviderInventoryRow {
  name: string;
  category: ProviderCategory;
  status: string;
  configured: boolean;
  detail: string | null;
  latency_ms: number | null;
  checked_at: string;
  extra: Record<string, unknown>;
}

export interface ProviderInventoryResponse {
  providers: ProviderInventoryRow[];
  totals: {
    count: number;
    by_category: Partial<Record<ProviderCategory, number>>;
    configured_by_category: Partial<Record<ProviderCategory, number>>;
  };
}

export async function getProviderInventory(): Promise<ProviderInventoryResponse> {
  return apiRequest<ProviderInventoryResponse>("/health/providers", { method: "GET" });
}
