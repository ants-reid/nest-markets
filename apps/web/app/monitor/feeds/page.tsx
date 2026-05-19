"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  getFeedMonitor,
  type FeedMonitorCategory,
  type FeedMonitorResponse,
  type FeedMonitorRow,
  type FeedMonitorStatus,
} from "../../../lib/api/feedMonitor";
import styles from "../../../styles/pages/feed-monitor.module.css";

const STATUS_BADGE_CLASS: Record<FeedMonitorStatus, string> = {
  ok: styles.statusOk,
  degraded: styles.statusDegraded,
  down: styles.statusDown,
  unknown: styles.statusUnknown,
  error: styles.statusError,
};

const CATEGORY_LABEL: Record<FeedMonitorCategory | "all", string> = {
  all: "All categories",
  feeds_in: "Feeds in",
  feeds_out: "Feeds out",
  runtime: "Runtime",
};

const STATUS_LABEL: Record<FeedMonitorStatus | "all", string> = {
  all: "All statuses",
  ok: "OK",
  degraded: "Degraded",
  down: "Down",
  unknown: "Unknown",
  error: "Error",
};

function StatusBadge({ status }: { status: FeedMonitorStatus }) {
  const cls = STATUS_BADGE_CLASS[status] ?? styles.statusUnknown;
  return <span className={`${styles.statusBadge} ${cls}`}>{status}</span>;
}

function formatTimestamp(value: string | null | undefined): string {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString();
}

function formatLatency(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `${value.toFixed(1)} ms`;
}

function formatFlag(value: boolean | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return value ? "yes" : "no";
}

