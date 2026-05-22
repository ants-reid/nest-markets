"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { AssetContextLink } from "../../../components/ui/AssetContextLink";
import {
  getCockpitEodReport,
  type CockpitEodIncidentItem,
  type CockpitEodMonitorNote,
  type CockpitEodReportResponse,
  type CockpitEodTradeItem,
} from "../../../lib/api/cockpitEodReport";
import { EmptyState } from "../../../components/ui/EmptyState";
import styles from "../../../styles/pages/cockpit-eod-report.module.css";

function formatTimestamp(value: string | null): string {
  if (!value) return "Unavailable";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString();
}

function formatDate(value: string): string {
  const parsed = new Date(`${value}T00:00:00Z`);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function formatNumber(value: number | null): string {
  if (value === null) return "Unavailable";
  return Number.isInteger(value) ? `${value}` : value.toFixed(2);
}

function formatCurrency(value: number | null): string {
  if (value === null) return "Unavailable";
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(value);
}

function severityClass(severity: string): string {
  const normal = severity.toLowerCase();
  if (normal === "critical" || normal === "error") return styles.severityDanger;
  if (normal === "warn") return styles.severityWarn;
  return styles.severityInfo;
}

function pnlClass(value: number | null): string {
  if (value === null) return styles.pnlUnknown;
  if (value > 0) return styles.pnlPositive;
  if (value < 0) return styles.pnlNegative;
  return styles.pnlNeutral;
}

function TradeCard({ trade, label }: { trade: CockpitEodTradeItem | null; label: string }) {
  if (!trade) {
    return (
      <div className={styles.metricCard}>
        <span className={styles.metricLabel}>{label}</span>
        <span className={styles.metricValue}>Unavailable</span>
      </div>
    );
  }

  return (
    <div className={styles.metricCard}>
      <span className={styles.metricLabel}>{label}</span>
      <span className={styles.metricValue}>{trade.asset_symbol}</span>
      <AssetContextLink context={trade} fallbackSymbol={trade.asset_symbol} />
      <span className={`${styles.metricSubvalue} ${pnlClass(trade.realized_pnl)}`}>
        {formatCurrency(trade.realized_pnl)}
      </span>
      <span className={styles.metricMeta}>
        {trade.side} · {trade.close_reason ?? "no close reason"}
      </span>
    </div>
  );
}

function IncidentRow({ item }: { item: CockpitEodIncidentItem }) {
  return (
    <div className={styles.listRow}>
      <span className={`${styles.badge} ${severityClass(item.severity)}`}>{item.severity}</span>
      <div className={styles.listMain}>
        <div className={styles.listTitle}>{item.title}</div>
        <div className={styles.listMeta}>
          {item.code} · {item.source}
        </div>
        {item.detail && <div className={styles.listDetail}>{item.detail}</div>}
      </div>
      <span className={styles.listTime}>{formatTimestamp(item.created_at)}</span>
    </div>
  );
}

function MonitorRow({ item }: { item: CockpitEodMonitorNote }) {
  return (
    <div className={styles.noteCard}>
      <div className={styles.noteHeader}>
        <span className={styles.noteTitle}>{item.title}</span>
        <span className={`${styles.badge} ${severityClass(item.severity)}`}>{item.severity}</span>
      </div>
      <p className={styles.noteBody}>{item.detail}</p>
      <span className={styles.noteMeta}>{formatTimestamp(item.created_at)}</span>
    </div>
  );
}

function isEmptyReport(report: CockpitEodReportResponse): boolean {
  return (
    report.summary.opened_today === 0 &&
    report.summary.closed_today === 0 &&
    report.summary.open_positions_now === 0 &&
    report.alerts_or_incidents.length === 0 &&
    report.monitor_notes.length === 0 &&
    report.lessons.length === 0
  );
}

export default function CockpitEodReportPage() {
  const [report, setReport] = useState<CockpitEodReportResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getCockpitEodReport();
      setReport(response);
      setLastRefreshed(new Date());
    } catch (fetchError) {
      setError(fetchError instanceof Error ? fetchError.message : "Failed to load EOD report.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <main className={styles.page} data-testid="cockpit-eod-report-page">
      <div className={styles.container}>
        <header className={styles.header}>
          <div>
            <h1 className={styles.title}>End-of-Day Report</h1>
            <p className={styles.subtitle}>
              Paper-mode recap for operators: what opened, what closed, what needs attention,
              and what the system learned today without changing any trading state.
            </p>
          </div>
          <div className={styles.headerActions}>
            <Link href="/cockpit" className={styles.linkPill}>
              ← Cockpit hub
            </Link>
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

        <div className={styles.paperBanner} data-testid="cockpit-eod-paper-mode">
          <strong>Paper mode only.</strong> This report is strictly read-only. It does not place,
          close, cancel, or modify trades, and it does not unlock live trading.
        </div>

        {error && (
          <EmptyState
            variant="error"
            title="EOD report unavailable"
            message={error}
            action={
              <button type="button" className={styles.retryButton} onClick={() => void load()}>
                Retry
              </button>
            }
          />
        )}

        {!error && loading && !report && (
          <EmptyState
            variant="loading"
            title="Loading end-of-day report…"
            message="Pulling the latest paper-mode summary from the cockpit API."
          />
        )}

        {report && (
          <>
            <section className={styles.heroCard}>
              <div>
                <p className={styles.eyebrow}>Report date</p>
                <h2 className={styles.heroTitle}>{formatDate(report.report_date)}</h2>
                <p className={styles.heroSubtitle}>{report.summary.headline}</p>
              </div>
              <div className={styles.heroMeta}>
                <span className={styles.modePill}>{report.mode}</span>
                <span className={styles.generatedAt}>
                  Generated {formatTimestamp(report.generated_at)}
                </span>
              </div>
            </section>

            <section className={styles.summaryGrid} data-testid="cockpit-eod-summary-cards">
              <div className={styles.summaryCard}>
                <span className={styles.summaryLabel}>Paper trades opened</span>
                <span className={styles.summaryValue}>{report.summary.opened_today}</span>
              </div>
              <div className={styles.summaryCard}>
                <span className={styles.summaryLabel}>Paper trades closed</span>
                <span className={styles.summaryValue}>{report.summary.closed_today}</span>
              </div>
              <div className={styles.summaryCard}>
                <span className={styles.summaryLabel}>Open positions now</span>
                <span className={styles.summaryValue}>{report.summary.open_positions_now}</span>
              </div>
              <div className={styles.summaryCard}>
                <span className={styles.summaryLabel}>Needs attention</span>
                <span className={styles.summaryValue}>{report.summary.alerts_needing_attention}</span>
              </div>
              <div className={styles.summaryCard}>
                <span className={styles.summaryLabel}>Lessons available</span>
                <span className={styles.summaryValue}>{report.summary.lessons_available}</span>
              </div>
            </section>

            {isEmptyReport(report) ? (
              <EmptyState
                title="No paper activity recorded yet"
                message="Today’s paper end-of-day report is empty so far. Counts remain at zero until paper orders, positions, incidents, or signal outcomes are persisted."
              />
            ) : null}

            <section className={styles.twoCol}>
              <div className={styles.sectionCard}>
                <h2 className={styles.sectionTitle}>Paper activity</h2>
                <div className={styles.metricGrid}>
                  <div className={styles.metricCard}>
                    <span className={styles.metricLabel}>Opened today</span>
                    <span className={styles.metricValue}>{report.paper_activity.opened_today}</span>
                  </div>
                  <div className={styles.metricCard}>
                    <span className={styles.metricLabel}>Closed today</span>
                    <span className={styles.metricValue}>{report.paper_activity.closed_today}</span>
                  </div>
                  <div className={styles.metricCard}>
                    <span className={styles.metricLabel}>Current open positions</span>
                    <span className={styles.metricValue}>{report.paper_activity.current_open_positions}</span>
                  </div>
                </div>
              </div>

              <div className={styles.sectionCard}>
                <h2 className={styles.sectionTitle}>P&amp;L snapshot</h2>
                <div className={styles.metricGrid}>
                  <div className={styles.metricCard}>
                    <span className={styles.metricLabel}>Realized today</span>
                    <span className={`${styles.metricValue} ${pnlClass(report.pnl.realized_day)}`}>
                      {formatCurrency(report.pnl.realized_day)}
                    </span>
                    <span className={styles.metricMeta}>{report.pnl.realized_basis}</span>
                  </div>
                  <div className={styles.metricCard}>
                    <span className={styles.metricLabel}>Unrealized snapshot</span>
                    <span className={`${styles.metricValue} ${pnlClass(report.pnl.unrealized_snapshot)}`}>
                      {formatCurrency(report.pnl.unrealized_snapshot)}
                    </span>
                    <span className={styles.metricMeta}>{report.pnl.unrealized_basis}</span>
                  </div>
                </div>
              </div>
            </section>

            <section className={styles.twoCol}>
              <div className={styles.sectionCard}>
                <div className={styles.sectionHeader}>
                  <h2 className={styles.sectionTitle}>Open positions</h2>
                  <Link href="/execution" className={styles.inlineLink}>
                    Review execution →
                  </Link>
                </div>
                {report.open_positions.items.length === 0 ? (
                  <p className={styles.emptyCopy}>No paper positions are currently open.</p>
                ) : (
                  <div className={styles.positionList}>
                    {report.open_positions.items.map((item) => (
                      <div key={`${item.asset_symbol}-${item.opened_at}`} className={styles.positionCard}>
                        <div className={styles.positionTop}>
                          <span className={styles.positionAsset}>{item.asset_symbol}</span>
                          <span className={styles.positionSide}>{item.side}</span>
                        </div>
                        <div className={styles.assetContextRow}>
                          <AssetContextLink context={item} fallbackSymbol={item.asset_symbol} />
                        </div>
                        <div className={styles.positionMeta}>Qty: {formatNumber(item.qty)}</div>
                        <div className={styles.positionMeta}>Opened: {formatTimestamp(item.opened_at)}</div>
                        <div className={`${styles.positionPnl} ${pnlClass(item.unrealized_pnl)}`}>
                          {formatCurrency(item.unrealized_pnl)}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className={styles.sectionCard}>
                <h2 className={styles.sectionTitle}>Closed positions</h2>
                <div className={styles.metricGrid}>
                  <div className={styles.metricCard}>
                    <span className={styles.metricLabel}>Closed count</span>
                    <span className={styles.metricValue}>{report.closed_positions.count}</span>
                  </div>
                  <div className={styles.metricCard}>
                    <span className={styles.metricLabel}>Wins / losses / flat</span>
                    <span className={styles.metricValue}>
                      {report.closed_positions.wins ?? "?"} / {report.closed_positions.losses ?? "?"} / {report.closed_positions.flat ?? "?"}
                    </span>
                    <span className={styles.metricMeta}>Unknown: {report.closed_positions.unknown}</span>
                  </div>
                  <TradeCard label="Best trade" trade={report.closed_positions.best_trade} />
                  <TradeCard label="Worst trade" trade={report.closed_positions.worst_trade} />
                </div>
              </div>
            </section>

            <section className={styles.sectionCard}>
              <h2 className={styles.sectionTitle}>Alerts and incidents needing attention</h2>
              {report.alerts_or_incidents.length === 0 ? (
                <p className={styles.emptyCopy}>No alerts or incidents crossed the attention threshold today.</p>
              ) : (
                <div className={styles.listWrap}>
                  {report.alerts_or_incidents.map((item) => (
                    <IncidentRow key={`${item.code}-${item.created_at}`} item={item} />
                  ))}
                </div>
              )}
            </section>

            <section className={styles.twoCol}>
              <div className={styles.sectionCard}>
                <h2 className={styles.sectionTitle}>Monitor and feed notes</h2>
                {report.monitor_notes.length === 0 ? (
                  <p className={styles.emptyCopy}>No monitor or feed issues were recorded today.</p>
                ) : (
                  <div className={styles.noteGrid}>
                    {report.monitor_notes.map((item) => (
                      <MonitorRow key={`${item.title}-${item.created_at}`} item={item} />
                    ))}
                  </div>
                )}
              </div>

              <div className={styles.sectionCard}>
                <h2 className={styles.sectionTitle}>Lessons and observations</h2>
                {report.lessons.length === 0 ? (
                  <p className={styles.emptyCopy}>No closed signal outcomes were available to summarize.</p>
                ) : (
                  <ul className={styles.bulletList}>
                    {report.lessons.map((lesson) => (
                      <li key={lesson.title} className={styles.bulletItem}>
                        <strong>{lesson.title}.</strong> {lesson.detail} Evidence count: {lesson.evidence_count}.
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </section>

            <section className={styles.twoCol}>
              <div className={styles.sectionCard}>
                <h2 className={styles.sectionTitle}>Recommended next actions</h2>
                <ul className={styles.bulletList}>
                  {report.recommended_actions.map((item) => (
                    <li key={item} className={styles.bulletItem}>{item}</li>
                  ))}
                </ul>
              </div>

              <div className={styles.sectionCard}>
                <h2 className={styles.sectionTitle}>Limitations</h2>
                {report.limitations.length === 0 ? (
                  <p className={styles.emptyCopy}>No known limitations were reported for this EOD snapshot.</p>
                ) : (
                  <ul className={styles.bulletList}>
                    {report.limitations.map((item) => (
                      <li key={item} className={styles.bulletItem}>{item}</li>
                    ))}
                  </ul>
                )}
              </div>
            </section>
          </>
        )}
      </div>
    </main>
  );
}