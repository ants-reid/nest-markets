"use client";

// MH-158-B — Worker run log overview page (read-only).
// Renders retention status + recent auto-paper run entries from
// /monitor/worker-run-log/overview. No control actions; no toggles.
// Drift lock: this view never feeds the trading path.

import { useCallback, useEffect, useState } from "react";

import {
  getWorkerRunLogOverview,
  type WorkerRunEntry,
  type WorkerRunLogOverview,
} from "../../../lib/api/workerRunLog";
import styles from "../../../styles/pages/worker-run-log.module.css";

const LIMIT_OPTIONS = [10, 20, 50, 100, 200];

const STATUS_COLOR: Record<string, string> = {
  ok: "var(--state-success)",
  success: "var(--state-success)",
  partial: "var(--state-warning)",
  warn: "var(--state-warning)",
  error: "var(--state-danger)",
  failed: "var(--state-danger)",
};

function formatTimestamp(value: string | null | undefined): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString();
}

function formatNumber(n: number | null | undefined, digits = 2): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return n.toLocaleString(undefined, {
    minimumFractionDigits: 0,
    maximumFractionDigits: digits,
  });
}

function gaugeColor(pct: number, nearCapacity: boolean): string {
  if (nearCapacity || pct >= 80) return "var(--state-danger)";
  if (pct >= 60) return "var(--state-warning)";
  return "var(--state-success)";
}

