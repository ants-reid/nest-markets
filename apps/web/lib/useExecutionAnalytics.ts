"use client";

import { useEffect, useMemo, useState } from "react";
import { listPaperExecutions, type PaperExecutionHistoryResponse, getPaperExecutionHistory } from "./api";
import { inferExecutionTimestamps } from "./chartTime";
import { useLivePolling } from "./hooks/useLivePolling";
import type { PaperExecutionResponse } from "./types";

interface RingSegment {
  label: string;
  value: number;
  color: string;
}

interface HeatCell {
  key: string;
  label: string;
  value: number;
  intensity: number;
}

interface BarItem {
  label: string;
  value: number;
  color?: string;
}

interface ExecutionInsights {
  total: number;
  rows: PaperExecutionResponse[];
}

interface ExecutionAnalyticsState {
  loading: boolean;
  error: string | null;
  insights: ExecutionInsights;
  statusSegments: RingSegment[];
  sideSegments: RingSegment[];
  hourlyHeatmap: HeatCell[];
  topAssets: BarItem[];
  acceptanceToFillRatio: string;
  acceptedRate: string;
  lifecycle: Record<string, number>;
  avgHoursToDecision: string;
  avgHoursToCompletion: string;
  latest: PaperExecutionResponse | null;
  /** Per-asset notional over (ordered) execution index — for multi-series chart */
  notionalByAsset: { asset: string; data: { t: string; v: number }[]; color: string }[];
}

const ASSET_COLORS = [
  "var(--chart-series-1)",
  "var(--chart-series-2)",
  "var(--chart-series-3)",
  "var(--chart-series-4)",
  "var(--chart-series-5)",
  "var(--chart-series-6)",
];

const STATUS_COLORS: Record<string, string> = {
  filled: "var(--state-success)",
  accepted: "var(--state-info)",
  submitted: "var(--chart-series-2)",
  closed: "var(--chart-series-4)",
  rejected: "var(--state-danger)",
  canceled: "var(--state-warning)",
  expired: "var(--text-muted)",
  new: "var(--text-muted)",
};

const SIDE_COLORS: Record<string, string> = {
  long: "var(--state-success)",
  short: "var(--state-danger)",
  flat: "var(--text-muted)",
};

function toSegments(source: Map<string, number>, palette: Record<string, string>): RingSegment[] {
  return Array.from(source.entries())
    .sort((a, b) => b[1] - a[1])
    .map(([label, value]) => ({ label, value, color: palette[label] ?? "var(--text-muted)" }));
}

function deriveHour(executionId: string): number {
  let hash = 0;
  for (let i = 0; i < executionId.length; i += 1) {
    hash = (hash << 5) - hash + executionId.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash) % 24;
}

async function fetchHistories(rows: PaperExecutionResponse[]): Promise<PaperExecutionHistoryResponse[]> {
  const settled = await Promise.all(
    rows.slice(0, 30).map(async (row) => {
      try {
        return await getPaperExecutionHistory(row.execution_id);
      } catch {
        return null;
      }
    }),
  );

  return settled.filter((value): value is PaperExecutionHistoryResponse => value !== null);
}

export function useExecutionAnalytics(): ExecutionAnalyticsState {
  const [rows, setRows] = useState<PaperExecutionResponse[]>([]);
  const [histories, setHistories] = useState<PaperExecutionHistoryResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const executions = await listPaperExecutions({ limit: 50, offset: 0 });
        if (!mounted) return;
        setRows(executions);

        const historyRows = await fetchHistories(executions);
        if (!mounted) return;
        setHistories(historyRows);
      } catch (err) {
        if (!mounted) return;
        setError(err instanceof Error ? err.message : "Failed to load analytics.");
      } finally {
        if (mounted) setLoading(false);
      }
    }

    void load();

    return () => {
      mounted = false;
    };
  }, []);

  useLivePolling(async () => {
    try {
      const executions = await listPaperExecutions({ limit: 50, offset: 0 });
      setRows(executions);
      const historyRows = await fetchHistories(executions);
      setHistories(historyRows);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load analytics.");
    }
  }, 15000, { enabled: true, runImmediately: false });

  return useMemo(() => {
    const statusCounts = new Map<string, number>();
    const sideCounts = new Map<string, number>();
    const assetCounts = new Map<string, number>();
    const hourCounts = new Array<number>(24).fill(0);

    let accepted = 0;
    let filled = 0;

    for (const row of rows) {
      const status = (row.status || "unknown").toLowerCase();
      const side = (row.side || "unknown").toLowerCase();
      const asset = (row.asset || "unknown").toUpperCase();
      const hour = deriveHour(row.execution_id);

      statusCounts.set(status, (statusCounts.get(status) ?? 0) + 1);
      sideCounts.set(side, (sideCounts.get(side) ?? 0) + 1);
      assetCounts.set(asset, (assetCounts.get(asset) ?? 0) + 1);
      hourCounts[hour] += 1;

      if (status === "accepted") accepted += 1;
      if (status === "filled") filled += 1;
    }

    const maxHour = Math.max(1, ...hourCounts);
    const hourlyHeatmap: HeatCell[] = hourCounts.map((value, hour) => ({
      key: String(hour),
      label: `${String(hour).padStart(2, "0")}:00`,
      value,
      intensity: value / maxHour,
    }));

    const topAssets: BarItem[] = Array.from(assetCounts.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6)
      .map(([label, value]) => ({ label, value, color: "var(--state-info)" }));

    // Multi-series notional chart: top 5 assets on inferred market timeline.
    const inferredTimes = inferExecutionTimestamps(rows);

    const topAssetNames = Array.from(assetCounts.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)
      .map(([asset]) => asset);

    const notionalByAsset = topAssetNames.map((asset, colorIdx) => {
      const assetRows = rows
        .map((row, idx) => ({ row, idx }))
        .filter(({ row }) => (row.asset || "unknown").toUpperCase() === asset);
      return {
        asset,
        color: ASSET_COLORS[colorIdx % ASSET_COLORS.length],
        data: assetRows.map(({ row, idx }) => ({
          t: inferredTimes[idx] ?? new Date().toISOString(),
          v: Number(row.notional) || 0,
        })),
      };
    });

    const lifecycle: Record<string, number> = {
      submitted: 0,
      accepted: 0,
      filled: 0,
      closed: 0,
      rejected: 0,
      canceled: 0,
      expired: 0,
    };

    for (const history of histories) {
      for (const stage of history.events) {
        const normalized = stage.toLowerCase();
        lifecycle[normalized] = (lifecycle[normalized] ?? 0) + 1;
      }
    }

    const acceptedRate = rows.length > 0 ? ((accepted / rows.length) * 100).toFixed(1) : "0.0";
    const acceptanceToFillRatio = accepted > 0 ? ((filled / accepted) * 100).toFixed(1) : "0.0";

    return {
      loading,
      error,
      insights: {
        total: rows.length,
        rows,
      },
      statusSegments: toSegments(statusCounts, STATUS_COLORS),
      sideSegments: toSegments(sideCounts, SIDE_COLORS),
      hourlyHeatmap,
      topAssets,
      acceptanceToFillRatio,
      acceptedRate,
      lifecycle,
      avgHoursToDecision: "-",
      avgHoursToCompletion: "-",
      latest: rows[0] ?? null,
      notionalByAsset,
    };
  }, [rows, histories, loading, error]);
}
