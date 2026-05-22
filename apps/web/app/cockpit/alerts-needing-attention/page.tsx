"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { EmptyState } from "../../../components/ui/EmptyState";
import {
  getCockpitAlertsNeedingAttention,
  type CockpitAlertsNeedingAttentionResponse,
  type CockpitAttentionItem,
  type CockpitAttentionPriority,
} from "../../../lib/api/cockpitAlertsNeedingAttention";
import styles from "../../../styles/pages/cockpit-alerts-needing-attention.module.css";

function formatTimestamp(value: string | null): string {
  if (!value) return "unknown";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString();
}

function titleCase(value: string): string {
  return value.replaceAll("_", " ");
}

function priorityClass(value: CockpitAttentionPriority): string {
  if (value === "high") return styles.priorityHigh;
  if (value === "medium") return styles.priorityMedium;
  if (value === "low") return styles.priorityLow;
  return styles.priorityUnknown;
}

function sourceClass(value: CockpitAttentionItem["source"]): string {
  if (value === "monitor") return styles.sourceMonitor;
  if (value === "risk") return styles.sourceRisk;
  if (value === "trading_halt") return styles.sourceHalt;
  if (value === "incident") return styles.sourceIncident;
  if (value === "alert" || value === "notification") return styles.sourceAlert;
  if (value === "paper") return styles.sourcePaper;
  return styles.sourceUnknown;
}

function isEmptyReport(report: CockpitAlertsNeedingAttentionResponse): boolean {
  return report.summary.total_items === 0;
}

