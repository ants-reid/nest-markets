"use client";

import { CompactBars } from "../../components/CompactBars";
import { HeatmapPanel } from "../../components/HeatmapPanel";
import { InfographicRing } from "../../components/InfographicRing";
import { ChartPanel, LineChart, SeriesToggle, TimeRangeBar, type ChartSeries, type TimeRange } from "../../components/chart";
import { LearnTooltip } from "../../components/LearnTooltip";
import { formatMarketTimeLabel, marketSessionLabel } from "../../lib/chartTime";
import styles from "../../styles/pages/analytics.module.css";
import { useAnalyticsPageController } from "../../lib/hooks/useAnalyticsPageController";

function controlStyle(active: boolean): React.CSSProperties {
  return {
    borderRadius: 10,
    border: `1px solid ${active ? "var(--state-info)" : "var(--surface-border)"}`,
    background: active ? "color-mix(in oklab, var(--state-info) 20%, var(--surface-soft))" : "var(--surface-soft)",
    color: active ? "var(--text-strong)" : "var(--text-muted)",
    fontSize: 12,
    fontWeight: 600,
    padding: "7px 10px",
    cursor: "pointer",
  };
}

export default function AnalyticsPage() {
  const {
    windowSize,
    assetFilter,
    statusFilter,
    viewMode,
    showLifecycle,
    drilldownStatus,
    hiddenSeries,
    timeRange,
    assetOptions,
    statusOptions,
    filteredRows,
    filteredSummary,
    topStatusCards,
    lifecycleRows,
    chartSeries,
    lastUpdated,
    loading,
    error,
    insights,
    statusSegments,
    sideSegments,
    hourlyHeatmap,
    topAssets,
    acceptanceToFillRatio,
    acceptedRate,
    avgHoursToDecision,
    avgHoursToCompletion,
    latest,
    setWindowSize,
    setAssetFilter,
    setStatusFilter,
    setViewMode,
    setShowLifecycle,
    setDrilldownStatus,
    toggleSeries,
    setTimeRange,
  } = useAnalyticsPageController();

  return (
    <div className={styles.shell}>
      <main className={styles.content}>
        <section className={styles.panel}>
          <div className={styles.intro}>
            <h1 className={styles.introTitle}>
              Analytics
            </h1>
            <p className={styles.introBody}>
              Operational performance with controlled interaction. Filter the observed window, inspect distribution changes,
              drill into status behavior, and switch between visual and tabular evidence views.
            </p>
            <span className={styles.timestamp}>
              Data last updated: {lastUpdated ? new Date(lastUpdated).toLocaleString() : "No data"}
            </span>
          </div>
        </section>

        <section className={styles.panel}>
          <div className={styles.filterStack}>
            <div className={styles.filterRow}>
              <span className={styles.filterLabel}>Window</span>
              {[25, 50, 100].map((n) => (
                <button key={n} type="button" onClick={() => setWindowSize(n as 25 | 50 | 100)} style={controlStyle(windowSize === n)}>
                  Last {n}
                </button>
              ))}

              <span className={`${styles.filterLabel} ${styles.filterLabelOffset}`}>Asset</span>
              <select
                value={assetFilter}
                onChange={(event) => setAssetFilter(event.target.value)}
                style={{ ...controlStyle(false), padding: "7px 10px" }}
                className={styles.selectControl}
              >
                {assetOptions.map((asset) => (
                  <option key={asset} value={asset}>
                    {asset === "all" ? "All assets" : asset}
                  </option>
                ))}
              </select>

              <span className={styles.filterLabel}>Status</span>
              <select
                value={statusFilter}
                onChange={(event) => setStatusFilter(event.target.value)}
                style={{ ...controlStyle(false), padding: "7px 10px" }}
                className={styles.selectControl}
              >
                {statusOptions.map((status) => (
                  <option key={status} value={status}>
                    {status === "all" ? "All statuses" : status}
                  </option>
                ))}
              </select>
            </div>

            <div className={styles.filterRow}>
              <span className={styles.filterLabel}>View</span>
              <button type="button" onClick={() => setViewMode("summary")} style={controlStyle(viewMode === "summary")}>Summary</button>
              <button type="button" onClick={() => setViewMode("visual")} style={controlStyle(viewMode === "visual")}>Visual</button>
              <button type="button" onClick={() => setViewMode("table")} style={controlStyle(viewMode === "table")}>Table</button>

              <button
                type="button"
                onClick={() => setShowLifecycle(!showLifecycle)}
                style={{ ...controlStyle(showLifecycle), marginLeft: 10 }}
              >
                {showLifecycle ? "Hide lifecycle" : "Expand lifecycle"}
              </button>

              {drilldownStatus !== null ? (
                <button
                  type="button"
                  onClick={() => setDrilldownStatus(null)}
                  style={{ ...controlStyle(false), border: "1px solid var(--state-warning)" }}
                >
                  Clear drilldown: {drilldownStatus}
                </button>
              ) : null}
            </div>

            <div className={styles.metaRow}>
              <span className={styles.metaText}>Rows after filter: <strong className={styles.metaStrong}>{filteredSummary.count}</strong></span>
              <span className={styles.metaText}>Avg filtered notional: <strong className={styles.metaNumeric}>${filteredSummary.avgNotional.toLocaleString("en-US", { maximumFractionDigits: 2 })}</strong></span>
            </div>
          </div>
        </section>

        {loading ? (
          <section className={styles.panel}>
            <p className={styles.stateMessage}>Loading analytics...</p>
          </section>
        ) : null}

        {!loading && error ? (
          <section className={styles.panel}>
            <div className={styles.errorBanner}>
              {error}
            </div>
          </section>
        ) : null}

        {!loading && !error ? (
          <>
            <section className={styles.panelGrid}>
              <h2 className={styles.sectionHeading}>
                Status Drilldown
              </h2>
              <div className={styles.drilldownGrid}>
                {topStatusCards.length === 0 ? (
                  <div className={styles.emptyCard}>
                    No status data for selected filters.
                  </div>
                ) : (
                  topStatusCards.map(([status, count]) => {
                    const active = drilldownStatus === status;
                    const pct = filteredSummary.count > 0 ? ((count / filteredSummary.count) * 100).toFixed(1) : "0.0";
                    return (
                      <button
                        key={status}
                        type="button"
                        onClick={() => setDrilldownStatus(active ? null : status)}
                        className={`${styles.drilldownCard} ${active ? styles.drilldownCardActive : ""}`}
                      >
                        <span className={styles.drilldownLabel}>
                          {status}
                        </span>
                        <strong className={styles.drilldownCount}>{count}</strong>
                        <span className={styles.drilldownPct}>{pct}% of filtered</span>
                      </button>
                    );
                  })
                )}
              </div>
            </section>

            {viewMode !== "table" ? (
              <>
                <ChartPanel
                  title={
                    <LearnTooltip
                      explain={{
                        beginner: "This chart shows the dollar value (notional) of paper trades over time. Each line is a different asset, with labels showing market session context.",
                        intermediate: "Multi-asset notional series chart with inferred market timeline and session-aware labels.",
                        experienced: "Notional by asset on inferred timestamps. Hover to inspect values and session context. Use toggles to isolate assets.",
                        expert: "Per-asset notional series mapped to inferred timestamp axis from timeframe cadence. Session context embedded in labels.",
                      }}
                      placement="bottom"
                    >
                      Notional by Asset
                    </LearnTooltip>
                  }
                  subtitle="Multi-series · top 5 assets · consistent chart controls"
                  controls={<TimeRangeBar value={timeRange} onChange={setTimeRange} />}
                  legend={<SeriesToggle series={chartSeries} hidden={hiddenSeries} onToggle={toggleSeries} />}
                >
                  <LineChart
                    series={chartSeries}
                    hidden={hiddenSeries}
                    height={260}
                    yLabel="Notional"
                    formatValue={(v) => `$${v >= 1000 ? `${(v / 1000).toFixed(1)}k` : v.toFixed(0)}`}
                    formatTime={formatMarketTimeLabel}
                    getTooltipContextRows={({ time, series }) => [
                      { label: "Session", value: marketSessionLabel(time) },
                      { label: "Range", value: timeRange },
                      { label: "Visible", value: String(series.length) },
                    ]}
                  />
                </ChartPanel>
                <section style={{ display: "grid", gap: 16, gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))" }}>
                  <InfographicRing title="Status Mix" centerValue={String(insights.total)} segments={statusSegments} />
                  <InfographicRing title="Direction Mix" centerValue={String(insights.total)} segments={sideSegments} />
                  <CompactBars title="Top Assets" subtitle="frequency" items={topAssets} />
                  <HeatmapPanel title="By Hour (UTC)" cells={hourlyHeatmap} />
                </section>
              </>
            ) : null}

            {(viewMode === "summary" || viewMode === "visual") ? (
              <section className={styles.insightGrid}>
                <article className={styles.panel}>
                  <p className={styles.insightLabel}>
                    <LearnTooltip explain={{ beginner: "The percentage of paper trades that were 'accepted' by the system — meaning they passed all pre-checks.", intermediate: "Ratio of accepted orders to total submitted.", experienced: "Accepted / total orders submitted.", expert: "Accepted rate = accepted / N." }}>Accepted Rate</LearnTooltip>
                  </p>
                  <p className={styles.insightValue}>{acceptedRate}%</p>
                </article>
                <article className={styles.panel}>
                  <p className={styles.insightLabel}>
                    <LearnTooltip explain={{ beginner: "Of the accepted trades, how many actually got filled (executed at a price)? Higher is better.", intermediate: "Fill rate from accepted orders — measures execution quality.", experienced: "Accepted → filled conversion ratio.", expert: "filled / accepted." }}>Accepted → Filled</LearnTooltip>
                  </p>
                  <p className={styles.insightValue}>{acceptanceToFillRatio}%</p>
                </article>
                <article className={styles.panel}>
                  <p className={styles.insightLabel}>
                    <LearnTooltip explain={{ beginner: "How long on average from when a trade was submitted to when a decision was made (accept or reject).", intermediate: "Mean time-to-decision across the filtered window.", experienced: "Avg latency from submission to accept/reject.", expert: "Mean submission → decision latency." }}>Avg Hours to Decision</LearnTooltip>
                  </p>
                  <p className={styles.insightValue}>{avgHoursToDecision}</p>
                </article>
                <article className={styles.panel}>
                  <p className={styles.insightLabel}>
                    <LearnTooltip explain={{ beginner: "How long on average from when a trade was submitted to when it was fully closed.", intermediate: "Mean time from submission to final closure.", experienced: "Full round-trip latency average.", expert: "Mean submission → close latency." }}>Avg Hours to Completion</LearnTooltip>
                  </p>
                  <p className={styles.insightValue}>{avgHoursToCompletion}</p>
                </article>
              </section>
            ) : null}

            {showLifecycle ? (
              <section className={styles.panel}>
                <h2 className={styles.sectionHeading}>
                  Lifecycle Expansion
                </h2>
                {lifecycleRows.length === 0 ? (
                  <p className={styles.emptyText}>No lifecycle transitions yet.</p>
                ) : (
                  <div className={styles.lifecycleList}>
                    {lifecycleRows.map(([stage, count]) => (
                      <div key={stage} className={styles.lifecycleItem}>
                        <div className={styles.lifecycleHeader}>
                          <span className={styles.lifecycleStage}>{stage}</span>
                          <span className={styles.lifecycleCount}>{count}</span>
                        </div>
                        <div className={styles.progressTrack}>
                          <div
                            className={styles.progressFill}
                            style={{ width: `${Math.min(100, (count / Math.max(1, insights.total)) * 100)}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </section>
            ) : null}

            {(viewMode === "table" || drilldownStatus !== null) ? (
              <section className={styles.panel}>
                <h2 className={styles.sectionHeading}>
                  Execution Records
                </h2>
                <div className={styles.tableWrap}>
                  <table className={styles.recordsTable}>
                    <thead>
                      <tr>
                        {[
                          "ID",
                          "Asset",
                          "Side",
                          "Status",
                          "Notional",
                          "Opened",
                          "Closed",
                        ].map((cell) => (
                          <th
                            key={cell}
                            className={styles.recordsHeaderCell}
                          >
                            {cell}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {filteredRows.slice(0, 40).map((row) => (
                        <tr key={row.execution_id}>
                          <td className={`${styles.recordsCell} ${styles.recordsStrong}`}>{row.execution_id}</td>
                          <td className={`${styles.recordsCell} ${styles.recordsStrong}`}>{(row.asset || "-").toUpperCase()}</td>
                          <td className={`${styles.recordsCell} ${styles.recordsStrong}`} style={{ textTransform: "capitalize" }}>{row.side || "-"}</td>
                          <td className={`${styles.recordsCell} ${styles.recordsMuted}`} style={{ textTransform: "capitalize" }}>{row.status || "-"}</td>
                          <td className={`${styles.recordsCell} ${styles.recordsNumeric}`}>
                            ${(Number(row.notional) || 0).toLocaleString("en-US", { maximumFractionDigits: 2 })}
                          </td>
                          <td className={`${styles.recordsCell} ${styles.recordsMuted}`}>-</td>
                          <td className={`${styles.recordsCell} ${styles.recordsMuted}`}>-</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            ) : null}

            <section className={styles.panel}>
              <h2 className={styles.sectionHeading}>
                Latest Result Snapshot
              </h2>
              {latest ? (
                <div className={styles.snapshotWrap}>
                  <pre className={styles.snapshotPre}>{JSON.stringify(latest, null, 2)}</pre>
                </div>
              ) : (
                <p className={styles.emptyText}>No latest analytics payload yet.</p>
              )}
            </section>
          </>
        ) : null}
      </main>
    </div>
  );
}
