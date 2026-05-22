import { apiRequest } from "./core";

export type CockpitDailyScoreboardDayStatus =
  | "green_day"
  | "red_day"
  | "flat_day"
  | "data_incomplete"
  | "review_required"
  | "monitor_attention"
  | "unknown";

export interface CockpitDailyScoreboardSummary {
  headline: string;
  day_status: CockpitDailyScoreboardDayStatus;
  trades_opened_today: number;
  trades_closed_today: number;
  open_positions_now: number;
}

export interface CockpitDailyScoreboardPerformance {
  realized_pnl_today: number | null;
  unrealized_pnl_snapshot: number | null;
  net_pnl_today: number | null;
  win_count: number | null;
  loss_count: number | null;
  flat_count: number | null;
  unknown_count: number;
}

export interface CockpitDailyScoreboardActivity {
  trades_opened_today: number;
  trades_closed_today: number;
  open_positions_now: number;
}

export interface CockpitDailyScoreboardOpenPositions {
  count: number;
  long_count: number;
  short_count: number;
}

export interface CockpitDailyScoreboardClosedPositions {
  count: number;
  wins: number | null;
  losses: number | null;
  flat: number | null;
  unknown: number;
}

export interface CockpitDailyScoreboardContributor {
  symbol: string;
  realized_pnl: number | null;
  contribution_label: "positive" | "negative" | "flat" | "unknown";
  evidence: string[];
}

export interface CockpitDailyScoreboardTopContributors {
  count: number;
  items: CockpitDailyScoreboardContributor[];
}

export interface CockpitDailyScoreboardNote {
  label: CockpitDailyScoreboardDayStatus;
  title: string;
  detail: string;
  severity: string;
  created_at: string | null;
}

export interface CockpitDailyScoreboardResponse {
  report_date: string;
  generated_at: string;
  mode: "paper";
  summary: CockpitDailyScoreboardSummary;
  performance: CockpitDailyScoreboardPerformance;
  activity: CockpitDailyScoreboardActivity;
  open_positions: CockpitDailyScoreboardOpenPositions;
  closed_positions: CockpitDailyScoreboardClosedPositions;
  top_contributors: CockpitDailyScoreboardTopContributors;
  risk_and_monitor_notes: CockpitDailyScoreboardNote[];
  review_priorities: string[];
  limitations: string[];
}

export async function getCockpitDailyScoreboard(): Promise<CockpitDailyScoreboardResponse> {
  return apiRequest<CockpitDailyScoreboardResponse>("/cockpit/daily-scoreboard", {
    method: "GET",
  });
}
