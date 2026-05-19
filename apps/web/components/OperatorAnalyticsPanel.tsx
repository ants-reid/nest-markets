"use client";

import { useMemo } from "react";
import type { PaperExecutionResponse } from "../lib/types";

interface OperatorAnalyticsPanelProps {
  executions: PaperExecutionResponse[];
  loading: boolean;
  error: string | null;
}

const openStatuses = new Set(["new", "submitted", "accepted", "filled"]);
const closedStatuses = new Set(["closed", "rejected", "canceled", "expired"]);

function panelStyle(): React.CSSProperties {
  return {
    display: "grid",
    gap: 18,
    padding: 24,
    borderRadius: 20,
    background: "var(--surface-fill)",
    border: "1px solid var(--surface-border)",
    boxShadow: "var(--surface-shadow)",
  };
}

function kpiRowStyle(): React.CSSProperties {
  return {
    display: "grid",
    gap: 14,
    gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
  };
}

function kpiCardStyle(): React.CSSProperties {
  return {
    display: "grid",
    gap: 6,
    padding: "12px 14px",
    borderRadius: 12,
    background: "var(--surface-soft)",
    border: "1px solid var(--surface-border)",
  };
}

function barTrackStyle(): React.CSSProperties {
  return {
    height: 6,
    borderRadius: 3,
    background: "var(--chart-track-bg)",
    overflow: "hidden",
  };
}

function barFillStyle(pct: number, color: string): React.CSSProperties {
  return {
    height: "100%",
    width: `${Math.min(100, Math.max(0, pct))}%`,
    borderRadius: 4,
    background: color,
  };
}

const STATUS_COLORS: Record<string, string> = {
  filled: "var(--state-success)",
  accepted: "var(--state-info)",
  closed: "var(--accent-primary)",
  submitted: "var(--accent-secondary)",
  new: "var(--text-muted)",
  rejected: "var(--state-danger)",
  canceled: "var(--state-warning)",
  expired: "var(--text-muted)",
};

const SIDE_COLORS: Record<string, string> = {
  long: "var(--state-success)",
  short: "var(--state-danger)",
  flat: "var(--text-muted)",
};

function pct(count: number, total: number): number {
  if (total === 0) return 0;
  return (count / total) * 100;
}

function fmtPct(count: number, total: number): string {
  if (total === 0) return "0%";
  return `${((count / total) * 100).toFixed(1)}%`;
}