function AttentionItemCard({ item }: { item: CockpitAttentionItem }) {
  return (
    <article className={styles.itemCard} data-testid="cockpit-attention-item-card">
      <header className={styles.itemHeader}>
        <div className={styles.itemTitleWrap}>
          <h3 className={styles.itemTitle}>{item.title}</h3>
          <p className={styles.itemMessage}>{item.message}</p>
        </div>
        <div className={styles.itemPills}>
          <span className={`${styles.pill} ${priorityClass(item.priority)}`}>{item.priority}</span>
          <span className={`${styles.pill} ${sourceClass(item.source)}`}>{titleCase(item.source)}</span>
          <span className={styles.pillMuted}>{titleCase(item.attention_type)}</span>
        </div>
      </header>

      <dl className={styles.metaGrid}>
        <div>
          <dt>Status</dt>
          <dd>{item.status}</dd>
        </div>
        <div>
          <dt>Detected</dt>
          <dd>{formatTimestamp(item.detected_at)}</dd>
        </div>
        <div>
          <dt>Actionability</dt>
          <dd>{item.is_actionable ? "actionable" : "read-only"}</dd>
        </div>
      </dl>

      <div className={styles.itemColumns}>
        <section>
          <h4>Evidence</h4>
          {item.evidence.length === 0 ? (
            <p className={styles.emptyText}>No evidence fields provided.</p>
          ) : (
            <ul className={styles.list}>
              {item.evidence.map((entry) => (
                <li key={entry}>{entry}</li>
              ))}
            </ul>
          )}
        </section>

        <section>
          <h4>Missing data</h4>
          {item.missing_data.length === 0 ? (
            <p className={styles.emptyText}>No missing-data flags.</p>
          ) : (
            <ul className={styles.list}>
              {item.missing_data.map((entry) => (
                <li key={entry}>{entry}</li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <p className={styles.reviewAction}>
        <strong>Recommended review:</strong> {item.recommended_review_action}
      </p>
    </article>
  );
}

export default function CockpitAlertsNeedingAttentionPage() {
  const [report, setReport] = useState<CockpitAlertsNeedingAttentionResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getCockpitAlertsNeedingAttention();
      setReport(response);
      setLastRefreshed(new Date());
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : String(loadError));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const byPriority = useMemo(() => {
    if (!report) return [];
    return report.grouped_by_priority;
  }, [report]);

  const bySource = useMemo(() => {
    if (!report) return [];
    return report.grouped_by_source;
  }, [report]);

  return (
    <main className={styles.page} data-testid="cockpit-alerts-needing-attention-page">
      <div className={styles.container}>
        <header className={styles.header}>
          <div>
            <h1 className={styles.title}>Alerts Needing Attention</h1>
            <p className={styles.subtitle}>
              Read-only paper visibility for active alerts, unresolved incidents, monitor degradation,
              stale-data warnings, and risk/trading-halt signals that need operator review.
            </p>
          </div>
          <div className={styles.headerActions}>
            <Link href="/cockpit" className={styles.linkPill}>
              ← Cockpit hub
            </Link>
            {lastRefreshed ? (
              <span className={styles.refreshTimestamp}>Updated {lastRefreshed.toLocaleTimeString()}</span>
            ) : null}
            <button type="button" className={styles.refreshButton} onClick={() => void load()} disabled={loading}>
              {loading ? "Loading…" : "Refresh"}
            </button>
          </div>
        </header>

        <div className={styles.paperBanner} data-testid="cockpit-alerts-paper-mode">
          <strong>Paper mode only.</strong> This page is strictly read-only and cannot execute,
          close, modify, approve, acknowledge, or resolve anything.
        </div>

        {error ? (
          <EmptyState
            variant="error"
            title="Alerts needing attention unavailable"
            message={error}
            action={
              <button type="button" className={styles.retryButton} onClick={() => void load()}>
                Retry
              </button>
            }
          />
        ) : null}

        {!error && loading && !report ? (
          <EmptyState
            variant="loading"
            title="Loading alerts needing attention…"
            message="Collecting read-only paper attention signals from cockpit alert, monitor, incident, and risk sources."
          />
        ) : null}

        {report ? (
          <>
            <section className={styles.heroCard}>
              <div>
                <p className={styles.eyebrow}>Generated</p>
                <h2 className={styles.heroTitle}>{formatTimestamp(report.generated_at)}</h2>
                <p className={styles.heroSubtitle}>{report.summary.headline}</p>
              </div>
              <div className={styles.heroMeta}>
                <span className={styles.modePill}>{report.mode}</span>
                <span className={styles.modeMeta}>All items are non-actionable visibility records.</span>
              </div>
            </section>

            <section className={styles.summaryGrid} data-testid="cockpit-alerts-summary-cards">
              <article className={styles.summaryCard}>
                <span className={styles.summaryLabel}>Attention items</span>
                <span className={styles.summaryValue}>{report.summary.total_items}</span>
              </article>
              <article className={styles.summaryCard}>
                <span className={styles.summaryLabel}>High priority</span>
                <span className={styles.summaryValue}>{report.summary.high_priority}</span>
              </article>
              <article className={styles.summaryCard}>
                <span className={styles.summaryLabel}>Unresolved incidents</span>
                <span className={styles.summaryValue}>{report.summary.unresolved_incidents}</span>
              </article>
              <article className={styles.summaryCard}>
                <span className={styles.summaryLabel}>Monitor degraded</span>
                <span className={styles.summaryValue}>{report.summary.monitor_degraded}</span>
              </article>
              <article className={styles.summaryCard}>
                <span className={styles.summaryLabel}>Risk attention</span>
                <span className={styles.summaryValue}>{report.summary.risk_attention}</span>
              </article>
              <article className={styles.summaryCard}>
                <span className={styles.summaryLabel}>Trading halt</span>
                <span className={styles.summaryValue}>{report.summary.trading_halt}</span>
              </article>
            </section>

            {isEmptyReport(report) ? (
              <EmptyState
                title="No active attention items"
                message="No active alerts, incidents, monitor degradations, stale-data issues, or risk/halt signals were found in the current read-only dataset."
              />
            ) : null}

            <section className={styles.twoCol} data-testid="cockpit-alerts-groups">
              <article className={styles.sectionCard}>
                <h2 className={styles.sectionTitle}>Grouped by priority</h2>
                {byPriority.length === 0 ? (
                  <p className={styles.emptyText}>No priority group rows available.</p>
                ) : (
                  <ul className={styles.groupList}>
                    {byPriority.map((group) => (
                      <li key={group.group} className={styles.groupRow}>
                        <span className={`${styles.groupPill} ${priorityClass(group.group as CockpitAttentionPriority)}`}>
                          {group.group}
                        </span>
                        <span className={styles.groupCount}>{group.count}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </article>

              <article className={styles.sectionCard}>
                <h2 className={styles.sectionTitle}>Grouped by source</h2>
                {bySource.length === 0 ? (
                  <p className={styles.emptyText}>No source group rows available.</p>
                ) : (
                  <ul className={styles.groupList}>
                    {bySource.map((group) => (
                      <li key={group.group} className={styles.groupRow}>
                        <span className={`${styles.groupPill} ${sourceClass(group.group as CockpitAttentionItem["source"])}`}>
                          {titleCase(group.group)}
                        </span>
                        <span className={styles.groupCount}>{group.count}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </article>
            </section>

            <section className={styles.sectionCard} data-testid="cockpit-alerts-items">
              <h2 className={styles.sectionTitle}>Attention items</h2>
              {report.attention_items.length === 0 ? (
                <p className={styles.emptyText}>No attention rows are currently available.</p>
              ) : (
                <div className={styles.itemsList}>
                  {report.attention_items.map((item) => (
                    <AttentionItemCard key={item.id} item={item} />
                  ))}
                </div>
              )}
            </section>

            <section className={styles.twoCol} data-testid="cockpit-alerts-notes">
              <article className={styles.sectionCard}>
                <h2 className={styles.sectionTitle}>Monitor notes</h2>
                {report.monitor_notes.length === 0 ? (
                  <p className={styles.emptyText}>No monitor notes were supplied.</p>
                ) : (
                  <ul className={styles.list}>
                    {report.monitor_notes.map((entry) => (
                      <li key={entry}>{entry}</li>
                    ))}
                  </ul>
                )}
              </article>

              <article className={styles.sectionCard}>
                <h2 className={styles.sectionTitle}>Risk notes</h2>
                {report.risk_notes.length === 0 ? (
                  <p className={styles.emptyText}>No risk notes were supplied.</p>
                ) : (
                  <ul className={styles.list}>
                    {report.risk_notes.map((entry) => (
                      <li key={entry}>{entry}</li>
                    ))}
                  </ul>
                )}
              </article>
            </section>

            <section className={styles.twoCol} data-testid="cockpit-alerts-limitations-actions">
              <article className={styles.sectionCard}>
                <h2 className={styles.sectionTitle}>Limitations</h2>
                {report.limitations.length === 0 ? (
                  <p className={styles.emptyText}>No limitations were reported.</p>
                ) : (
                  <ul className={styles.list}>
                    {report.limitations.map((entry) => (
                      <li key={entry}>{entry}</li>
                    ))}
                  </ul>
                )}
              </article>

              <article className={styles.sectionCard}>
                <h2 className={styles.sectionTitle}>Recommended review actions</h2>
                {report.recommended_review_actions.length === 0 ? (
                  <p className={styles.emptyText}>No review actions were reported.</p>
                ) : (
                  <ul className={styles.list}>
                    {report.recommended_review_actions.map((entry) => (
                      <li key={entry}>{entry}</li>
                    ))}
                  </ul>
                )}
              </article>
            </section>
          </>
        ) : null}
      </div>
    </main>
  );
}
