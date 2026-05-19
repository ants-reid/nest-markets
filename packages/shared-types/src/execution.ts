/** Execution types shared across frontend and backend boundary */

export type ExecutionStatus =
  | "new"
  | "accepted"
  | "filled"
  | "closed"
  | "rejected"
  | "canceled";

export type ExecutionSide = "buy" | "sell";

export interface ExecutionBase {
  execution_id: string;
  asset: string;
  side: ExecutionSide;
  status: ExecutionStatus;
  quantity: number;
  price: number;
  notional: number;
  created_at: string;
  updated_at: string;
}

export interface ExecutionJournalEntry {
  journal_id: string;
  execution_id: string;
  note: string;
  outcome_tag?: string;
  created_at: string;
}
