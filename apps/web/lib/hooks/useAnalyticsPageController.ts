"use client";

import { useEffect, useMemo, useReducer, useState } from "react";
import { getMarketDataStatus } from "../api";
import { useExecutionAnalytics } from "../useExecutionAnalytics";
import type { ChartSeries, TimeRange } from "../../components/chart";
import { analyticsReducer, analyticsInitialState } from "../state/analyticsReducer";
import { useLivePolling } from "./useLivePolling";

type ViewMode = "summary" | "visual" | "table";

export interface AnalyticsPageState {
  // Filters
  windowSize: 25 | 50 | 100;
  assetFilter: string;
  statusFilter: string;
  viewMode: ViewMode;
  showLifecycle: boolean;
  drilldownStatus: string | null;
  hiddenSeries: Set<string>;
  timeRange: TimeRange;

  // Derived
  assetOptions: string[];
  statusOptions: string[];
  filteredRows: any[];
  filteredSummary: {
    count: number;
    avgNotional: number;
    statusList: [string, number][];
    sideList: [string, number][];
  };
  topStatusCards: [string, number][];
  lifecycleRows: [string, number][];
  chartSeries: ChartSeries[];
  lastUpdated: string | null;

  // From useExecutionAnalytics
  loading: boolean;
  error: string | null;
  insights: ReturnType<typeof useExecutionAnalytics>["insights"];
  statusSegments: ReturnType<typeof useExecutionAnalytics>["statusSegments"];
  sideSegments: ReturnType<typeof useExecutionAnalytics>["sideSegments"];
  hourlyHeatmap: ReturnType<typeof useExecutionAnalytics>["hourlyHeatmap"];
  topAssets: ReturnType<typeof useExecutionAnalytics>["topAssets"];
  acceptanceToFillRatio: ReturnType<typeof useExecutionAnalytics>["acceptanceToFillRatio"];
  acceptedRate: ReturnType<typeof useExecutionAnalytics>["acceptedRate"];
  avgHoursToDecision: ReturnType<typeof useExecutionAnalytics>["avgHoursToDecision"];
  avgHoursToCompletion: ReturnType<typeof useExecutionAnalytics>["avgHoursToCompletion"];
  latest: ReturnType<typeof useExecutionAnalytics>["latest"];
}

export interface AnalyticsPageActions {
  setWindowSize: (size: 25 | 50 | 100) => void;
  setAssetFilter: (asset: string) => void;
  setStatusFilter: (status: string) => void;
  setViewMode: (mode: ViewMode) => void;
  setShowLifecycle: (show: boolean) => void;
  setDrilldownStatus: (status: string | null) => void;
  toggleSeries: (id: string) => void;
  setTimeRange: (range: TimeRange) => void;
}

