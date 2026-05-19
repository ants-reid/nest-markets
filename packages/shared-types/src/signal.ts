/** Signal types shared across frontend and backend boundary */

export type SignalSide = "buy" | "sell";
export type SignalStatus = "pending" | "approved" | "rejected" | "canceled";

export interface Signal {
  signal_id: string;
  asset: string;
  side: SignalSide;
  price: number;
  quantity: number;
  notional: number;
  status: SignalStatus;
  created_at: string;
  updated_at: string;
  rationale?: string;
}

export interface SignalSummary {
  total: number;
  approved: number;
  rejected: number;
  pending: number;
}
