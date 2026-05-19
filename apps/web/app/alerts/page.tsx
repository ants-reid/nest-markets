"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { ChartPanel, LineChart, SeriesToggle, TimeRangeBar, type ChartSeries, type TimeRange } from "../../components/chart";
import { LearnTooltip } from "../../components/LearnTooltip";
import { formatMarketTimeLabel, inferExecutionTimestamps, marketSessionLabel } from "../../lib/chartTime";
import {
  acknowledgeAlertRule,
  createAlertRule,
  listActiveAlerts,
  listAlertNotifications,
  listAlertRules,
  listPaperExecutions,
  markAlertNotificationRead,
  snoozeAlertRule,
  type ActiveAlertResponse,
  type AlertNotificationResponse,
  type AlertRuleResponse,
} from "../../lib/api";
import type { PaperExecutionResponse } from "../../lib/types";
import { useLivePolling } from "../../lib/hooks/useLivePolling";
import { PageShell } from "../../components/ui/PageShell";
import { PageHeader } from "../../components/shell/PageHeader";

const OPEN_STATUSES = new Set(["new", "submitted", "accepted", "filled"]);

interface DerivedAlert {
  id: string;
  asset: string;
  executionId: string;
  status: string;
  level: "warning" | "info";
  message: string;
}

function deriveAlerts(executions: PaperExecutionResponse[]): DerivedAlert[] {
  const alerts: DerivedAlert[] = [];

  for (const ex of executions) {
    const status = ex.status.toLowerCase();

    if (status === "submitted") {
      alerts.push({
        id: `${ex.execution_id}-submitted`,
        asset: ex.asset,
        executionId: ex.execution_id,
        status: ex.status,
        level: "info",
        message: `${ex.asset} execution is submitted and awaiting fill/processing.`,
      });
    }

    if (status === "accepted") {
      alerts.push({
        id: `${ex.execution_id}-accepted`,
        asset: ex.asset,
        executionId: ex.execution_id,
        status: ex.status,
        level: "info",
        message: `${ex.asset} execution accepted - position is open.`,
      });
    }

    if (status === "rejected") {
      alerts.push({
        id: `${ex.execution_id}-rejected`,
        asset: ex.asset,
        executionId: ex.execution_id,
        status: ex.status,
        level: "warning",
        message: `${ex.asset} execution was rejected. Consider reviewing risk settings or re-running workflow.`,
      });
    }

    if (status === "filled") {
      alerts.push({
        id: `${ex.execution_id}-filled`,
        asset: ex.asset,
        executionId: ex.execution_id,
        status: ex.status,
        level: "info",
        message: `${ex.asset} execution filled - monitoring for close/exit.`,
      });
    }
  }

  return alerts;
}

type PageState =
  | { state: "loading"; data: null; error: null }
  | { state: "ready"; data: PaperExecutionResponse[]; error: null }
  | { state: "error"; data: null; error: string };

function panelStyle(): React.CSSProperties {
  return {
    display: "grid",
    gap: 12,
    padding: 22,
    borderRadius: 20,
    background: "var(--surface-fill)",
    border: "1px solid var(--surface-border)",
    boxShadow: "var(--surface-shadow)",
  };
}

function badgeStyle(level: "warning" | "info"): React.CSSProperties {
  return {
    display: "inline-block",
    borderRadius: 999,
    padding: "3px 10px",
    fontSize: 11,
    fontWeight: 700,
    textTransform: "uppercase",
    letterSpacing: 0.7,
    background: level === "warning" ? "var(--state-warning-soft)" : "var(--state-info-soft)",
    color: level === "warning" ? "var(--state-warning)" : "var(--state-info)",
    border: `1px solid ${level === "warning" ? "var(--state-warning-border)" : "var(--state-info-border)"}`,
  };
}