export function useAnalyticsPageController(): AnalyticsPageState & AnalyticsPageActions {
  const [state, dispatch] = useReducer(analyticsReducer, analyticsInitialState);
  const {
    windowSize,
    assetFilter,
    statusFilter,
    viewMode,
    showLifecycle,
    drilldownStatus,
    hiddenSeries,
    timeRange,
  } = state;

  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const {
    loading,
    error,
    insights,
    statusSegments,
    sideSegments,
    hourlyHeatmap,
    topAssets,
    acceptanceToFillRatio,
    acceptedRate,
    lifecycle,
    avgHoursToDecision,
    avgHoursToCompletion,
    latest,
    notionalByAsset,
  } = useExecutionAnalytics();

  const sourceRows = useMemo(() => {
    const rows = insights?.rows ?? [];
    return rows.slice(0, windowSize);
  }, [insights?.rows, windowSize]);

  const assetOptions = useMemo(() => {
    const assets = new Set<string>();
    for (const row of sourceRows) {
      assets.add(((row as { asset?: string }).asset ?? "").toUpperCase());
    }
    return ["all", ...Array.from(assets).filter(Boolean).sort()];
  }, [sourceRows]);

  const statusOptions = useMemo(() => {
    const statuses = new Set<string>();
    for (const row of sourceRows) {
      statuses.add(((row as { status?: string }).status ?? "").toLowerCase());
    }
    return ["all", ...Array.from(statuses).filter(Boolean).sort()];
  }, [sourceRows]);

  const filteredRows = useMemo(() => {
    return sourceRows.filter((row) => {
      const r = row as { asset?: string; status?: string };
      const assetOk = assetFilter === "all" || (r.asset ?? "").toUpperCase() === assetFilter;
      const status = (r.status ?? "").toLowerCase();
      const statusOk = statusFilter === "all" || status === statusFilter;
      const drillOk = drilldownStatus === null || status === drilldownStatus;
      return assetOk && statusOk && drillOk;
    });
  }, [sourceRows, assetFilter, statusFilter, drilldownStatus]);

  const filteredSummary = useMemo(() => {
    const byStatus = new Map<string, number>();
    const bySide = new Map<string, number>();
    let totalNotional = 0;

    for (const row of filteredRows) {
      const r = row as { status?: string; side?: string; notional?: number };
      const status = (r.status ?? "unknown").toLowerCase();
      const side = (r.side ?? "unknown").toLowerCase();
      byStatus.set(status, (byStatus.get(status) ?? 0) + 1);
      bySide.set(side, (bySide.get(side) ?? 0) + 1);
      totalNotional += Number(r.notional) || 0;
    }

    return {
      count: filteredRows.length,
      avgNotional: filteredRows.length > 0 ? totalNotional / filteredRows.length : 0,
      statusList: Array.from(byStatus.entries()).sort((a, b) => b[1] - a[1]) as [string, number][],
      sideList: Array.from(bySide.entries()).sort((a, b) => b[1] - a[1]) as [string, number][],
    };
  }, [filteredRows]);

  const topStatusCards = filteredSummary.statusList.slice(0, 4);

  const lifecycleRows = useMemo(() => {
    return Object.entries(lifecycle).sort((a, b) => b[1] - a[1]);
  }, [lifecycle]);

  const chartSeries = useMemo((): ChartSeries[] => {
    return notionalByAsset.map((s) => ({
      id: s.asset,
      label: s.asset,
      data: s.data,
      color: s.color,
    }));
  }, [notionalByAsset]);

  function toggleSeries(id: string) {
    dispatch({ type: "TOGGLE_SERIES", payload: id });
  }

  useEffect(() => {
    getMarketDataStatus()
      .then((res) => {
        const latestTs = res.items
          .map((item) => item.last_bar_ts)
          .filter((value): value is string => Boolean(value))
          .sort()
          .at(-1);
        setLastUpdated(latestTs ?? null);
      })
      .catch(() => setLastUpdated(null));
  }, []);

  useLivePolling(() => {
    getMarketDataStatus()
      .then((res) => {
        const latestTs = res.items
          .map((item) => item.last_bar_ts)
          .filter((value): value is string => Boolean(value))
          .sort()
          .at(-1);
        setLastUpdated(latestTs ?? null);
      })
      .catch(() => setLastUpdated(null));
  }, 15000, { enabled: true, runImmediately: false });

  return {
    windowSize,
    assetFilter,
    statusFilter,
    viewMode,
    showLifecycle,
    drilldownStatus,
    hiddenSeries,
    timeRange,
    assetOptions,
    statusOptions,
    filteredRows,
    filteredSummary,
    topStatusCards,
    lifecycleRows,
    chartSeries,
    lastUpdated,
    loading,
    error,
    insights,
    statusSegments,
    sideSegments,
    hourlyHeatmap,
    topAssets,
    acceptanceToFillRatio,
    acceptedRate,
    avgHoursToDecision,
    avgHoursToCompletion,
    latest,
    setWindowSize: (size) => dispatch({ type: "SET_WINDOW_SIZE", payload: size }),
    setAssetFilter: (asset) => dispatch({ type: "SET_ASSET_FILTER", payload: asset }),
    setStatusFilter: (status) => dispatch({ type: "SET_STATUS_FILTER", payload: status }),
    setViewMode: (mode) => dispatch({ type: "SET_VIEW_MODE", payload: mode }),
    setShowLifecycle: (show) => dispatch({ type: "SET_SHOW_LIFECYCLE", payload: show }),
    setDrilldownStatus: (status) => dispatch({ type: "SET_DRILLDOWN", payload: status }),
    toggleSeries,
    setTimeRange: (range) => dispatch({ type: "SET_TIME_RANGE", payload: range }),
  };
}
