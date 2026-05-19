"use client";

import Link from "next/link";
import { useState } from "react";
import { getMarketDataNews, type MarketDataNewsItem } from "../../lib/api";
import { useLivePolling } from "../../lib/hooks/useLivePolling";

const SENTIMENT_STYLE: Record<string, { bg: string; color: string }> = {
  positive: { bg: "var(--state-success-soft)", color: "var(--state-success)" },
  negative: { bg: "var(--state-danger-soft)", color: "var(--state-danger)" },
  neutral: { bg: "var(--surface-soft)", color: "var(--text-muted)" },
};

const DEFAULT_TICKER = "EURUSD";

export default function NewsPage() {
  const [ticker, setTicker] = useState(DEFAULT_TICKER);
  const [inputValue, setInputValue] = useState(DEFAULT_TICKER);
  const [items, setItems] = useState<MarketDataNewsItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  async function load(t: string) {
    if (!t.trim()) return;
    setLoading(true);
    setError(null);
    setSearched(true);
    try {
      const result = await getMarketDataNews(t.trim().toUpperCase(), 30);
      setItems(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load news.");
      setItems([]);
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const t = inputValue.trim().toUpperCase();
    setTicker(t);
    void load(t);
  }

  useLivePolling(() => load(ticker), 20000, { enabled: searched, runImmediately: false });

  return (
    <main style={{ minHeight: "100vh", background: "var(--app-shell-bg)", fontFamily: "var(--font-base)", color: "var(--text-body)" }}>
      <div style={{ maxWidth: 860, margin: "0 auto", padding: "2rem 1.5rem" }}>

        <h1 style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--text-strong)", marginBottom: "0.375rem" }}>News Intelligence</h1>
        <p style={{ color: "var(--text-muted)", fontSize: "0.875rem", marginBottom: "1.25rem" }}>
          Recent news headlines for a specific asset ticker.
        </p>

        <form onSubmit={handleSubmit} style={{ display: "flex", gap: "0.75rem", marginBottom: "1.5rem" }}>
          <input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value.toUpperCase())}
            placeholder="Ticker (e.g. AAPL, EURUSD)"
            style={{
              flex: 1,
              padding: "0.5rem 0.875rem",
              fontSize: "0.875rem",
              background: "var(--control-bg)",
              border: "1px solid var(--control-border)",
              borderRadius: 8,
              color: "var(--control-text)",
              outline: "none",
              fontFamily: "var(--font-base)",
            }}
          />
          <button
            type="submit"
            style={{ padding: "0.5rem 1rem", fontSize: "0.875rem", cursor: "pointer", border: "1px solid var(--accent-primary)", borderRadius: 8, background: "transparent", color: "var(--accent-primary)", fontWeight: 600 }}
          >
            Search
          </button>
        </form>

        {loading && <p style={{ color: "var(--text-muted)" }}>Loading news for {ticker}…</p>}
        {error && <p style={{ color: "var(--state-danger)", padding: "0.75rem 1rem", background: "var(--surface-soft)", borderRadius: 10, border: "1px solid var(--surface-border)" }}>{error}</p>}

        {!loading && searched && items.length === 0 && !error && (
          <p style={{ color: "var(--text-muted)", fontSize: "0.875rem" }}>No news found for {ticker}.</p>
        )}

        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {items.map((n) => {
            const sentStyle = n.tickers.length > 0 ? undefined : undefined;
            return (
              <div key={n.id} style={{ background: "var(--surface-soft)", border: "1px solid var(--surface-border)", borderRadius: 12, padding: "1rem 1.25rem" }}>
                {n.url ? (
                  <a href={n.url} target="_blank" rel="noopener noreferrer" style={{ color: "var(--text-strong)", fontWeight: 500, fontSize: "0.9rem", lineHeight: 1.45, textDecoration: "none" }}>
                    {n.headline}
                  </a>
                ) : (
                  <p style={{ color: "var(--text-strong)", fontWeight: 500, fontSize: "0.9rem", lineHeight: 1.45, margin: 0 }}>{n.headline}</p>
                )}
                <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginTop: "0.5rem", flexWrap: "wrap" }}>
                  {n.source_name && <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>{n.source_name}</span>}
                  <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>{n.published_at.slice(0, 10)}</span>
                  {n.tickers.length > 0 && n.tickers.map((t) => (
                    <Link
                      key={t}
                      href={`/signals?asset=${encodeURIComponent(t)}`}
                      style={{ fontSize: "0.7rem", padding: "2px 7px", borderRadius: 6, background: "var(--state-info-soft)", color: "var(--state-info)", fontWeight: 600, textDecoration: "none" }}
                    >
                      {t}
                    </Link>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </main>
  );
}
