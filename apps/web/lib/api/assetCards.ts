// MH-COCKPIT-02-B — Asset cards API client (read-only).

import { apiRequest } from "./core";

export type AssetCardQuality = "fresh" | "stale" | "very_stale" | "no_data";

export interface AssetCardMarketQuality {
  bar_count: number;
  last_close: number | null;
  last_bar_ts: string | null;
  bars_age_seconds: number | null;
  recent_avg_volume: number | null;
  recent_volatility: number | null;
  timeframe: string | null;
  quality: AssetCardQuality;
}

export interface AssetCardItem {
  id: string;
  symbol: string;
  name: string | null;
  asset_class: string;
  exchange: string | null;
  sector: string | null;
  industry: string | null;
  is_active: boolean;
  market_quality: AssetCardMarketQuality;
}

export interface AssetCardsSnapshot {
  as_of_utc: string;
  count: number;
  limit: number;
  filters: {
    asset_class: string | null;
    active_only: boolean;
  };
  advisory: string;
  items: AssetCardItem[];
}

export interface AssetCardsQuery {
  limit?: number;
  assetClass?: string;
  activeOnly?: boolean;
}

export async function getAssetCardsSnapshot(
  query: AssetCardsQuery = {},
): Promise<AssetCardsSnapshot> {
  const params = new URLSearchParams();
  if (query.limit !== undefined) params.set("limit", String(query.limit));
  if (query.assetClass) params.set("asset_class", query.assetClass);
  if (query.activeOnly !== undefined) {
    params.set("active_only", query.activeOnly ? "true" : "false");
  }
  const qs = params.toString();
  const path = qs ? `/asset-cards/snapshot?${qs}` : "/asset-cards/snapshot";
  return apiRequest<AssetCardsSnapshot>(path, { method: "GET" });
}

// MH-COCKPIT-11-B — Asset card detail (read-only).

export interface AssetCardAsset {
  id: string;
  symbol: string;
  name: string | null;
  asset_class: string;
  base_currency: string | null;
  quote_currency: string | null;
  exchange: string | null;
  sector: string | null;
  industry: string | null;
  is_active: boolean;
}

export interface AssetCardRecentBar {
  ts: string | null;
  timeframe: string | null;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number | null;
  volume: number | null;
  vwap: number | null;
  source: string | null;
}

export interface AssetCardDetail {
  as_of_utc: string;
  advisory: string;
  recent_bars_limit: number;
  asset: AssetCardAsset;
  market_quality: AssetCardMarketQuality;
  recent_bars: AssetCardRecentBar[];
}

export async function getAssetCardDetail(
  assetId: string,
  recentBarsLimit = 30,
): Promise<AssetCardDetail> {
  const path = `/asset-cards/${encodeURIComponent(assetId)}?recent_bars_limit=${encodeURIComponent(String(recentBarsLimit))}`;
  return apiRequest<AssetCardDetail>(path, { method: "GET" });
}
