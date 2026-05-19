"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { CompactBars } from "./CompactBars";
import { InfographicRing } from "./InfographicRing";
import { JournalAttentionWidget } from "./JournalAttentionWidget";
import { LearnTooltip } from "./LearnTooltip";
import { OperatorNotificationSurface } from "./OperatorNotificationSurface";
import { ChartPanel, LineChart, SeriesToggle, TimeRangeBar, type ChartSeries, type TimeRange } from "./chart";
import { DashboardAlertsSection } from "./dashboard/DashboardAlertsSection";
import { DashboardChartsSection } from "./dashboard/DashboardChartsSection";
import { DashboardMetricsSection } from "./dashboard/DashboardMetricsSection";
import { useLivePolling } from "../lib/hooks/useLivePolling";
import styles from "../styles/pages/dashboard.module.css";
import {
  listActiveAlerts,
  listAlertNotifications,
  listAlertRules,
  listPaperExecutions,
  runAutoPaperTrader,
  getAutoPaperHistory,
  getKillSwitch,
  activateKillSwitch,
  deactivateKillSwitch,
  type WorkerResultResponse,
  type RunHistoryEntry,
  type KillSwitchResponse,
  type ActiveAlertResponse,
  type AlertNotificationResponse,
  type AlertRuleResponse,
} from "../lib/api";
import { formatMarketTimeLabel, inferExecutionTimestamps, marketSessionLabel } from "../lib/chartTime";
import type { PaperExecutionResponse } from "../lib/types";

const ASSET_COLORS = [
  "var(--chart-series-1)",
  "var(--chart-series-2)",
  "var(--chart-series-3)",
  "var(--chart-series-4)",
  "var(--chart-series-5)",
];

type DashboardPayload = {
  executions: PaperExecutionResponse[];
  activeAlerts: ActiveAlertResponse[];
  notifications: AlertNotificationResponse[];
  rules: AlertRuleResponse[];
};

type DashboardState =
  | { state: "loading"; data: null; error: null }
  | { state: "ready"; data: DashboardPayload; error: null }
  | { state: "error"; data: null; error: string };

const OPEN_STATUSES = new Set(["new", "submitted", "accepted", "filled"]);
const CLOSED_STATUSES = new Set(["closed", "rejected", "canceled", "expired"]);
const ACTIONABLE_STATUSES = new Set(["new", "submitted", "rejected"]);
const MAX_OPEN_POSITIONS = 6;
const AUTO_PAPER_INTERVAL_OPTIONS_MINUTES = [5, 10, 15, 30, 60];
const AUTO_PAPER_DEFAULT_INTERVAL_MINUTES = 15;
const AUTO_PAPER_SETTINGS_KEY = "dashboard:autoPaperSettings:v2";
const AUTO_PAPER_NEXT_RUN_AT_KEY = "dashboard:autoPaperNextRunAt:v1";
const EXECUTION_MODE_OPTIONS = [
  { value: "paper", label: "Paper account" },
  { value: "confirm_live", label: "Confirm before live" },
  { value: "auto_live", label: "Auto live" },
] as const;
type GlobalExecutionMode = "paper" | "confirm_live" | "auto_live";
export const GLOBAL_EXECUTION_MODE_KEY = "dashboard:globalExecutionMode:v1";

