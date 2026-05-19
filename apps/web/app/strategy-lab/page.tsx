"use client";

import { useEffect, useMemo, useState } from "react";

import { PageHeader } from "../../components/shell/PageHeader";
import {
  createAIBacktestReport,
  getAIBacktestReports,
  getBacktestDrawdowns,
  getBacktestEquityCurve,
  getBacktestQualitySummary,
  getBacktestResults,
  getBacktestRun,
  getBacktestRuns,
  getBacktestTrades,
  getBacktestWalkForward,
  getCostModelProfiles,
  getCostModelStressPresets,
  getStrategyComparisonDetail,
  getStrategyComparisons,
  getStrategyConfigs,
  runWalkForwardValidation,
} from "../../lib/api/strategyLab";
import type {
  AIBacktestReport,
  BacktestRun,
  CostModelProfile,
  CostModelStressPreset,
  DrawdownPeriod,
  EquityCurvePoint,
  MockTrade,
  QualitySummary,
  ResearchWarnings,
  StrategyComparisonDetailResponse,
  StrategyComparisonHistoryRow,
  StrategyConfig,
  StrategyResult,
  WalkForwardStrategyValidation,
  WalkForwardValidation,
} from "../../lib/types";
import styles from "../../styles/pages/strategy-lab.module.css";

type LoadState = "loading" | "ready" | "error";

type ReviewRow = {
  key: string;
  strategyConfigId: string | null;
  strategyName: string;
  asset: string;
  timeframe: string;
  totalTrades: number;
  winRate: number | null;
  grossReturn: number | null;
  baseNetReturn: number | null;
  highCostNetReturn: number | null;
  grossProfitFactor: number | null;
  baseNetProfitFactor: number | null;
  highCostProfitFactor: number | null;
  maxDrawdown: number | null;
  qualityGrade: string | null;
  confidence: number | null;
  overfittingRisk: number | null;
  costSensitivity: string | null;
  stabilityGrade: string | null;
  warnings: string[];
  score: number | null;
};

const NO_DATA_MESSAGE =
  "Run a Strategy Lab comparison or backtest first. This page only reviews existing research outputs.";

const DEFAULT_RESEARCH_WARNINGS: ResearchWarnings = {
  research_only: true,
  execution_costs_modelled: true,
  spread_modelled: true,
  slippage_modelled: true,
  fees_modelled: true,
  live_ready: false,
  warning:
    "Execution costs are modelled using deterministic research assumptions, not broker-confirmed live execution costs.",
  cost_model_version: "mh15c_v1",
  cost_model_status: "modelled",
  cost_model_notes:
    "Cost profiles and stress presets are deterministic research assumptions and not broker-calibrated.",
};

function formatDateTime(value: string | null | undefined): string {
  if (!value) return "-";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString();
}

