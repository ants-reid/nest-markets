"use client";

// MH-NEWS-07-B — Read-only news-archive surface.
// Renders persisted research-only news articles from /news-articles/recent.
// Citations are always shown when present. The evidence_class badge is always
// rendered so operators see at a glance that this data is research-only and
// must never be used to relax a risk control.

import { useCallback, useEffect, useState } from "react";

import {
  getRecentNewsArticles,
  type NewsArticleItem,
} from "../../lib/api/newsArticles";
import styles from "../../styles/pages/news-archive.module.css";

function formatTimestamp(value: string | null | undefined): string {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString();
}

function citationLabel(citation: { title?: string; url?: string; source?: string }): string {
  return citation.title || citation.source || citation.url || "(citation)";
}

export default function NewsArchivePage() {
  const [items, setItems] = useState<NewsArticleItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);

  // Filters
  const [sourceFilter, setSourceFilter] = useState<string>("");
  const [tickerFilter, setTickerFilter] = useState<string>("");
  const [limit, setLimit] = useState<number>(25);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await getRecentNewsArticles({
        limit,
        source: sourceFilter.trim() || undefined,
        ticker: tickerFilter.trim() || undefined,
      });
      setItems(resp.items);
      setLastRefreshed(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, [limit, sourceFilter, tickerFilter]);

  useEffect(() => {
    void load();
    // Initial load only; subsequent loads are user-driven via Refresh.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <main className={styles.page}>
      <div className={styles.container}>
        <header className={styles.header}>
          <div>
            <h1 className={styles.title}>News Archive</h1>
            <p className={styles.subtitle}>
              Read-only view of persisted research-only news articles. Every
              row is locked to <code>evidence_class = research_only</code> at
              the database layer; news may add caution but it must never relax
              a risk control or trigger any trading action.
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
          <span className={styles.filterLabel}>Source</span>
          <input
            className={styles.filterInput}
            type="text"
            placeholder="exact match, e.g. reuters"
            value={sourceFilter}
            onChange={(e) => setSourceFilter(e.target.value)}
            maxLength={255}
          />
          <span className={styles.filterLabel}>Ticker</span>
          <input
            className={styles.filterInput}
            type="text"
            placeholder="e.g. EURUSD"
            value={tickerFilter}
            onChange={(e) => setTickerFilter(e.target.value)}
            maxLength={32}
          />
          <span className={styles.filterLabel}>Limit</span>
          <input
            className={styles.filterInput}
            type="number"
            min={1}
            max={200}
            value={limit}
            onChange={(e) =>
              setLimit(Math.max(1, Math.min(200, Number(e.target.value) || 25)))
            }
            style={{ minWidth: 80 }}
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

        {loading && items.length === 0 ? (
          <div className={styles.loading}>Loading news archive…</div>
        ) : items.length === 0 ? (
          <div className={styles.empty}>
            No news articles match the current filters. Articles are written
            only when a research provider job persists them — none may exist
            yet.
          </div>
        ) : (
          items.map((item) => (
            <article key={item.id} className={styles.articleCard}>
              <div className={styles.articleHeader}>
                <h2 className={styles.headline}>{item.headline ?? "(no headline)"}</h2>
                <div className={styles.timestamp}>
                  {formatTimestamp(item.published_at)}
                </div>
              </div>

              <div className={styles.metaRow}>
                <span className={styles.evidenceBadge}>
                  {item.evidence_class}
                </span>
                {item.source_name && (
                  <span className={styles.metaPill}>{item.source_name}</span>
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
                {item.tickers && item.tickers.length > 0 && (
                  <>
                    {item.tickers.map((t) => (
                      <span key={`tk-${item.id}-${t}`} className={styles.metaPill}>
                        {t}
                      </span>
                    ))}
                  </>
                )}
                {item.sector_tags && item.sector_tags.length > 0 && (
                  <>
                    {item.sector_tags.map((s) => (
                      <span key={`sc-${item.id}-${s}`} className={styles.metaPill}>
                        {s}
                      </span>
                    ))}
                  </>
                )}
              </div>

              {item.summary && <p className={styles.summary}>{item.summary}</p>}

              {item.body_text && <pre className={styles.body}>{item.body_text}</pre>}

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
            </article>
          ))
        )}

        <div className={styles.driftLockNotice}>
          Drift lock active: this view is read-only and research-only. News
          must never relax a risk control, never escalate to a trading-decision
          input, and never trigger an order. Auto-paper, auto trading, and live
          trading remain OFF.
        </div>
      </div>
    </main>
  );
}
