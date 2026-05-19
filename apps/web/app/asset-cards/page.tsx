"use client";

// MH-COCKPIT-02-B — Asset cards / market-quality surface (read-only).
// Renders per-asset cards with derived market-quality flags from
// /asset-cards/snapshot. Operator hint only — never feeds the trading path.

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import {
  getAssetCardsSnapshot,
  type AssetCardItem,
  type AssetCardQuality,
  type AssetCardsSnapshot,
} from "../../lib/api/assetCards";
import styles from "../../styles/pages/asset-cards.module.css";

const QUALITY_CLASS: Record<AssetCardQuality, string> = {
  fresh: styles.qFresh,
  stale: styles.qStale,
  very_stale: styles.qVeryStale,
  no_data: styles.qNoData,
};

const QUALITY_LABEL: Record<AssetCardQuality, string> = {
  fresh: "Fresh",
  stale: "Stale",
  very_stale: "Very stale",
  no_data: "No data",
};

const ASSET_CLASS_OPTIONS: Array<{ value: string; label: string }> = [
  { value: "", label: "All classes" },
  { value: "fx", label: "FX" },
  { value: "equity", label: "Equity" },
  { value: "etf", label: "ETF" },
  { value: "index_proxy", label: "Index proxy" },
  { value: "commodity_proxy", label: "Commodity proxy" },
  { value: "crypto", label: "Crypto" },
];

function formatNumber(n: number | null, digits = 4): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return n.toLocaleString(undefined, {
    minimumFractionDigits: 0,
    maximumFractionDigits: digits,
  });
}

function formatAge(seconds: number | null): string {
  if (seconds === null || seconds === undefined) return "—";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  if (seconds < 86400) return `${Math.round(seconds / 3600)}h`;
  return `${Math.round(seconds / 86400)}d`;
}

function formatTimestamp(value: string | null | undefined): string {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString();
}

export default function AssetCardsPage() {
  const [snapshot, setSnapshot] = useState<AssetCardsSnapshot | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);

  const [assetClass, setAssetClass] = useState<string>("");
  const [activeOnly, setActiveOnly] = useState<boolean>(true);
  const [limit, setLimit] = useState<number>(50);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await getAssetCardsSnapshot({
        limit,
        assetClass: assetClass || undefined,
        activeOnly,
      });
      setSnapshot(resp);
      setLastRefreshed(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, [limit, assetClass, activeOnly]);

  useEffect(() => {
    void load();
    // Initial load only; subsequent loads are user-driven via Refresh.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const items: AssetCardItem[] = snapshot?.items ?? [];

  return (
    <main className={styles.page}>
      <div className={styles.container}>
        <header className={styles.header}>
          <div>
            <h1 className={styles.title}>Asset Cards</h1>
            <p className={styles.subtitle}>
              Per-asset market-quality snapshot. The quality badge reflects bar
              freshness only and is an operator hint — it never influences risk
              gates, the broker, or the auto-paper worker.
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
          <span className={styles.filterLabel}>Asset class</span>
          <select
            className={styles.filterSelect}
            value={assetClass}
            onChange={(e) => setAssetClass(e.target.value)}
          >
            {ASSET_CLASS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>

          <span className={styles.filterLabel}>Limit</span>
          <input
            className={styles.filterInput}
            type="number"
            min={1}
            max={200}
            value={limit}
            onChange={(e) =>
              setLimit(Math.max(1, Math.min(200, Number(e.target.value) || 50)))
            }
            style={{ minWidth: 80 }}
          />

          <label className={styles.checkboxLabel}>
            <input
              type="checkbox"
              checked={activeOnly}
              onChange={(e) => setActiveOnly(e.target.checked)}
            />
            Active only
          </label>

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

        {loading && items.length === 0 ? (
          <div className={styles.loading}>Loading asset cards…</div>
        ) : items.length === 0 ? (
          <div className={styles.empty}>
            No assets match the current filters. The asset universe may be
            empty for this class.
          </div>
        ) : (
          <div className={styles.grid}>
            {items.map((item) => {
              const mq = item.market_quality;
              return (
                <article key={item.id} className={styles.card}>
                  <div className={styles.cardHeader}>
                    <div>
                      <h2 className={styles.symbol}>
                        <Link
                          href={`/asset-cards/${item.id}`}
                          style={{ color: "inherit", textDecoration: "none" }}
                        >
                          {item.symbol}
                        </Link>
                      </h2>
                      {item.name && <p className={styles.assetName}>{item.name}</p>}
                    </div>
                    <span
                      className={`${styles.qualityBadge} ${QUALITY_CLASS[mq.quality]}`}
                    >
                      {QUALITY_LABEL[mq.quality]}
                    </span>
                  </div>

                  <div className={styles.tagRow}>
                    <span className={styles.tag}>{item.asset_class}</span>
                    {item.exchange && <span className={styles.tag}>{item.exchange}</span>}
                    {item.sector && <span className={styles.tag}>{item.sector}</span>}
                    {!item.is_active && (
                      <span className={styles.tag}>inactive</span>
                    )}
                  </div>

                  <div className={styles.metaRow}>
                    <span className={styles.metaLabel}>Last close</span>
                    <span className={styles.metaValue}>
                      {formatNumber(mq.last_close)}
                    </span>
                    <span className={styles.metaLabel}>Last bar</span>
                    <span className={styles.metaValue}>
                      {formatTimestamp(mq.last_bar_ts)}
                    </span>
                    <span className={styles.metaLabel}>Age</span>
                    <span className={styles.metaValue}>
                      {formatAge(mq.bars_age_seconds)}
                    </span>
                    <span className={styles.metaLabel}>Bars (recent)</span>
                    <span className={styles.metaValue}>{mq.bar_count}</span>
                    <span className={styles.metaLabel}>Timeframe</span>
                    <span className={styles.metaValue}>{mq.timeframe ?? "—"}</span>
                    <span className={styles.metaLabel}>Avg volume</span>
                    <span className={styles.metaValue}>
                      {formatNumber(mq.recent_avg_volume, 0)}
                    </span>
                    <span className={styles.metaLabel}>Volatility (σ)</span>
                    <span className={styles.metaValue}>
                      {formatNumber(mq.recent_volatility, 6)}
                    </span>
                  </div>
                </article>
              );
            })}
          </div>
        )}

        <div className={styles.driftLockNotice}>
          Drift lock active: this view is read-only. Quality flags are
          advisory; trading decisions are never made from this surface.
          Auto-paper, auto trading, and live trading remain OFF.
        </div>
      </div>
    </main>
  );
}
