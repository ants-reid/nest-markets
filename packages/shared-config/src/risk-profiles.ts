/** Risk profile definitions */
export const RISK_PROFILES = {
  conservative: {
    label: "Conservative",
    maxNotionalUsd: 10_000,
    maxPositions: 3,
    stopLossPct: 0.02,
    takeProfitPct: 0.04,
  },
  moderate: {
    label: "Moderate",
    maxNotionalUsd: 50_000,
    maxPositions: 8,
    stopLossPct: 0.05,
    takeProfitPct: 0.10,
  },
  aggressive: {
    label: "Aggressive",
    maxNotionalUsd: 200_000,
    maxPositions: 20,
    stopLossPct: 0.10,
    takeProfitPct: 0.20,
  },
} as const;

export type RiskProfile = keyof typeof RISK_PROFILES;