export default function AlertsPage() {
  const [page, setPage] = useState<PageState>({ state: "loading", data: null, error: null });
  const [timeRange, setTimeRange] = useState<TimeRange>("1M");
  const [hiddenSeries, setHiddenSeries] = useState<Set<string>>(new Set());

  const [ruleAsset, setRuleAsset] = useState("EURUSD");
  const [ruleCondition, setRuleCondition] = useState("status = submitted");
  const [rules, setRules] = useState<AlertRuleResponse[]>([]);
  const [activeAlerts, setActiveAlerts] = useState<ActiveAlertResponse[]>([]);
  const [notifications, setNotifications] = useState<AlertNotificationResponse[]>([]);

  const [ruleError, setRuleError] = useState<string | null>(null);
  const [activeAlertsError, setActiveAlertsError] = useState<string | null>(null);
  const [notificationError, setNotificationError] = useState<string | null>(null);
  const [isSubmittingRule, setIsSubmittingRule] = useState(false);
  const [ruleAction, setRuleAction] = useState<string | null>(null);
  const [notificationAction, setNotificationAction] = useState<string | null>(null);

  const loadExecutionsOnly = useCallback(async () => {
    setPage({ state: "loading", data: null, error: null });
    try {
      const data = await listPaperExecutions({ limit: 50, offset: 0 });
      setPage({ state: "ready", data, error: null });
    } catch (err) {
      setPage({
        state: "error",
        data: null,
        error: err instanceof Error ? err.message : "Failed to load executions.",
      });
    }
  }, []);

  const loadRulesAndAlerts = useCallback(async () => {
    const [rulesResult, alertsResult, notificationsResult] = await Promise.allSettled([
      listAlertRules(),
      listActiveAlerts(),
      listAlertNotifications(),
    ]);

    if (rulesResult.status === "fulfilled") {
      setRules(rulesResult.value);
      setRuleError(null);
    } else {
      setRuleError(rulesResult.reason instanceof Error ? rulesResult.reason.message : "Failed to load alert rules.");
    }

    if (alertsResult.status === "fulfilled") {
      setActiveAlerts(alertsResult.value);
      setActiveAlertsError(null);
    } else {
      setActiveAlertsError(
        alertsResult.reason instanceof Error ? alertsResult.reason.message : "Failed to load active alerts.",
      );
    }

    if (notificationsResult.status === "fulfilled") {
      setNotifications(notificationsResult.value);
      setNotificationError(null);
    } else {
      setNotificationError(
        notificationsResult.reason instanceof Error
          ? notificationsResult.reason.message
          : "Failed to load notifications.",
      );
    }
  }, []);

  const load = useCallback(async () => {
    await loadExecutionsOnly();
    await loadRulesAndAlerts();
  }, [loadExecutionsOnly, loadRulesAndAlerts]);

  useEffect(() => {
    void load();
  }, [load]);

  useLivePolling(load, 12000, { enabled: true, runImmediately: false });

  const watchlist = useMemo(() => {
    if (page.state !== "ready") return [];
    const byAsset: Record<string, PaperExecutionResponse[]> = {};
    for (const ex of page.data) {
      if (!OPEN_STATUSES.has(ex.status.toLowerCase())) continue;
      if (!byAsset[ex.asset]) byAsset[ex.asset] = [];
      byAsset[ex.asset].push(ex);
    }
    return Object.entries(byAsset).map(([asset, items]) => ({ asset, items }));
  }, [page]);

  const fallbackDerivedAlerts = useMemo(() => {
    if (page.state !== "ready") return [];
    return deriveAlerts(page.data);
  }, [page]);

  const alertDistribution = useMemo(() => {
    const all = activeAlerts.length > 0 ? activeAlerts : fallbackDerivedAlerts;
    const byLevel: Record<string, number> = {};
    const byStatus: Record<string, number> = {};
    for (const a of all) {
      const level = (a as ActiveAlertResponse).level ?? (a as DerivedAlert).level ?? "info";
      const status = (a as ActiveAlertResponse).status ?? (a as DerivedAlert).status ?? "unknown";
      byLevel[level] = (byLevel[level] ?? 0) + 1;
      byStatus[status] = (byStatus[status] ?? 0) + 1;
    }
    return { byLevel, byStatus, total: all.length };
  }, [activeAlerts, fallbackDerivedAlerts]);

  const watchlistSeries = useMemo((): ChartSeries[] => {
    if (page.state !== "ready") return [];

    const rows = page.data;
    const inferredTimes = inferExecutionTimestamps(rows);
    const byAsset: Record<string, Array<{ t: string; v: number }>> = {};

    rows.forEach((row, index) => {
      if (!OPEN_STATUSES.has(row.status.toLowerCase())) return;
      const asset = row.asset.toUpperCase();
      if (!byAsset[asset]) byAsset[asset] = [];
      byAsset[asset].push({ t: inferredTimes[index] ?? new Date().toISOString(), v: row.notional });
    });

    const colors = [
      "var(--chart-series-1)",
      "var(--chart-series-2)",
      "var(--chart-series-3)",
      "var(--chart-series-4)",
      "var(--chart-series-5)",
    ];
    return Object.entries(byAsset)
      .sort(([, a], [, b]) => b.length - a.length)
      .slice(0, 5)
      .map(([asset, data], colorIndex) => ({
        id: asset,
        label: asset,
        color: colors[colorIndex % colors.length],
        data,
      }));
  }, [page]);

  const inputStyle: React.CSSProperties = {
    padding: "9px 12px",
    borderRadius: 10,
    border: "1px solid var(--surface-border)",
    background: "var(--control-bg)",
    color: "var(--text-strong)",
    fontSize: 14,
  };

  function filterByRange(data: { t: string; v: number }[]): { t: string; v: number }[] {
    if (timeRange === "ALL" || data.length === 0) return data;

    const latest = Date.parse(data[data.length - 1].t);
    if (!Number.isFinite(latest)) return data;

    const lookbackMs: Record<Exclude<TimeRange, "ALL">, number> = {
      "1D": 24 * 60 * 60 * 1000,
      "1W": 7 * 24 * 60 * 60 * 1000,
      "1M": 30 * 24 * 60 * 60 * 1000,
      "3M": 90 * 24 * 60 * 60 * 1000,
      "1Y": 365 * 24 * 60 * 60 * 1000,
    };

    const minTime = latest - lookbackMs[timeRange];
    const filtered = data.filter((point) => Date.parse(point.t) >= minTime);
    return filtered.length > 1 ? filtered : data;
  }

  function toggleSeries(id: string) {
    setHiddenSeries((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function addRule() {
    const asset = ruleAsset.trim().toUpperCase();
    const condition = ruleCondition.trim();
    if (!asset || !condition) {
      return;
    }

    setIsSubmittingRule(true);
    setRuleError(null);
    try {
      await createAlertRule({ asset, condition });
      await loadRulesAndAlerts();
    } catch (err) {
      setRuleError(err instanceof Error ? err.message : "Failed to create alert rule.");
    } finally {
      setIsSubmittingRule(false);
    }
  }

  async function acknowledgeRule(ruleId: string) {
    setRuleAction(`ack:${ruleId}`);
    setRuleError(null);
    try {
      await acknowledgeAlertRule(ruleId);
      await loadRulesAndAlerts();
    } catch (err) {
      setRuleError(err instanceof Error ? err.message : "Failed to acknowledge alert rule.");
    } finally {
      setRuleAction(null);
    }
  }

  async function snoozeRule(ruleId: string) {
    setRuleAction(`snooze:${ruleId}`);
    setRuleError(null);
    try {
      await snoozeAlertRule(ruleId, 30);
      await loadRulesAndAlerts();
    } catch (err) {
      setRuleError(err instanceof Error ? err.message : "Failed to snooze alert rule.");
    } finally {
      setRuleAction(null);
    }
  }

  async function markNotificationRead(notificationId: string) {
    setNotificationAction(notificationId);
    setNotificationError(null);
    try {
      await markAlertNotificationRead(notificationId);
      await loadRulesAndAlerts();
    } catch (err) {
      setNotificationError(err instanceof Error ? err.message : "Failed to mark notification as read.");
    } finally {
      setNotificationAction(null);
    }
  }

  return (
    <PageShell width="xl">
      <PageHeader
        title="Alerts & Watchlist"
        subtitle="Watchlist is derived from open paper executions. Rules and active alerts use backend-backed persistence and lifecycle actions."
      />

        <section style={panelStyle()}>
          <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 12, alignItems: "center" }}>
            <span style={{ color: "var(--text-muted)", fontSize: 13 }}>Data source: /execution/paper and /approvals/alerts/*</span>
            <button
              type="button"
              onClick={() => {
                void load();
              }}
              style={{
                border: 0,
                borderRadius: 12,
                padding: "10px 14px",
                background: "var(--surface-fill)",
                color: "var(--surface-soft)",
                fontWeight: 700,
                cursor: "pointer",
              }}
            >
              Refresh
            </button>
          </div>
          {page.state === "loading" && <p style={{ margin: 0, color: "var(--text-muted)" }}>Loading execution data...</p>}
          {page.state === "error" && (
            <div
              style={{
                padding: 14,
                borderRadius: 12,
                background: "var(--state-warning-soft)",
                color: "var(--state-warning)",
                border: "1px solid var(--state-warning-border)",
              }}
            >
              {page.error}
            </div>
          )}
        </section>

        {/* Alert Distribution Chart */}
        {alertDistribution.total > 0 ? (
          <section style={panelStyle()}>
            <h2 style={{ margin: 0, color: "var(--text-strong)", fontSize: 20 }}>Alert Distribution</h2>
            <p style={{ margin: 0, color: "var(--text-muted)", fontSize: 13 }}>
              Breakdown of current alerts by level and execution status.
            </p>

            <div data-rs="alert-distribution" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
              {/* By Level */}
              <div>
                <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: 0.8, color: "var(--text-muted)", fontWeight: 700, marginBottom: 10 }}>
                  <LearnTooltip explain={{ beginner: "Alert level shows severity: Warning = something needs attention. Info = informational only.", intermediate: "warning: elevated risk or action required. info: informational status update.", experienced: "Alert severity tiers. warning triggers priority notification; info is ambient.", expert: "level: warning | info. Determines notification priority and escalation path." }}>By Level</LearnTooltip>
                </div>
                <div style={{ display: "grid", gap: 8 }}>
                  {Object.entries(alertDistribution.byLevel).map(([level, count]) => {
                    const pct = alertDistribution.total > 0 ? (count / alertDistribution.total) * 100 : 0;
                    const color = level === "warning" ? "var(--state-warning)" : "var(--state-info)";
                    return (
                      <div key={level}>
                        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                          <span style={{ fontSize: 12, color: "var(--text-body)", fontWeight: 600 }}>{level}</span>
                          <span style={{ fontSize: 12, color: "var(--text-muted)" }}>{count}</span>
                        </div>
                        <div style={{ height: 8, borderRadius: 999, background: "color-mix(in oklab, var(--text-strong) 8%, transparent)" }}>
                          <div style={{ height: "100%", borderRadius: 999, width: `${pct}%`, background: color, transition: "width 0.4s ease" }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* By Status */}
              <div>
                <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: 0.8, color: "var(--text-muted)", fontWeight: 700, marginBottom: 10 }}>
                  <LearnTooltip explain={{ beginner: "Execution status tells you where each trade is in its lifecycle: submitted, accepted, filled, or rejected.", intermediate: "Execution lifecycle statuses: new → submitted → accepted → filled → closed/rejected.", experienced: "Status distribution of flagged executions. submitted/accepted indicate open positions.", expert: "Execution lifecycle state machine: new | submitted | accepted | filled | closed | rejected | cancelled." }}>By Status</LearnTooltip>
                </div>
                <div style={{ display: "grid", gap: 8 }}>
                  {Object.entries(alertDistribution.byStatus).map(([status, count]) => {
                    const pct = alertDistribution.total > 0 ? (count / alertDistribution.total) * 100 : 0;
                    const statusColors: Record<string, string> = {
                      filled: "var(--state-success)",
                      accepted: "var(--state-info)",
                      submitted: "var(--accent-primary)",
                      rejected: "var(--state-danger)",
                      new: "var(--text-muted)",
                    };
                    const color = statusColors[status.toLowerCase()] ?? "var(--text-muted)";
                    return (
                      <div key={status}>
                        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                          <span style={{ fontSize: 12, color: "var(--text-body)", fontWeight: 600 }}>{status}</span>
                          <span style={{ fontSize: 12, color: "var(--text-muted)" }}>{count}</span>
                        </div>
                        <div style={{ height: 8, borderRadius: 999, background: "color-mix(in oklab, var(--text-strong) 8%, transparent)" }}>
                          <div style={{ height: "100%", borderRadius: 999, width: `${pct}%`, background: color, transition: "width 0.4s ease" }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </section>
        ) : null}

        <section style={panelStyle()}>
          <h2 style={{ margin: 0, color: "var(--text-strong)", fontSize: 24 }}>Notification Center</h2>
          <p style={{ margin: 0, color: "var(--text-muted)", fontSize: 13 }}>
            In-app notifications are derived from active persisted alerts. Unread items can be marked as read.
          </p>

          {notificationError ? (
            <div
              style={{
                padding: 12,
                borderRadius: 10,
                border: "1px solid var(--state-warning-border)",
                background: "var(--state-warning-soft)",
                color: "var(--state-warning)",
              }}
            >
              {notificationError}
            </div>
          ) : null}

          {notifications.length === 0 && page.state === "ready" ? (
            <div
              style={{
                padding: 14,
                borderRadius: 12,
                border: "1px dashed var(--surface-border)",
                color: "var(--text-muted)",
                background: "var(--surface-soft)",
              }}
            >
              No notifications yet. Create an alert rule that matches an active execution status.
            </div>
          ) : null}

          {notifications.length > 0 ? (
            <div style={{ display: "grid", gap: 10 }}>
              {notifications.map((notification) => (
                <div
                  data-rs="notification-row"
                  key={notification.notification_id}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "auto 1fr auto auto",
                    gap: 12,
                    padding: "12px 14px",
                    borderRadius: 12,
                    border: `1px solid ${notification.level === "warning" ? "var(--state-warning-border)" : "var(--state-info-border)"}`,
                    background: notification.level === "warning" ? "var(--state-warning-soft)" : "var(--state-info-soft)",
                    alignItems: "center",
                  }}
                >
                  <span style={badgeStyle(notification.is_read ? "info" : "warning")}>
                    {notification.is_read ? "read" : "unread"}
                  </span>
                  <div style={{ display: "grid", gap: 6 }}>
                    <span style={{ fontSize: 13, color: "var(--text-body)" }}>{notification.message}</span>
                    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                      <Link
                        href="/alerts"
                        style={{
                          fontSize: 12,
                          color: "var(--text-body)",
                          fontWeight: 700,
                          textDecoration: "none",
                          border: "1px solid var(--surface-border)",
                          borderRadius: 8,
                          padding: "4px 8px",
                        }}
                      >
                        Alerts
                      </Link>
                      <Link
                        href={`/execution?asset=${encodeURIComponent(notification.asset)}&executionId=${encodeURIComponent(notification.execution_id)}&status=${encodeURIComponent(notification.status)}`}
                        style={{
                          fontSize: 12,
                          color: "var(--text-body)",
                          fontWeight: 700,
                          textDecoration: "none",
                          border: "1px solid var(--surface-border)",
                          borderRadius: 8,
                          padding: "4px 8px",
                        }}
                      >
                        Execution
                      </Link>
                      <Link
                        href={`/workflow?asset=${encodeURIComponent(notification.asset)}&executionId=${encodeURIComponent(notification.execution_id)}`}
                        style={{
                          fontSize: 12,
                          color: "var(--text-strong)",
                          fontWeight: 700,
                          textDecoration: "none",
                          border: "1px solid var(--surface-border)",
                          borderRadius: 8,
                          padding: "4px 8px",
                        }}
                      >
                        Workflow
                      </Link>
                    </div>
                  </div>
                  <span style={badgeStyle(notification.level === "warning" ? "warning" : "info")}>{notification.level}</span>
                  <button
                    type="button"
                    onClick={() => {
                      void markNotificationRead(notification.notification_id);
                    }}
                    disabled={notification.is_read || notificationAction !== null}
                    style={{
                      border: "1px solid var(--surface-border)",
                      borderRadius: 8,
                      background: "var(--surface-soft)",
                      color: "var(--text-body)",
                      fontWeight: 700,
                      padding: "4px 10px",
                      cursor: notification.is_read || notificationAction !== null ? "not-allowed" : "pointer",
                      fontSize: 12,
                    }}
                  >
                    {notificationAction === notification.notification_id ? "Marking..." : "Mark read"}
                  </button>
                </div>
              ))}
            </div>
          ) : null}
        </section>

        <section style={panelStyle()}>
          <h2 style={{ margin: 0, color: "var(--text-strong)", fontSize: 24 }}>Watchlist</h2>
          <p style={{ margin: 0, color: "var(--text-muted)", fontSize: 13 }}>
            Open positions grouped by asset. Click an asset row to drill into execution/workflow context.
          </p>

          <ChartPanel
            title={
              <LearnTooltip explain={{ beginner: "This chart tracks open-position notional by asset over time for your watchlist.", intermediate: "Watchlist exposure chart: open notional by asset on inferred market timeline.", experienced: "Top-asset open notional trend in watchlist context. Use legend toggles to isolate assets.", expert: "Open-position notional series by asset over inferred timestamps from execution cadence." }}>
                Watchlist Exposure
              </LearnTooltip>
            }
            subtitle="Open-position trend by asset · session-aware hover context"
            controls={<TimeRangeBar value={timeRange} onChange={setTimeRange} />}
            legend={watchlistSeries.length > 0 ? <SeriesToggle series={watchlistSeries} hidden={hiddenSeries} onToggle={toggleSeries} /> : undefined}
          >
            <LineChart
              series={watchlistSeries.map((series) => ({ ...series, data: filterByRange(series.data) }))}
              hidden={hiddenSeries}
              height={220}
              yLabel="Notional"
              formatValue={(v) => `$${v >= 1000 ? `${(v / 1000).toFixed(1)}k` : v.toFixed(0)}`}
              formatTime={formatMarketTimeLabel}
              getTooltipContextRows={({ time, series }) => [
                { label: "Session", value: marketSessionLabel(time) },
                { label: "Range", value: timeRange },
                { label: "Assets", value: series.map((item) => item.label).join(", ") },
              ]}
            />
          </ChartPanel>

          {page.state === "ready" && watchlist.length === 0 && (
            <div
              style={{
                padding: 14,
                borderRadius: 12,
                border: "1px dashed var(--surface-border)",
                color: "var(--text-muted)",
                background: "var(--surface-soft)",
              }}
            >
              No open positions. Submit a workflow to populate the watchlist.
            </div>
          )}

          {page.state === "ready" && watchlist.length > 0 && (
            <div style={{ display: "grid", gap: 10 }}>
              <div
                data-rs="watchlist-header"
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr minmax(80px, 100px) minmax(80px, 100px) minmax(100px, 130px) minmax(140px, 160px)",
                  gap: 10,
                  padding: "8px 12px",
                  borderRadius: 10,
                  background: "var(--surface-soft)",
                  color: "var(--text-muted)",
                  fontSize: 12,
                  fontWeight: 700,
                  textTransform: "uppercase",
                  letterSpacing: 0.8,
                }}
              >
                <span>Asset</span>
                <span>Open Count</span>
                <span>Notional</span>
                  <span>
                    <LearnTooltip explain={{ beginner: "Status shows each trade's current stage, like submitted, accepted, or filled.", intermediate: "Execution lifecycle stage for each grouped asset row.", experienced: "Current lifecycle status mix per asset.", expert: "Distinct lifecycle states in row aggregation." }}>Statuses</LearnTooltip>
                  </span>
                  <span>
                    <LearnTooltip explain={{ beginner: "Actions are quick links to inspect this asset in Execution and Workflow.", intermediate: "Context actions jump to execution and workflow pages pre-filtered by asset.", experienced: "Navigation actions with asset and execution context parameters.", expert: "Deep-link actions using query params for execution/workflow context." }}>Actions</LearnTooltip>
                  </span>
              </div>

              {watchlist.map(({ asset, items }) => {
                const totalNotional = items.reduce((sum, i) => sum + i.notional, 0);
                const statuses = [...new Set(items.map((i) => i.status))].join(", ");
                const firstId = items[0].execution_id;
                return (
                  <div
                    data-rs="watchlist-row"
                    key={asset}
                    style={{
                      display: "grid",
                      gridTemplateColumns: "1fr minmax(80px, 100px) minmax(80px, 100px) minmax(100px, 130px) minmax(140px, 160px)",
                      gap: 10,
                      padding: "10px 12px",
                      borderRadius: 10,
                      border: "1px solid var(--surface-border)",
                      alignItems: "center",
                      fontSize: 13,
                      color: "var(--text-body)",
                    }}
                  >
                    <span style={{ fontWeight: 700 }}>{asset}</span>
                    <span>{items.length}</span>
                    <span>${totalNotional.toFixed(2)}</span>
                    <span>{statuses}</span>
                    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                      <Link
                        href={`/execution?asset=${encodeURIComponent(asset)}&executionId=${encodeURIComponent(firstId)}`}
                        style={{
                          fontSize: 12,
                          color: "var(--text-strong)",
                          fontWeight: 700,
                          textDecoration: "none",
                          border: "1px solid var(--surface-border)",
                          borderRadius: 8,
                          padding: "4px 8px",
                        }}
                      >
                        Execution
                      </Link>
                      <Link
                        href={`/workflow?asset=${encodeURIComponent(asset)}&executionId=${encodeURIComponent(firstId)}`}
                        style={{
                          fontSize: 12,
                          color: "var(--text-strong)",
                          fontWeight: 700,
                          textDecoration: "none",
                          border: "1px solid var(--surface-border)",
                          borderRadius: 8,
                          padding: "4px 8px",
                        }}
                      >
                        Workflow
                      </Link>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>

        <section style={panelStyle()}>
          <h2 style={{ margin: 0, color: "var(--text-strong)", fontSize: 22 }}>Active Alerts</h2>
          <p style={{ margin: 0, color: "var(--text-muted)", fontSize: 13 }}>
            Active alerts from backend rules; falls back to local derived alerts if backend list is unavailable.
          </p>

          {activeAlertsError ? (
            <div
              style={{
                padding: 12,
                borderRadius: 10,
                border: "1px solid var(--state-warning-border)",
                background: "var(--state-warning-soft)",
                color: "var(--state-warning)",
              }}
            >
              {activeAlertsError}
            </div>
          ) : null}

          {activeAlerts.length === 0 && fallbackDerivedAlerts.length === 0 && page.state === "ready" ? (
            <div
              style={{
                padding: 14,
                borderRadius: 12,
                border: "1px dashed var(--surface-border)",
                color: "var(--text-muted)",
                background: "var(--surface-soft)",
              }}
            >
              No active alerts. All tracked executions are in a stable state or no data yet.
            </div>
          ) : null}

          {activeAlerts.length > 0 ? (
            <div style={{ display: "grid", gap: 10 }}>
              {activeAlerts.map((alert) => (
                <div
                  data-rs="alert-row"
                  key={alert.alert_id}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "auto 1fr auto",
                    gap: 12,
                    padding: "12px 14px",
                    borderRadius: 12,
                    border: `1px solid ${alert.level === "warning" ? "var(--state-warning-border)" : "var(--state-info-border)"}`,
                    background: alert.level === "warning" ? "var(--state-warning-soft)" : "var(--state-info-soft)",
                    alignItems: "center",
                  }}
                >
                  <span style={badgeStyle(alert.level === "warning" ? "warning" : "info")}>{alert.level}</span>
                  <span style={{ fontSize: 13, color: "var(--text-body)" }}>{alert.message}</span>
                  <Link
                    href={`/execution?asset=${encodeURIComponent(alert.asset)}&executionId=${encodeURIComponent(alert.execution_id)}&status=${encodeURIComponent(alert.status)}`}
                    style={{
                      fontSize: 12,
                      color: "var(--text-strong)",
                      fontWeight: 700,
                      textDecoration: "none",
                      border: "1px solid var(--surface-border)",
                      borderRadius: 8,
                      padding: "5px 10px",
                      whiteSpace: "nowrap",
                    }}
                  >
                    View execution
                  </Link>
                </div>
              ))}
            </div>
          ) : null}

          {activeAlerts.length === 0 && fallbackDerivedAlerts.length > 0 ? (
            <div style={{ display: "grid", gap: 10 }}>
              {fallbackDerivedAlerts.map((alert) => (
                <div
                  data-rs="alert-row"
                  key={alert.id}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "auto 1fr auto",
                    gap: 12,
                    padding: "12px 14px",
                    borderRadius: 12,
                    border: `1px solid ${alert.level === "warning" ? "var(--state-warning-border)" : "var(--state-info-border)"}`,
                    background: alert.level === "warning" ? "var(--state-warning-soft)" : "var(--state-info-soft)",
                    alignItems: "center",
                  }}
                >
                  <span style={badgeStyle(alert.level)}>{alert.level}</span>
                  <span style={{ fontSize: 13, color: "var(--text-body)" }}>{alert.message}</span>
                  <Link
                    href={`/execution?asset=${encodeURIComponent(alert.asset)}&executionId=${encodeURIComponent(alert.executionId)}&status=${encodeURIComponent(alert.status)}`}
                    style={{
                      fontSize: 12,
                      color: "var(--text-strong)",
                      fontWeight: 700,
                      textDecoration: "none",
                      border: "1px solid var(--surface-border)",
                      borderRadius: 8,
                      padding: "5px 10px",
                      whiteSpace: "nowrap",
                    }}
                  >
                    View execution
                  </Link>
                </div>
              ))}
            </div>
          ) : null}
        </section>

        <section style={panelStyle()}>
          <h2 style={{ margin: 0, color: "var(--text-strong)", fontSize: 22 }}>Alert Rules</h2>
          <p style={{ margin: 0, color: "var(--text-muted)", fontSize: 13 }}>
            Backend-backed alert rules with lifecycle actions (acknowledge and snooze).
          </p>

          {ruleError ? (
            <div
              style={{
                padding: 12,
                borderRadius: 10,
                border: "1px solid var(--state-warning-border)",
                background: "var(--state-warning-soft)",
                color: "var(--state-warning)",
              }}
            >
              {ruleError}
            </div>
          ) : null}

          <div
            data-rs="rule-form"
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr auto",
              gap: 10,
              alignItems: "end",
            }}
          >
            <label style={{ display: "grid", gap: 6, fontSize: 13, fontWeight: 600, color: "var(--text-body)" }}>
              Asset
              <input
                value={ruleAsset}
                onChange={(e) => setRuleAsset(e.target.value)}
                placeholder="e.g. EURUSD"
                style={inputStyle}
              />
            </label>
            <label style={{ display: "grid", gap: 6, fontSize: 13, fontWeight: 600, color: "var(--text-body)" }}>
              <LearnTooltip
                explain={{
                  beginner: "The condition is a rule that triggers an alert — like 'status = submitted'. When an execution matches this rule, you get notified.",
                  intermediate: "Alert condition: a simple expression matched against execution state. e.g. 'status = submitted'.",
                  experienced: "Condition expression matched against execution fields. Supported: equality checks on status, asset, side.",
                  expert: "condition: string expression. Evaluated server-side against execution snapshot. Format: 'field = value'.",
                }}
              >
                Condition
              </LearnTooltip>
              <input
                value={ruleCondition}
                onChange={(e) => setRuleCondition(e.target.value)}
                placeholder="e.g. status = submitted"
                style={inputStyle}
              />
            </label>
            <button
              type="button"
              onClick={() => {
                void addRule();
              }}
              disabled={isSubmittingRule}
              style={{
                border: 0,
                borderRadius: 12,
                padding: "10px 16px",
                background: "var(--accent-primary)",
                color: "var(--surface-soft)",
                fontWeight: 700,
                cursor: isSubmittingRule ? "not-allowed" : "pointer",
                fontSize: 14,
                opacity: isSubmittingRule ? 0.7 : 1,
              }}
            >
              {isSubmittingRule ? "Adding..." : "Add rule"}
            </button>
          </div>

          {rules.length === 0 ? (
            <div
              style={{
                padding: 14,
                borderRadius: 12,
                border: "1px dashed var(--surface-border)",
                color: "var(--text-muted)",
                background: "var(--surface-soft)",
              }}
            >
              No persisted alert rules found. Add a rule above.
            </div>
          ) : (
            <div style={{ display: "grid", gap: 8 }}>
              {rules.map((rule) => (
                <div
                  data-rs="rule-row"
                  key={rule.rule_id}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "minmax(80px, 120px) 1fr minmax(90px, 130px) auto auto",
                    gap: 10,
                    padding: "10px 14px",
                    borderRadius: 12,
                    border: "1px solid var(--surface-border)",
                    alignItems: "center",
                    fontSize: 13,
                    color: "var(--text-body)",
                  }}
                >
                  <span style={{ fontWeight: 700 }}>{rule.asset}</span>
                  <span>{rule.condition}</span>
                  <span style={badgeStyle(rule.status === "acknowledged" ? "warning" : "info")}>{rule.status}</span>
                  <button
                    type="button"
                    onClick={() => {
                      void acknowledgeRule(rule.rule_id);
                    }}
                    disabled={ruleAction !== null}
                    style={{
                      border: "1px solid var(--surface-border)",
                      borderRadius: 8,
                      background: "var(--surface-soft)",
                      color: "var(--text-strong)",
                      fontWeight: 700,
                      padding: "4px 10px",
                      cursor: ruleAction ? "not-allowed" : "pointer",
                      fontSize: 12,
                    }}
                  >
                    {ruleAction === `ack:${rule.rule_id}` ? "Acknowledging..." : "Acknowledge"}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      void snoozeRule(rule.rule_id);
                    }}
                    disabled={ruleAction !== null}
                    style={{
                      border: "1px solid var(--surface-border)",
                      borderRadius: 8,
                      background: "var(--surface-soft)",
                      color: "var(--text-strong)",
                      fontWeight: 700,
                      padding: "4px 10px",
                      cursor: ruleAction ? "not-allowed" : "pointer",
                      fontSize: 12,
                    }}
                  >
                    {ruleAction === `snooze:${rule.rule_id}` ? "Snoozing..." : "Snooze 30m"}
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>
    </PageShell>
  );
}