function formatMoney(value: number): string {
  return `$${value.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function compactId(value: string): string {
  if (value.length <= 14) return value;
  return `${value.slice(0, 8)}...${value.slice(-4)}`;
}

function filterByRange(data: { t: string; v: number }[], range: TimeRange): { t: string; v: number }[] {
  if (range === "ALL" || data.length === 0) return data;

  const latest = Date.parse(data[data.length - 1].t);
  if (!Number.isFinite(latest)) return data;

  const lookbackMs: Record<Exclude<TimeRange, "ALL">, number> = {
    "1D": 24 * 60 * 60 * 1000,
    "1W": 7 * 24 * 60 * 60 * 1000,
    "1M": 30 * 24 * 60 * 60 * 1000,
    "3M": 90 * 24 * 60 * 60 * 1000,
    "1Y": 365 * 24 * 60 * 60 * 1000,
  };

  const minTime = latest - lookbackMs[range];
  const filtered = data.filter((point) => Date.parse(point.t) >= minTime);
  return filtered.length > 1 ? filtered : data;
}

export function PersonalDashboard() {
  const [dashboard, setDashboard] = useState<DashboardState>({ state: "loading", data: null, error: null });
  const [autoPaperRunning, setAutoPaperRunning] = useState(false);
  const [autoPaperStatus, setAutoPaperStatus] = useState<string | null>(null);
  const [autoPaperAutoEnabled, setAutoPaperAutoEnabled] = useState(false);
  const [autoPaperIntervalMinutes, setAutoPaperIntervalMinutes] = useState(AUTO_PAPER_DEFAULT_INTERVAL_MINUTES);
  const [lastAutoPaperResult, setLastAutoPaperResult] = useState<WorkerResultResponse | null>(null);
  const [nextAutoPaperRunAt, setNextAutoPaperRunAt] = useState<Date | null>(null);
  const [secondsUntilAutoRun, setSecondsUntilAutoRun] = useState<number | null>(null);
  const [killSwitch, setKillSwitch] = useState<KillSwitchResponse | null>(null);
  const [killSwitchLoading, setKillSwitchLoading] = useState(false);
  const [runHistory, setRunHistory] = useState<RunHistoryEntry[]>([]);

  const [autoPaperSettingsLoaded, setAutoPaperSettingsLoaded] = useState(false);
  const [globalExecutionMode, setGlobalExecutionMode] = useState<GlobalExecutionMode>("paper");

  async function loadDashboard() {
    setDashboard((prev) => {
      if (prev.data !== null) return prev; // background refresh — don't flash loading state
      return { state: "loading", data: null, error: null };
    });
    try {
      const [executions, activeAlerts, notifications, rules] = await Promise.all([
        listPaperExecutions({ limit: 50, offset: 0 }),
        listActiveAlerts(),
        listAlertNotifications(),
        listAlertRules(),
      ]);

      setDashboard({
        state: "ready",
        data: { executions, activeAlerts, notifications, rules },
        error: null,
      });
    } catch (error) {
      setDashboard((prev) => {
        if (prev.data !== null) return prev; // background refresh failure — keep showing stale data
        return {
          state: "error",
          data: null,
          error: error instanceof Error ? error.message : "Failed to load personal dashboard data.",
        };
      });
    }
  }

  useEffect(() => {
    void loadDashboard();
  }, []);

  useLivePolling(() => loadDashboard(), 12000, { enabled: true, runImmediately: false });

  useEffect(() => {
    if (typeof window === "undefined") return;
    let loadedAutoEnabled = false;
    let loadedInterval = AUTO_PAPER_DEFAULT_INTERVAL_MINUTES;
    let loadedNextRunAt: Date | null = null;
    let loadedMode: GlobalExecutionMode = "paper";

    try {
      const raw = window.localStorage.getItem(AUTO_PAPER_SETTINGS_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as {
          autoEnabled?: boolean;
          intervalMinutes?: number;
        };
        if (typeof parsed.autoEnabled === "boolean") {
          loadedAutoEnabled = parsed.autoEnabled;
        }
        if (
          typeof parsed.intervalMinutes === "number"
          && AUTO_PAPER_INTERVAL_OPTIONS_MINUTES.includes(parsed.intervalMinutes)
        ) {
          loadedInterval = parsed.intervalMinutes;
        }
      }
      const nextRunRaw = window.localStorage.getItem(AUTO_PAPER_NEXT_RUN_AT_KEY);
      if (nextRunRaw) {
        const nextRunTs = Date.parse(nextRunRaw);
        if (Number.isFinite(nextRunTs) && nextRunTs > Date.now()) {
          loadedNextRunAt = new Date(nextRunTs);
        }
      }
      const savedMode = window.localStorage.getItem(GLOBAL_EXECUTION_MODE_KEY);
      if (savedMode === "paper" || savedMode === "confirm_live" || savedMode === "auto_live") {
        loadedMode = savedMode;
      }
    } catch {
      // Ignore invalid persisted state and continue with defaults.
    }

    setAutoPaperAutoEnabled(loadedAutoEnabled);
    setAutoPaperIntervalMinutes(loadedInterval);
    setNextAutoPaperRunAt(loadedNextRunAt);
    setGlobalExecutionMode(loadedMode);
    setAutoPaperSettingsLoaded(true);
  }, []);

  useEffect(() => {
    if (!autoPaperSettingsLoaded) return;
    if (typeof window === "undefined") return;
    window.localStorage.setItem(
      AUTO_PAPER_SETTINGS_KEY,
      JSON.stringify({
        autoEnabled: autoPaperAutoEnabled,
        intervalMinutes: autoPaperIntervalMinutes,
      }),
    );
    window.localStorage.setItem(GLOBAL_EXECUTION_MODE_KEY, globalExecutionMode);
  }, [autoPaperSettingsLoaded, autoPaperAutoEnabled, autoPaperIntervalMinutes, globalExecutionMode]);

  useEffect(() => {
    if (!nextAutoPaperRunAt) {
      setSecondsUntilAutoRun(null);
      return;
    }
    const updateCountdown = () => {
      const diffMs = nextAutoPaperRunAt.getTime() - Date.now();
      setSecondsUntilAutoRun(Math.max(0, Math.floor(diffMs / 1000)));
    };
    updateCountdown();
    const timer = window.setInterval(updateCountdown, 1000);
    return () => {
      window.clearInterval(timer);
    };
  }, [nextAutoPaperRunAt]);

  function scheduleNextAutoRun(intervalMinutes: number) {
    const next = new Date(Date.now() + intervalMinutes * 60 * 1000);
    setNextAutoPaperRunAt(next);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(AUTO_PAPER_NEXT_RUN_AT_KEY, next.toISOString());
    }
    return next;
  }

  async function loadKillSwitchAndHistory() {
    try {
      const [ks, hist] = await Promise.all([getKillSwitch(), getAutoPaperHistory(5)]);
      setKillSwitch(ks);
      setRunHistory(hist);
    } catch {
      // non-critical — ignore
    }
  }

  useEffect(() => {
    void loadKillSwitchAndHistory();
  }, []);

  useLivePolling(() => loadKillSwitchAndHistory(), 12000, { enabled: true, runImmediately: false });

  async function handleToggleKillSwitch() {
    if (killSwitchLoading) return;
    setKillSwitchLoading(true);
    try {
      const updated = killSwitch?.kill_switch_active
        ? await deactivateKillSwitch()
        : await activateKillSwitch();
      setKillSwitch(updated);
    } catch {
      // ignore
    } finally {
      setKillSwitchLoading(false);
    }
  }

  async function executeAutoPaperBatch(source: "manual" | "auto") {
    if (autoPaperRunning) return;

    setAutoPaperRunning(true);
    setAutoPaperStatus(
      source === "manual"
        ? "Submitting auto-paper batch..."
        : "Auto cadence triggered: running auto-paper batch...",
    );
    try {
      const apiSource = source === "auto" ? "scheduled" : "manual";
      const result = await runAutoPaperTrader(apiSource);
      setLastAutoPaperResult(result);
      setAutoPaperStatus(`${result.status}: ${result.message}`);
      await Promise.all([loadDashboard(), loadKillSwitchAndHistory()]);
    } catch (error) {
      setAutoPaperStatus(error instanceof Error ? error.message : "Failed to run auto-paper batch.");
    } finally {
      setAutoPaperRunning(false);
    }
  }

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (!autoPaperSettingsLoaded) return;

    if (!autoPaperAutoEnabled) {
      setNextAutoPaperRunAt(null);
      window.localStorage.removeItem(AUTO_PAPER_NEXT_RUN_AT_KEY);
      return;
    }

    // Only seed next-run once (or after it has been cleared), never on remount.
    const existing = window.localStorage.getItem(AUTO_PAPER_NEXT_RUN_AT_KEY);
    if (!existing) {
      scheduleNextAutoRun(autoPaperIntervalMinutes);
    }

    const syncTimer = window.setInterval(() => {
      const raw = window.localStorage.getItem(AUTO_PAPER_NEXT_RUN_AT_KEY);
      if (!raw) {
        setNextAutoPaperRunAt(null);
        return;
      }
      const ts = Date.parse(raw);
      if (!Number.isFinite(ts)) {
        setNextAutoPaperRunAt(null);
        return;
      }
      setNextAutoPaperRunAt(new Date(ts));
    }, 1000);

    return () => {
      window.clearInterval(syncTimer);
    };
  }, [autoPaperSettingsLoaded, autoPaperAutoEnabled, autoPaperIntervalMinutes]);

  async function handleRunAutoPaperBatch() {
    await executeAutoPaperBatch("manual");
  }

  function formatAutoCountdown(value: number | null): string {
    if (value === null) return "--:--";
    const minutes = Math.floor(value / 60)
      .toString()
      .padStart(2, "0");
    const seconds = Math.floor(value % 60)
      .toString()
      .padStart(2, "0");
    return `${minutes}:${seconds}`;
  }

  const metrics = useMemo(() => {
    if (dashboard.state !== "ready") {
      return {
        totalExecutions: 0,
        openPositions: [] as PaperExecutionResponse[],
        pendingItems: [] as PaperExecutionResponse[],
        recentExecutions: [] as PaperExecutionResponse[],
        unreadNotifications: 0,
        activeAlerts: 0,
        ruleCount: 0,
        openNotional: 0,
        closedNotional: 0,
        longOpenNotional: 0,
        shortOpenNotional: 0,
        exposureByAsset: [] as Array<{ asset: string; value: number }>,
        statusCounts: {
          open: 0,
          closed: 0,
          rejected: 0,
          pending: 0,
        },
      };
    }

    const executions = dashboard.data.executions;
    const openPositions = executions.filter((item) => OPEN_STATUSES.has(item.status.toLowerCase()));
    const closedExecutions = executions.filter((item) => CLOSED_STATUSES.has(item.status.toLowerCase()));
    const pendingItems = executions.filter((item) => ACTIONABLE_STATUSES.has(item.status.toLowerCase()));
    const recentExecutions = executions.slice(0, 8);

    const unreadNotifications = dashboard.data.notifications.filter((item) => !item.is_read).length;
    const activeAlerts = dashboard.data.activeAlerts.length;
    const ruleCount = dashboard.data.rules.length;

    let openNotional = 0;
    let closedNotional = 0;
    let longOpenNotional = 0;
    let shortOpenNotional = 0;

    const byAsset: Record<string, number> = {};
    let rejected = 0;

    for (const execution of executions) {
      const status = execution.status.toLowerCase();
      const side = execution.side.toLowerCase();

      if (OPEN_STATUSES.has(status)) {
        openNotional += execution.notional;
        byAsset[execution.asset] = (byAsset[execution.asset] ?? 0) + execution.notional;
        if (side === "buy" || side === "long") longOpenNotional += execution.notional;
        if (side === "sell" || side === "short") shortOpenNotional += execution.notional;
      }

      if (CLOSED_STATUSES.has(status)) {
        closedNotional += execution.notional;
      }

      if (status === "rejected") {
        rejected += 1;
      }
    }

    const exposureByAsset = Object.entries(byAsset)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 5)
      .map(([asset, value]) => ({ asset, value }));

    return {
      totalExecutions: executions.length,
      openPositions,
      pendingItems,
      recentExecutions,
      unreadNotifications,
      activeAlerts,
      ruleCount,
      openNotional,
      closedNotional,
      longOpenNotional,
      shortOpenNotional,
      exposureByAsset,
      statusCounts: {
        open: openPositions.length,
        closed: closedExecutions.length,
        rejected,
        pending: pendingItems.length,
      },
    };
  }, [dashboard]);

  const riskSnapshot = useMemo(() => {
    const utilizationPct = (metrics.openPositions.length / MAX_OPEN_POSITIONS) * 100;
    const topAsset = metrics.exposureByAsset[0];
    const topAssetPct = metrics.openNotional > 0 ? (topAsset?.value ?? 0) / metrics.openNotional : 0;

    return {
      utilizationPct,
      topAssetName: topAsset?.asset ?? "n/a",
      topAssetPct,
      directionalDelta: metrics.longOpenNotional - metrics.shortOpenNotional,
    };
  }, [metrics]);

  const [hiddenSeries, setHiddenSeries] = useState<Set<string>>(new Set());
  const [movementHiddenSeries, setMovementHiddenSeries] = useState<Set<string>>(new Set());
  const [timeRange, setTimeRange] = useState<TimeRange>("1M");

  const notionalChartSeries = useMemo((): ChartSeries[] => {
    if (dashboard.state !== "ready") return [];
    const executions = dashboard.data.executions;
    const inferredTimes = inferExecutionTimestamps(executions);
    const assetCount: Record<string, number> = {};
    for (const ex of executions) {
      assetCount[ex.asset] = (assetCount[ex.asset] ?? 0) + 1;
    }
    const topAssets = Object.entries(assetCount)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 5)
      .map(([asset]) => asset);

    return topAssets.map((asset, colorIdx) => {
      const assetExecs = executions
        .map((ex, idx) => ({ ex, idx }))
        .filter(({ ex }) => ex.asset === asset);
      return {
        id: asset,
        label: asset,
        color: ASSET_COLORS[colorIdx % ASSET_COLORS.length],
        data: assetExecs.map(({ ex, idx }) => ({
          t: inferredTimes[idx] ?? new Date().toISOString(),
          v: ex.notional,
        })),
      };
    });
  }, [dashboard]);

  const portfolioMovementSeries = useMemo((): ChartSeries[] => {
    if (dashboard.state !== "ready") return [];
    const executions = [...dashboard.data.executions];
    const inferredTimes = inferExecutionTimestamps(executions);

    const chronological = executions
      .map((execution, index) => ({ execution, t: inferredTimes[index] ?? new Date().toISOString() }))
      .sort((a, b) => Date.parse(a.t) - Date.parse(b.t));

    const raw = chronological.map((item) => ({ t: item.t, v: item.execution.notional }));
    const trend = raw.map((point, index) => {
      const window = raw.slice(Math.max(0, index - 4), index + 1);
      const avg = window.reduce((sum, value) => sum + value.v, 0) / window.length;
      return { t: point.t, v: avg };
    });

    return [
      { id: "notional_raw", label: "Execution notional", color: "var(--chart-series-1)", data: filterByRange(raw, timeRange) },
      { id: "notional_trend", label: "5-point trend", color: "var(--chart-series-2)", dashed: true, data: filterByRange(trend, timeRange) },
    ];
  }, [dashboard, timeRange]);

  function toggleSeries(id: string) {
    setHiddenSeries((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleMovementSeries(id: string) {
    setMovementHiddenSeries((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  const attentionItems = useMemo(() => {
    const items: Array<{ text: string; tone: string; href: string }> = [];

    if (metrics.unreadNotifications > 0) {
      items.push({
        text: `${metrics.unreadNotifications} unread notifications need triage`,
        tone: "var(--state-danger)",
        href: "/alerts",
      });
    }

    if (metrics.statusCounts.pending > 0) {
      items.push({
        text: `${metrics.statusCounts.pending} workflow items are pending review`,
        tone: "var(--state-warning)",
        href: "/workflow",
      });
    }

    if (metrics.statusCounts.rejected > 0) {
      items.push({
        text: `${metrics.statusCounts.rejected} rejected executions require follow-up`,
        tone: "var(--state-danger)",
        href: "/execution?status=rejected",
      });
    }

    if (metrics.activeAlerts > 0) {
      items.push({
        text: `${metrics.activeAlerts} active alerts are still open`,
        tone: "var(--state-info)",
        href: "/alerts",
      });
    }

    if (riskSnapshot.utilizationPct >= 100) {
      items.push({
        text: "Open-position cap reached (6/6)",
        tone: "var(--state-danger)",
        href: "/risk",
      });
    }

    if (items.length === 0) {
      items.push({
        text: "No urgent blockers right now. You are clear to monitor and execute.",
        tone: "var(--state-success)",
        href: "/execution",
      });
    }

    return items.slice(0, 5);
  }, [metrics, riskSnapshot]);

  const isLoading = dashboard.state === "loading";
  const isError = dashboard.state === "error";
  const isEmpty = dashboard.state === "ready" && dashboard.data.executions.length === 0;

  return (
    <main className={styles.shell}>
      <div className={styles.content}>
        <DashboardAlertsSection
          attentionItems={attentionItems}
          onRefresh={() => { void loadDashboard(); }}
        />

        <DashboardMetricsSection metrics={metrics} formatMoney={formatMoney} />

        {isLoading ? (
          <section className={`${styles.panel} ${styles.statePanel}`}>
            <p className={styles.stateMessage}>Loading personal dashboard...</p>
          </section>
        ) : null}

        {isError ? (
          <section className={`${styles.panel} ${styles.statePanel}`}>
            <div className={`${styles.stateMessage} ${styles.errorMessage}`}>
              {dashboard.state === "error" ? dashboard.error : "Unknown dashboard error"}
            </div>
          </section>
        ) : null}

        {isEmpty ? (
          <section className={`${styles.panel} ${styles.statePanel}`}>
            <div className={`${styles.stateMessage} ${styles.emptyMessage}`}>
              No executions yet. Run workflow or execution actions to populate your cockpit.
            </div>
          </section>
        ) : null}

        {!isLoading && !isError ? (
          <>
            <DashboardChartsSection
              notionalChartSeries={notionalChartSeries}
              portfolioMovementSeries={portfolioMovementSeries}
              hiddenSeries={hiddenSeries}
              movementHiddenSeries={movementHiddenSeries}
              onToggleSeries={toggleSeries}
              onToggleMovementSeries={toggleMovementSeries}
              timeRange={timeRange}
              onTimeRangeChange={setTimeRange}
            />

            <section data-rs="dashboard-split" className={styles.splitGrid}>
              <article className={styles.panel}>
                <div className={styles.panelHeader}>
                  <h2 className={styles.panelTitle}>
                    <LearnTooltip
                      explain={{
                        beginner: "Open Positions are trades that are still active and not fully closed.",
                        intermediate: "Open positions include new/submitted/accepted/filled lifecycle states.",
                        experienced: "Open inventory table filtered by live statuses for active management.",
                        expert: "OPEN_STATUSES set membership indicates live position inventory.",
                      }}
                    >
                      Open Positions
                    </LearnTooltip>
                  </h2>
                  <Link href="/execution" className={styles.panelLink}>
                    Open execution workspace
                  </Link>
                </div>

                {metrics.openPositions.length === 0 ? (
                  <p className={styles.stateMessage}>No open positions right now.</p>
                ) : (
                  <div className={styles.stack}>
                    {metrics.openPositions.slice(0, 7).map((position) => (
                      <div data-rs="position-row" key={position.execution_id} className={styles.positionRow}>
                        <span className={styles.monoId}>{compactId(position.execution_id)}</span>
                        <span className={styles.assetText}>{position.asset}</span>
                        <span className={position.side.toLowerCase().includes("sell") ? styles.sideSell : styles.sideBuy}>
                          {position.side}
                        </span>
                        <span className={styles.notionalText}>{formatMoney(position.notional)}</span>
                        <span className={styles.mutedTiny}>{position.status}</span>
                      </div>
                    ))}
                  </div>
                )}
              </article>

              <article className={styles.panel}>
                <h2 className={styles.panelTitle}>P&L Snapshot</h2>
                <p className={styles.bodyText}>
                  Realized and unrealized P&L is not exposed in current payloads, so these are notional-based proxies.
                </p>
                <div data-rs="two-col" className={styles.pnlGrid}>
                  <div className={styles.miniStat}>
                    <span className={styles.miniLabel}>Open exposure</span>
                    <strong className={`${styles.miniValue} ${styles.valueWarning}`}>
                      {formatMoney(metrics.openNotional)}
                    </strong>
                  </div>
                  <div className={styles.miniStat}>
                    <span className={styles.miniLabel}>Closed book size</span>
                    <strong className={`${styles.miniValue} ${styles.valueWarning}`}>
                      {formatMoney(metrics.closedNotional)}
                    </strong>
                  </div>
                  <div className={styles.miniStat}>
                    <span className={styles.miniLabel}>Long exposure</span>
                    <strong className={`${styles.miniValue} ${styles.valueSuccess}`}>
                      {formatMoney(metrics.longOpenNotional)}
                    </strong>
                  </div>
                  <div className={styles.miniStat}>
                    <span className={styles.miniLabel}>Short exposure</span>
                    <strong className={`${styles.miniValue} ${styles.valueDanger}`}>
                      {formatMoney(metrics.shortOpenNotional)}
                    </strong>
                  </div>
                </div>
              </article>
            </section>

            <section data-rs="two-col" className={styles.twoColumnGrid}>
              <article className={styles.panel}>
                <div className={styles.panelHeader}>
                  <h2 className={styles.panelTitle}>Approvals and Workflow Lane</h2>
                  <div className={styles.linkGroup}>
                    <Link href="/workflow" className={styles.panelLink}>
                      Workflow
                    </Link>
                    <Link href="/approvals" className={styles.panelLink}>
                      Approvals
                    </Link>
                  </div>
                </div>

                <div className={styles.statsList}>
                  <div className={styles.statsRow}>
                    <span>Pending workflow items</span>
                    <strong className={styles.statsValueWarning}>{metrics.statusCounts.pending}</strong>
                  </div>
                  <div className={styles.statsRow}>
                    <span>Rejected requiring review</span>
                    <strong className={styles.statsValueDanger}>{metrics.statusCounts.rejected}</strong>
                  </div>
                  <div className={styles.statsRow}>
                    <span>Open position capacity</span>
                    <strong className={styles.statsValueSuccess}>
                      {metrics.openPositions.length}/{MAX_OPEN_POSITIONS}
                    </strong>
                  </div>
                </div>

                <CompactBars
                  title="Execution activity"
                  subtitle="Recent status mix"
                  items={[
                    { label: "Open", value: metrics.statusCounts.open, color: "var(--state-success)" },
                    { label: "Closed", value: metrics.statusCounts.closed, color: "var(--state-info)" },
                    { label: "Rejected", value: metrics.statusCounts.rejected, color: "var(--state-danger)" },
                    { label: "Pending", value: metrics.statusCounts.pending, color: "var(--state-warning)" },
                  ]}
                />
              </article>

              <article className={styles.panel}>
                <h2 className={styles.panelTitle}>Trading Control Panel</h2>
                <p className={styles.bodyText}>
                  Batch controls for routing opportunities into paper execution with one action.
                </p>

                <div className={styles.tradeAutoControls}>
                  <label htmlFor="global-execution-mode" className={styles.controlLabel}>
                    Execution mode
                  </label>
                  <select
                    id="global-execution-mode"
                    className={styles.tradeSelect}
                    value={globalExecutionMode}
                    onChange={(event) => {
                      setGlobalExecutionMode(event.target.value as GlobalExecutionMode);
                    }}
                  >
                    {EXECUTION_MODE_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>

                  <label htmlFor="auto-paper-interval" className={styles.controlLabel} style={{ marginTop: "0.5rem" }}>
                    Auto batch cadence
                  </label>
                  <select
                    id="auto-paper-interval"
                    className={styles.tradeSelect}
                    value={autoPaperIntervalMinutes}
                    onChange={(event) => {
                      setAutoPaperIntervalMinutes(Number(event.target.value));
                    }}
                  >
                    {AUTO_PAPER_INTERVAL_OPTIONS_MINUTES.map((minutes) => (
                      <option key={minutes} value={minutes}>
                        Every {minutes} min
                      </option>
                    ))}
                  </select>

                  <button
                    type="button"
                    className={autoPaperAutoEnabled ? styles.tradeActionButtonSecondary : styles.tradeActionButton}
                    onClick={() => {
                      setAutoPaperAutoEnabled((previous) => !previous);
                    }}
                    disabled={autoPaperRunning}
                  >
                    {autoPaperAutoEnabled ? "Pause Auto Paper" : "Resume Auto Paper"}
                  </button>
                </div>

                <div className={styles.tradeButtonGroup}>
                  <button
                    type="button"
                    className={styles.tradeActionButton}
                    onClick={() => {
                      void handleRunAutoPaperBatch();
                    }}
                    disabled={autoPaperRunning}
                  >
                    {autoPaperRunning ? "Running Auto Paper Batch..." : "Auto Trade Paper Stock (Batch)"}
                  </button>

                  <Link href="/workflow" className={styles.tradeActionButtonSecondary}>
                    Workflow Queue
                  </Link>

                  <Link href="/execution" className={styles.tradeActionButtonSecondary}>
                    Manual Paper Execution
                  </Link>

                  <Link href="/approvals" className={styles.tradeActionButtonSecondary}>
                    Approval Controls
                  </Link>
                </div>

                <div className={styles.tradeStatusCard}>
                  <div className={styles.statsRow}>
                    <span>Execution mode</span>
                    <strong className={globalExecutionMode === "paper" ? styles.statsValueWarning : styles.statsValueDanger}>
                      {EXECUTION_MODE_OPTIONS.find((o) => o.value === globalExecutionMode)?.label ?? globalExecutionMode}
                    </strong>
                  </div>
                  <div className={styles.statsRow}>
                    <span>Auto mode</span>
                    <strong className={autoPaperAutoEnabled ? styles.statsValueSuccess : styles.statsValueDanger}>
                      {autoPaperAutoEnabled ? "Running" : "Paused"}
                    </strong>
                  </div>
                  <div className={styles.statsRow}>
                    <span>Cadence</span>
                    <strong className={styles.statsValueWarning}>Every {autoPaperIntervalMinutes} min</strong>
                  </div>
                  <div className={styles.statsRow}>
                    <span>Next auto run</span>
                    <strong className={styles.statsValueWarning}>{formatAutoCountdown(secondsUntilAutoRun)}</strong>
                  </div>
                  <div className={styles.statsRow}>
                    <span>Last run status</span>
                    <strong className={styles.statsValueSuccess}>{lastAutoPaperResult?.status ?? "n/a"}</strong>
                  </div>
                  <p className={styles.statusMessage}>
                    {lastAutoPaperResult
                      ? `${lastAutoPaperResult.message} (${formatMarketTimeLabel(lastAutoPaperResult.finished_at)})`
                      : "No auto-paper run recorded in this session yet."}
                  </p>
                </div>

                {/* Kill-switch panel */}
                <div className={styles.tradeStatusCard}>
                  <div className={styles.statsRow}>
                    <span>Kill switch</span>
                    <strong className={killSwitch?.kill_switch_active ? styles.statsValueDanger : styles.statsValueSuccess}>
                      {killSwitch === null ? "…" : killSwitch.kill_switch_active ? "ACTIVE — trading halted" : "Inactive"}
                    </strong>
                  </div>
                  <button
                    className={killSwitch?.kill_switch_active ? styles.tradeActionButton : styles.tradeActionButtonSecondary}
                    onClick={() => void handleToggleKillSwitch()}
                    disabled={killSwitchLoading || killSwitch === null}
                    style={{ marginTop: "0.5rem", width: "100%" }}
                  >
                    {killSwitchLoading
                      ? "Updating…"
                      : killSwitch?.kill_switch_active
                        ? "Deactivate Kill Switch (resume trading)"
                        : "Activate Kill Switch (halt trading)"}
                  </button>
                </div>

                {/* Recent run history */}
                {runHistory.length > 0 && (
                  <div className={styles.tradeStatusCard}>
                    <p style={{ fontWeight: 600, marginBottom: "0.4rem" }}>Recent runs</p>
                    <table style={{ width: "100%", fontSize: "0.75rem", borderCollapse: "collapse" }}>
                      <thead>
                        <tr>
                          <th style={{ textAlign: "left", paddingBottom: "0.25rem" }}>Time</th>
                          <th style={{ textAlign: "left", paddingBottom: "0.25rem" }}>Status</th>
                          <th style={{ textAlign: "left", paddingBottom: "0.25rem" }}>Message</th>
                        </tr>
                      </thead>
                      <tbody>
                        {runHistory.map((entry, i) => (
                          <tr key={i} style={{ borderTop: "1px solid var(--surface-border)" }}>
                            <td style={{ padding: "0.2rem 0.4rem 0.2rem 0", whiteSpace: "nowrap" }}>
                              {formatMarketTimeLabel(entry.finished_at)}
                            </td>
                            <td style={{ padding: "0.2rem 0.4rem", whiteSpace: "nowrap" }}>
                              <span className={entry.status === "success" ? styles.statsValueSuccess : styles.statsValueDanger}>
                                {entry.status}
                              </span>
                            </td>
                            <td style={{ padding: "0.2rem 0" }}>{entry.message}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {autoPaperStatus ? <p className={styles.statusMessage}>{autoPaperStatus}</p> : null}
              </article>

              <article className={styles.panel}>
                <h2 className={styles.panelTitle}>Risk Snapshot</h2>
                <div data-rs="risk-snapshot" className={styles.riskGrid}>
                  <InfographicRing
                    title="Position Capacity"
                    subtitle="Open vs remaining"
                    centerLabel="usage"
                    centerValue={`${Math.min(999, Math.round(riskSnapshot.utilizationPct))}%`}
                    segments={[
                      { label: "Open", value: metrics.openPositions.length, color: "var(--state-success)" },
                      { label: "Remaining", value: Math.max(0, MAX_OPEN_POSITIONS - metrics.openPositions.length), color: "var(--surface-border)" },
                    ]}
                  />

                  <CompactBars
                    title="Pressure signals"
                    subtitle="Risk-related summaries"
                    items={[
                      { label: "Top asset concentration", value: Math.round(riskSnapshot.topAssetPct * 100), color: "var(--state-warning)", suffix: "%" },
                      { label: "Directional delta", value: Math.abs(riskSnapshot.directionalDelta), color: "var(--state-info)" },
                      { label: "Unread notifications", value: metrics.unreadNotifications, color: "var(--state-danger)" },
                    ]}
                  />
                </div>
                <p className={styles.bodyText}>
                  Top concentration asset: <span className={styles.bodyTextStrong}>{riskSnapshot.topAssetName}</span>
                </p>
              </article>
            </section>

            <section data-rs="two-col" className={styles.twoColumnGrid}>
              <JournalAttentionWidget recentExecutions={metrics.recentExecutions} />

              <article className={styles.panel}>
                <div className={styles.panelHeader}>
                  <h2 className={styles.panelTitle}>Execution Activity</h2>
                  <Link href="/analytics" className={styles.panelLink}>
                    Open deeper analytics
                  </Link>
                </div>

                {metrics.recentExecutions.length === 0 ? (
                  <p className={styles.stateMessage}>No recent execution activity.</p>
                ) : (
                  <div className={styles.stack}>
                    {metrics.recentExecutions.map((item) => (
                      <div data-rs="recent-row" key={item.execution_id} className={styles.recentRow}>
                        <span className={styles.assetText}>{item.asset}</span>
                        <span className={styles.mutedTiny}>{item.status}</span>
                        <span className={styles.monoId}>{compactId(item.execution_id)}</span>
                        <span className={styles.notionalText}>{formatMoney(item.notional)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </article>
            </section>

            <section data-rs="two-col" className={styles.twoColumnGrid}>
              <OperatorNotificationSurface title="Unread Notifications" maxItems={3} />

              <div className={`${styles.panel} ${styles.notePanel}`}>
                <h2 className={styles.panelTitle}>Journal Persistence</h2>
                <p className={styles.bodyText}>
                  Notes and tags now persist through the backend journal contract:
                  <span className={styles.bodyTextStrong}> GET /execution/paper/{'{id}'}/journal</span>
                  and
                  <span className={styles.bodyTextStrong}> PUT /execution/paper/{'{id}'}/journal</span>.
                </p>
              </div>
            </section>
          </>
        ) : null}
      </div>
    </main>
  );
}
