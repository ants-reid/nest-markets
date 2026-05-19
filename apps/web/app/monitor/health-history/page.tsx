"use client";

// MH-MON-08-B — Health-history charts page (read-only).
// Renders time-bucketed incident counts from /monitor/health-history.
// Inline SVG only — no new chart libraries. Drift lock: read-only,
// never feeds the trading path.

import { useCallback, useEffect, useState } from "react";

import {
  getHealthHistory,
  type HealthHistoryBucket,
  type HealthHistorySnapshot,
} from "../../../lib/api/healthHistory";
import styles from "../../../styles/pages/health-history.module.css";

const SEVERITY_ORDER: ReadonlyArray<"info" | "warn" | "error" | "critical"> = [
  "info",
  "warn",
  "error",
  "critical",
];

const SEVERITY_COLOR: Record<string, string> = {
  info: "var(--state-info)",
  warn: "var(--state-warning)",
  error: "var(--state-danger)",
  critical: "var(--state-danger)",
};

const BUCKET_OPTIONS = [15, 30, 60, 120, 240];
const HOURS_OPTIONS = [4, 8, 12, 24, 48, 72, 168];

function formatBucketLabel(iso: string, bucketMinutes: number): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  if (bucketMinutes >= 60) {
    return d.toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
    });
  }
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

interface StackedBarsProps {
  buckets: HealthHistoryBucket[];
  bucketMinutes: number;
}

function StackedBars({ buckets, bucketMinutes }: StackedBarsProps) {
  const width = 1000;
  const height = 220;
  const padding = { top: 12, right: 12, bottom: 28, left: 36 };
  const innerW = width - padding.left - padding.right;
  const innerH = height - padding.top - padding.bottom;

  if (buckets.length === 0) {
    return <div className={styles.empty}>No buckets to render.</div>;
  }

  const maxTotal = Math.max(1, ...buckets.map((b) => b.total));
  const barW = innerW / buckets.length;
  const gap = Math.min(2, barW * 0.15);

  // Y-axis ticks (4 lines)
  const ticks = 4;
  const tickValues = Array.from({ length: ticks + 1 }, (_, i) =>
    Math.round((maxTotal * i) / ticks),
  );

  return (
    <svg
      className={styles.svg}
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      role="img"
      aria-label="Incident counts per time bucket, stacked by severity"
    >
      {/* gridlines + y labels */}
      {tickValues.map((v, i) => {
        const y = padding.top + innerH - (innerH * i) / ticks;
        return (
          <g key={`tick-${i}`}>
            <line
              x1={padding.left}
              x2={padding.left + innerW}
              y1={y}
              y2={y}
              stroke="color-mix(in oklab, var(--text-muted) 18%, transparent)"
              strokeWidth={1}
            />
            <text
              x={padding.left - 6}
              y={y + 3}
              fontSize={10}
              fill="var(--text-muted)"
              textAnchor="end"
            >
              {v}
            </text>
          </g>
        );
      })}

      {/* bars */}
      {buckets.map((b, i) => {
        const x = padding.left + i * barW + gap / 2;
        const w = Math.max(1, barW - gap);
        let yCursor = padding.top + innerH;
        return (
          <g key={b.bucket_start}>
            {SEVERITY_ORDER.map((sev) => {
              const c = b.counts[sev] ?? 0;
              if (c <= 0) return null;
              const segH = (c / maxTotal) * innerH;
              yCursor -= segH;
              return (
                <rect
                  key={sev}
                  x={x}
                  y={yCursor}
                  width={w}
                  height={segH}
                  fill={SEVERITY_COLOR[sev] ?? "var(--text-muted)"}
                  opacity={0.85}
                >
                  <title>
                    {`${formatBucketLabel(b.bucket_start, bucketMinutes)} — ${sev}: ${c}`}
                  </title>
                </rect>
              );
            })}
          </g>
        );
      })}

      {/* x-axis labels — sparse */}
      {buckets.map((b, i) => {
        const labelEvery = Math.max(1, Math.ceil(buckets.length / 8));
        if (i % labelEvery !== 0) return null;
        const x = padding.left + i * barW + barW / 2;
        return (
          <text
            key={`xl-${b.bucket_start}`}
            x={x}
            y={height - 8}
            fontSize={10}
            fill="var(--text-muted)"
            textAnchor="middle"
          >
            {formatBucketLabel(b.bucket_start, bucketMinutes)}
          </text>
        );
      })}
    </svg>
  );
}

