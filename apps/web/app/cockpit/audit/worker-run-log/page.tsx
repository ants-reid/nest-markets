"use client";

// MH-MON-AUDIT-RECENT-WORKER-RUN-A — Read-only cockpit tile for worker
// run log overview.
//
// Renders /monitor/worker-run-log/overview (MH-158-A). The endpoint
// returns retention metadata + recent auto-paper worker runs. This page
// surfaces both as an operator-observability view.
//
// Drift-lock guarantee: pure read-only frontend. Does not call any
// trading, broker, worker, or risk-mutation endpoint.

import { useCallback, useEffect, useState } from "react";

import {
  getWorkerRunLogOverview,
  type WorkerRunLogOverview,
  type WorkerRunEntry,
} from "../../../../lib/api/workerRunLog";
import styles from "../../../../styles/pages/cockpit-audit-worker-run-log.module.css";

const LIMIT_OPTIONS = [20, 50, 100, 200];

function formatTimestamp(value: string | null): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString();
}

function statusClass(status: string): string {
  if (status === "success" || status === "ok") return styles.badgeOk;
  if (status === "failure" || status === "error") return styles.badgeError;
  return styles.badgeNeutral;
}

function Row({ row }: { row: WorkerRunEntry }) {
  const counts = row.outcome_counts
    ? Object.entries(row.outcome_counts)
        .map(([k, v]) => `${k}=${v}`)
        .join(", ")
    : "—";
  return (
    <tr className={styles.row}>
      <td className={styles.cellTime}>{formatTimestamp(row.started_at)}</td>
      <td className={styles.cellMono}>{row.worker_name}</td>
      <td>
        <span className={statusClass(row.status)}>{row.status}</span>
      </td>
      <td className={styles.cellMono}>{row.source}</td>
      <td className={styles.cellMessage} title={row.message}>
        {row.message || "—"}
      </td>
      <td className={styles.cellMono}>{counts}</td>
    </tr>
  );
}

export default function WorkerRunLogAuditPage() {
  const [snapshot, setSnapshot] = useState<WorkerRunLogOverview | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);
  const [limit, setLimit] = useState<number>(20);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await getWorkerRunLogOverview(limit);
      setSnapshot(resp);
      setLastRefreshed(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, [limit]);

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const entries = snapshot?.entries ?? [];
  const retention = snapshot?.retention ?? null;
  const totals = snapshot?.totals ?? null;
  const advisory = snapshot?.advisory ?? null;

  return (
    <main className={styles.page}>
      <div className={styles.container}>
        <header className={styles.header}>
          <div>
            <h1 className={styles.title}>Worker Run Log Audit</h1>
            <p className={styles.subtitle}>
              Read-only audit view of recent auto-paper worker runs and
              retention status (MH-158-A). This page never modifies the
              run log or any trading control.
            </p>
          </div>
          <div className={styles.headerActions}>
            <button
              type="button"
              className={styles.refreshButton}
              onClick={() => {
                void load();
              }}
              disabled={loading}
            >
              {loading ? "Refreshing…" : "Refresh"}
            </button>
            {lastRefreshed && (
              <span className={styles.refreshTimestamp}>
                refreshed {lastRefreshed.toLocaleTimeString()}
              </span>
            )}
          </div>
        </header>

        <section className={styles.filters}>
          <label className={styles.filterLabel} htmlFor="limit">
            Limit
          </label>
          <select
            id="limit"
            className={styles.filterSelect}
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
          >
            {LIMIT_OPTIONS.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </section>

        {advisory && <div className={styles.advisory}>{advisory}</div>}

        {retention && (
          <section className={styles.retention}>
            <div className={styles.retentionRow}>
              <span className={styles.retentionLabel}>Backend</span>
              <span className={styles.retentionValue}>
                {retention.storage_backend}
              </span>
            </div>
            <div className={styles.retentionRow}>
              <span className={styles.retentionLabel}>Entries</span>
              <span className={styles.retentionValue}>
                {retention.current_entry_count} / {retention.max_entries}
                {" ("}
                {retention.utilization_pct.toFixed(1)}% used)
              </span>
            </div>
            <div className={styles.retentionRow}>
              <span className={styles.retentionLabel}>Status</span>
              <span
                className={
                  retention.near_capacity
                    ? styles.retentionWarn
                    : styles.retentionOk
                }
              >
                {retention.retention_status}
                {retention.retention_warning
                  ? ` — ${retention.retention_warning}`
                  : ""}
              </span>
            </div>
            {retention.retained_span_hours !== null && (
              <div className={styles.retentionRow}>
                <span className={styles.retentionLabel}>Span</span>
                <span className={styles.retentionValue}>
                  {retention.retained_span_hours.toFixed(1)}h retained
                  {retention.estimated_days_until_capacity !== null
                    ? ` · ~${retention.estimated_days_until_capacity.toFixed(
                        1,
                      )}d to capacity`
                    : ""}
                </span>
              </div>
            )}
          </section>
        )}

        {totals && (
          <section className={styles.totals}>
            <span className={styles.totalsLabel}>
              Returned: {totals.returned}
            </span>
            <span className={styles.totalsLabel}>
              By status:{" "}
              {Object.entries(totals.by_status)
                .map(([k, v]) => `${k}=${v}`)
                .join(", ") || "—"}
            </span>
            <span className={styles.totalsLabel}>
              By source:{" "}
              {Object.entries(totals.by_source)
                .map(([k, v]) => `${k}=${v}`)
                .join(", ") || "—"}
            </span>
          </section>
        )}

        <div className={styles.driftLockNotice}>
          Drift lock: this page is strictly read-only. No request from
          this page modifies the worker run log, the worker, or any
          trading state.
        </div>

        {error && <div className={styles.errorBanner}>{error}</div>}

        {!error && entries.length === 0 && !loading ? (
          <div className={styles.empty}>
            No worker run entries match the current window.
          </div>
        ) : (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Started</th>
                  <th>Worker</th>
                  <th>Status</th>
                  <th>Source</th>
                  <th>Message</th>
                  <th>Outcomes</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((row, i) => (
                  <Row key={`${row.worker_name}-${row.started_at}-${i}`} row={row} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </main>
  );
}
