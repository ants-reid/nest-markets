import { apiRequest, VISUAL_SEED_PREVIEW_ENABLED } from "./core";

export type AssetClass = "fx" | "equity" | "etf" | "index_proxy" | "commodity_proxy" | "crypto";

export interface AssetResponse {
  id: string;
  symbol: string;
  name: string | null;
  asset_class: AssetClass;
  base_currency: string | null;
  quote_currency: string | null;
  exchange: string | null;
  sector: string | null;
  industry: string | null;
  is_active: boolean;
}

export interface AssetListResponse {
  items: AssetResponse[];
  total: number;
}

export interface CreateAssetRequest {
  symbol: string;
  name?: string;
  asset_class: AssetClass;
  base_currency?: string;
  quote_currency?: string;
  exchange?: string;
  sector?: string;
  industry?: string;
}

export interface RankedOpportunity {
  signal_id: string;
  asset: string;
  asset_class: AssetClass;
  direction: string;
  setup_type: string;
  confidence: number;
  score: number;
  regime: string;
  horizon: string;
  entry_low: number;
  entry_high: number;
  stop_price: number;
  target_price: number;
}

export interface OpportunityListResponse {
  items: RankedOpportunity[];
  total: number;
  sweep_id: string | null;
}

export interface DimensionWinRate {
  key: string;
  total: number;
  wins: number;
  win_rate: number;
}

export interface PerformanceStatsResponse {
  total_trades: number;
  total_wins: number;
  overall_win_rate: number;
  by_setup: DimensionWinRate[];
  by_asset: DimensionWinRate[];
  by_catalyst: DimensionWinRate[];
  by_regime: DimensionWinRate[];
}

export interface ModelVersionRecord {
  id: string;
  provider_name: string;
  model_name: string;
  alias_name: string | null;
  is_active: boolean;
  notes: string | null;
  created_at: string;
}

export interface ModelVersionListResponse {
  items: ModelVersionRecord[];
  total: number;
}

export interface ModelGovernanceActionResponse {
  action: string;
  model_version_id: string;
  is_active: boolean;
  message: string;
}

export async function getAssets(params?: {
  asset_class?: AssetClass;
  active_only?: boolean;
}): Promise<AssetListResponse> {
  const qs = new URLSearchParams();
  if (params?.asset_class) qs.set("asset_class", params.asset_class);
  if (params?.active_only !== undefined) qs.set("active_only", String(params.active_only));
  const query = qs.toString() ? `?${qs.toString()}` : "";
  return apiRequest<AssetListResponse>(`/assets${query}`, { method: "GET" });
}

export async function createAsset(body: CreateAssetRequest): Promise<AssetResponse> {
  return apiRequest<AssetResponse>("/assets", { method: "POST", body: JSON.stringify(body) });
}

export async function deactivateAsset(assetId: string): Promise<void> {
  await apiRequest<void>(`/assets/${assetId}`, { method: "DELETE" });
}

export async function getOpportunities(limit = 10): Promise<OpportunityListResponse> {
  const qs = new URLSearchParams({ limit: String(limit) });
  if (VISUAL_SEED_PREVIEW_ENABLED) qs.set("include_visual_seed", "true");
  return apiRequest<OpportunityListResponse>(`/opportunities?${qs.toString()}`, { method: "GET" });
}

export async function getPerformanceStats(): Promise<PerformanceStatsResponse> {
  const qs = new URLSearchParams();
  if (VISUAL_SEED_PREVIEW_ENABLED) qs.set("include_visual_seed", "true");
  const path = qs.toString() ? `/performance-stats?${qs.toString()}` : "/performance-stats";
  return apiRequest<PerformanceStatsResponse>(path, { method: "GET" });
}

export interface SweepRunResponse {
  worker_name: string;
  status: string;
  message: string;
  started_at: string;
  finished_at: string;
}

export async function runSweep(): Promise<SweepRunResponse> {
  return apiRequest<SweepRunResponse>("/opportunities/sweep/run", { method: "POST" });
}

export async function getModelVersions(): Promise<ModelVersionListResponse> {
  return apiRequest<ModelVersionListResponse>("/models", { method: "GET" });
}

export async function promoteModelVersion(modelVersionId: string): Promise<ModelGovernanceActionResponse> {
  return apiRequest<ModelGovernanceActionResponse>("/governance/promote", {
    method: "POST",
    body: JSON.stringify({ model_version_id: modelVersionId }),
  });
}

export async function rollbackModelVersion(): Promise<ModelGovernanceActionResponse> {
  return apiRequest<ModelGovernanceActionResponse>("/governance/rollback", {
    method: "POST",
    body: JSON.stringify({}),
  });
}
