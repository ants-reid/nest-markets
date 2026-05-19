/** Scoring types shared across frontend and backend boundary */

export interface WinRateStat {
  asset: string;
  total: number;
  wins: number;
  losses: number;
  win_rate: number;
}

export interface PerformanceStats {
  total_trades: number;
  win_rate: number;
  avg_notional: number;
  total_notional: number;
  by_asset: WinRateStat[];
  by_side: { side: string; count: number; win_rate: number }[];
}
