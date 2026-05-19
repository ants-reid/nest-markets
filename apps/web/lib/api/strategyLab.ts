import { apiRequest } from "./core";
import type {
  BacktestReplayRequest,
  BacktestReplayResponse,
  BacktestRun,
  BacktestRunCreateRequest,
  BacktestRunListResponse,
  CostModelProfileListResponse,
  CostModelStressPresetListResponse,
  DrawdownPeriodListResponse,
  EquityCurveResponse,
  MockTradeListResponse,
  QualitySummary,
  StrategyComparisonDetailResponse,
  StrategyComparisonHistoryResponse,
  StrategyComparisonLabelRequest,
  StrategyComparisonLabelResponse,
  StrategyComparison,
  StrategyComparisonRequest,
  StrategyComparisonResponse,
  StrategyConfig,
  StrategyConfigCreateRequest,
  StrategyConfigListResponse,
  StrategyResultListResponse,
  AIBacktestReport,
  AIBacktestReportRequest,
  AIBacktestReportListResponse,
  WalkForwardSplitRequest,
  WalkForwardValidation,
  BaselineCandidate,
  BaselineCandidateCreateRequest,
  BaselineCandidateListResponse,
  BaselineCandidateRejectRequest,
  BaselineCandidateUpdateRequest,
  PaperValidationEvent,
  PaperValidationEvidence,
  PaperValidationEvidenceListResponse,
  PaperValidationManualEvidenceRequest,
  PaperValidationPlan,
  PaperValidationPlanActionRequest,
  PaperValidationPlanCreateRequest,
  PaperValidationPlanListResponse,
  PaperValidationPlanUpdateRequest,
  PaperValidationReconcileRequest,
  PaperValidationReconcileResponse,
  PaperValidationDashboardResponse,
  PaperValidationReadinessResponse,
} from "../types";

