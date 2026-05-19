"use client";

// MH-COCKPIT-11-B — Asset-card detail deep-link page (read-only).
// Renders /asset-cards/{id}. No trading actions. Operator hint only.

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import {
  getAssetCardDetail,
  type AssetCardDetail,
  type AssetCardQuality,
} from "../../../lib/api/assetCards";
import {
  getRecentNewsArticles,
  type NewsArticleItem,
} from "../../../lib/api/newsArticles";
import styles from "../../../styles/pages/asset-card-detail.module.css";

const QUALITY_CLASS: Record<AssetCardQuality, string> = {
  fresh: "qFresh",
  stale: "qStale",
  very_stale: "qVeryStale",
  no_data: "qNoData",
};

const QUALITY_LABEL: Record<AssetCardQuality, string> = {
  fresh: "Fresh",
  stale: "Stale",
  very_stale: "Very stale",
  no_data: "No data",
};

function formatNumber(n: number | null | undefined, digits = 4): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return n.toLocaleString(undefined, {
    minimumFractionDigits: 0,
    maximumFractionDigits: digits,
  });
}

function formatTimestamp(value: string | null | undefined): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString();
}

function formatAge(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return "—";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  if (seconds < 86400) return `${Math.round(seconds / 3600)}h`;
  return `${Math.round(seconds / 86400)}d`;
}

// MH-NEWS-07-C-1 — read-only news surface on the asset-detail page.
// Filters /news-articles/recent by the asset's symbol. Citations and the
// research-only evidence_class badge are always shown. News must never
// relax a risk control or trigger any trading action.
const NEWS_LIMIT = 10;

