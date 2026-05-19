"use client";

// MH-COCKPIT-04-UI — Plain-English explainer surface.
// Read-only view of redacted LLM round-trips from /llm-logs/recent.
// No mutation surfaces. No buttons that imply LLM calls or trading actions
// can be triggered from here.

import { useCallback, useEffect, useState } from "react";

import { getRecentLLMLogs, type LLMLogItem } from "../../lib/api/llmLogs";
import styles from "../../styles/pages/explainer.module.css";

function formatTimestamp(value: string | null | undefined): string {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString();
}

function formatNumber(n: number | null | undefined): string {
  if (n === null || n === undefined) return "—";
  return String(n);
}

function formatLatency(ms: number | null | undefined): string {
  if (ms === null || ms === undefined) return "—";
  return `${ms} ms`;
}

export default function ExplainerPage() {
  const [items, setItems] = useState<LLMLogItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);

  // Filters
  const [providerFilter, setProviderFilter] = useState<string>("");
  const [correlationFilter, setCorrelationFilter] = useState<string>("");
  const [onlyErrors, setOnlyErrors] = useState<boolean>(false);
  const [limit, setLimit] = useState<number>(25);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await getRecentLLMLogs({
        limit,
        provider: providerFilter.trim() || undefined,
        correlationId: correlationFilter.trim() || undefined,
        onlyErrors,
      });
      setItems(resp.items);
      setLastRefreshed(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, [limit, providerFilter, correlationFilter, onlyErrors]);

  useEffect(() => {
    void load();
    // Initial load only; subsequent loads are user-driven via Refresh.
    // Filters intentionally do not auto-trigger to keep network calls explicit.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <main className={styles.page}>
      <div className={styles.container}>
        <header className={styles.header}>
          <div>
            <h1 className={styles.title}>LLM Explainer</h1>
            <p className={styles.subtitle}>
              Read-only view of recent LLM round-trips for plain-English review.
              Prompt previews are length-capped and control-stripped at write
              time; no API keys or full payloads are stored or shown.
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
          <span className={styles.filterLabel}>Provider</span>
          <input
            className={styles.filterInput}
            type="text"
            placeholder="e.g. openai"
            value={providerFilter}
            onChange={(e) => setProviderFilter(e.target.value)}
            maxLength={50}
          />
          <span className={styles.filterLabel}>Correlation ID</span>
          <input
            className={styles.filterInput}
            type="text"
            placeholder="e.g. abc123…"
            value={correlationFilter}
            onChange={(e) => setCorrelationFilter(e.target.value)}
            maxLength={100}
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
          <label className={styles.checkboxLabel}>
            <input
              type="checkbox"
              checked={onlyErrors}
              onChange={(e) => setOnlyErrors(e.target.checked)}
            />
            Errors only
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

        {loading && items.length === 0 ? (
          <div className={styles.loading}>Loading recent LLM activity…</div>
        ) : items.length === 0 ? (
          <div className={styles.empty}>
            No LLM logs match the current filters. Logs are written only when an
            adapter explicitly wires the sink — none may exist yet.
          </div>
        ) : (
          items.map((item) => (
            <article key={item.id} className={styles.logCard}>
              <div className={styles.logHeader}>
                <div className={styles.logTitle}>
                  {item.provider} — {item.model_requested}
                  {item.error_class && (
                    <>
                      {" "}
                      <span className={styles.errorBadge}>error</span>
                    </>
                  )}
                </div>
                <div className={styles.logTimestamp}>
                  {formatTimestamp(item.created_at)}
                </div>
              </div>
              <div className={styles.metaGrid}>
                <div>
                  <div className={styles.metaLabel}>Model returned</div>
                  <div className={styles.metaValue}>{item.model_returned ?? "—"}</div>
                </div>
                <div>
                  <div className={styles.metaLabel}>Stop reason</div>
                  <div className={styles.metaValue}>{item.stop_reason ?? "—"}</div>
                </div>
                <div>
                  <div className={styles.metaLabel}>Latency</div>
                  <div className={styles.metaValue}>{formatLatency(item.latency_ms)}</div>
                </div>
                <div>
                  <div className={styles.metaLabel}>Tokens (p/c/t)</div>
                  <div className={styles.metaValue}>
                    {formatNumber(item.prompt_tokens)} / {formatNumber(item.completion_tokens)}{" "}
                    / {formatNumber(item.total_tokens)}
                  </div>
                </div>
                <div>
                  <div className={styles.metaLabel}>Correlation ID</div>
                  <div className={styles.metaValue}>{item.correlation_id ?? "—"}</div>
                </div>
                <div>
                  <div className={styles.metaLabel}>Prompt version</div>
                  <div className={styles.metaValue}>{item.prompt_version_id ?? "—"}</div>
                </div>
              </div>
              {item.system_prompt_preview && (
                <>
                  <div className={styles.previewLabel}>System prompt (preview)</div>
                  <div className={styles.previewBlock}>{item.system_prompt_preview}</div>
                </>
              )}
              {item.user_prompt_preview && (
                <>
                  <div className={styles.previewLabel}>User prompt (preview)</div>
                  <div className={styles.previewBlock}>{item.user_prompt_preview}</div>
                </>
              )}
              {item.response_payload_preview && (
                <>
                  <div className={styles.previewLabel}>Response payload (preview)</div>
                  <div className={styles.previewBlock}>
                    {item.response_payload_preview}
                  </div>
                </>
              )}
              {item.error_class && (
                <>
                  <div className={styles.previewLabel}>
                    Error: {item.error_class}
                  </div>
                  <div className={styles.previewBlock}>
                    {item.error_message ?? "(no message)"}
                  </div>
                </>
              )}
            </article>
          ))
        )}

        <div className={styles.driftLockNotice}>
          Drift lock active: this view is read-only. No LLM calls can be made
          from here, no trading actions can be triggered, and no auto/live
          enforcement is changed. Auto-paper, auto trading, and live trading
          remain OFF.
        </div>
      </div>
    </main>
  );
}
