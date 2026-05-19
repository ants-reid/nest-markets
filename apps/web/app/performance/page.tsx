"use client";

import { useEffect, useState, useCallback } from "react";

import { getPerformanceStats, type PerformanceStatsResponse } from "../../lib/api";
import { PageShell } from "../../components/ui/PageShell";
import { PageHeader } from "../../components/shell/PageHeader";
import { DataTable, type DataTableColumn } from "../../components/ui/DataTable";
import { EmptyState } from "../../components/ui/EmptyState";

const REFRESH_INTERVAL_MS = 30_000;

function pct(n: number): string {
  return `${(n * 100).toFixed(1)}%`;
}

function WinBar({ rate }: { rate: number }) {
  const color =
    rate >= 0.6
      ? "var(--state-success)"
      : rate >= 0.45
        ? "var(--state-warning)"
        : "var(--state-danger)";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 120 }}>
      <div style={{ flex: 1, height: 6, borderRadius: 3, background: "var(--chart-track-bg)", overflow: "hidden" }}>
        <div style={{ width: `${Math.min(100, rate * 100).toFixed(1)}%`, height: "100%", background: color, borderRadius: 3, transition: "width 0.4s ease" }} />
      </div>
      <span style={{ color, fontWeight: 700, fontSize: 12, minWidth: 44, textAlign: "right" as const, fontVariantNumeric: "tabular-nums" }}>
        {pct(rate)}
      </span>
    </div>
  );
}

interface PerfRow { key: string; total: number; wins: number; win_rate: number; }

const PERF_COLUMNS: DataTableColumn<PerfRow>[] = [
  { key: "key", label: "Name", sortable: true },
  { key: "total", label: "Trades", sortable: true, align: "right", width: "80px" },
  { key: "wins", label: "Wins", sortable: true, align: "right", width: "70px" },
  { key: "win_rate", label: "Win Rate", sortable: true, align: "left", width: "180px", render: (v) => <WinBar rate={Number(v)} /> },
];

function TablePanel({ title, rows }: { title: string; rows: PerfRow[] }) {
  return (
    <div style={{ border: "1px solid var(--surface-border)", borderRadius: 14, overflow: "hidden" }}>
      <div style={{ padding: "11px 16px", background: "var(--surface-soft)", borderBottom: "1px solid var(--surface-border)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <span style={{ fontSize: 12, fontWeight: 700, letterSpacing: "0.06em", textTransform: "uppercase" as const, color: "var(--text-muted)" }}>{title}</span>
        <span style={{ fontSize: 11, color: "var(--text-muted)" }}>{rows.length} row{rows.length !== 1 ? "s" : ""}</span>
      </div>
      {rows.length === 0 ? <EmptyState message="No data recorded yet." /> : <DataTable<PerfRow> columns={PERF_COLUMNS} data={rows} rowKey={(r) => r.key} />}
    </div>
  );
}

export default function PerformancePage() {
  const [data, setData] = useState<PerformanceStatsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchData = useCallback(async (isInitial = false) => {
    if (isInitial) setLoading(true);
    try {
      setData(await getPerformanceStats());
      setLastUpdated(new Date());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load performance stats.");
    } finally {
      if (isInitial) setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchData(true);
    const interval = setInterval(() => void fetchData(false), REFRESH_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [fetchData]);

  const kpis = data
    ? [
        { label: "Total Trades", value: String(data.total_trades), highlight: false },
        { label: "Total Wins", value: String(data.total_wins), highlight: false },
        { label: "Overall Win Rate", value: pct(data.overall_win_rate), highlight: true },
      ]
    : [];

  return (
    <PageShell>
      <PageHeader
        title="Performance"
        subtitle="Aggregate results from paper trades executed by the AI auto-trader."
        actions={
          lastUpdated ? (
            <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
              Live · updated {lastUpdated.toLocaleTimeString()}
            </span>
          ) : undefined
        }
      />

      {loading && <EmptyState variant="loading" title="Loading performance data…" />}

      {error && <EmptyState variant="error" message={error} />}

      {data && (
        <>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            {kpis.map((kpi) => (
              <div
                key={kpi.label}
                style={{
                  flex: "1 1 140px",
                  minWidth: 140,
                  padding: "14px 18px",
                  border: "1px solid var(--surface-border)",
                  borderRadius: 14,
                  background: "var(--surface-fill)",
                  boxShadow: "var(--surface-shadow)",
                }}
              >
                <p style={{ margin: 0, fontSize: 11, fontWeight: 700, letterSpacing: "0.07em", textTransform: "uppercase", color: "var(--text-muted)" }}>
                  {kpi.label}
                </p>
                <p style={{ margin: "6px 0 0", fontSize: 30, fontWeight: 700, color: kpi.highlight ? "var(--state-success)" : "var(--text-strong)", fontVariantNumeric: "tabular-nums", lineHeight: 1.1 }}>
                  {kpi.value}
                </p>
              </div>
            ))}
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))", gap: 16 }}>
            <TablePanel title="Win Rate by Setup" rows={data.by_setup} />
            <TablePanel title="Win Rate by Asset" rows={data.by_asset} />
            <TablePanel title="Win Rate by Catalyst" rows={data.by_catalyst} />
            <TablePanel title="Win Rate by Regime" rows={data.by_regime} />
          </div>
        </>
      )}
    </PageShell>
  );
}
