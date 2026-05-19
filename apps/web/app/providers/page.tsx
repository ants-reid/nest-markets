"use client";

// MH-MON-07 — Provider Configuration view (read-only).
// Consumes GET /health/providers. No mutation surfaces, no toggles.

import { useCallback, useEffect, useState } from "react";

import {
  getProviderInventory,
  type ProviderCategory,
  type ProviderInventoryResponse,
  type ProviderInventoryRow,
} from "../../lib/api/providers";
import styles from "../../styles/pages/providers.module.css";

const STATUS_BADGE_CLASS: Record<string, string> = {
  ok: styles.statusOk,
  degraded: styles.statusDegraded,
  down: styles.statusDown,
  unknown: styles.statusUnknown,
  error: styles.statusError,
};

const CATEGORY_ORDER: ProviderCategory[] = ["feeds_in", "feeds_out", "infrastructure"];

const CATEGORY_LABEL: Record<ProviderCategory, string> = {
  feeds_in: "Feeds In",
  feeds_out: "Feeds Out",
  infrastructure: "Infrastructure",
};

function StatusBadge({ status }: { status: string }) {
  const cls = STATUS_BADGE_CLASS[status] ?? styles.statusUnknown;
  return <span className={`${styles.statusBadge} ${cls}`}>{status}</span>;
}

function formatTimestamp(value: string | null | undefined): string {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString();
}

function formatLatency(ms: number | null | undefined): string {
  if (ms === null || ms === undefined) return "—";
  return `${ms.toFixed(1)} ms`;
}

function groupByCategory(
  rows: ProviderInventoryRow[]
): Record<ProviderCategory, ProviderInventoryRow[]> {
  const grouped: Record<ProviderCategory, ProviderInventoryRow[]> = {
    feeds_in: [],
    feeds_out: [],
    infrastructure: [],
  };
  for (const row of rows) {
    grouped[row.category].push(row);
  }
  return grouped;
}

export default function ProvidersPage() {
  const [data, setData] = useState<ProviderInventoryResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await getProviderInventory();
      setData(resp);
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

  const grouped = data ? groupByCategory(data.providers) : null;

  return (
    <main className={styles.page}>
      <div className={styles.container}>
        <header className={styles.header}>
          <div>
            <h1 className={styles.title}>Provider Configuration</h1>
            <p className={styles.subtitle}>
              Read-only inventory of every registered service probe. Configuration
              is reported by presence of the corresponding env variable; secrets
              are never echoed in the response payload.
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

        {data && (
          <div className={styles.totalsRow}>
            <div className={styles.totalCard}>
              <div className={styles.totalLabel}>Total providers</div>
              <div className={styles.totalValue}>{data.totals.count}</div>
            </div>
            {CATEGORY_ORDER.map((cat) => {
              const total = data.totals.by_category[cat] ?? 0;
              const configured = data.totals.configured_by_category[cat] ?? 0;
              return (
                <div key={cat} className={styles.totalCard}>
                  <div className={styles.totalLabel}>{CATEGORY_LABEL[cat]}</div>
                  <div className={styles.totalValue}>
                    {configured} / {total} configured
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {loading && !data ? (
          <div className={styles.loading}>Loading providers…</div>
        ) : (
          grouped &&
          CATEGORY_ORDER.map((cat) => {
            const rows = grouped[cat];
            if (rows.length === 0) return null;
            return (
              <section
                key={cat}
                className={styles.section}
                aria-labelledby={`cat-${cat}-title`}
              >
                <h2 id={`cat-${cat}-title`} className={styles.sectionTitle}>
                  {CATEGORY_LABEL[cat]}
                </h2>
                <table className={styles.providerTable}>
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Status</th>
                      <th>Configured</th>
                      <th>Latency</th>
                      <th>Checked</th>
                      <th>Detail</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row) => (
                      <tr key={row.name}>
                        <td>{row.name}</td>
                        <td>
                          <StatusBadge status={row.status} />
                        </td>
                        <td>
                          <span
                            className={
                              row.configured ? styles.configuredYes : styles.configuredNo
                            }
                          >
                            {row.configured ? "yes" : "no"}
                          </span>
                        </td>
                        <td>{formatLatency(row.latency_ms)}</td>
                        <td>{formatTimestamp(row.checked_at)}</td>
                        <td className={styles.detailCell}>{row.detail ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </section>
            );
          })
        )}

        <div className={styles.driftLockNotice}>
          Drift lock active: this view reports configuration presence only. No
          probe is mutated, no provider is enabled or disabled, and no API keys
          are emitted in the payload. Auto-paper enforcement, auto trading, and
          live trading remain OFF.
        </div>
      </div>
    </main>
  );
}