export async function createStrategyConfig(
  request: StrategyConfigCreateRequest,
): Promise<StrategyConfig> {
  return apiRequest<StrategyConfig>("/strategy-lab/configs", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function getStrategyConfigs(): Promise<StrategyConfigListResponse> {
  return apiRequest<StrategyConfigListResponse>("/strategy-lab/configs", {
    method: "GET",
  });
}

export async function getStrategyConfig(configId: string): Promise<StrategyConfig> {
  return apiRequest<StrategyConfig>(`/strategy-lab/configs/${configId}`, {
    method: "GET",
  });
}

export async function createBacktestRun(
  request: BacktestRunCreateRequest,
): Promise<BacktestRun> {
  return apiRequest<BacktestRun>("/strategy-lab/backtests", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function getBacktestRuns(): Promise<BacktestRunListResponse> {
  return apiRequest<BacktestRunListResponse>("/strategy-lab/backtests", {
    method: "GET",
  });
}

export async function getBacktestRun(backtestId: string): Promise<BacktestRun> {
  return apiRequest<BacktestRun>(`/strategy-lab/backtests/${backtestId}`, {
    method: "GET",
  });
}

export async function replayBacktest(
  backtestId: string,
  request: BacktestReplayRequest,
): Promise<BacktestReplayResponse> {
  return apiRequest<BacktestReplayResponse>(`/strategy-lab/backtests/${backtestId}/replay`, {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function getBacktestTrades(backtestId: string): Promise<MockTradeListResponse> {
  return apiRequest<MockTradeListResponse>(`/strategy-lab/backtests/${backtestId}/trades`, {
    method: "GET",
  });
}

export async function getBacktestResults(backtestId: string): Promise<StrategyResultListResponse> {
  return apiRequest<StrategyResultListResponse>(`/strategy-lab/backtests/${backtestId}/results`, {
    method: "GET",
  });
}

export async function getBacktestEquityCurve(backtestId: string): Promise<EquityCurveResponse> {
  return apiRequest<EquityCurveResponse>(`/strategy-lab/backtests/${backtestId}/equity-curve`, {
    method: "GET",
  });
}

export async function getBacktestDrawdowns(backtestId: string): Promise<DrawdownPeriodListResponse> {
  return apiRequest<DrawdownPeriodListResponse>(`/strategy-lab/backtests/${backtestId}/drawdowns`, {
    method: "GET",
  });
}

export async function runStrategyComparison(
  request: StrategyComparisonRequest,
): Promise<StrategyComparisonResponse> {
  return apiRequest<StrategyComparisonResponse>("/strategy-lab/comparisons/run", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function getStrategyComparisonHistory(): Promise<StrategyComparisonHistoryResponse> {
  return apiRequest<StrategyComparisonHistoryResponse>("/strategy-lab/comparisons", {
    method: "GET",
  });
}

export async function getStrategyComparisons(): Promise<StrategyComparisonHistoryResponse> {
  return getStrategyComparisonHistory();
}

export async function getStrategyComparisonDetail(
  backtestRunId: string,
): Promise<StrategyComparisonDetailResponse> {
  return apiRequest<StrategyComparisonDetailResponse>(`/strategy-lab/comparisons/${backtestRunId}`, {
    method: "GET",
  });
}

export async function labelStrategyComparison(
  backtestRunId: string,
  request: StrategyComparisonLabelRequest,
): Promise<StrategyComparisonLabelResponse> {
  return apiRequest<StrategyComparisonLabelResponse>(`/strategy-lab/comparisons/${backtestRunId}/label`, {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function getBacktestQualitySummary(backtestId: string): Promise<QualitySummary> {
  return apiRequest<QualitySummary>(`/strategy-lab/backtests/${backtestId}/quality-summary`, {
    method: "GET",
  });
}

export async function getBacktestWalkForward(backtestId: string): Promise<WalkForwardValidation> {
  return apiRequest<WalkForwardValidation>(`/strategy-lab/backtests/${backtestId}/walk-forward`, {
    method: "GET",
  });
}

export async function runWalkForwardValidation(
  backtestId: string,
  request: WalkForwardSplitRequest = {},
): Promise<WalkForwardValidation> {
  return apiRequest<WalkForwardValidation>(`/strategy-lab/backtests/${backtestId}/walk-forward`, {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function getCostModelProfiles(): Promise<CostModelProfileListResponse> {
  return apiRequest<CostModelProfileListResponse>("/strategy-lab/cost-model/profiles", {
    method: "GET",
  });
}

export async function getCostModelStressPresets(): Promise<CostModelStressPresetListResponse> {
  return apiRequest<CostModelStressPresetListResponse>("/strategy-lab/cost-model/stress-presets", {
    method: "GET",
  });
}

export async function createAIBacktestReport(
  backtestId: string,
  request: AIBacktestReportRequest,
): Promise<AIBacktestReport> {
  return generateAIBacktestReport(backtestId, request);
}

// ── MH-14 AI Backtest Reports ──────────────────────────────────────────────

export async function generateAIBacktestReport(
  backtestId: string,
  request: AIBacktestReportRequest,
): Promise<AIBacktestReport> {
  return apiRequest<AIBacktestReport>(`/strategy-lab/backtests/${backtestId}/ai-report`, {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function getAIBacktestReports(
  backtestId: string,
): Promise<AIBacktestReportListResponse> {
  return apiRequest<AIBacktestReportListResponse>(`/strategy-lab/backtests/${backtestId}/ai-reports`, {
    method: "GET",
  });
}

export async function getAIBacktestReport(reportId: string): Promise<AIBacktestReport> {
  return apiRequest<AIBacktestReport>(`/strategy-lab/ai-reports/${reportId}`, {
    method: "GET",
  });
}

// ── MH-15 Baseline Candidates ─────────────────────────────────────────────

export async function createBaselineCandidate(
  request: BaselineCandidateCreateRequest,
): Promise<BaselineCandidate> {
  return apiRequest<BaselineCandidate>("/baseline-candidates", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function getBaselineCandidates(
  params?: { status?: string; backtest_run_id?: string },
): Promise<BaselineCandidateListResponse> {
  const query = new URLSearchParams();
  if (params?.status) query.set("status", params.status);
  if (params?.backtest_run_id) query.set("backtest_run_id", params.backtest_run_id);
  const suffix = query.toString() ? `?${query.toString()}` : "";

  return apiRequest<BaselineCandidateListResponse>(`/baseline-candidates${suffix}`, {
    method: "GET",
  });
}

export async function getBaselineCandidate(candidateId: string): Promise<BaselineCandidate> {
  return apiRequest<BaselineCandidate>(`/baseline-candidates/${candidateId}`, {
    method: "GET",
  });
}

export async function updateBaselineCandidate(
  candidateId: string,
  request: BaselineCandidateUpdateRequest,
): Promise<BaselineCandidate> {
  return apiRequest<BaselineCandidate>(`/baseline-candidates/${candidateId}`, {
    method: "PATCH",
    body: JSON.stringify(request),
  });
}

export async function rejectBaselineCandidate(
  candidateId: string,
  request: BaselineCandidateRejectRequest,
): Promise<BaselineCandidate> {
  return apiRequest<BaselineCandidate>(`/baseline-candidates/${candidateId}/reject`, {
    method: "POST",
    body: JSON.stringify(request),
  });
}

// ── MH-16 Paper Validation ────────────────────────────────────────────────

export async function createPaperValidationPlan(
  request: PaperValidationPlanCreateRequest,
): Promise<PaperValidationPlan> {
  return apiRequest<PaperValidationPlan>("/paper-validation/plans", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function getPaperValidationPlans(
  params?: { status?: string; baseline_candidate_id?: string; backtest_run_id?: string },
): Promise<PaperValidationPlanListResponse> {
  const query = new URLSearchParams();
  if (params?.status) query.set("status", params.status);
  if (params?.baseline_candidate_id) query.set("baseline_candidate_id", params.baseline_candidate_id);
  if (params?.backtest_run_id) query.set("backtest_run_id", params.backtest_run_id);
  const suffix = query.toString() ? `?${query.toString()}` : "";

  return apiRequest<PaperValidationPlanListResponse>(`/paper-validation/plans${suffix}`, {
    method: "GET",
  });
}

export async function getPaperValidationPlan(planId: string): Promise<PaperValidationPlan> {
  return apiRequest<PaperValidationPlan>(`/paper-validation/plans/${planId}`, {
    method: "GET",
  });
}

export async function updatePaperValidationPlan(
  planId: string,
  request: PaperValidationPlanUpdateRequest,
): Promise<PaperValidationPlan> {
  return apiRequest<PaperValidationPlan>(`/paper-validation/plans/${planId}`, {
    method: "PATCH",
    body: JSON.stringify(request),
  });
}

export async function startPaperValidationPlan(
  planId: string,
  request: PaperValidationPlanActionRequest,
): Promise<PaperValidationPlan> {
  return apiRequest<PaperValidationPlan>(`/paper-validation/plans/${planId}/start`, {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function stopPaperValidationPlan(
  planId: string,
  request: PaperValidationPlanActionRequest,
): Promise<PaperValidationPlan> {
  return apiRequest<PaperValidationPlan>(`/paper-validation/plans/${planId}/stop`, {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function recalculatePaperValidationPlan(
  planId: string,
): Promise<PaperValidationPlan> {
  return apiRequest<PaperValidationPlan>(`/paper-validation/plans/${planId}/recalculate`, {
    method: "POST",
  });
}

export async function getPaperValidationEvents(planId: string): Promise<PaperValidationEvent[]> {
  return apiRequest<PaperValidationEvent[]>(`/paper-validation/plans/${planId}/events`, {
    method: "GET",
  });
}

// ── MH-17 Evidence / Reconciliation ────────────────────────────────────────

export async function getPaperValidationEvidence(
  planId: string,
): Promise<PaperValidationEvidenceListResponse> {
  return apiRequest<PaperValidationEvidenceListResponse>(
    `/paper-validation/plans/${planId}/evidence`,
    { method: "GET" },
  );
}

export async function addManualPaperValidationEvidence(
  planId: string,
  request: PaperValidationManualEvidenceRequest,
): Promise<PaperValidationEvidence> {
  return apiRequest<PaperValidationEvidence>(
    `/paper-validation/plans/${planId}/evidence/manual`,
    { method: "POST", body: JSON.stringify(request) },
  );
}

export async function excludePaperValidationEvidence(
  planId: string,
  evidenceId: string,
): Promise<PaperValidationEvidence> {
  return apiRequest<PaperValidationEvidence>(
    `/paper-validation/plans/${planId}/evidence/${evidenceId}/exclude`,
    { method: "POST" },
  );
}

export async function includePaperValidationEvidence(
  planId: string,
  evidenceId: string,
): Promise<PaperValidationEvidence> {
  return apiRequest<PaperValidationEvidence>(
    `/paper-validation/plans/${planId}/evidence/${evidenceId}/include`,
    { method: "POST" },
  );
}

export async function reconcilePaperValidationPlan(
  planId: string,
  request: PaperValidationReconcileRequest,
): Promise<PaperValidationReconcileResponse> {
  return apiRequest<PaperValidationReconcileResponse>(
    `/paper-validation/plans/${planId}/reconcile`,
    { method: "POST", body: JSON.stringify(request) },
  );
}

// ── MH-18: Dashboard & Readiness Review ────────────────────────────────────

export async function getPaperValidationDashboard(): Promise<PaperValidationDashboardResponse> {
  return apiRequest<PaperValidationDashboardResponse>("/paper-validation/dashboard", {
    method: "GET",
  });
}

export async function getPaperValidationReadiness(
  planId: string,
): Promise<PaperValidationReadinessResponse> {
  return apiRequest<PaperValidationReadinessResponse>(
    `/paper-validation/plans/${planId}/readiness`,
    { method: "GET" },
  );
}