export default function WorkerRunLogPage() {
  const [overview, setOverview] = useState<WorkerRunLogOverview | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);
  const [limit, setLimit] = useState<number>(20);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await getWorkerRunLogOverview(limit);
      setOverview(resp);
      setLastRefreshed(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, [limit]);

  useEffect(() => {
    void load();
    // Initial load only; subsequent loads are user-driven via Refresh.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const retention = overview?.retention;
  const totals = overview?.totals;
  const entries: WorkerRunEntry[] = overview?.entries ?? [];

  const fillPct = retention ? Math.min(100, retention.utilization_pct) : 0;
  const fillColor = retention
    ? gaugeColor(retention.utilization_pct, retention.near_capacity)
    : "var(--text-muted)";

  return (
    <main className={styles.page}>
      <div className={styles.container}>
        <header className={styles.header}>
          <div>
            <h1 className={styles.title}>Worker Run Log</h1>
            <p className={styles.subtitle}>
              Read-only overview of the file-backed auto-paper worker run log,
              including retention status and the most-recent entries.
              Operator-facing only — never feeds the trading path.
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
          <span className={styles.filterLabel}>Recent entries</span>
          <select
            className={styles.filterSelect}
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value) || 20)}
          >
            {LIMIT_OPTIONS.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
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

        {overview && <div className={styles.advisory}>{overview.advisory}</div>}

        {retention?.retention_warning && (
          <div className={styles.warningBanner}>{retention.retention_warning}</div>
        )}

        {retention && (
          <section className={styles.gaugeCard}>
            <h2 className={styles.sectionTitle}>Retention</h2>
            <div className={styles.gaugeLabel}>
              <span>
                {retention.current_entry_count} / {retention.max_entries} entries
              </span>
              <span className={styles.gaugeValue}>
                {retention.utilization_pct.toFixed(1)}%
              </span>
            </div>
            <div className={styles.gaugeTrack}>
              <div
                className={styles.gaugeFill}
                style={{ width: `${fillPct}%`, background: fillColor }}
              />
            </div>
            <div className={styles.metaGrid}>
              <div className={styles.metaItem}>
                <span className={styles.metaLabel}>Status</span>
                <span className={styles.metaValue}>{retention.retention_status}</span>
              </div>
              <div className={styles.metaItem}>
                <span className={styles.metaLabel}>Storage backend</span>
                <span className={styles.metaValue}>{retention.storage_backend}</span>
              </div>
              <div className={styles.metaItem}>
                <span className={styles.metaLabel}>Trim on append</span>
                <span className={styles.metaValue}>
                  {retention.trim_on_append ? "yes" : "no"}
                </span>
              </div>
              <div className={styles.metaItem}>
                <span className={styles.metaLabel}>Entries remaining</span>
                <span className={styles.metaValue}>
                  {retention.entries_remaining}
                </span>
              </div>
              <div className={styles.metaItem}>
                <span className={styles.metaLabel}>Span (h)</span>
                <span className={styles.metaValue}>
                  {formatNumber(retention.retained_span_hours)}
                </span>
              </div>
              <div className={styles.metaItem}>
                <span className={styles.metaLabel}>Avg / day</span>
                <span className={styles.metaValue}>
                  {formatNumber(retention.average_entries_per_day)}
                </span>
              </div>
              <div className={styles.metaItem}>
                <span className={styles.metaLabel}>Days to capacity</span>
                <span className={styles.metaValue}>
                  {formatNumber(retention.estimated_days_until_capacity)}
                </span>
              </div>
              <div className={styles.metaItem}>
                <span className={styles.metaLabel}>Trend</span>
                <span className={styles.metaValue}>
                  {retention.retention_trend_status}
                </span>
              </div>
              <div className={styles.metaItem}>
                <span className={styles.metaLabel}>Oldest entry</span>
                <span className={styles.metaValue}>
                  {formatTimestamp(retention.oldest_started_at)}
                </span>
              </div>
              <div className={styles.metaItem}>
                <span className={styles.metaLabel}>Latest entry</span>
                <span className={styles.metaValue}>
                  {formatTimestamp(retention.latest_started_at)}
                </span>
              </div>
            </div>
          </section>
        )}

        {totals && (
          <div className={styles.summaryGrid}>
            <div className={styles.summaryCard}>
              <span className={styles.summaryHeading}>Returned</span>
              <span className={styles.summaryValue}>{totals.returned}</span>
            </div>
            {Object.entries(totals.by_status).map(([status, count]) => (
              <div key={`s-${status}`} className={styles.summaryCard}>
                <span className={styles.summaryHeading}>status: {status}</span>
                <span
                  className={styles.summaryValue}
                  style={{ color: STATUS_COLOR[status] ?? undefined }}
                >
                  {count}
                </span>
              </div>
            ))}
            {Object.entries(totals.by_source).map(([src, count]) => (
              <div key={`src-${src}`} className={styles.summaryCard}>
                <span className={styles.summaryHeading}>source: {src}</span>
                <span className={styles.summaryValue}>{count}</span>
              </div>
            ))}
          </div>
        )}

        <section className={styles.tableCard}>
          <h2 className={styles.sectionTitle}>Recent runs</h2>
          {loading && entries.length === 0 ? (
            <div className={styles.loading}>Loading run log…</div>
          ) : entries.length === 0 ? (
            <div className={styles.empty}>No worker runs recorded yet.</div>
          ) : (
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Started</th>
                  <th>Worker</th>
                  <th>Status</th>
                  <th>Source</th>
                  <th>Outcomes</th>
                  <th>Message</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((e, idx) => {
                  const color = STATUS_COLOR[e.status?.toLowerCase()] ?? "var(--text-muted)";
                  return (
                    <tr key={`${e.started_at}-${idx}`}>
                      <td>{formatTimestamp(e.started_at)}</td>
                      <td className={styles.code}>{e.worker_name}</td>
                      <td>
                        <span className={styles.statusBadge} style={{ color }}>
                          {e.status}
                        </span>
                      </td>
                      <td>{e.source}</td>
                      <td className={styles.code}>
                        {e.outcome_counts
                          ? Object.entries(e.outcome_counts)
                              .filter(([, v]) => v > 0)
                              .map(([k, v]) => `${k}=${v}`)
                              .join(", ") || "—"
                          : "—"}
                      </td>
                      <td className={styles.code}>{e.message}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </section>

        <div className={styles.driftLockNotice}>
          Drift lock active: this view is read-only. Auto-paper, auto trading,
          and live trading remain OFF. The worker run log is operator-facing
          only; nothing on this page can submit orders or change a gate.
        </div>
      </div>
    </main>
  );
}