export default function FeedMonitorPage() {
  const [data, setData] = useState<FeedMonitorResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);
  const [search, setSearch] = useState<string>("");
  const [category, setCategory] = useState<FeedMonitorCategory | "all">("all");
  const [status, setStatus] = useState<FeedMonitorStatus | "all">("all");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getFeedMonitor();
      setData(response);
      setLastRefreshed(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const filteredRows = useMemo(() => {
    const rows = data?.rows ?? [];
    const query = search.trim().toLowerCase();
    return rows.filter((row) => {
      if (category !== "all" && row.category !== category) return false;
      if (status !== "all" && row.status !== status) return false;
      if (!query) return true;
      return [row.name, row.detail ?? "", row.action ?? "", row.target ?? ""]
        .join(" ")
        .toLowerCase()
        .includes(query);
    });
  }, [category, data?.rows, search, status]);

  const problemRows = useMemo(
    () => filteredRows.filter((row) => row.status !== "ok"),
    [filteredRows],
  );

  const summary = data?.summary;

  return (
    <main className={styles.page}>
      <div className={styles.container}>
        <header className={styles.header}>
          <div>
            <h1 className={styles.title}>Feed Monitor</h1>
            <p className={styles.subtitle}>
              Read-only posture for inbound data feeds, outbound API dependencies,
              and broker gateway runtime reachability. This page never changes
              provider state, trading controls, or broker mode.
            </p>
          </div>
          <div className={styles.headerRight}>
            {lastRefreshed && (
              <span className={styles.refreshTimestamp}>
                Updated {lastRefreshed.toLocaleTimeString()}
              </span>
            )}
            <button
              type="button"
              className={styles.refreshButton}
              onClick={() => void load()}
              disabled={loading}
            >
              {loading ? "Refreshing…" : "Refresh"}
            </button>
          </div>
        </header>

        {error && <div className={styles.errorBanner}>Failed to load: {error}</div>}

        {data && <div className={styles.advisory}>{data.advisory}</div>}

        {summary && (
          <div className={styles.summaryGrid}>
            <div className={styles.summaryCard}>
              <span className={styles.summaryLabel}>Overall</span>
              <div className={styles.summaryStatusRow}>
                <StatusBadge status={data?.overall ?? "unknown"} />
              </div>
            </div>
            <div className={styles.summaryCard}>
              <span className={styles.summaryLabel}>Rows</span>
              <span className={styles.summaryValue}>{summary.total}</span>
            </div>
            <div className={styles.summaryCard}>
              <span className={styles.summaryLabel}>Configured</span>
              <span className={styles.summaryValue}>{summary.configured}</span>
            </div>
            <div className={styles.summaryCard}>
              <span className={styles.summaryLabel}>Runtime reachable</span>
              <span className={styles.summaryValue}>{summary.runtime_reachable}</span>
            </div>
            <div className={styles.summaryCard}>
              <span className={styles.summaryLabel}>Issues</span>
              <span className={styles.summaryValue}>{summary.issue_count}</span>
            </div>
          </div>
        )}

        <section className={styles.filters} aria-label="Feed monitor filters">
          <label className={styles.filterField}>
            <span className={styles.filterLabel}>Search</span>
            <input
              className={styles.filterInput}
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="feed name, detail, action"
            />
          </label>

          <label className={styles.filterField}>
            <span className={styles.filterLabel}>Category</span>
            <select
              className={styles.filterSelect}
              value={category}
              onChange={(event) => setCategory(event.target.value as FeedMonitorCategory | "all")}
            >
              {Object.entries(CATEGORY_LABEL).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>

          <label className={styles.filterField}>
            <span className={styles.filterLabel}>Status</span>
            <select
              className={styles.filterSelect}
              value={status}
              onChange={(event) => setStatus(event.target.value as FeedMonitorStatus | "all")}
            >
              {Object.entries(STATUS_LABEL).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
        </section>

        {data && data.next_actions.length > 0 && (
          <section className={styles.actionsCard}>
            <h2 className={styles.sectionTitle}>Operator actions</h2>
            <ul className={styles.actionList}>
              {data.next_actions.map((action) => (
                <li key={action}>{action}</li>
              ))}
            </ul>
          </section>
        )}

        <section className={styles.tableCard}>
          <div className={styles.tableHeader}>
            <div>
              <h2 className={styles.sectionTitle}>Feed rows</h2>
              <p className={styles.sectionSubtext}>
                {filteredRows.length} shown, {problemRows.length} currently non-OK.
              </p>
            </div>
            {data && (
              <span className={styles.sectionSubtext}>
                Snapshot {formatTimestamp(data.as_of_utc)}
              </span>
            )}
          </div>

          {loading && !data ? (
            <div className={styles.loading}>Loading feed posture…</div>
          ) : filteredRows.length === 0 ? (
            <div className={styles.empty}>No feed rows match the current filters.</div>
          ) : (
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Feed</th>
                  <th>Category</th>
                  <th>Status</th>
                  <th>Configured</th>
                  <th>Runtime</th>
                  <th>Checked</th>
                  <th>Latency</th>
                  <th>Detail</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredRows.map((row: FeedMonitorRow) => (
                  <tr key={row.id}>
                    <td>
                      <div className={styles.feedCell}>
                        <span className={styles.feedName}>{row.name}</span>
                        {row.target && <span className={styles.feedTarget}>{row.target}</span>}
                      </div>
                    </td>
                    <td>{CATEGORY_LABEL[row.category]}</td>
                    <td>
                      <StatusBadge status={row.status} />
                    </td>
                    <td>{formatFlag(row.configured)}</td>
                    <td>{formatFlag(row.runtime_reachable)}</td>
                    <td>{formatTimestamp(row.checked_at)}</td>
                    <td>{formatLatency(row.latency_ms)}</td>
                    <td className={styles.detailCell}>{row.detail ?? "—"}</td>
                    <td className={styles.actionCell}>{row.action ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>

        <div className={styles.driftLockNotice}>
          Drift lock active: this monitor is read-only over backend probe and
          health surfaces. Auto-paper enforcement, auto trading, and live trading
          remain OFF.
        </div>
      </div>
    </main>
  );
}
