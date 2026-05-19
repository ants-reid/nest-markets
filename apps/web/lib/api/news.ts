import { apiRequest } from "./core";

export interface MarketDataStatusItem {
  asset_symbol: string;
  timeframe: string;
  last_bar_ts: string | null;
  bar_count: number;
}

export interface MarketDataStatusResponse {
  items: MarketDataStatusItem[];
}

export interface MarketDataNewsItem {
  id: string;
  headline: string;
  source_name: string | null;
  published_at: string;
  url: string | null;
  tickers: string[];
}

export interface MarketDataBarItem {
  ts: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number | null;
}

export interface MarketDataBarsResponse {
  asset_symbol: string;
  timeframe: string;
  items: MarketDataBarItem[];
}

export interface PromptListResponse {
  prompts: string[];
}

export interface PromptDetailResponse {
  name: string;
  content: string;
}

export interface PromptHistoryItem {
  id: string;
  name: string;
  role: string;
  version: string;
  is_active: boolean;
  file_hash: string | null;
  created_at: string;
}

export interface PromptAdaptationProposalRequest {
  setup_type: string;
  rationale: string;
  proposed_prompt_text: string;
  current_win_rate: number;
  total_samples: number;
}

export interface PromptVersionCreatedResponse {
  id: string;
  name: string;
  role: string;
  version: string;
  is_active: boolean;
}

export async function getMarketDataStatus(): Promise<MarketDataStatusResponse> {
  return apiRequest<MarketDataStatusResponse>("/market-data/status", { method: "GET" });
}

export async function getMarketDataNews(ticker: string, limit = 5): Promise<MarketDataNewsItem[]> {
  return apiRequest<MarketDataNewsItem[]>(`/market-data/news/${ticker}?limit=${limit}`, { method: "GET" });
}

export async function getMarketDataBars(
  ticker: string,
  timeframe = "1h",
  limit = 120,
): Promise<MarketDataBarsResponse> {
  return apiRequest<MarketDataBarsResponse>(
    `/market-data/bars/${encodeURIComponent(ticker)}?timeframe=${encodeURIComponent(timeframe)}&limit=${limit}`,
    { method: "GET" },
  );
}

export async function listPrompts(): Promise<PromptListResponse> {
  return apiRequest<PromptListResponse>("/prompts", { method: "GET" });
}

export async function getPrompt(subdir: string, filename: string): Promise<PromptDetailResponse> {
  return apiRequest<PromptDetailResponse>(`/prompts/${subdir}/${filename}`, { method: "GET" });
}

export async function getPromptHistory(subdir: string, filename: string): Promise<PromptHistoryItem[]> {
  return apiRequest<PromptHistoryItem[]>(`/prompts/${subdir}/${filename}/history`, { method: "GET" });
}

export async function applyPromptAdaptation(
  proposal: PromptAdaptationProposalRequest,
): Promise<PromptVersionCreatedResponse> {
  return apiRequest<PromptVersionCreatedResponse>("/prompt-adaptations/apply", {
    method: "POST",
    body: JSON.stringify(proposal),
  });
}

export interface RegimeSnapshot {
  regime: string;
  confidence: number;
  detected_at: string;
}

export async function getRegime(): Promise<RegimeSnapshot> {
  return apiRequest<RegimeSnapshot>("/regime/current", { method: "GET" });
}
