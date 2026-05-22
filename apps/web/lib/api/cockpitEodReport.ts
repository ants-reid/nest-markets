import { apiRequest } from "./core";

export interface CockpitEodSummary {
  headline: string;
  opened_today: number;
  closed_today: number;
  open_positions_now: number;
  alerts_needing_attention: number;
  lessons_available: number;
}

export interface CockpitEodPnl {
  realized_day: number | null;
  unrealized_snapshot: number | null;
  realized_basis: string;
  unrealized_basis: string;
}

export interface CockpitEodOpenPositionItem {
  asset_symbol: string;
  asset_id: string | null;
  asset_name: string | null;
  asset_detail_path: string | null;
  has_asset_context: boolean;
  side: string;
  qty: number | null;
  opened_at: string | null;
  unrealized_pnl: number | null;
}

export interface CockpitEodTradeItem {
  asset_symbol: string;
  asset_id: string | null;
  asset_name: string | null;
  asset_detail_path: string | null;
  has_asset_context: boolean;
  side: string;
  opened_at: string | null;
  closed_at: string | null;
  realized_pnl: number | null;
  close_reason: string | null;
}

export interface CockpitEodPaperActivity {
  opened_today: number;
  closed_today: number;
  current_open_positions: number;
}

export interface CockpitEodOpenPositions {
  count: number;
  items: CockpitEodOpenPositionItem[];
}

export interface CockpitEodClosedPositions {
  count: number;
  wins: number | null;
  losses: number | null;
  flat: number | null;
  unknown: number;
  best_trade: CockpitEodTradeItem | null;
  worst_trade: CockpitEodTradeItem | null;
  items: CockpitEodTradeItem[];
}

export interface CockpitEodIncidentItem {
  severity: string;
  code: string;
  title: string;
  source: string;
  created_at: string | null;
  detail: string | null;
}

export interface CockpitEodMonitorNote {
  title: string;
  detail: string;
  severity: string;
  created_at: string | null;
}

export interface CockpitEodLesson {
  title: string;
  detail: string;
  evidence_count: number;
}

export interface CockpitEodReportResponse {
  report_date: string;
  generated_at: string;
  mode: "paper";
  summary: CockpitEodSummary;
  paper_activity: CockpitEodPaperActivity;
  pnl: CockpitEodPnl;
  open_positions: CockpitEodOpenPositions;
  closed_positions: CockpitEodClosedPositions;
  alerts_or_incidents: CockpitEodIncidentItem[];
  monitor_notes: CockpitEodMonitorNote[];
  lessons: CockpitEodLesson[];
  recommended_actions: string[];
  limitations: string[];
}

export async function getCockpitEodReport(): Promise<CockpitEodReportResponse> {
  return apiRequest<CockpitEodReportResponse>("/cockpit/eod-report", {
    method: "GET",
  });
}