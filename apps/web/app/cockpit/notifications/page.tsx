"use client";

// MH-COCKPIT-06-B — Cockpit notifications-digest page (read-only).
// Renders a compact "needs attention" digest from
// /cockpit/notifications/digest. Distinct from the existing /notifications
// page — this page is a focused operator overview.

import { useCallback, useEffect, useState } from "react";

import {
  getNotificationsDigest,
  type DigestSeverity,
  type NotificationsDigestRow,
  type NotificationsDigestSnapshot,
} from "../../../lib/api/cockpitNotifications";
import styles from "../../../styles/pages/cockpit-notifications.module.css";

const SEVERITY_ORDER: ReadonlyArray<DigestSeverity> = [
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

const HOURS_OPTIONS = [1, 4, 12, 24, 48, 72, 168];
const SEVERITY_OPTIONS: ReadonlyArray<{ value: DigestSeverity; label: string }> = [
  { value: "info", label: "info+" },
  { value: "warn", label: "warn+" },
  { value: "error", label: "error+" },
  { value: "critical", label: "critical only" },
];

function formatTimestamp(value: string | null): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString();
}

function formatRelative(value: string | null): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  const sec = Math.max(0, Math.round((Date.now() - d.getTime()) / 1000));
  if (sec < 60) return `${sec}s ago`;
  if (sec < 3600) return `${Math.round(sec / 60)}m ago`;
  if (sec < 86400) return `${Math.round(sec / 3600)}h ago`;
  return `${Math.round(sec / 86400)}d ago`;
}

function AttentionRow({ row }: { row: NotificationsDigestRow }) {
  const color = SEVERITY_COLOR[row.severity] ?? "var(--text-muted)";
  return (
    <div className={styles.attentionRow}>
      <span className={styles.sevBadge} style={{ color }}>
        {row.severity}
      </span>
      <div className={styles.rowMain}>
        <div className={styles.rowTitle} title={row.title}>
          {row.title}
        </div>
        <div className={styles.rowMeta}>
          <code>{row.code}</code> · {row.source}
        </div>
      </div>
      <div className={styles.rowTime} title={formatTimestamp(row.created_at)}>
        {formatRelative(row.created_at)}
      </div>
    </div>
  );
}

export default function CockpitNotificationsPage() {
  const [snapshot, setSnapshot] = useState<NotificationsDigestSnapshot | null>(
    null,
  );
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);

  const [hours, setHours] = useState<number>(24);
  const [minSeverity, setMinSeverity] = useState<DigestSeverity>("warn");
  const [limit, setLimit] = useState<number>(20);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await getNotificationsDigest({
        hours,
        minSeverity,
        limit,
      });
      setSnapshot(resp);
      setLastRefreshed(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, [hours, minSeverity, limit]);

  useEffect(() => {
    void load();
    // Initial load only; subsequent loads are user-driven via Refresh.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const totals = snapshot?.totals;
  const rows = snapshot?.attention ?? [];
  const highest = snapshot?.highest_severity ?? "none";
  const highestColor = SEVERITY_COLOR[highest] ?? "var(--text-muted)";

  return (
    <main className={styles.page}>
      <div className={styles.container}>
        <header className={styles.header}>
          <div>
            <h1 className={styles.title}>Cockpit Notifications</h1>
            <p className={styles.subtitle}>
              Compact operator digest of recent incidents that need attention.
              Read-only view over the append-only incident log — never feeds
              the trading path.
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

          <span className={styles.filterLabel}>Severity</span>
          <select
            className={styles.filterSelect}
            value={minSeverity}
            onChange={(e) => setMinSeverity(e.target.value as DigestSeverity)}
          >
            {SEVERITY_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>

          <span className={styles.filterLabel}>Limit</span>
          <select
            className={styles.filterSelect}
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value) || 20)}
          >
            {[5, 10, 20, 50].map((n) => (
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

        {snapshot && <div className={styles.advisory}>{snapshot.advisory}</div>}

        {totals && (
          <div className={styles.summaryGrid}>
            <div className={styles.summaryCard}>
              <span className={styles.summaryLabel}>Total in window</span>
              <span className={styles.summaryValue}>{totals.incidents}</span>
            </div>
            <div className={styles.summaryCard}>
              <span className={styles.summaryLabel}>Highest severity</span>
              <span className={styles.summaryValue} style={{ color: highestColor }}>
                {highest}
              </span>
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

        <h2 className={styles.sectionTitle}>
          Needs attention ({snapshot?.attention_count ?? 0})
        </h2>

        {loading && rows.length === 0 ? (
          <div className={styles.loading}>Loading digest…</div>
        ) : rows.length === 0 ? (
          <div className={styles.empty}>
            Nothing needs attention in this window. ✓
          </div>
        ) : (
          <div className={styles.attentionList}>
            {rows.map((r) => (
              <AttentionRow key={r.id} row={r} />
            ))}
          </div>
        )}

        <div className={styles.driftLockNotice}>
          Drift lock active: this view is read-only over the append-only
          incident log. Auto-paper, auto trading, and live trading remain OFF.
        </div>
      </div>
    </main>
  );
}
