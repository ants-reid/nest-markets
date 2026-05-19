/** Asset/model types shared across frontend and backend boundary */

export type AssetClass = "equity" | "crypto" | "forex" | "commodity" | "index";

export interface Asset {
  asset_id: string;
  symbol: string;
  name: string;
  asset_class: AssetClass;
  created_at: string;
}

export interface RankedOpportunity {
  asset: string;
  score: number;
  rationale: string;
  rank: number;
}