export default function AssetCardDetailPage() {
  const params = useParams<{ id: string }>();
  const assetId = Array.isArray(params?.id) ? params?.id[0] : params?.id;
  const [detail, setDetail] = useState<AssetCardDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);
  const [news, setNews] = useState<NewsArticleItem[]>([]);
  const [newsLoading, setNewsLoading] = useState<boolean>(false);
  const [newsError, setNewsError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!assetId) return;
    setLoading(true);
    setError(null);
    try {
      const resp = await getAssetCardDetail(assetId, 30);
      setDetail(resp);
      setLastRefreshed(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, [assetId]);

  useEffect(() => {
    void load();
  }, [load]);

  // Load news whenever we have a fresh detail payload (we need its symbol).
  useEffect(() => {
    const symbol = detail?.asset.symbol;
    if (!symbol) return;
    let cancelled = false;
    setNewsLoading(true);
    setNewsError(null);
    getRecentNewsArticles({ ticker: symbol, limit: NEWS_LIMIT })
      .then((resp) => {
        if (cancelled) return;
        setNews(resp.items);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setNewsError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (cancelled) return;
        setNewsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [detail?.asset.symbol]);

  const mq = detail?.market_quality;
  const qualityClassKey = mq ? QUALITY_CLASS[mq.quality] : "qNoData";
  const qualityClass = styles[qualityClassKey] ?? "";

  return (
    <main className={styles.page}>
      <div className={styles.container}>
        <header className={styles.header}>
          <div>
            <Link href="/asset-cards" className={styles.backLink}>
              ← Back to asset cards
            </Link>
            <h1 className={styles.title}>
              {detail ? detail.asset.symbol : "Asset detail"}
            </h1>
            <p className={styles.subtitle}>
              {detail?.asset.name ?? "Read-only asset detail. Market quality is an operator hint and never feeds the trading path."}
            </p>
          </div>
          <div style={{ display: "grid", gap: "0.4rem", justifyItems: "end" }}>
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

        {detail && <div className={styles.advisory}>{detail.advisory}</div>}

        {!detail && loading && <div className={styles.loading}>Loading detail…</div>}

        {detail && (
          <>
            <section className={styles.section}>
              <h2 className={styles.sectionTitle}>Asset</h2>
              <div className={styles.tagRow}>
                <span className={styles.tag}>{detail.asset.asset_class}</span>
                {detail.asset.exchange && (
                  <span className={styles.tag}>{detail.asset.exchange}</span>
                )}
                {detail.asset.sector && (
                  <span className={styles.tag}>{detail.asset.sector}</span>
                )}
                {!detail.asset.is_active && (
                  <span className={styles.tag}>inactive</span>
                )}
                {mq && (
                  <span className={`${styles.qualityBadge} ${qualityClass}`}>
                    {QUALITY_LABEL[mq.quality]}
                  </span>
                )}
              </div>
              <div className={styles.metaGrid}>
                <div className={styles.metaItem}>
                  <span className={styles.metaLabel}>Symbol</span>
                  <span className={styles.metaValue}>{detail.asset.symbol}</span>
                </div>
                <div className={styles.metaItem}>
                  <span className={styles.metaLabel}>Name</span>
                  <span className={styles.metaValue}>
                    {detail.asset.name ?? "—"}
                  </span>
                </div>
                <div className={styles.metaItem}>
                  <span className={styles.metaLabel}>Industry</span>
                  <span className={styles.metaValue}>
                    {detail.asset.industry ?? "—"}
                  </span>
                </div>
                <div className={styles.metaItem}>
                  <span className={styles.metaLabel}>Base / quote</span>
                  <span className={styles.metaValue}>
                    {(detail.asset.base_currency ?? "—") +
                      " / " +
                      (detail.asset.quote_currency ?? "—")}
                  </span>
                </div>
                <div className={styles.metaItem}>
                  <span className={styles.metaLabel}>Asset id</span>
                  <span className={styles.metaValue}>{detail.asset.id}</span>
                </div>
              </div>
            </section>

            <section className={styles.section}>
              <h2 className={styles.sectionTitle}>Market quality</h2>
              <div className={styles.metaGrid}>
                <div className={styles.metaItem}>
                  <span className={styles.metaLabel}>Quality</span>
                  <span className={styles.metaValue}>
                    {mq ? QUALITY_LABEL[mq.quality] : "—"}
                  </span>
                </div>
                <div className={styles.metaItem}>
                  <span className={styles.metaLabel}>Last close</span>
                  <span className={styles.metaValue}>
                    {formatNumber(mq?.last_close ?? null)}
                  </span>
                </div>
                <div className={styles.metaItem}>
                  <span className={styles.metaLabel}>Last bar</span>
                  <span className={styles.metaValue}>
                    {formatTimestamp(mq?.last_bar_ts ?? null)}
                  </span>
                </div>
                <div className={styles.metaItem}>
                  <span className={styles.metaLabel}>Bar age</span>
                  <span className={styles.metaValue}>
                    {formatAge(mq?.bars_age_seconds ?? null)}
                  </span>
                </div>
                <div className={styles.metaItem}>
                  <span className={styles.metaLabel}>Bars (recent)</span>
                  <span className={styles.metaValue}>{mq?.bar_count ?? 0}</span>
                </div>
                <div className={styles.metaItem}>
                  <span className={styles.metaLabel}>Timeframe</span>
                  <span className={styles.metaValue}>{mq?.timeframe ?? "—"}</span>
                </div>
                <div className={styles.metaItem}>
                  <span className={styles.metaLabel}>Avg volume</span>
                  <span className={styles.metaValue}>
                    {formatNumber(mq?.recent_avg_volume ?? null, 2)}
                  </span>
                </div>
                <div className={styles.metaItem}>
                  <span className={styles.metaLabel}>Volatility (σ)</span>
                  <span className={styles.metaValue}>
                    {formatNumber(mq?.recent_volatility ?? null, 6)}
                  </span>
                </div>
              </div>
            </section>

            <section className={`${styles.section} ${styles.tableCard}`}>
              <h2 className={styles.sectionTitle}>
                Recent bars (limit {detail.recent_bars_limit})
              </h2>
              {detail.recent_bars.length === 0 ? (
                <div className={styles.empty}>No bar history yet.</div>
              ) : (
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>Timestamp</th>
                      <th>TF</th>
                      <th>Open</th>
                      <th>High</th>
                      <th>Low</th>
                      <th>Close</th>
                      <th>Volume</th>
                      <th>Source</th>
                    </tr>
                  </thead>
                  <tbody>
                    {detail.recent_bars.map((b, idx) => (
                      <tr key={`${b.ts ?? idx}-${idx}`}>
                        <td>{formatTimestamp(b.ts)}</td>
                        <td className={styles.code}>{b.timeframe ?? "—"}</td>
                        <td className={styles.code}>{formatNumber(b.open)}</td>
                        <td className={styles.code}>{formatNumber(b.high)}</td>
                        <td className={styles.code}>{formatNumber(b.low)}</td>
                        <td className={styles.code}>{formatNumber(b.close)}</td>
                        <td className={styles.code}>
                          {formatNumber(b.volume, 2)}
                        </td>
                        <td className={styles.code}>{b.source ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </section>

            <section className={styles.section}>
              <h2 className={styles.sectionTitle}>
                Recent news (research-only)
              </h2>
              <p className={styles.subtitle}>
                Filtered by symbol <code>{detail.asset.symbol}</code>. Every
                row is locked to <code>evidence_class = research_only</code>;
                news may add caution but must never relax a risk control or
                trigger an order.
              </p>
              {newsError && (
                <div className={styles.errorBanner}>
                  Failed to load news: {newsError}
                </div>
              )}
              {newsLoading && news.length === 0 ? (
                <div className={styles.loading}>Loading news…</div>
              ) : news.length === 0 ? (
                <div className={styles.empty}>
                  No news articles tagged with this symbol.
                </div>
              ) : (
                <ul className={styles.newsList}>
                  {news.map((item) => (
                    <li key={item.id} className={styles.newsItem}>
                      <div className={styles.newsHeader}>
                        <span className={styles.newsHeadline}>
                          {item.headline ?? "(no headline)"}
                        </span>
                        <span className={styles.newsTimestamp}>
                          {formatTimestamp(item.published_at)}
                        </span>
                      </div>
                      <div className={styles.tagRow}>
                        <span className={styles.evidenceBadge}>
                          {item.evidence_class}
                        </span>
                        {item.source_name && (
                          <span className={styles.tag}>{item.source_name}</span>
                        )}
                        {item.url && (
                          <a
                            className={styles.newsLink}
                            href={item.url}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            Open source ↗
                          </a>
                        )}
                      </div>
                      {item.summary && (
                        <p className={styles.newsSummary}>{item.summary}</p>
                      )}
                      {item.citations && item.citations.length > 0 && (
                        <div className={styles.citationsBlock}>
                          <div className={styles.citationsLabel}>
                            Citations ({item.citations.length})
                          </div>
                          <ol className={styles.citationsList}>
                            {item.citations.map((c, idx) => {
                              const label =
                                c.title || c.source || c.url || "(citation)";
                              return (
                                <li key={`c-${item.id}-${idx}`}>
                                  {c.url ? (
                                    <a
                                      href={c.url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                    >
                                      {label}
                                    </a>
                                  ) : (
                                    <span>{label}</span>
                                  )}
                                </li>
                              );
                            })}
                          </ol>
                        </div>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </>
        )}

        <div className={styles.driftLockNotice}>
          Drift lock active: this view is read-only. Auto-paper enforcement,
          auto trading, and live trading remain OFF. Nothing on this page can
          submit orders or change a gate.
        </div>
      </div>
    </main>
  );
}
