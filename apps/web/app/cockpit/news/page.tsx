"use client";

// MH-NEWS-07-C-2 — Cockpit news surface (read-only).
// Compact recent-news widget for the cockpit. Shares the same backend
// (/news-articles/recent) as /news-archive but renders a tighter layout
// for cockpit operators. Citations and the research-only evidence_class
// badge are always rendered. News must never relax a risk control or
// trigger a trading action.

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import {
  getRecentNewsArticles,
  type NewsArticleItem,
} from "../../../lib/api/newsArticles";
import styles from "../../../styles/pages/cockpit-news.module.css";

const DEFAULT_LIMIT = 15;
const MAX_LIMIT = 50;

function formatTimestamp(value: string | null | undefined): string {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString();
}

function citationLabel(citation: { title?: string; url?: string; source?: string }): string {
  return citation.title || citation.source || citation.url || "(citation)";
}

export default function CockpitNewsPage() {
  const [items, setItems] = useState<NewsArticleItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);
  const [limit, setLimit] = useState<number>(DEFAULT_LIMIT);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await getRecentNewsArticles({ limit });
      setItems(resp.items);
      setLastRefreshed(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, [limit]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <main className={styles.page}>
      <div className={styles.container}>
        <header className={styles.header}>
          <div>
            <h1 className={styles.title}>Cockpit · News</h1>
            <p className={styles.subtitle}>
              Read-only research-only news feed for cockpit operators. Every
              row is locked to <code>evidence_class = research_only</code> at
              the database layer; news may add caution but it must never relax
              a risk control or trigger any trading action.
            </p>
            <p className={styles.subtitleAlt}>
              Looking for filters and full bodies?{" "}
              <Link href="/news-archive" className={styles.inlineLink}>
                Open the news archive →
              </Link>
            </p>
          </div>
          <div className={styles.headerControls}>
            {lastRefreshed && (
              <span className={styles.refreshTimestamp}>
                Updated {lastRefreshed.toLocaleTimeString()}
              </span>
            )}
            <div className={styles.limitControl}>
              <label className={styles.limitLabel} htmlFor="cockpit-news-limit">
                Items
              </label>
              <input
                id="cockpit-news-limit"
                className={styles.limitInput}
                type="number"
                min={1}
                max={MAX_LIMIT}
                value={limit}
                onChange={(e) =>
                  setLimit(
                    Math.max(
                      1,
                      Math.min(MAX_LIMIT, Number(e.target.value) || DEFAULT_LIMIT),
                    ),
                  )
                }
              />
            </div>
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

        {loading && items.length === 0 ? (
          <div className={styles.loading}>Loading cockpit news…</div>
        ) : items.length === 0 ? (
          <div className={styles.empty}>
            No persisted news articles yet. The feed populates only when a
            research-provider job writes to <code>news_articles</code>.
          </div>
        ) : (
          <ul className={styles.newsList}>
            {items.map((item) => (
              <li key={item.id} className={styles.newsItem}>
                <div className={styles.newsHeader}>
                  <span className={styles.newsHeadline}>
                    {item.headline ?? "(no headline)"}
                  </span>
                  <span className={styles.newsTimestamp}>
                    {formatTimestamp(item.published_at)}
                  </span>
                </div>
                <div className={styles.metaRow}>
                  <span className={styles.evidenceBadge}>
                    {item.evidence_class}
                  </span>
                  {item.source_name && (
                    <span className={styles.metaPill}>{item.source_name}</span>
                  )}
                  {item.tickers && item.tickers.length > 0 && (
                    <>
                      {item.tickers.slice(0, 8).map((t) => (
                        <span key={`tk-${item.id}-${t}`} className={styles.metaPill}>
                          {t}
                        </span>
                      ))}
                    </>
                  )}
                  {item.url && (
                    <a
                      className={styles.sourceLink}
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
                        const label = citationLabel(c);
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

        <div className={styles.driftLockNotice}>
          Drift lock active: this view is read-only and research-only. News
          must never relax a risk control, never escalate to a trading-decision
          input, and never trigger an order. Auto-paper enforcement, auto
          trading, and live trading remain OFF.
        </div>
      </div>
    </main>
  );
}
