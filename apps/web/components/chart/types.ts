export interface DataPoint {
  /** ISO timestamp or label */
  t: string;
  /** Numeric value */
  v: number;
}

export interface ChartSeries {
  id: string;
  label: string;
  data: DataPoint[];
  color: string;
  /** dashed line style */
  dashed?: boolean;
}

export type TimeRange = "1D" | "1W" | "1M" | "3M" | "1Y" | "ALL";

export interface TooltipData {
  t: string;
  series: { id: string; label: string; color: string; value: number }[];
  x: number;
  y: number;
}

export interface TooltipContextRow {
  label: string;
  value: string;
}
