import type { ChartSeries, TimeRange } from "../../components/chart";

type ViewMode = "summary" | "visual" | "table";

export interface AnalyticsState {
  windowSize: 25 | 50 | 100;
  assetFilter: string;
  statusFilter: string;
  viewMode: ViewMode;
  showLifecycle: boolean;
  drilldownStatus: string | null;
  hiddenSeries: Set<string>;
  timeRange: TimeRange;
}

export type AnalyticsAction =
  | { type: "SET_WINDOW_SIZE"; payload: 25 | 50 | 100 }
  | { type: "SET_ASSET_FILTER"; payload: string }
  | { type: "SET_STATUS_FILTER"; payload: string }
  | { type: "SET_VIEW_MODE"; payload: ViewMode }
  | { type: "SET_SHOW_LIFECYCLE"; payload: boolean }
  | { type: "SET_DRILLDOWN"; payload: string | null }
  | { type: "TOGGLE_SERIES"; payload: string }
  | { type: "SET_TIME_RANGE"; payload: TimeRange }
  | { type: "RESET" };

export const analyticsInitialState: AnalyticsState = {
  windowSize: 50,
  assetFilter: "all",
  statusFilter: "all",
  viewMode: "visual",
  showLifecycle: false,
  drilldownStatus: null,
  hiddenSeries: new Set(),
  timeRange: "ALL",
};

export function analyticsReducer(state: AnalyticsState, action: AnalyticsAction): AnalyticsState {
  switch (action.type) {
    case "SET_WINDOW_SIZE":
      return { ...state, windowSize: action.payload };
    case "SET_ASSET_FILTER":
      return { ...state, assetFilter: action.payload };
    case "SET_STATUS_FILTER":
      return { ...state, statusFilter: action.payload };
    case "SET_VIEW_MODE":
      return { ...state, viewMode: action.payload };
    case "SET_SHOW_LIFECYCLE":
      return { ...state, showLifecycle: action.payload };
    case "SET_DRILLDOWN":
      return { ...state, drilldownStatus: action.payload };
    case "TOGGLE_SERIES": {
      const next = new Set(state.hiddenSeries);
      if (next.has(action.payload)) {
        next.delete(action.payload);
      } else {
        next.add(action.payload);
      }
      return { ...state, hiddenSeries: next };
    }
    case "SET_TIME_RANGE":
      return { ...state, timeRange: action.payload };
    case "RESET":
      return analyticsInitialState;
    default:
      return state;
  }
}