export default function HealthHistoryPage() {
  const [snapshot, setSnapshot] = useState<HealthHistorySnapshot | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);

  const [hours, setHours] = useState<number>(24);
  const [bucketMinutes, setBucketMinutes] = useState<number>(60);
  const [source, setSource] = useState<string>("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await getHealthHistory({
        hours,
        bucketMinutes,
        source: source.trim() || undefined,
      });
      setSnapshot(resp);
      setLastRefreshed(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, [hours, bucketMinutes, source]);

  useEffect(() => {
    void load();
    // Initial load only; subsequent loads are user-driven via Refresh.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const buckets = snapshot?.timeseries ?? [];
  const totals = snapshot?.totals;
  const lastPerSource = snapshot?.last_per_source ?? {};
  const sourceRows = Object.entries(lastPerSource).sort((a, b) =>
    a[0].localeCompare(b[0]),
  );

  return (
    <main className={styles.page}>
      <div className={styles.container}>
        <header className={styles.header}>
          <div>
            <h1 className={styles.title}>Health History</h1>
            <p className={styles.subtitle}>
              Time-bucketed incident counts from the append-only incident log.
              Operator-facing only — never feeds risk gates, the broker, or
              the worker.
            </p>
          </div>
          <div>
            {lastRefreshed && (
              <span className={styles.refreshTimestamp}>
                Updated {lastRefreshed.toLocaleTimeString()}
              </span>
            )}
          </div>
        </header>

        <div className={styles.filters}>
          <span className={styles.filterLabel}>Window</span>
          <select
            className={styles.filterSelect}
            value={hours}
            onChange={(e) => setHours(Number(e.target.value) || 24)}
          >
            {HOURS_OPTIONS.map((h) => (
              <option key={h} value={h}>
                {h < 24 ? `${h}h` : `${h / 24}d`}
              </option>
            ))}
          </select>

          <span className={styles.filterLabel}>Bucket</span>
          <select
            className={styles.filterSelect}
            value={bucketMinutes}
            onChange={(e) => setBucketMinutes(Number(e.target.value) || 60)}
          >
            {BUCKET_OPTIONS.map((m) => (
              <option key={m} value={m}>
                {m < 60 ? `${m}m` : `${m / 60}h`}
              </option>
            ))}
          </select>

          <span className={styles.filterLabel}>Source</span>
          <input
            className={styles.filterInput}
            type="text"
            placeholder="any"
            value={source}
            onChange={(e) => setSource(e.target.value)}
          />

          <button
            type="button"
            className={styles.refreshButton}
            onClick={() => void load()}
            disabled={loading}
          >
            {loading ? "Loading…" : "Refresh"}
          </button>
        </div>

        {error && <div className={styles.errorBanner}>Failed to load: {error}</div>}

        {snapshot && <div className={styles.advisory}>{snapshot.advisory}</div>}

        {totals && (
          <div className={styles.summaryGrid}>
            <div className={styles.summaryCard}>
              <span className={styles.summaryLabel}>Total incidents</span>
              <span className={styles.summaryValue}>{totals.incidents}</span>
            </div>
            {SEVERITY_ORDER.map((sev) => (
              <div key={sev} className={styles.summaryCard}>
                <span className={styles.summaryLabel}>{sev}</span>
                <span
                  className={styles.summaryValue}
                  style={{ color: SEVERITY_COLOR[sev] }}
                >
                  {totals.by_severity[sev] ?? 0}
                </span>
              </div>
            ))}
          </div>
        )}

        <section className={styles.chartCard}>
          <h2 className={styles.chartTitle}>
            Incidents per {bucketMinutes < 60 ? `${bucketMinutes} min` : `${bucketMinutes / 60} h`} bucket
          </h2>
          <div className={styles.chartLegend}>
            {SEVERITY_ORDER.map((sev) => (
              <span key={sev} className={styles.legendItem}>
                <span
                  className={styles.legendSwatch}
                  style={{ background: SEVERITY_COLOR[sev] }}
                />
                {sev}
              </span>
            ))}
          </div>
          {loading && buckets.length === 0 ? (
            <div className={styles.loading}>Loading health history…</div>
          ) : (
            <StackedBars buckets={buckets} bucketMinutes={bucketMinutes} />
          )}
        </section>

        <section className={styles.tableCard}>
          <h2 className={styles.chartTitle}>Last incident per source</h2>
          {sourceRows.length === 0 ? (
            <div className={styles.empty}>No incidents in the selected window.</div>
          ) : (
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Source</th>
                  <th>Severity</th>
                  <th>Code</th>
                  <th>Title</th>
                  <th>When</th>
                  <th>Total in window</th>
                </tr>
              </thead>
              <tbody>
                {sourceRows.map(([src, last]) => (
                  <tr key={src}>
                    <td>{src}</td>
                    <td style={{ color: SEVERITY_COLOR[last.severity] ?? undefined }}>
                      {last.severity}
                    </td>
                    <td>
                      <code>{last.code}</code>
                    </td>
                    <td>{last.title}</td>
                    <td>{formatTimestamp(last.created_at)}</td>
                    <td>{totals?.by_source?.[src] ?? 0}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>

        <div className={styles.driftLockNotice}>
          Drift lock active: this view is read-only over the append-only
          incident log. Auto-paper, auto trading, and live trading remain OFF.
        </div>
      </div>
    </main>
  );
}
