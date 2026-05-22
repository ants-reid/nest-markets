import { apiRequest } from "./core";
import type { BrokerModeInfo } from "./broker";

export type RecommendationRouteCheckStatus = "eligible" | "blocked" | "missing_context" | "unknown";

export interface PaperRecommendationRouteCheck {
  recommendation_id: string;
  recommendation_status: string;
  ticker: string | null;
  side: string | null;
  quantity: number | null;
  order_type: string | null;
  limit_price: number | null;
  estimated_notional: number | null;
  risk_score: number | null;
  route_check_status: RecommendationRouteCheckStatus;
  resolved_route: string | null;
  resolved_execution_source: string | null;
  execution_source: string;
  serious_paper_source: string;
  is_canonical_paper: boolean;
  broker_account_mode: string;
  live_state: string;
  would_block: boolean;
  blocked_reason: string | null;
  missing_data: string[];
  next_required_action: string;
  is_submit: boolean;
  workers_allowed_to_submit: boolean;
  live_trading_enabled: boolean;
  canonical_paper_route: string;
  broker_mode: BrokerModeInfo;
}

export async function getPaperRecommendationRouteCheck(
  recommendationId: string,
): Promise<PaperRecommendationRouteCheck> {
  return apiRequest<PaperRecommendationRouteCheck>(
    `/paper/recommendations/${encodeURIComponent(recommendationId)}/serious-paper-route-check`,
    { method: "GET" },
  );
}