function fmtMoney(value: number): string {
  return `$${value.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function OperatorAnalyticsPanel({ executions, loading, error }: OperatorAnalyticsPanelProps) {
  const analytics = useMemo(() => {
    const total = executions.length;
    if (total === 0) {
      return null;
    }

    const byStatus: Record<string, number> = {};
    const bySide: Record<string, number> = {};
    const byAsset: Record<string, number> = {};

    let filledCount = 0;
    let closedCount = 0;
    let openCount = 0;
    let totalNotional = 0;
    let openNotional = 0;

    for (const ex of executions) {
      const status = ex.status.toLowerCase();
      const side = ex.side.toLowerCase();
      const asset = ex.asset.toUpperCase();

      byStatus[status] = (byStatus[status] ?? 0) + 1;
      bySide[side] = (bySide[side] ?? 0) + 1;
      byAsset[asset] = (byAsset[asset] ?? 0) + 1;

      if (status === "filled") filledCount += 1;
      if (closedStatuses.has(status)) closedCount += 1;
      if (openStatuses.has(status)) {
        openCount += 1;
        openNotional += ex.notional;
      }

      totalNotional += ex.notional;
    }

    const avgNotional = totalNotional / total;
    const dominantSide = Object.entries(bySide).sort(([, a], [, b]) => b - a)[0]?.[0] ?? "-";
    const sortedStatuses = Object.entries(byStatus).sort(([, a], [, b]) => b - a);
    const sortedSides = Object.entries(bySide).sort(([, a], [, b]) => b - a);
    const sortedAssets = Object.entries(byAsset).sort(([, a], [, b]) => b - a);

    return {
      total,
      filledCount,
      closedCount,
      openCount,
      avgNotional,
      openNotional,
      dominantSide,
      sortedStatuses,
      sortedSides,
      sortedAssets,
    };
  }, [executions]);

  return (
    <section style={panelStyle()}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
        <h2 style={{ margin: 0, color: "var(--text-strong)", fontSize: 22, fontWeight: 800, letterSpacing: 0.1 }}>
          Analytics &amp; Performance
        </h2>
        <span style={{ color: "var(--text-muted)", fontSize: 11, textTransform: "uppercase", letterSpacing: 1.4, fontWeight: 700 }}>
          Derived from /execution/paper
        </span>
      </div>

      {loading ? <p style={{ margin: 0, color: "var(--text-muted)" }}>Loading analytics...</p> : null}

      {!loading && error ? (
        <div
          style={{
            padding: 12,
            borderRadius: 12,
            background: "var(--state-danger-soft)",
            color: "var(--state-danger)",
            border: "1px solid var(--state-danger-border)",
          }}
        >
          Analytics unavailable: {error}
        </div>
      ) : null}

      {!loading && !error && analytics === null ? (
        <div
          style={{
            padding: 12,
            borderRadius: 12,
            border: "1px dashed var(--surface-border)",
            color: "var(--text-muted)",
            background: "var(--surface-soft)",
          }}
        >
          No execution data yet. Submit a workflow or paper execution to populate analytics.
        </div>
      ) : null}

      {!loading && !error && analytics !== null ? (
        <>
          <div style={kpiRowStyle()}>
            <div style={kpiCardStyle()}>
              <span style={{ color: "var(--text-muted)", fontSize: 11, textTransform: "uppercase", letterSpacing: 1.2, fontWeight: 700 }}>
                Filled Rate
              </span>
              <strong style={{ color: "var(--state-success)", fontSize: 26, lineHeight: 1.1, fontVariantNumeric: "tabular-nums" }}>
                {fmtPct(analytics.filledCount, analytics.total)}
              </strong>
              <span style={{ color: "var(--text-muted)", fontSize: 12 }}>{analytics.filledCount} of {analytics.total} executions</span>
            </div>

            <div style={kpiCardStyle()}>
              <span style={{ color: "var(--text-muted)", fontSize: 11, textTransform: "uppercase", letterSpacing: 1.2, fontWeight: 700 }}>
                Closed Rate
              </span>
              <strong style={{ color: "var(--accent-primary)", fontSize: 26, lineHeight: 1.1, fontVariantNumeric: "tabular-nums" }}>
                {fmtPct(analytics.closedCount, analytics.total)}
              </strong>
              <span style={{ color: "var(--text-muted)", fontSize: 12 }}>{analytics.closedCount} closed of {analytics.total}</span>
            </div>

            <div style={kpiCardStyle()}>
              <span style={{ color: "var(--text-muted)", fontSize: 11, textTransform: "uppercase", letterSpacing: 1.2, fontWeight: 700 }}>
                Open Rate
              </span>
              <strong style={{ color: "var(--state-info)", fontSize: 26, lineHeight: 1.1, fontVariantNumeric: "tabular-nums" }}>
                {fmtPct(analytics.openCount, analytics.total)}
              </strong>
              <span style={{ color: "var(--text-muted)", fontSize: 12 }}>{analytics.openCount} open of {analytics.total}</span>
            </div>

            <div style={kpiCardStyle()}>
              <span style={{ color: "var(--text-muted)", fontSize: 11, textTransform: "uppercase", letterSpacing: 1.2, fontWeight: 700 }}>
                Avg Notional
              </span>
              <strong style={{ color: "var(--accent-highlight)", fontSize: 26, lineHeight: 1.1, fontVariantNumeric: "tabular-nums" }}>
                {fmtMoney(analytics.avgNotional)}
              </strong>
              <span style={{ color: "var(--text-muted)", fontSize: 12 }}>per execution (notional)</span>
            </div>

            <div style={kpiCardStyle()}>
              <span style={{ color: "var(--text-muted)", fontSize: 11, textTransform: "uppercase", letterSpacing: 1.2, fontWeight: 700 }}>
                Dominant Side
              </span>
              <strong
                style={{
                  color: SIDE_COLORS[analytics.dominantSide] ?? "var(--accent-highlight)",
                  fontSize: 26,
                  lineHeight: 1.1,
                  textTransform: "capitalize",
                  fontVariantNumeric: "tabular-nums",
                }}
              >
                {analytics.dominantSide}
              </strong>
              <span style={{ color: "var(--text-muted)", fontSize: 12 }}>most common direction</span>
            </div>

            <div style={kpiCardStyle()}>
              <span style={{ color: "var(--text-muted)", fontSize: 11, textTransform: "uppercase", letterSpacing: 1.2, fontWeight: 700 }}>
                Open Notional
              </span>
              <strong style={{ color: "var(--accent-highlight)", fontSize: 26, lineHeight: 1.1, fontVariantNumeric: "tabular-nums" }}>
                {fmtMoney(analytics.openNotional)}
              </strong>
              <span style={{ color: "var(--text-muted)", fontSize: 12 }}>live paper exposure proxy</span>
            </div>
          </div>

          <div style={{ display: "grid", gap: 10 }}>
            <h3 style={{ margin: 0, color: "var(--text-strong)", fontSize: 14, fontWeight: 700, letterSpacing: 0.2 }}>
              Status Conversion Breakdown
            </h3>
            <div style={{ display: "grid", gap: 8 }}>
              {analytics.sortedStatuses.map(([status, count]) => (
                <div key={status} style={{ display: "grid", gap: 4 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontSize: 12, color: "var(--text-strong)", textTransform: "capitalize", fontWeight: 600 }}>{status}</span>
                    <span style={{ fontSize: 11, color: "var(--text-muted)" }}>{count} ({fmtPct(count, analytics.total)})</span>
                  </div>
                  <div style={barTrackStyle()}>
                    <div style={barFillStyle(pct(count, analytics.total), STATUS_COLORS[status] ?? "var(--text-muted)")} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div style={{ display: "grid", gap: 16, gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))" }}>
            <div style={{ display: "grid", gap: 10 }}>
              <h3 style={{ margin: 0, color: "var(--text-strong)", fontSize: 14, fontWeight: 700, letterSpacing: 0.2 }}>
                Side Distribution
              </h3>
              <div style={{ display: "grid", gap: 8 }}>
                {analytics.sortedSides.map(([side, count]) => (
                  <div key={side} style={{ display: "grid", gap: 4 }}>
                    <div style={{ display: "flex", justifyContent: "space-between" }}>
                      <span style={{ fontSize: 13, color: SIDE_COLORS[side] ?? "var(--text-strong)", textTransform: "capitalize", fontWeight: 600 }}>
                        {side}
                      </span>
                      <span style={{ fontSize: 11, color: "var(--text-muted)" }}>{count} ({fmtPct(count, analytics.total)})</span>
                    </div>
                    <div style={barTrackStyle()}>
                      <div style={barFillStyle(pct(count, analytics.total), SIDE_COLORS[side] ?? "var(--text-muted)")} />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div style={{ display: "grid", gap: 10 }}>
              <h3 style={{ margin: 0, color: "var(--text-strong)", fontSize: 14, fontWeight: 700, letterSpacing: 0.2 }}>
                Asset Distribution
              </h3>
              {analytics.sortedAssets.length === 0 ? (
                <p style={{ margin: 0, color: "var(--text-muted)", fontSize: 12 }}>No asset data available.</p>
              ) : (
                <div style={{ display: "grid", gap: 8 }}>
                  {analytics.sortedAssets.map(([asset, count]) => (
                    <div key={asset} style={{ display: "grid", gap: 4 }}>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <span style={{ fontSize: 12, color: "var(--text-strong)", fontWeight: 600 }}>{asset}</span>
                        <span style={{ fontSize: 11, color: "var(--text-muted)" }}>{count} ({fmtPct(count, analytics.total)})</span>
                      </div>
                      <div style={barTrackStyle()}>
                        <div style={barFillStyle(pct(count, analytics.total), "var(--accent-highlight)")} />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </>
      ) : null}
    </section>
  );
}