function formatNumber(value: number | null | undefined, decimals = 2): string {
  if (value == null || Number.isNaN(value)) return "-";
  return value.toLocaleString(undefined, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function formatPercent(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "-";
  return `${value.toFixed(2)}%`;
}

function formatSignedPercent(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "-";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

function toFileToken(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
}

function csvEscape(value: string): string {
  if (value.includes(",") || value.includes("\n") || value.includes("\"")) {
    return `"${value.replace(/\"/g, '""')}"`;
  }
  return value;
}

function triggerDownload(filename: string, content: string, mimeType: string): void {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function formatList(value: string[] | { assets?: string[]; timeframes?: string[]; config_ids?: string[] } | null | undefined): string {
  if (!value) return "-";
  if (Array.isArray(value)) return value.join(", ") || "-";
  if (Array.isArray(value.assets)) return value.assets.join(", ") || "-";
  if (Array.isArray(value.timeframes)) return value.timeframes.join(", ") || "-";
  if (Array.isArray(value.config_ids)) return value.config_ids.join(", ") || "-";
  return "-";
}

function getMetricNumber(metrics: Record<string, unknown> | null | undefined, key: string): number | null {
  if (!metrics) return null;
  const value = metrics[key];
  if (typeof value === "number") return value;
  if (typeof value === "string") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function getMetricString(metrics: Record<string, unknown> | null | undefined, key: string): string | null {
  if (!metrics) return null;
  const value = metrics[key];
  return typeof value === "string" && value.trim() ? value : null;
}

function getMetricWarnings(metrics: Record<string, unknown> | null | undefined, key: string): string[] {
  if (!metrics) return [];
  const value = metrics[key];
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function buildEquityPolyline(points: EquityCurvePoint[]): string {
  if (points.length === 0) return "";
  const width = 520;
  const height = 180;
  const padding = 12;
  const values = points.map((point) => point.equity);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;

  return points
    .map((point, index) => {
      const x =
        points.length === 1
          ? width / 2
          : padding + (index / (points.length - 1)) * (width - padding * 2);
      const y = height - padding - ((point.equity - min) / span) * (height - padding * 2);
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");
}

function statusTone(status: string | null | undefined): string {
  if (!status) return styles.statusMuted;
  if (["completed", "passed", "stable"].includes(status)) return styles.statusGood;
  if (["failed", "error", "unstable"].includes(status)) return styles.statusBad;
  return styles.statusWarn;
}

function normalizeConfidence(value: number | null | undefined): number | null {
  if (value == null || Number.isNaN(value)) return null;
  return value >= 0 && value <= 1 ? value * 100 : value;
}

function confidenceLabel(value: number | null | undefined): string {
  const normalized = normalizeConfidence(value);
  if (normalized == null) return "-";
  return `${normalized.toFixed(0)}%`;
}

function latestValidationStatus(walkForward: WalkForwardValidation | null): string {
  if (!walkForward) return "Not run";
  if (walkForward.rolling_window_summary?.rolling_validation_grade) {
    return walkForward.rolling_window_summary.rolling_validation_grade;
  }
  return walkForward.strategies[0]?.validation_stability_grade ?? "Available";
}

function backtestSummaryLabel(run: BacktestRun): string {
  const summary = run.result_summary ?? {};
  const totalTrades = typeof summary.total_mock_trades === "number" ? summary.total_mock_trades : null;
  const message = typeof summary.message === "string" ? summary.message : null;
  if (totalTrades != null) return `${totalTrades} trades`;
  if (message) return message;
  return "Research output only";
}

function latestAiSummary(report: AIBacktestReport | null): string {
  if (!report) return "No AI report generated yet.";
  return report.plain_english_summary ?? report.report_json?.plain_english_summary ?? "Summary unavailable.";
}

function MetricCard({ label, value, helper }: { label: string; value: string; helper?: string }) {
  return (
    <article className={styles.metricCard}>
      <p className={styles.metricLabel}>{label}</p>
      <p className={styles.metricValue}>{value}</p>
      {helper ? <p className={styles.metricHelper}>{helper}</p> : null}
    </article>
  );
}

function EmptyState({ title, body, testId }: { title: string; body: string; testId?: string }) {
  return (
    <div className={styles.emptyState} data-testid={testId}>
      <p className={styles.emptyTitle}>{title}</p>
      <p className={styles.emptyBody}>{body}</p>
    </div>
  );
}

export default function StrategyLabPage() {
  const [state, setState] = useState<LoadState>("loading");
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState(0);
  const [actionPending, setActionPending] = useState<string | null>(null);
  const [denseMode, setDenseMode] = useState(false);

  const [configs, setConfigs] = useState<StrategyConfig[]>([]);
  const [runs, setRuns] = useState<BacktestRun[]>([]);
  const [comparisons, setComparisons] = useState<StrategyComparisonHistoryRow[]>([]);
  const [costProfiles, setCostProfiles] = useState<CostModelProfile[]>([]);
  const [stressPresets, setStressPresets] = useState<CostModelStressPreset[]>([]);

  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [selectedComparisonId, setSelectedComparisonId] = useState<string | null>(null);
  const [selectedResultKey, setSelectedResultKey] = useState<string | null>(null);

  const [selectedRun, setSelectedRun] = useState<BacktestRun | null>(null);
  const [results, setResults] = useState<StrategyResult[]>([]);
  const [trades, setTrades] = useState<MockTrade[]>([]);
  const [equityCurve, setEquityCurve] = useState<EquityCurvePoint[]>([]);
  const [drawdowns, setDrawdowns] = useState<DrawdownPeriod[]>([]);
  const [qualitySummary, setQualitySummary] = useState<QualitySummary | null>(null);
  const [walkForward, setWalkForward] = useState<WalkForwardValidation | null>(null);
  const [aiReports, setAiReports] = useState<AIBacktestReport[]>([]);
  const [comparisonDetail, setComparisonDetail] = useState<StrategyComparisonDetailResponse | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);

  const [filters, setFilters] = useState({
    search: "",
    asset: "all",
    timeframe: "all",
    status: "all",
    qualityGrade: "all",
    stabilityGrade: "all",
    costSensitivity: "all",
  });

  useEffect(() => {
    let active = true;

    async function loadOverview() {
      setState("loading");
      setError(null);
      setActionMessage(null);

      const [configsResp, runsResp, comparisonsResp, profilesResp, presetsResp] = await Promise.allSettled([
        getStrategyConfigs(),
        getBacktestRuns(),
        getStrategyComparisons(),
        getCostModelProfiles(),
        getCostModelStressPresets(),
      ]);

      if (!active) return;

      const failures: string[] = [];

      if (configsResp.status === "fulfilled") {
        setConfigs(configsResp.value.items);
      } else {
        setConfigs([]);
        failures.push("strategy configs");
      }

      if (runsResp.status === "fulfilled") {
        setRuns(runsResp.value.items);
        setSelectedRunId((current) => current ?? runsResp.value.items[0]?.id ?? null);
      } else {
        setRuns([]);
        failures.push("backtest runs");
      }

      if (comparisonsResp.status === "fulfilled") {
        setComparisons(comparisonsResp.value.items);
        setSelectedComparisonId((current) => current ?? comparisonsResp.value.items[0]?.backtest_run_id ?? null);
      } else {
        setComparisons([]);
        failures.push("comparison runs");
      }

      if (profilesResp.status === "fulfilled") {
        setCostProfiles(profilesResp.value.items);
      } else {
        setCostProfiles([]);
        failures.push("cost profiles");
      }

      if (presetsResp.status === "fulfilled") {
        setStressPresets(presetsResp.value.items);
      } else {
        setStressPresets([]);
        failures.push("stress presets");
      }

      if (failures.length === 5) {
        setState("error");
        setError("Failed to load Strategy Lab research review data.");
        return;
      }

      if (failures.length > 0) {
        setActionMessage(`Some Strategy Lab panels could not load: ${failures.join(", ")}.`);
      }

      setState("ready");
    }

    void loadOverview();

    return () => {
      active = false;
    };
  }, [refreshToken]);

  useEffect(() => {
    let active = true;

    async function loadRunDetail(runId: string) {
      setDetailError(null);

      const [runResp, tradesResp, resultsResp, equityResp, drawdownResp, qualityResp, walkResp, aiResp] =
        await Promise.allSettled([
          getBacktestRun(runId),
          getBacktestTrades(runId),
          getBacktestResults(runId),
          getBacktestEquityCurve(runId),
          getBacktestDrawdowns(runId),
          getBacktestQualitySummary(runId),
          getBacktestWalkForward(runId),
          getAIBacktestReports(runId),
        ]);

      if (!active) return;

      if (runResp.status !== "fulfilled") {
        setSelectedRun(null);
        setDetailError("Selected backtest details could not be loaded.");
        return;
      }

      setSelectedRun(runResp.value);
      setTrades(tradesResp.status === "fulfilled" ? tradesResp.value.items : []);
      setResults(resultsResp.status === "fulfilled" ? resultsResp.value.items : []);
      setEquityCurve(equityResp.status === "fulfilled" ? equityResp.value.items : []);
      setDrawdowns(drawdownResp.status === "fulfilled" ? drawdownResp.value.items : []);
      setQualitySummary(qualityResp.status === "fulfilled" ? qualityResp.value : null);
      setWalkForward(walkResp.status === "fulfilled" ? walkResp.value : null);
      setAiReports(aiResp.status === "fulfilled" ? aiResp.value.items : []);
    }

    if (!selectedRunId) {
      setSelectedRun(null);
      setTrades([]);
      setResults([]);
      setEquityCurve([]);
      setDrawdowns([]);
      setQualitySummary(null);
      setWalkForward(null);
      setAiReports([]);
      return;
    }

    void loadRunDetail(selectedRunId);

    return () => {
      active = false;
    };
  }, [selectedRunId]);

  useEffect(() => {
    let active = true;

    async function loadComparisonDetail(runId: string) {
      try {
        const detail = await getStrategyComparisonDetail(runId);
        if (!active) return;
        setComparisonDetail(detail);
      } catch {
        if (!active) return;
        setComparisonDetail(null);
      }
    }

    if (!selectedComparisonId) {
      setComparisonDetail(null);
      return;
    }

    void loadComparisonDetail(selectedComparisonId);

    return () => {
      active = false;
    };
  }, [selectedComparisonId]);

  const configById = useMemo(() => new Map(configs.map((config) => [config.id, config])), [configs]);

  const comparisonRowByConfigId = useMemo(
    () => new Map((comparisonDetail?.ranked_rows ?? []).map((row) => [row.strategy_config_id, row])),
    [comparisonDetail],
  );

  const safetyWarnings =
    comparisonDetail?.research_warnings
    ?? selectedRun?.research_warnings
    ?? aiReports[0]?.research_warnings
    ?? DEFAULT_RESEARCH_WARNINGS;

  const runOptions = useMemo(() => {
    return runs.filter((run) => {
      if (filters.search && !run.name.toLowerCase().includes(filters.search.toLowerCase())) return false;
      if (filters.status !== "all" && run.status !== filters.status) return false;
      return true;
    });
  }, [filters.search, filters.status, runs]);

  const comparisonOptions = useMemo(() => {
    return comparisons.filter((row) => {
      if (filters.search && !row.name.toLowerCase().includes(filters.search.toLowerCase())) return false;
      if (filters.status !== "all" && row.status !== filters.status) return false;
      return true;
    });
  }, [comparisons, filters.search, filters.status]);

  const resultRows = useMemo<ReviewRow[]>(() => {
    if (comparisonDetail?.ranked_rows?.length) {
      return comparisonDetail.ranked_rows.map((row) => ({
        key: row.strategy_config_id,
        strategyConfigId: row.strategy_config_id,
        strategyName: row.strategy_name,
        asset: row.asset,
        timeframe: row.timeframe,
        totalTrades: row.total_trades,
        winRate: row.win_rate,
        grossReturn: row.total_return_pct,
        baseNetReturn: row.total_return_pct,
        highCostNetReturn: row.high_cost_scenario_net_return_pct ?? null,
        grossProfitFactor: row.profit_factor,
        baseNetProfitFactor: row.profit_factor,
        highCostProfitFactor: row.high_cost_scenario_profit_factor ?? null,
        maxDrawdown: row.max_drawdown_pct,
        qualityGrade: row.quality_grade ?? null,
        confidence: row.research_confidence_score ?? null,
        overfittingRisk: row.overfitting_risk_score ?? null,
        costSensitivity: row.cost_sensitivity_level ?? null,
        stabilityGrade: row.validation_stability_grade ?? null,
        warnings: [...(row.quality_warnings ?? []), ...(row.walk_forward_warnings ?? [])],
        score: row.score,
      }));
    }

    return results.map((row) => {
      const metrics = row.metrics;
      const matchingComparison = row.strategy_config_id ? comparisonRowByConfigId.get(row.strategy_config_id) : undefined;
      const config = row.strategy_config_id ? configById.get(row.strategy_config_id) : undefined;

      return {
        key: row.id,
        strategyConfigId: row.strategy_config_id,
        strategyName: matchingComparison?.strategy_name ?? config?.name ?? "Research result",
        asset: row.asset ?? config?.asset ?? "-",
        timeframe: row.timeframe ?? config?.timeframe ?? "-",
        totalTrades: row.total_trades,
        winRate: row.win_rate,
        grossReturn: row.total_return_pct,
        baseNetReturn: getMetricNumber(metrics, "base_net_total_return_pct") ?? getMetricNumber(metrics, "net_total_return_pct"),
        highCostNetReturn: getMetricNumber(metrics, "high_net_total_return_pct"),
        grossProfitFactor: row.profit_factor,
        baseNetProfitFactor: getMetricNumber(metrics, "base_net_profit_factor") ?? getMetricNumber(metrics, "net_profit_factor"),
        highCostProfitFactor: getMetricNumber(metrics, "high_net_profit_factor"),
        maxDrawdown: row.max_drawdown_pct,
        qualityGrade: getMetricString(metrics, "quality_grade"),
        confidence: getMetricNumber(metrics, "research_confidence_score"),
        overfittingRisk: getMetricNumber(metrics, "overfitting_risk_score"),
        costSensitivity: getMetricString(metrics, "cost_sensitivity_level"),
        stabilityGrade: getMetricString(metrics, "validation_stability_grade"),
        warnings: [
          ...getMetricWarnings(metrics, "quality_warnings"),
          ...getMetricWarnings(metrics, "walk_forward_warnings"),
        ],
        score: row.score,
      };
    });
  }, [comparisonDetail, comparisonRowByConfigId, configById, results]);

  const assetOptions = useMemo(
    () => Array.from(new Set(resultRows.map((row) => row.asset).filter(Boolean))).sort(),
    [resultRows],
  );

  const timeframeOptions = useMemo(
    () => Array.from(new Set(resultRows.map((row) => row.timeframe).filter(Boolean))).sort(),
    [resultRows],
  );

  const filteredResultRows = useMemo(() => {
    return resultRows.filter((row) => {
      if (filters.asset !== "all" && row.asset !== filters.asset) return false;
      if (filters.timeframe !== "all" && row.timeframe !== filters.timeframe) return false;
      if (filters.qualityGrade !== "all" && (row.qualityGrade ?? "unknown") !== filters.qualityGrade) return false;
      if (filters.stabilityGrade !== "all" && (row.stabilityGrade ?? "unknown") !== filters.stabilityGrade) return false;
      if (filters.costSensitivity !== "all" && (row.costSensitivity ?? "unknown") !== filters.costSensitivity) return false;
      return true;
    });
  }, [filters.asset, filters.costSensitivity, filters.qualityGrade, filters.stabilityGrade, filters.timeframe, resultRows]);

  useEffect(() => {
    if (filteredResultRows.length === 0) {
      setSelectedResultKey(null);
      return;
    }

    setSelectedResultKey((current) => {
      if (current && filteredResultRows.some((row) => row.key === current)) return current;
      return filteredResultRows[0].key;
    });
  }, [filteredResultRows]);

  const selectedResultRow = useMemo(
    () => filteredResultRows.find((row) => row.key === selectedResultKey) ?? null,
    [filteredResultRows, selectedResultKey],
  );

  const selectedValidation = useMemo<WalkForwardStrategyValidation | null>(() => {
    if (!walkForward?.strategies?.length) return null;
    const preferredConfigId = filteredResultRows[0]?.strategyConfigId;
    if (preferredConfigId) {
      const matched = walkForward.strategies.find((row) => row.strategy_config_id === preferredConfigId);
      if (matched) return matched;
    }
    return walkForward.strategies[0] ?? null;
  }, [filteredResultRows, walkForward]);

  const selectedRunName = useMemo(() => {
    if (selectedRun?.name) return selectedRun.name;
    const matched = runs.find((run) => run.id === selectedRunId);
    return matched?.name ?? "No run selected";
  }, [runs, selectedRun, selectedRunId]);

  const reportPayload = useMemo(() => {
    if (!selectedResultRow) return null;

    return {
      report_type: "strategy_lab_research_summary",
      generated_at: new Date().toISOString(),
      run: {
        id: selectedRunId,
        name: selectedRunName,
      },
      comparison: {
        id: selectedComparisonId,
      },
      strategy: {
        name: selectedResultRow.strategyName,
        asset: selectedResultRow.asset,
        timeframe: selectedResultRow.timeframe,
        trades: selectedResultRow.totalTrades,
      },
      metrics: {
        win_rate_pct: selectedResultRow.winRate != null ? selectedResultRow.winRate * 100 : null,
        gross_return_pct: selectedResultRow.grossReturn,
        base_net_return_pct: selectedResultRow.baseNetReturn,
        high_cost_net_return_pct: selectedResultRow.highCostNetReturn,
        gross_profit_factor: selectedResultRow.grossProfitFactor,
        base_net_profit_factor: selectedResultRow.baseNetProfitFactor,
        high_cost_profit_factor: selectedResultRow.highCostProfitFactor,
        max_drawdown_pct: selectedResultRow.maxDrawdown,
      },
      quality: {
        grade: selectedResultRow.qualityGrade,
        confidence_pct: normalizeConfidence(selectedResultRow.confidence),
        overfitting_risk: selectedResultRow.overfittingRisk,
        quality_summary_average_confidence_pct: normalizeConfidence(qualitySummary?.average_confidence ?? null),
        quality_summary_highest_overfitting_risk: qualitySummary?.highest_overfitting_risk ?? null,
      },
      walk_forward: {
        stability_grade: selectedValidation?.validation_stability_grade ?? null,
        stability_score: selectedValidation?.validation_stability_score ?? null,
        out_of_sample_pass: selectedValidation?.out_of_sample_pass ?? null,
        return_degradation_pct: selectedValidation?.return_degradation_pct ?? null,
        confidence_degradation_pct: selectedValidation?.confidence_degradation_pct ?? null,
      },
      assumptions: {
        research_only: true,
        paper_trade_ready: false,
        live_ready: false,
        cost_model_version: safetyWarnings.cost_model_version ?? "mh15c_v1",
        cost_model_status: safetyWarnings.cost_model_status ?? "modelled",
        cost_model_notes: safetyWarnings.cost_model_notes ?? "Deterministic research assumptions.",
      },
      warnings: [
        "Research only. Not approved for paper or live trading.",
        ...(selectedResultRow.warnings.length ? selectedResultRow.warnings : ["No additional strategy warnings."]),
      ],
    };
  }, [qualitySummary, safetyWarnings, selectedComparisonId, selectedResultRow, selectedRunId, selectedRunName, selectedValidation]);

  const reportText = useMemo(() => {
    if (!reportPayload) return "No selected strategy result. Select a row to generate a research report.";

    return [
      "Strategy Lab Research Summary",
      `Generated: ${formatDateTime(reportPayload.generated_at)}`,
      "",
      `Run: ${reportPayload.run.name} (${reportPayload.run.id ?? "-"})`,
      `Comparison: ${reportPayload.comparison.id ?? "-"}`,
      `Strategy: ${reportPayload.strategy.name}`,
      `Asset/Timeframe: ${reportPayload.strategy.asset} / ${reportPayload.strategy.timeframe}`,
      `Trades: ${reportPayload.strategy.trades}`,
      "",
      "Performance",
      `- Win rate: ${formatPercent(reportPayload.metrics.win_rate_pct)}`,
      `- Gross return: ${formatPercent(reportPayload.metrics.gross_return_pct)}`,
      `- Base-net return: ${formatPercent(reportPayload.metrics.base_net_return_pct)}`,
      `- High-cost return: ${formatPercent(reportPayload.metrics.high_cost_net_return_pct)}`,
      `- Gross PF: ${formatNumber(reportPayload.metrics.gross_profit_factor)}`,
      `- Base-net PF: ${formatNumber(reportPayload.metrics.base_net_profit_factor)}`,
      `- High-cost PF: ${formatNumber(reportPayload.metrics.high_cost_profit_factor)}`,
      `- Max drawdown: ${formatPercent(reportPayload.metrics.max_drawdown_pct)}`,
      "",
      "Quality & Stability",
      `- Quality grade: ${reportPayload.quality.grade ?? "-"}`,
      `- Confidence: ${reportPayload.quality.confidence_pct != null ? `${reportPayload.quality.confidence_pct.toFixed(0)}%` : "-"}`,
      `- Overfitting risk: ${formatNumber(reportPayload.quality.overfitting_risk)}`,
      `- Walk-forward grade: ${reportPayload.walk_forward.stability_grade ?? "-"}`,
      `- Walk-forward score: ${formatNumber(reportPayload.walk_forward.stability_score, 0)}`,
      `- Out-of-sample pass: ${reportPayload.walk_forward.out_of_sample_pass == null ? "-" : reportPayload.walk_forward.out_of_sample_pass ? "Passed" : "Not passed"}`,
      "",
      "Cost Assumptions",
      `- Version: ${reportPayload.assumptions.cost_model_version}`,
      `- Status: ${reportPayload.assumptions.cost_model_status}`,
      `- Notes: ${reportPayload.assumptions.cost_model_notes}`,
      "",
      "Warnings",
      ...reportPayload.warnings.map((warning) => `- ${warning}`),
      "",
      "Research-only notice: This summary is for research review only. No trade execution or approval is implied.",
    ].join("\n");
  }, [reportPayload]);

  const safetyCards = [
    { label: "Research scope", value: safetyWarnings.research_only ? "Research only" : "Unknown", helper: "Display and review only" },
    { label: "Paper trading", value: "Not paper ready", helper: "No paper-trading coupling" },
    { label: "Live trading", value: "Not live ready", helper: "No live approval or execution" },
    { label: "Execution costs", value: safetyWarnings.execution_costs_modelled ? "Modelled" : "Unavailable", helper: safetyWarnings.cost_model_version ?? "No version" },
    { label: "Broker calibration", value: "Not broker-calibrated", helper: "Deterministic research assumptions" },
    { label: "Latest validation", value: latestValidationStatus(walkForward), helper: "Research guidance only" },
  ];

  async function handleRefresh() {
    setRefreshToken((value) => value + 1);
  }

  async function handleRunResearchWalkForward() {
    if (!selectedRunId) return;
    setActionPending("walk-forward");
    setActionMessage(null);
    try {
      const response = await runWalkForwardValidation(selectedRunId, { fold_count: 3 });
      setWalkForward(response);
      setActionMessage("Research action completed: walk-forward validation refreshed. Does not execute trades.");
    } catch (err) {
      setActionMessage(err instanceof Error ? err.message : "Walk-forward validation failed.");
    } finally {
      setActionPending(null);
    }
  }

  async function handleCreateAiReport() {
    if (!selectedRunId) return;
    setActionPending("ai-report");
    setActionMessage(null);
    try {
      const report = await createAIBacktestReport(selectedRunId, { focus: "balanced" });
      setAiReports((current) => [report, ...current.filter((item) => item.id !== report.id)]);
      setActionMessage("Research action completed: AI review report created. Does not execute trades.");
    } catch (err) {
      setActionMessage(err instanceof Error ? err.message : "AI report generation failed.");
    } finally {
      setActionPending(null);
    }
  }

  async function handleCopyReportText() {
    if (!reportPayload) return;
    try {
      await navigator.clipboard.writeText(reportText);
      setActionMessage("Research report text copied. Share for review only. Does not execute trades.");
    } catch {
      setActionMessage("Unable to copy report text in this environment.");
    }
  }

  function handleExportJson() {
    if (!reportPayload) return;
    const token = toFileToken(`${reportPayload.strategy.asset}-${reportPayload.strategy.timeframe}-${reportPayload.strategy.name}`) || "strategy";
    triggerDownload(
      `strategy-lab-research-summary-${token}.json`,
      `${JSON.stringify(reportPayload, null, 2)}\n`,
      "application/json;charset=utf-8",
    );
    setActionMessage("Research summary exported as JSON. Review only.");
  }

  function handleExportCsv() {
    if (!reportPayload) return;
    const rows: Array<[string, string]> = [
      ["generated_at", reportPayload.generated_at],
      ["run_id", reportPayload.run.id ?? ""],
      ["run_name", reportPayload.run.name],
      ["comparison_id", reportPayload.comparison.id ?? ""],
      ["strategy_name", reportPayload.strategy.name],
      ["asset", reportPayload.strategy.asset],
      ["timeframe", reportPayload.strategy.timeframe],
      ["trades", String(reportPayload.strategy.trades)],
      ["win_rate_pct", reportPayload.metrics.win_rate_pct == null ? "" : reportPayload.metrics.win_rate_pct.toFixed(2)],
      ["gross_return_pct", reportPayload.metrics.gross_return_pct == null ? "" : reportPayload.metrics.gross_return_pct.toFixed(2)],
      ["base_net_return_pct", reportPayload.metrics.base_net_return_pct == null ? "" : reportPayload.metrics.base_net_return_pct.toFixed(2)],
      ["high_cost_net_return_pct", reportPayload.metrics.high_cost_net_return_pct == null ? "" : reportPayload.metrics.high_cost_net_return_pct.toFixed(2)],
      ["validation_stability_grade", reportPayload.walk_forward.stability_grade ?? ""],
      ["validation_stability_score", reportPayload.walk_forward.stability_score == null ? "" : reportPayload.walk_forward.stability_score.toFixed(0)],
      ["out_of_sample_pass", reportPayload.walk_forward.out_of_sample_pass == null ? "" : String(reportPayload.walk_forward.out_of_sample_pass)],
      ["cost_model_version", reportPayload.assumptions.cost_model_version],
      ["cost_model_status", reportPayload.assumptions.cost_model_status],
      ["cost_model_notes", reportPayload.assumptions.cost_model_notes],
      ["warnings", reportPayload.warnings.join(" | ")],
    ];
    const csv = ["field,value", ...rows.map(([field, value]) => `${csvEscape(field)},${csvEscape(value)}`)].join("\n");
    const token = toFileToken(`${reportPayload.strategy.asset}-${reportPayload.strategy.timeframe}-${reportPayload.strategy.name}`) || "strategy";
    triggerDownload(`strategy-lab-research-summary-${token}.csv`, `${csv}\n`, "text/csv;charset=utf-8");
    setActionMessage("Research summary exported as CSV. Review only.");
  }

  function handlePrintReport() {
    if (!reportPayload) return;
    window.print();
  }

  if (state === "loading") {
    return (
      <section className={styles.page}>
        <div className={styles.container}>
          <PageHeader
            title="Strategy Lab"
            subtitle="Research-only strategy validation, cost modelling, and walk-forward review."
          />
          <div className={styles.loadingState} data-testid="strategy-lab-loading-state">
            Loading Strategy Lab research cockpit...
          </div>
        </div>
      </section>
    );
  }

  if (state === "error") {
    return (
      <section className={styles.page}>
        <div className={styles.container}>
          <PageHeader
            title="Strategy Lab"
            subtitle="Research-only strategy validation, cost modelling, and walk-forward review."
          />
          <div className={styles.errorState} data-testid="strategy-lab-error-state">
            <p className={styles.errorTitle}>Strategy Lab research review is temporarily unavailable.</p>
            <p className={styles.errorBody}>{error ?? "Failed to load Strategy Lab research review data."}</p>
            <button className={styles.secondaryButton} onClick={handleRefresh} type="button">
              Refresh research review
            </button>
          </div>
        </div>
      </section>
    );
  }

  const equityPolyline = buildEquityPolyline(equityCurve);
  const latestAiReport = aiReports[0] ?? null;

  return (
    <section className={styles.page}>
      <div className={`${styles.container} ${denseMode ? styles.dense : ""}`.trim()}>
        <PageHeader
          title="Strategy Lab"
          subtitle="Research-only strategy validation, cost modelling, and walk-forward review."
          actions={(
            <button className={styles.secondaryButton} onClick={handleRefresh} type="button">
              Refresh
            </button>
          )}
        />

        <section className={styles.banner} data-testid="strategy-lab-banner">
          <div>
            <p className={styles.bannerEyebrow}>Research safety</p>
            <h2 className={styles.bannerTitle}>Research only. Not approved for paper or live trading.</h2>
            <p className={styles.bannerBody}>
              Cost profiles are deterministic research assumptions. Stress presets are not broker-calibrated.
              Walk-forward validation remains research guidance only.
            </p>
          </div>
          <div className={styles.bannerActions}>
            <button
              className={styles.primaryButton}
              data-testid="run-walk-forward-btn"
              disabled={!selectedRunId || actionPending === "walk-forward"}
              onClick={handleRunResearchWalkForward}
              type="button"
            >
              Research action: Run walk-forward
            </button>
            <button
              className={styles.secondaryButton}
              data-testid="create-ai-report-btn"
              disabled={!selectedRunId || actionPending === "ai-report"}
              onClick={handleCreateAiReport}
              type="button"
            >
              Research action: Create AI report
            </button>
            <p className={styles.bannerNote}>Does not execute trades.</p>
          </div>
        </section>

        <section className={styles.summaryStrip} data-testid="strategy-lab-summary-strip">
          <div className={styles.summaryPill}>
            <p className={styles.summaryLabel}>Backtest runs</p>
            <p className={styles.summaryValue}>{runs.length}</p>
          </div>
          <div className={styles.summaryPill}>
            <p className={styles.summaryLabel}>Comparison runs</p>
            <p className={styles.summaryValue}>{comparisons.length}</p>
          </div>
          <div className={styles.summaryPill}>
            <p className={styles.summaryLabel}>Visible results</p>
            <p className={styles.summaryValue}>{filteredResultRows.length}</p>
          </div>
          <div className={styles.summaryPill}>
            <p className={styles.summaryLabel}>Selected run</p>
            <p className={styles.summaryValue}>{selectedRunName}</p>
          </div>
          <div className={styles.summaryPill}>
            <p className={styles.summaryLabel}>Selected strategy</p>
            <p className={styles.summaryValue}>{selectedResultRow?.strategyName ?? "None selected"}</p>
          </div>
        </section>

        {actionMessage ? <p className={styles.inlineMessage}>{actionMessage}</p> : null}
        {detailError ? <p className={styles.inlineWarning}>{detailError}</p> : null}

        <section className={styles.section} data-testid="strategy-lab-safety-section">
          <div className={styles.sectionHeader}>
            <h2 className={styles.sectionTitle}>Research safety cards</h2>
            <p className={styles.sectionSubtitle}>{safetyWarnings.cost_model_notes}</p>
          </div>
          <div className={styles.metricGrid}>
            {safetyCards.map((card) => (
              <MetricCard key={card.label} label={card.label} value={card.value} helper={card.helper} />
            ))}
          </div>
        </section>

        <section className={styles.section} data-testid="strategy-lab-filter-bar">
          <div className={styles.sectionHeader}>
            <div>
              <h2 className={styles.sectionTitle}>Filters and refresh controls</h2>
              <p className={styles.sectionSubtitle}>Client-side filters only. This page reviews existing research outputs.</p>
            </div>
            <button
              className={styles.secondaryButton}
              data-testid="strategy-lab-density-toggle"
              onClick={() => setDenseMode((current) => !current)}
              type="button"
            >
              {denseMode ? "Density: Compact" : "Density: Comfortable"}
            </button>
          </div>
          <div className={styles.filterGrid}>
            <label className={styles.field}>
              <span>Search run name</span>
              <input
                className={styles.input}
                onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value }))}
                placeholder="Search backtest or comparison runs"
                type="search"
                value={filters.search}
              />
            </label>
            <label className={styles.field}>
              <span>Asset</span>
              <select
                className={styles.input}
                onChange={(event) => setFilters((current) => ({ ...current, asset: event.target.value }))}
                value={filters.asset}
              >
                <option value="all">All assets</option>
                {assetOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>
            <label className={styles.field}>
              <span>Timeframe</span>
              <select
                className={styles.input}
                onChange={(event) => setFilters((current) => ({ ...current, timeframe: event.target.value }))}
                value={filters.timeframe}
              >
                <option value="all">All timeframes</option>
                {timeframeOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>
            <label className={styles.field}>
              <span>Status</span>
              <select
                className={styles.input}
                onChange={(event) => setFilters((current) => ({ ...current, status: event.target.value }))}
                value={filters.status}
              >
                <option value="all">All statuses</option>
                <option value="completed">Completed</option>
                <option value="queued">Queued</option>
                <option value="running">Running</option>
                <option value="failed">Failed</option>
              </select>
            </label>
            <label className={styles.field}>
              <span>Quality grade</span>
              <select
                className={styles.input}
                onChange={(event) => setFilters((current) => ({ ...current, qualityGrade: event.target.value }))}
                value={filters.qualityGrade}
              >
                <option value="all">All grades</option>
                <option value="A">A</option>
                <option value="B">B</option>
                <option value="C">C</option>
                <option value="D">D</option>
                <option value="F">F</option>
                <option value="unknown">Unknown</option>
              </select>
            </label>
            <label className={styles.field}>
              <span>Stability grade</span>
              <select
                className={styles.input}
                onChange={(event) => setFilters((current) => ({ ...current, stabilityGrade: event.target.value }))}
                value={filters.stabilityGrade}
              >
                <option value="all">All stability grades</option>
                <option value="stable">Stable</option>
                <option value="mixed">Mixed</option>
                <option value="unstable">Unstable</option>
                <option value="unknown">Unknown</option>
              </select>
            </label>
            <label className={styles.field}>
              <span>Cost sensitivity</span>
              <select
                className={styles.input}
                onChange={(event) => setFilters((current) => ({ ...current, costSensitivity: event.target.value }))}
                value={filters.costSensitivity}
              >
                <option value="all">All sensitivity levels</option>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="loss_sensitive">Loss sensitive</option>
                <option value="unknown">Unknown</option>
              </select>
            </label>
          </div>
        </section>

        <div className={styles.splitGrid}>
          <section className={styles.section} data-testid="strategy-lab-runs-section">
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}>Backtest runs</h2>
              <p className={styles.sectionSubtitle}>Select one run to review results, quality, walk-forward, and AI summaries.</p>
            </div>
            {runOptions.length === 0 ? (
              <EmptyState title="No backtest runs" body={NO_DATA_MESSAGE} testId="strategy-lab-runs-empty-state" />
            ) : (
              <div className={styles.tableWrap}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th className={styles.th}>Run</th>
                      <th className={styles.th}>Status</th>
                      <th className={styles.th}>Date range</th>
                      <th className={styles.th}>Assets</th>
                      <th className={styles.th}>Timeframes</th>
                      <th className={styles.th}>Created</th>
                      <th className={styles.th}>Completed</th>
                      <th className={styles.th}>Result summary</th>
                      <th className={styles.th}>Select</th>
                    </tr>
                  </thead>
                  <tbody>
                    {runOptions.map((run) => (
                      <tr key={run.id}>
                        <td className={styles.td}>{run.name}</td>
                        <td className={styles.td}>
                          <span className={`${styles.statusChip} ${statusTone(run.status)}`}>{run.status}</span>
                        </td>
                        <td className={styles.td}>{formatDateTime(run.date_from)} to {formatDateTime(run.date_to)}</td>
                        <td className={styles.td}>{formatList(run.requested_assets)}</td>
                        <td className={styles.td}>{formatList(run.requested_timeframes)}</td>
                        <td className={styles.td}>{formatDateTime(run.created_at)}</td>
                        <td className={styles.td}>{formatDateTime(run.completed_at)}</td>
                        <td className={styles.td}>{backtestSummaryLabel(run)}</td>
                        <td className={styles.td}>
                          <button className={styles.secondaryButton} onClick={() => setSelectedRunId(run.id)} type="button">
                            {selectedRunId === run.id ? "Selected" : "Review"}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <section className={styles.section} data-testid="strategy-lab-comparison-section">
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}>Comparison runs</h2>
              <p className={styles.sectionSubtitle}>Comparison history for ranking and parameter review. No execution actions are available.</p>
            </div>
            {comparisonOptions.length === 0 ? (
              <EmptyState title="No comparison runs" body={NO_DATA_MESSAGE} testId="strategy-lab-comparisons-empty-state" />
            ) : (
              <div className={styles.tableWrap}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th className={styles.th}>Run</th>
                      <th className={styles.th}>Status</th>
                      <th className={styles.th}>Top score</th>
                      <th className={styles.th}>Cost profile</th>
                      <th className={styles.th}>Stress preset</th>
                      <th className={styles.th}>Quality grade</th>
                      <th className={styles.th}>Confidence</th>
                      <th className={styles.th}>Walk-forward</th>
                      <th className={styles.th}>Warnings</th>
                      <th className={styles.th}>Select</th>
                    </tr>
                  </thead>
                  <tbody>
                    {comparisonOptions.map((row) => {
                      const selectedTopRow = selectedComparisonId === row.backtest_run_id ? comparisonDetail?.ranked_rows?.[0] : null;
                      return (
                        <tr key={row.backtest_run_id}>
                          <td className={styles.td}>{row.name}</td>
                          <td className={styles.td}>
                            <span className={`${styles.statusChip} ${statusTone(row.status)}`}>{row.status}</span>
                          </td>
                          <td className={styles.td}>{formatNumber(row.best_score, 1)}</td>
                          <td className={styles.td}>{selectedTopRow?.scoring_cost_scenario ?? "-"}</td>
                          <td className={styles.td}>{selectedComparisonId === row.backtest_run_id ? (comparisonDetail?.research_warnings?.cost_model_version ?? "-") : "-"}</td>
                          <td className={styles.td}>{selectedTopRow?.quality_grade ?? "-"}</td>
                          <td className={styles.td}>{confidenceLabel(selectedTopRow?.research_confidence_score ?? null)}</td>
                          <td className={styles.td}>{selectedTopRow?.validation_stability_grade ?? "-"}</td>
                          <td className={styles.td}>{(selectedTopRow?.quality_warnings?.length ?? 0) + (selectedTopRow?.walk_forward_warnings?.length ?? 0)}</td>
                          <td className={styles.td}>
                            <button
                              className={styles.secondaryButton}
                              onClick={() => {
                                setSelectedComparisonId(row.backtest_run_id);
                                setSelectedRunId(row.backtest_run_id);
                              }}
                              type="button"
                            >
                              {selectedComparisonId === row.backtest_run_id ? "Selected" : "Review"}
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </div>

        <section className={styles.section} data-testid="strategy-lab-results-section">
          <div className={styles.sectionHeader}>
            <div>
              <h2 className={styles.sectionTitle}>Strategy results table</h2>
              <p className={styles.sectionSubtitle}>Gross vs net review, cost sensitivity, quality scoring, and validation stability.</p>
            </div>
            <p className={styles.sectionMeta}>{filteredResultRows.length} rows</p>
          </div>
          {filteredResultRows.length === 0 ? (
            <EmptyState title="No strategy results" body={NO_DATA_MESSAGE} testId="strategy-lab-results-empty-state" />
          ) : (
            <div className={styles.tableWrap}>
              <table className={styles.tableWide}>
                <thead>
                  <tr>
                    <th className={styles.th}>Asset</th>
                    <th className={styles.th}>Timeframe</th>
                    <th className={styles.th}>Strategy</th>
                    <th className={styles.th}>Trades</th>
                    <th className={styles.th}>Win rate</th>
                    <th className={styles.th}>Gross return</th>
                    <th className={styles.th}>Base net return</th>
                    <th className={styles.th}>High-cost net</th>
                    <th className={styles.th}>Gross PF</th>
                    <th className={styles.th}>Base net PF</th>
                    <th className={styles.th}>High-cost PF</th>
                    <th className={styles.th}>Max DD</th>
                    <th className={styles.th}>Quality</th>
                    <th className={styles.th}>Confidence</th>
                    <th className={styles.th}>Overfitting</th>
                    <th className={styles.th}>Cost sensitivity</th>
                    <th className={styles.th}>Validation</th>
                    <th className={styles.th}>Warnings</th>
                    <th className={styles.th}>Drill-down</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredResultRows.map((row) => (
                    <tr className={selectedResultKey === row.key ? styles.tableRowSelected : undefined} key={row.key}>
                      <td className={styles.td}>{row.asset}</td>
                      <td className={styles.td}>{row.timeframe}</td>
                      <td className={styles.td}>{row.strategyName}</td>
                      <td className={styles.td}>{row.totalTrades}</td>
                      <td className={styles.td}>{formatPercent(row.winRate != null ? row.winRate * 100 : null)}</td>
                      <td className={styles.td}>{formatPercent(row.grossReturn)}</td>
                      <td className={styles.td}>{formatPercent(row.baseNetReturn)}</td>
                      <td className={styles.td}>{formatPercent(row.highCostNetReturn)}</td>
                      <td className={styles.td}>{formatNumber(row.grossProfitFactor)}</td>
                      <td className={styles.td}>{formatNumber(row.baseNetProfitFactor)}</td>
                      <td className={styles.td}>{formatNumber(row.highCostProfitFactor)}</td>
                      <td className={styles.td}>{formatPercent(row.maxDrawdown)}</td>
                      <td className={styles.td}>{row.qualityGrade ?? "-"}</td>
                      <td className={styles.td}>{confidenceLabel(row.confidence)}</td>
                      <td className={styles.td}>{formatNumber(row.overfittingRisk)}</td>
                      <td className={styles.td}>{row.costSensitivity ?? "-"}</td>
                      <td className={styles.td}>{row.stabilityGrade ?? "-"}</td>
                      <td className={styles.td}>{row.warnings.length ? row.warnings.join(" | ") : "-"}</td>
                      <td className={styles.td}>
                        <button className={styles.secondaryButton} onClick={() => setSelectedResultKey(row.key)} type="button">
                          {selectedResultKey === row.key ? "Selected" : "View details"}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section className={styles.section} data-testid="strategy-lab-result-drilldown-section">
          <div className={styles.sectionHeader}>
            <div>
              <h2 className={styles.sectionTitle}>Result drill-down</h2>
              <p className={styles.sectionSubtitle}>Focused review for the selected strategy row. Research-only context and metrics.</p>
            </div>
            {selectedResultRow ? <p className={styles.sectionMeta}>{selectedResultRow.strategyName}</p> : null}
          </div>
          {!selectedResultRow ? (
            <div className={styles.cardStack}>
              <div className={styles.exportActions} data-testid="strategy-lab-report-actions">
                <button className={styles.secondaryButton} data-testid="strategy-lab-export-json-btn" disabled type="button">
                  Export JSON
                </button>
                <button className={styles.secondaryButton} data-testid="strategy-lab-export-csv-btn" disabled type="button">
                  Export CSV
                </button>
                <button className={styles.secondaryButton} data-testid="strategy-lab-copy-report-btn" disabled type="button">
                  Copy report text
                </button>
                <button className={styles.secondaryButton} data-testid="strategy-lab-print-report-btn" disabled type="button">
                  Print summary
                </button>
              </div>
              <EmptyState title="No selected result" body={NO_DATA_MESSAGE} testId="strategy-lab-result-drilldown-empty-state" />
              <article className={styles.reportPreview} data-testid="strategy-lab-report-preview">
                <h3 className={styles.subSectionTitle}>Printable research summary</h3>
                <pre className={styles.reportText}>{NO_DATA_MESSAGE}</pre>
              </article>
            </div>
          ) : (
            <div className={styles.cardStack}>
              <div className={styles.exportActions} data-testid="strategy-lab-report-actions">
                <button className={styles.secondaryButton} data-testid="strategy-lab-export-json-btn" onClick={handleExportJson} type="button">
                  Export JSON
                </button>
                <button className={styles.secondaryButton} data-testid="strategy-lab-export-csv-btn" onClick={handleExportCsv} type="button">
                  Export CSV
                </button>
                <button className={styles.secondaryButton} data-testid="strategy-lab-copy-report-btn" onClick={() => void handleCopyReportText()} type="button">
                  Copy report text
                </button>
                <button className={styles.secondaryButton} data-testid="strategy-lab-print-report-btn" onClick={handlePrintReport} type="button">
                  Print summary
                </button>
              </div>
              <div className={styles.metricGridCompact}>
                <MetricCard label="Strategy" value={selectedResultRow.strategyName} helper={`${selectedResultRow.asset} • ${selectedResultRow.timeframe}`} />
                <MetricCard label="Total trades" value={String(selectedResultRow.totalTrades)} helper={`Win rate ${formatPercent(selectedResultRow.winRate != null ? selectedResultRow.winRate * 100 : null)}`} />
                <MetricCard label="Quality" value={selectedResultRow.qualityGrade ?? "-"} helper={`Confidence ${confidenceLabel(selectedResultRow.confidence)}`} />
                <MetricCard label="Validation" value={selectedResultRow.stabilityGrade ?? "-"} helper={selectedResultRow.costSensitivity ?? "No cost sensitivity tag"} />
              </div>
              <div className={styles.detailGrid}>
                <div className={styles.infoCard}>
                  <p className={styles.infoTitle}>Return profile</p>
                  <div className={styles.warningList}>
                    <p className={styles.warningItem}>Gross return: {formatPercent(selectedResultRow.grossReturn)}</p>
                    <p className={styles.warningItem}>Base-net return: {formatPercent(selectedResultRow.baseNetReturn)}</p>
                    <p className={styles.warningItem}>High-cost return: {formatPercent(selectedResultRow.highCostNetReturn)}</p>
                    <p className={styles.warningItem}>
                      High-cost delta vs base: {formatSignedPercent(
                        selectedResultRow.highCostNetReturn != null && selectedResultRow.baseNetReturn != null
                          ? selectedResultRow.highCostNetReturn - selectedResultRow.baseNetReturn
                          : null,
                      )}
                    </p>
                  </div>
                </div>
                <div className={styles.infoCard}>
                  <p className={styles.infoTitle}>Risk and quality profile</p>
                  <div className={styles.warningList}>
                    <p className={styles.warningItem}>Gross PF: {formatNumber(selectedResultRow.grossProfitFactor)}</p>
                    <p className={styles.warningItem}>Base-net PF: {formatNumber(selectedResultRow.baseNetProfitFactor)}</p>
                    <p className={styles.warningItem}>High-cost PF: {formatNumber(selectedResultRow.highCostProfitFactor)}</p>
                    <p className={styles.warningItem}>Overfitting risk: {formatNumber(selectedResultRow.overfittingRisk)}</p>
                    <p className={styles.warningItem}>Max drawdown: {formatPercent(selectedResultRow.maxDrawdown)}</p>
                  </div>
                </div>
              </div>
              <div className={styles.warningList}>
                <p className={styles.warningItem}>Research only. Not approved for paper or live trading.</p>
                <p className={styles.warningItem}>Selected run: {selectedRun?.name ?? "-"}</p>
                <p className={styles.warningItem}>Selected comparison run: {selectedComparisonId ?? "-"}</p>
                {(selectedResultRow.warnings.length ? selectedResultRow.warnings : ["No additional strategy warnings."]).map((warning) => (
                  <p className={styles.warningItem} key={warning}>{warning}</p>
                ))}
              </div>
              <article className={styles.reportPreview} data-testid="strategy-lab-report-preview">
                <h3 className={styles.subSectionTitle}>Printable research summary</h3>
                <pre className={styles.reportText}>{reportText}</pre>
              </article>
            </div>
          )}
        </section>

        <div className={styles.analyticsGrid}>
          <section className={styles.section} data-testid="strategy-lab-cost-model-section">
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}>Cost modelling</h2>
              <p className={styles.sectionSubtitle}>Low/base/high scenarios are deterministic research assumptions only.</p>
            </div>
            <div className={styles.cardStack}>
              <div className={styles.infoCard}>
                <p className={styles.infoTitle}>Cost model version</p>
                <p className={styles.infoValue}>{safetyWarnings.cost_model_version ?? "mh15c_v1"}</p>
                <p className={styles.infoBody}>Default profile: standard_research. Default stress preset: normal_liquidity.</p>
              </div>
              <div className={styles.infoCard}>
                <p className={styles.infoTitle}>Scenario guide</p>
                <p className={styles.infoBody}>Low, base, and high scenarios show how spread, slippage, commission, and stress assumptions affect net performance.</p>
              </div>
              <div className={styles.subSection}>
                <h3 className={styles.subSectionTitle}>Research cost profiles</h3>
                {costProfiles.length === 0 ? (
                  <EmptyState title="No cost profiles" body="Cost profile metadata is unavailable right now." />
                ) : (
                  <div className={styles.compactTableWrap}>
                    <table className={styles.compactTable}>
                      <thead>
                        <tr>
                          <th className={styles.th}>Profile</th>
                          <th className={styles.th}>Multiplier</th>
                          <th className={styles.th}>Broker calibrated</th>
                        </tr>
                      </thead>
                      <tbody>
                        {costProfiles.map((profile) => (
                          <tr key={profile.profile_name}>
                            <td className={styles.td}>{profile.profile_label}</td>
                            <td className={styles.td}>{formatNumber(profile.profile_multiplier)}</td>
                            <td className={styles.td}>No</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
              <div className={styles.subSection}>
                <h3 className={styles.subSectionTitle}>Stress presets</h3>
                {stressPresets.length === 0 ? (
                  <EmptyState title="No stress presets" body="Stress preset metadata is unavailable right now." />
                ) : (
                  <div className={styles.compactTableWrap}>
                    <table className={styles.compactTable}>
                      <thead>
                        <tr>
                          <th className={styles.th}>Preset</th>
                          <th className={styles.th}>Spread</th>
                          <th className={styles.th}>Slippage</th>
                          <th className={styles.th}>Commission</th>
                        </tr>
                      </thead>
                      <tbody>
                        {stressPresets.map((preset) => (
                          <tr key={preset.preset_name}>
                            <td className={styles.td}>{preset.preset_label}</td>
                            <td className={styles.td}>{formatNumber(preset.spread_multiplier)}</td>
                            <td className={styles.td}>{formatNumber(preset.slippage_multiplier)}</td>
                            <td className={styles.td}>{formatNumber(preset.commission_multiplier)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          </section>

          <section className={styles.section} data-testid="strategy-lab-quality-section">
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}>Quality summary</h2>
              <p className={styles.sectionSubtitle}>Confidence, overfitting risk, and grade distribution remain research guidance only.</p>
            </div>
            {!qualitySummary ? (
              <EmptyState title="No quality summary" body={NO_DATA_MESSAGE} />
            ) : (
              <div className={styles.cardStack}>
                <div className={styles.metricGridCompact}>
                  <MetricCard label="Average confidence" value={confidenceLabel(qualitySummary.average_confidence)} />
                  <MetricCard label="Highest overfitting risk" value={formatNumber(qualitySummary.highest_overfitting_risk)} />
                  <MetricCard label="Paper trading" value="Not paper ready" />
                  <MetricCard label="Live trading" value="Not live ready" />
                </div>
                <div className={styles.subSection}>
                  <h3 className={styles.subSectionTitle}>Grade distribution</h3>
                  <div className={styles.barList}>
                    {Object.entries(qualitySummary.grade_distribution).map(([grade, count]) => (
                      <div className={styles.barRow} key={grade}>
                        <span className={styles.barLabel}>{grade}</span>
                        <div className={styles.barTrack}>
                          <div className={styles.barFill} style={{ width: `${Math.min(100, count * 20)}%` }} />
                        </div>
                        <span className={styles.barValue}>{count}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div className={styles.warningList}>
                  {(qualitySummary.warnings.length ? qualitySummary.warnings : ["No additional quality warnings."]).map((warning) => (
                    <p className={styles.warningItem} key={warning}>{warning}</p>
                  ))}
                </div>
              </div>
            )}
          </section>

          <section className={styles.section} data-testid="strategy-lab-walk-forward-section">
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}>Walk-forward validation</h2>
              <p className={styles.sectionSubtitle}>In-sample, validation, out-of-sample, and rolling-window folds are research guidance only.</p>
            </div>
            {!walkForward || !selectedValidation ? (
              <EmptyState title="No walk-forward data" body={NO_DATA_MESSAGE} testId="strategy-lab-walk-forward-empty-state" />
            ) : (
              <div className={styles.cardStack}>
                <div className={styles.metricGridCompact}>
                  <MetricCard
                    label="Fold count"
                    value={String(walkForward.rolling_window_summary?.fold_count ?? selectedValidation.folds.length ?? 1)}
                  />
                  <MetricCard label="Stability score" value={formatNumber(selectedValidation.validation_stability_score, 0)} />
                  <MetricCard label="Stability grade" value={selectedValidation.validation_stability_grade} />
                  <MetricCard label="Out-of-sample" value={selectedValidation.out_of_sample_pass ? "Passed" : "Not passed"} />
                  <MetricCard label="Return degradation" value={formatPercent(selectedValidation.return_degradation_pct)} />
                  <MetricCard label="Confidence degradation" value={formatPercent(selectedValidation.confidence_degradation_pct)} />
                </div>
                <div className={styles.subSection}>
                  <h3 className={styles.subSectionTitle}>Period metrics</h3>
                  <div className={styles.compactTableWrap}>
                    <table className={styles.compactTable}>
                      <thead>
                        <tr>
                          <th className={styles.th}>Period</th>
                          <th className={styles.th}>Trades</th>
                          <th className={styles.th}>Return</th>
                          <th className={styles.th}>PF</th>
                          <th className={styles.th}>Quality</th>
                        </tr>
                      </thead>
                      <tbody>
                        {[selectedValidation.in_sample, selectedValidation.validation, selectedValidation.out_of_sample].map((period) => (
                          <tr key={period.period}>
                            <td className={styles.td}>{period.period}</td>
                            <td className={styles.td}>{period.total_trades}</td>
                            <td className={styles.td}>{formatPercent(period.net_total_return_pct)}</td>
                            <td className={styles.td}>{formatNumber(period.net_profit_factor)}</td>
                            <td className={styles.td}>{period.quality_grade ?? "-"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
                <div className={styles.subSection}>
                  <h3 className={styles.subSectionTitle}>Rolling folds</h3>
                  {selectedValidation.folds.length === 0 ? (
                    <p className={styles.mutedCopy}>Single-fold validation only.</p>
                  ) : (
                    <div className={styles.compactTableWrap}>
                      <table className={styles.compactTable}>
                        <thead>
                          <tr>
                            <th className={styles.th}>Fold</th>
                            <th className={styles.th}>Stability</th>
                            <th className={styles.th}>Out-of-sample</th>
                            <th className={styles.th}>Return degradation</th>
                            <th className={styles.th}>Warnings</th>
                          </tr>
                        </thead>
                        <tbody>
                          {selectedValidation.folds.map((fold) => (
                            <tr key={fold.fold_index}>
                              <td className={styles.td}>Fold {fold.fold_index}</td>
                              <td className={styles.td}>{fold.validation_stability_grade}</td>
                              <td className={styles.td}>{fold.out_of_sample_pass ? "Passed" : "Not passed"}</td>
                              <td className={styles.td}>{formatPercent(fold.return_degradation_pct)}</td>
                              <td className={styles.td}>{fold.warnings.map((warning) => warning.message).join(" | ") || "-"}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
                <div className={styles.warningList}>
                  {(walkForward.rolling_window_summary?.warnings ?? selectedValidation.warnings).map((warning) => (
                    <p className={styles.warningItem} key={warning.message}>{warning.message}</p>
                  ))}
                </div>
              </div>
            )}
          </section>

          <section className={styles.section} data-testid="strategy-lab-ai-report-section">
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}>AI research reports</h2>
              <p className={styles.sectionSubtitle}>Optional research summaries only. No signal generation or trading actions are exposed here.</p>
            </div>
            {!latestAiReport ? (
              <EmptyState title="No AI report" body={NO_DATA_MESSAGE} testId="strategy-lab-ai-empty-state" />
            ) : (
              <div className={styles.cardStack} data-testid="strategy-lab-ai-report-card">
                <div className={styles.metricGridCompact}>
                  <MetricCard label="Report status" value={latestAiReport.status} />
                  <MetricCard label="Created" value={formatDateTime(latestAiReport.created_at)} />
                  <MetricCard label="Confidence" value={confidenceLabel(latestAiReport.confidence_score)} />
                  <MetricCard label="Research scope" value="Review only" />
                </div>
                <div className={styles.infoCard}>
                  <p className={styles.infoTitle}>Summary</p>
                  <p className={styles.infoBody}>{latestAiSummary(latestAiReport)}</p>
                </div>
                <div className={styles.warningList}>
                  <p className={styles.warningItem}>Research only. Not approved for paper or live trading.</p>
                  {latestAiReport.research_warnings?.warning ? (
                    <p className={styles.warningItem}>{latestAiReport.research_warnings.warning}</p>
                  ) : null}
                </div>
              </div>
            )}
          </section>
        </div>

        <section className={styles.section} data-testid="strategy-lab-run-diagnostics-section">
          <div className={styles.sectionHeader}>
            <h2 className={styles.sectionTitle}>Run diagnostics</h2>
            <p className={styles.sectionSubtitle}>Equity curve and drawdown review for the selected backtest run.</p>
          </div>
          {!selectedRun ? (
            <EmptyState title="No selected run" body={NO_DATA_MESSAGE} />
          ) : (
            <div className={styles.diagnosticsGrid}>
              <div className={styles.infoCard}>
                <p className={styles.infoTitle}>Equity curve</p>
                {equityCurve.length === 0 ? (
                  <p className={styles.infoBody}>No equity curve points are available for this run.</p>
                ) : (
                  <svg className={styles.sparkline} viewBox="0 0 520 180" role="img" aria-label="Equity curve preview">
                    <polyline fill="none" points={equityPolyline} stroke="currentColor" strokeWidth="3" />
                  </svg>
                )}
              </div>
              <div className={styles.infoCard}>
                <p className={styles.infoTitle}>Drawdown summary</p>
                <p className={styles.infoBody}>Drawdown periods: {drawdowns.length}</p>
                <p className={styles.infoBody}>
                  Worst drawdown: {formatPercent(drawdowns.reduce<number | null>((worst, row) => (
                    worst == null || row.max_drawdown_pct > worst ? row.max_drawdown_pct : worst
                  ), null))}
                </p>
                <p className={styles.infoBody}>Closed trades reviewed: {trades.length}</p>
              </div>
            </div>
          )}
        </section>
      </div>
    </section>
  );
}