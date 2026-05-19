"use client";

// MH-COCKPIT-01-B — Markets-open snapshot surface.
// Read-only operator hint. Does not influence trading decisions.

import { useCallback, useEffect, useState } from "react";

import {
  getMarketsSnapshot,
  type MarketSnapshotResponse,
} from "../../lib/api/markets";
import styles from "../../styles/pages/markets-open.module.css";

const WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function formatLocal(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString();
}

function formatWeekdays(days: number[]): string {
  return days.map((d) => WEEKDAY_NAMES[d] ?? String(d)).join(", ");
}

export default function MarketsOpenPage() {
  const [snapshot, setSnapshot] = useState<MarketSnapshotResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await getMarketsSnapshot();
      setSnapshot(resp);
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

  return (
    <main className={styles.page}>
      <div className={styles.container}>
        <header className={styles.header}>
          <div>
            <h1 className={styles.title}>Markets Open</h1>
            <p className={styles.subtitle}>
              Coarse open/closed snapshot for the major sessions Market Hunter
              tracks. Operator hint only — this surface is never consulted by
              the broker, the auto-paper worker, or any risk gate.
            </p>
          </div>
          <div className={styles.refreshRow}>
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
              {loading ? "Loading…" : "Refresh"}
            </button>
          </div>
        </header>

        {error && <div className={styles.errorBanner}>Failed to load: {error}</div>}

        {snapshot && (
          <div className={styles.advisory}>{snapshot.advisory}</div>
        )}

        {loading && !snapshot ? (
          <div className={styles.loading}>Loading market snapshot…</div>
        ) : snapshot ? (
          <div className={styles.grid}>
            {snapshot.markets.map((market) => (
              <article key={market.code} className={styles.card}>
                <div className={styles.cardHeader}>
                  <h2 className={styles.cardTitle}>{market.label}</h2>
                  <span
                    className={`${styles.statusBadge} ${
                      market.is_open ? styles.statusOpen : styles.statusClosed
                    }`}
                  >
                    {market.is_open ? "Open" : "Closed"}
                  </span>
                </div>
                <div className={styles.metaRow}>
                  <span className={styles.metaLabel}>Code</span>
                  <span className={styles.metaValue}>{market.code}</span>
                  <span className={styles.metaLabel}>Timezone</span>
                  <span className={styles.metaValue}>{market.timezone}</span>
                  <span className={styles.metaLabel}>Local time</span>
                  <span className={styles.metaValue}>{formatLocal(market.local_time)}</span>
                  <span className={styles.metaLabel}>Session</span>
                  <span className={styles.metaValue}>
                    {market.open_time} – {market.close_time}
                  </span>
                  <span className={styles.metaLabel}>Days</span>
                  <span className={styles.metaValue}>
                    {formatWeekdays(market.open_weekdays)}
                  </span>
                </div>
                <p className={styles.notes}>{market.notes}</p>
              </article>
            ))}
          </div>
        ) : null}

        <div className={styles.driftLockNotice}>
          Drift lock active: this view is read-only. Market open/closed state is
          a coarse operator hint and is never read by trading code, the
          auto-paper worker, or any risk gate. Auto-paper, auto trading, and
          live trading remain OFF.
        </div>
      </div>
    </main>
  );
}
