import { apiRequest } from "./core";
import type {
  BrokerModeInfo,
  BrokerOrderDryRunIssue,
  BrokerOrderDryRunPreflightDecision,
  DryRunPreflightContext,
} from "./broker";

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

export interface PaperRecommendationDetails {
  id: string;
  signal_id: string | null;
  model_version_id: string | null;
  ticker: string;
  side: string;
  quantity: number;
  order_type: string;
  limit_price: number | null;
  confidence: number | null;
  risk_score: number | null;
  estimated_notional: number | null;
  rationale: string | null;
  status: string;
  created_at: string;
  reviewed_at: string | null;
  reviewed_by: string | null;
  review_notes: string | null;
  executed_at: string | null;
  paper_order_ids: string[] | null;
}

export interface PaperRecommendationBrokerDryRunPreview {
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
  dry_run_status: "ready" | "invalid" | "blocked" | "missing_context";
  dry_run_only: boolean;
  dry_run_executed: boolean;
  allowed_to_submit: boolean | null;
  resolved_route: string | null;
  resolved_execution_source: string | null;
  dry_run_execution_source: string | null;
  balance_source: string | null;
  fees_source: string | null;
  fills_source: string | null;
  positions_source: string | null;
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
  mode_guard_ok: boolean | null;
  request_valid: boolean | null;
  issues: BrokerOrderDryRunIssue[];
  warnings: BrokerOrderDryRunIssue[];
  preflight_decision: BrokerOrderDryRunPreflightDecision | null;
  preflight_context: DryRunPreflightContext | null;
  paper_path_note: string | null;
}

export async function getPaperRecommendationRouteCheck(
  recommendationId: string,
): Promise<PaperRecommendationRouteCheck> {
  return apiRequest<PaperRecommendationRouteCheck>(
    `/paper/recommendations/${encodeURIComponent(recommendationId)}/serious-paper-route-check`,
    { method: "GET" },
  );
}

export async function getPaperRecommendation(
  recommendationId: string,
): Promise<PaperRecommendationDetails> {
  return apiRequest<PaperRecommendationDetails>(
    `/paper/recommendations/${encodeURIComponent(recommendationId)}`,
    { method: "GET" },
  );
}

export async function previewPaperRecommendationBrokerDryRun(
  recommendationId: string,
): Promise<PaperRecommendationBrokerDryRunPreview> {
  return apiRequest<PaperRecommendationBrokerDryRunPreview>(
    `/paper/recommendations/${encodeURIComponent(recommendationId)}/broker-dry-run-preview`,
    { method: "POST" },
  );
}