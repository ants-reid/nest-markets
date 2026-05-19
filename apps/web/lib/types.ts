export type Timeframe = "15m" | "1h" | "4h" | "1d";

export type ExecutionMode = "paper" | "confirm_live" | "auto_live";

export type SignalDirection = "long" | "short" | "flat";

export type SignalRegime =
  | "trend"
  | "range"
  | "breakout"
  | "high_volatility"
  | "low_volatility"
  | "risk_on"
  | "risk_off";

export type SignalSetupType = "trend_pullback" | "breakout_confirmation" | "news_continuation" | "none";

export type HorizonLabel = "intraday" | "1_3_days" | "3_10_days";

export type CatalystType =
  | "none"
  | "macro"
  | "earnings"
  | "sector_news"
  | "commodity_move"
  | "central_bank"
  | "geopolitics";

export interface SignalResponse {
  asset: string;
  timeframe: Timeframe;
  direction: SignalDirection;
  regime: SignalRegime;
  setup_type: SignalSetupType;
  entry_zone: [number, number];
  stop_price: number;
  target_price: number;
  confidence: number;
  horizon_label: HorizonLabel;
  catalyst_type: CatalystType;
  catalyst_score: number;
  catalyst_summary: string;
  thesis: string;
  invalidators: string[];
  signal_score: number;
  should_trade: boolean;
}

export interface HealthStatusResponse {
  status: string;
}

export interface WorkflowSignalInput {
  asset: string;
  timeframe: Timeframe;
  latest_price: number;
  feature_snapshot: Record<string, unknown>;
  catalyst_context: Record<string, unknown>;
  risk_notes?: string | null;
}

export interface WorkflowRiskContext {
  spread_bps: number;
  daily_drawdown_pct: number;
  consecutive_losses: number;
  minutes_since_last_loss?: number | null;
  correlated_exposure_count: number;
  open_positions_count?: number;
  session_allowed?: boolean;
  kill_switch_active?: boolean;
  market_quality_flag: boolean;
  account_equity: number;
  requested_execution_mode: ExecutionMode;
}

export interface WorkflowRunRequest {
  signal_input: WorkflowSignalInput;
  risk_context: WorkflowRiskContext;
}

export interface LiveExecutionResultResponse {
  accepted: boolean;
  status: string;
  reason: string;
}

export interface WorkflowRunResponse {
  signal_id: string;
  risk_approved: boolean;
  selected_execution_mode: string;
  approval_request_id: string | null;
  paper_execution_id: string | null;
  blocked_reasons: string[];
  live_execution_result: LiveExecutionResultResponse | null;
}

export interface RiskContextRequest {
  spread_bps: number;
  daily_drawdown_pct: number;
  consecutive_losses: number;
  minutes_since_last_loss?: number | null;
  correlated_exposure_count: number;
  open_positions_count?: number;
  session_allowed?: boolean;
  kill_switch_active?: boolean;
  market_quality_flag: boolean;
  account_equity: number;
  requested_execution_mode: ExecutionMode;
}

export interface RiskEvaluateRequest {
  signal: SignalResponse;
  risk_context: RiskContextRequest;
}

export interface RiskDecisionResponse {
  approved: boolean;
  blocked_reasons: string[];
  allowed_risk_amount: number;
  selected_execution_mode: string;
  execution_mode?: string;
  position_size_pct?: number;
  risk_score?: number;
  rejection_reasons?: string[];
  notes?: string[];
}

export interface ApprovalCreateRequest {
  signal: SignalResponse;
  execution_mode: ExecutionMode;
  risk_approved?: boolean;
  ttl_minutes?: number;
}

export interface ApprovalRequestResponse {
  request_id: string;
  status: string;
  created_at: string;
  expires_at: string;
  asset: string;
  timeframe: string;
  execution_mode: string;
}

export interface PaperExecutionRequest {
  signal: SignalResponse;
  allowed_risk_amount: number;
  latest_price: number;
}

export interface PaperExecutionResponse {
  execution_id: string;
  status: string;
  asset: string;
  timeframe: string;
  side: string;
  qty: number;
  notional: number;
  stop_price: number;
  target_price: number;
  fill_price: number;
  reason?: string | null;
}

export interface LiveExecutionRequest {
  asset: string;
  side: string;
  qty: number;
  notional: number;
  stop_price: number;
  target_price: number;
}

export interface LiveExecutionResponse {
  accepted: boolean;
  status: string;
  reason: string;
  processed_at: string;
}

export interface PositionResponse {
  id: string;
  asset_id: string;
  asset_symbol: string;
  signal_id: string | null;
  status: string;
  side: string;
  avg_entry_price: number | null;
  current_price: number | null;
  stop_price: number | null;
  target_price: number | null;
  qty: number | null;
  opened_at: string | null;
  closed_at: string | null;
  close_reason: string | null;
  realized_pnl: number | null;
  unrealized_pnl: number | null;
}

export interface ResearchDataAsset {
  asset_symbol: string;
  asset_name: string | null;
  is_active: boolean;
  timeframes: string[];
  total_bars: number;
  earliest_bar_ts: string | null;
  latest_bar_ts: string | null;
  providers: string[];
}

export interface ResearchDataAssetsResponse {
  evaluated_at: string;
  total_assets: number;
  covered_assets: number;
  uncovered_assets: number;
  items: ResearchDataAsset[];
}

export interface ResearchDataProvider {
  name: string;
  label: string;
  supported_asset_classes: string[];
  supported_timeframes: string[];
  notes: string | null;
}

export interface ResearchDataProvidersResponse {
  providers: ResearchDataProvider[];
}

export interface ResearchDataQualityReport {
  asset_symbol: string;
  timeframe: string;
  provider: string | null;
  expected_bars: number | null;
  actual_bars: number | null;
  total_bars: number;
  completeness_pct: number | null;
  missing_pct: number | null;
  missing_bars: number;
  duplicate_bars: number;
  bad_price_bars: number;
  suspicious_spike_bars: number;
  stale_bars: number;
  earliest_bar_ts: string | null;
  latest_bar_ts: string | null;
  quality_score: number | null;
  approved_for_backtest: boolean | null;
  notes: string | null;
}

export interface ResearchDataQualityResponse {
  evaluated_at: string;
  total_items: number;
  items: ResearchDataQualityReport[];
}

export interface ResearchDataGap {
  id: string;
  asset_symbol: string;
  timeframe: string;
  provider: string | null;
  gap_start: string;
  gap_end: string;
  expected_candles_missing: number;
  severity: "low" | "medium" | "high";
  status: "open" | "filling" | "resolved" | "ignored";
  import_run_id: string | null;
  notes: string | null;
  created_at: string;
}

export interface ResearchDataGapsResponse {
  total: number;
  items: ResearchDataGap[];
}

export interface ResearchDataImportResult {
  asset_symbol: string;
  timeframe: string;
  provider: string;
  requested_start: string;
  requested_end: string;
  available_from: string | null;
  available_to: string | null;
  candles_imported: number;
  status: "completed" | "partial" | "failed" | "dry_run" | "skipped";
  message: string | null;
}

export interface ResearchDataImportRun {
  batch_id: string;
  status: string;
  dry_run: boolean;
  requested_years: number;
  assets: string[];
  timeframes: string[];
  providers: string[];
  started_at: string;
  completed_at: string | null;
  total_candles_imported: number;
  failed_count: number;
  run_count: number;
}

export interface ResearchDataImportRunsResponse {
  total: number;
  items: ResearchDataImportRun[];
}

export interface QualityRecalculateRequest {
  assets: string[];
  timeframes: string[];
  providers?: string[];
}

export interface QualityRecalculateItem {
  asset_symbol: string;
  timeframe: string;
  provider: string | null;
  quality_score: number;
  completeness_pct: number | null;
  missing_bars: number;
  duplicate_bars: number;
  bad_price_bars: number;
  suspicious_spike_bars: number;
  approved_for_backtest: boolean;
  gap_count: number;
  notes: string | null;
}

export interface QualityRecalculateResponse {
  total: number;
  succeeded: number;
  failed: number;
  items: QualityRecalculateItem[];
}

export type ResearchJobType = "historical_import" | "quality_recalculate";

export type ResearchJobStatus = "queued" | "running" | "completed" | "partial" | "failed" | "cancelled";

export interface ResearchJob {
  id: string;
  job_type: ResearchJobType;
  status: ResearchJobStatus;
  requested_by: string | null;
  request_payload: Record<string, unknown>;
  result_payload: Record<string, unknown> | null;
  progress_current: number;
  progress_total: number;
  progress_message: string | null;
  error_message: string | null;
  retry_of_job_id: string | null;
  started_at: string | null;
  completed_at: string | null;
  cancelled_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ResearchJobListResponse {
  total: number;
  items: ResearchJob[];
}

export interface ResearchJobDetailResponse {
  job: ResearchJob;
}

export interface ResearchJobActionResponse {
  success: boolean;
  message: string;
  job: ResearchJob | null;
}

export interface ResearchWarnings {
  research_only: boolean;
  execution_costs_modelled: boolean;
  spread_modelled: boolean;
  slippage_modelled: boolean;
  fees_modelled: boolean;
  live_ready: boolean;
  warning: string;
  cost_model_version: string | null;
  cost_model_status: string;
  cost_model_notes: string;
}

export interface StrategyConfig {
  id: string;
  name: string;
  strategy_type: string;
  asset: string;
  timeframe: string;
  parameters: Record<string, unknown>;
  risk_settings: Record<string, unknown>;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface StrategyConfigCreateRequest {
  name: string;
  strategy_type: string;
  asset: string;
  timeframe: string;
  parameters: Record<string, unknown>;
  risk_settings: Record<string, unknown>;
  enabled: boolean;
}

export interface StrategyConfigListResponse {
  total: number;
  items: StrategyConfig[];
}

export interface BacktestRun {
  id: string;
  name: string;
  status: string;
  date_from: string;
  date_to: string;
  requested_assets: string[] | { assets?: string[] };
  requested_timeframes: string[] | { timeframes?: string[] };
  strategy_config_ids: string[] | { config_ids?: string[] };
  starting_capital: number;
  result_summary: Record<string, unknown> | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
  message?: string | null;
  research_warnings?: ResearchWarnings;
}

export interface BacktestRunCreateRequest {
  name: string;
  date_from: string;
  date_to: string;
  requested_assets: string[];
  requested_timeframes: string[];
  strategy_config_ids: string[];
  starting_capital: number;
  allow_unapproved_data: boolean;
}

export interface BacktestRunListResponse {
  total: number;
  items: BacktestRun[];
}

export interface ReplayAssetSummary {
  asset: string;
  timeframe: string;
  candles_loaded: number;
  approved: boolean;
  first_timestamp: string | null;
  last_timestamp: string | null;
  skipped: boolean;
  skip_reason: string | null;
}

export interface BacktestReplayRequest {
  allow_unapproved_data: boolean;
  max_candles: number;
  simulate_trades: boolean;
  clear_existing_results: boolean;
}

export interface BacktestReplayResponse {
  backtest_run_id: string;
  status: string;
  total_candles_loaded: number;
  total_mock_trades: number;
  assets_replayed: string[];
  timeframes_replayed: string[];
  skipped_assets: string[];
  first_timestamp: string | null;
  last_timestamp: string | null;
  warnings: string[];
  asset_summaries: ReplayAssetSummary[];
  win_rate: number | null;
  profit_factor: number | null;
  max_drawdown_pct: number | null;
  total_return_pct: number | null;
  message: string;
}

export interface MockTrade {
  id: string;
  backtest_run_id: string;
  strategy_config_id: string | null;
  asset: string;
  timeframe: string;
  side: string;
  entry_time: string;
  entry_price: number;
  stop_price: number | null;
  target_price: number | null;
  exit_time: string | null;
  exit_price: number | null;
  status: string;
  result: string | null;
  pnl_amount: number | null;
  pnl_pct: number | null;
  r_multiple: number | null;
  reason_for_entry: string | null;
  reason_for_exit: string | null;
  metadata_json: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface MockTradeListResponse {
  total: number;
  items: MockTrade[];
}

export interface StrategyResult {
  id: string;
  backtest_run_id: string;
  strategy_config_id: string | null;
  asset: string | null;
  timeframe: string | null;
  total_trades: number;
  wins: number;
  losses: number;
  breakeven: number;
  win_rate: number | null;
  average_win: number | null;
  average_loss: number | null;
  profit_factor: number | null;
  expectancy: number | null;
  total_return_pct: number | null;
  max_drawdown_pct: number | null;
  score: number | null;
  metrics: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
  research_warnings?: ResearchWarnings;
}

export interface StrategyResultListResponse {
  total: number;
  items: StrategyResult[];
}

export interface EquityCurvePoint {
  id: string;
  backtest_run_id: string;
  timestamp: string;
  equity: number;
  cash: number | null;
  open_pnl: number | null;
  drawdown_pct: number | null;
  created_at: string;
}

export interface EquityCurveResponse {
  total: number;
  items: EquityCurvePoint[];
}

export interface DrawdownPeriod {
  id: string;
  backtest_run_id: string;
  start_time: string;
  trough_time: string | null;
  end_time: string | null;
  max_drawdown_pct: number;
  duration_candles: number | null;
  recovered: boolean;
  created_at: string;
}

export interface DrawdownPeriodListResponse {
  total: number;
  items: DrawdownPeriod[];
}

// ── Strategy Comparison (MH-10) ────────────────────────────────────────────

export interface StrategyComparisonRequest {
  name: string;
  asset: string;
  timeframe: string;
  date_from: string;
  date_to: string;
  starting_capital: number;
  allow_unapproved_data: boolean;
  max_candles: number;
  fast_windows: number[];
  slow_windows: number[];
  risk_rewards: number[];
  hold_bars_options: number[];
  risk_per_trade_pct_options: number[];
  max_configs: number;
}

export interface StrategyComparisonRow {
  strategy_config_id: string;
  strategy_name: string;
  backtest_run_id: string;
  asset: string;
  timeframe: string;
  parameters: Record<string, unknown>;
  total_trades: number;
  wins: number;
  losses: number;
  win_rate: number | null;
  profit_factor: number | null;
  expectancy: number | null;
  total_return_pct: number | null;
  max_drawdown_pct: number | null;
  scoring_cost_scenario?: string | null;
  high_cost_scenario_net_return_pct?: number | null;
  high_cost_scenario_profit_factor?: number | null;
  cost_sensitivity_level?: string | null;
  quality_grade?: string | null;
  research_confidence_score?: number | null;
  overfitting_risk_score?: number | null;
  quality_warnings?: string[];
  validation_stability_score?: number | null;
  validation_stability_grade?: string | null;
  out_of_sample_pass?: boolean | null;
  walk_forward_warnings?: string[];
  score: number;
  rank: number;
}

export interface StrategyComparisonResponse {
  backtest_run_id: string;
  total_configs_tested: number;
  asset: string;
  timeframe: string;
  cost_profile_used?: string | null;
  stress_preset_used?: string | null;
  broker_calibrated?: boolean;
  rows: StrategyComparisonRow[];
  warnings: string[];
  message: string;
  research_warnings?: ResearchWarnings;
}

export interface StrategyComparison extends StrategyComparisonResponse {}

export interface CostModelProfile {
  profile_name: string;
  profile_label: string;
  profile_description: string;
  profile_multiplier: number;
  intended_use: string;
  is_broker_calibrated: boolean;
  live_ready: boolean;
}

export interface CostModelProfileListResponse {
  total: number;
  items: CostModelProfile[];
}

export interface CostModelStressPreset {
  preset_name: string;
  preset_label: string;
  preset_description: string;
  spread_multiplier: number;
  slippage_multiplier: number;
  commission_multiplier: number;
  is_broker_calibrated: boolean;
  live_ready: boolean;
}

export interface CostModelStressPresetListResponse {
  total: number;
  items: CostModelStressPreset[];
}

export interface QualitySummary {
  backtest_run_id: string;
  total_strategies: number;
  average_confidence: number;
  grade_distribution: Record<string, number>;
  highest_overfitting_risk: number;
  warnings: string[];
  paper_trade_ready: boolean;
  live_ready: boolean;
}

export interface WalkForwardSplitRequest {
  in_sample_pct?: number;
  validation_pct?: number;
  out_of_sample_pct?: number;
  fold_count?: number;
}

export interface WalkForwardDateSplit {
  period: string;
  start: string;
  end: string;
  percentage: number;
}

export interface WalkForwardPeriodMetrics {
  period: string;
  total_trades: number;
  win_rate: number | null;
  net_profit_factor: number | null;
  net_total_return_pct: number | null;
  max_drawdown_pct: number | null;
  research_confidence_score: number | null;
  quality_grade: string | null;
}

export interface WalkForwardWarning {
  message: string;
}

export interface WalkForwardFold {
  fold_index: number;
  splits: WalkForwardDateSplit[];
  in_sample: WalkForwardPeriodMetrics;
  validation: WalkForwardPeriodMetrics;
  out_of_sample: WalkForwardPeriodMetrics;
  validation_stability_score: number;
  validation_stability_grade: string;
  out_of_sample_pass: boolean;
  return_degradation_pct: number;
  profit_factor_degradation_pct: number;
  confidence_degradation_pct: number;
  warnings: WalkForwardWarning[];
}

export interface RollingWindowSummary {
  fold_count: number;
  stable_fold_ratio: number;
  average_validation_stability_score: number;
  stability_dispersion: number;
  average_return_degradation_pct: number;
  average_confidence_degradation_pct: number;
  rolling_validation_grade: string;
  rolling_out_of_sample_pass: boolean;
  warnings: WalkForwardWarning[];
}

export interface WalkForwardStrategyValidation {
  strategy_config_id: string | null;
  strategy_name: string | null;
  in_sample: WalkForwardPeriodMetrics;
  validation: WalkForwardPeriodMetrics;
  out_of_sample: WalkForwardPeriodMetrics;
  folds: WalkForwardFold[];
  in_sample_return: number;
  validation_return: number;
  out_of_sample_return: number;
  out_of_sample_profit_factor: number;
  return_degradation_pct: number;
  profit_factor_degradation_pct: number;
  confidence_degradation_pct: number;
  validation_stability_score: number;
  validation_stability_grade: string;
  out_of_sample_pass: boolean;
  paper_trade_ready: boolean;
  live_ready: boolean;
  warnings: WalkForwardWarning[];
}

export interface WalkForwardValidation {
  backtest_run_id: string;
  splits: WalkForwardDateSplit[];
  strategies: WalkForwardStrategyValidation[];
  rolling_window_summary: RollingWindowSummary | null;
  warnings: WalkForwardWarning[];
  paper_trade_ready: boolean;
  live_ready: boolean;
}

export interface StrategyComparisonHistoryRow {
  backtest_run_id: string;
  name: string;
  status: string;
  date_from: string;
  date_to: string;
  requested_assets: string[];
  requested_timeframes: string[];
  starting_capital: number;
  created_at: string;
  completed_at: string | null;
  total_configs_tested: number;
  best_score: number | null;
  best_asset: string | null;
  best_timeframe: string | null;
  best_strategy_config_id: string | null;
  best_strategy_name: string | null;
  best_parameters: Record<string, unknown> | null;
  best_total_trades: number | null;
  best_win_rate: number | null;
  best_profit_factor: number | null;
  best_total_return_pct: number | null;
  best_max_drawdown_pct: number | null;
}

export interface StrategyComparisonHistoryResponse {
  total: number;
  items: StrategyComparisonHistoryRow[];
}

export interface StrategyComparisonEquityCurveSummary {
  total_points: number;
  start_equity: number | null;
  end_equity: number | null;
  peak_equity: number | null;
  latest_drawdown_pct: number | null;
  total_return_pct: number | null;
  preview_points: number[];
}

export interface StrategyComparisonDrawdownSummary {
  total_periods: number;
  worst_drawdown_pct: number | null;
  recovered_periods: number;
  open_periods: number;
}

export interface StrategyComparisonDetailResponse {
  backtest_run: BacktestRun;
  ranked_rows: StrategyComparisonRow[];
  mock_trade_count: number;
  equity_curve_summary: StrategyComparisonEquityCurveSummary;
  drawdown_summary: StrategyComparisonDrawdownSummary;
  warnings: string[];
  research_label: "watchlist_candidate" | "rejected" | "needs_more_testing" | null;
  research_notes: string | null;
  research_warnings?: ResearchWarnings;
}

export interface StrategyComparisonLabelRequest {
  research_label: "watchlist_candidate" | "rejected" | "needs_more_testing";
  research_notes: string;
}

export interface StrategyComparisonLabelResponse {
  backtest_run_id: string;
  research_label: "watchlist_candidate" | "rejected" | "needs_more_testing";
  research_notes: string;
  updated: boolean;
}

// ── MH-12 Data Quality Review ─────────────────────────────────────────────

export type DataQualityReviewStatus =
  | "unreviewed"
  | "valid_market_move"
  | "bad_data"
  | "needs_provider_check"
  | "ignore_for_now";

export interface DataQualityOutlierItem {
  id: string;
  asset_symbol: string;
  timeframe: string;
  provider: string | null;
  quality_score: number | null;
  approved_for_backtest: boolean;
  suspicious_spike_bars: number;
  bad_price_bars: number;
  missing_bars: number;
  completeness_pct: number | null;
  total_bars: number;
  evaluated_at: string;
  review_status: DataQualityReviewStatus;
  review_notes: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
}

export interface DataQualityOutliersResponse {
  total: number;
  items: DataQualityOutlierItem[];
}

export interface DataQualityReviewRequest {
  review_status: DataQualityReviewStatus;
  review_notes?: string | null;
  reviewed_by?: string | null;
}

export interface DataQualityReviewResponse {
  id: string;
  asset_symbol: string;
  timeframe: string;
  review_status: DataQualityReviewStatus;
  review_notes: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
}

export interface DataQualityAuditEntry {
  id: string;
  report_id: string;
  asset_symbol: string;
  timeframe: string;
  provider: string | null;
  previous_status: string | null;
  new_status: string;
  review_notes: string | null;
  reviewed_by: string | null;
  reviewed_at: string;
  created_at: string;
}

export interface DataQualityAuditResponse {
  total: number;
  entries: DataQualityAuditEntry[];
}

export interface DataQualityUnreviewedSummary {
  total_flagged: number;
  unreviewed: number;
  reviewed: number;
  by_status: Record<string, number>;
}

// ── MH-14 AI Backtest Reports ──────────────────────────────────────────────

export interface AIReportContent {
  plain_english_summary: string;
  strongest_configs: Array<string | AIReportConfigItem>;
  weak_configs: Array<string | AIReportConfigItem>;
  overfitting_warnings: string[];
  sample_size_warnings: string[];
  risk_notes: string[];
  data_quality_notes: string[];
  recommended_next_tests: string[];
  reject_or_continue: "continue_testing" | "needs_more_data" | "reject_for_now";
  confidence_score: number;
}

export interface AIReportConfigMetrics {
  total_trades?: number | null;
  win_rate?: number | null;
  profit_factor?: number | null;
  total_return_pct?: number | null;
  max_drawdown_pct?: number | null;
  score?: number | null;
}

export interface AIReportConfigItem {
  strategy_config_id?: string | null;
  strategy_name?: string | null;
  reason?: string | null;
  metrics?: AIReportConfigMetrics | null;
  parameters?: Record<string, unknown> | null;
}

export interface AIBacktestReport {
  id: string;
  backtest_run_id: string | null;
  report_type: string;
  focus: string;
  status: "completed" | "failed" | "pending";
  model_name: string | null;
  input_summary: Record<string, unknown> | null;
  report_json: AIReportContent | null;
  plain_english_summary: string | null;
  confidence_score: number | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  research_warnings?: ResearchWarnings;
}

export interface AIBacktestReportRequest {
  focus: "balanced" | "risk" | "performance" | "overfitting";
  include_trade_samples?: boolean;
}

export interface AIBacktestReportListResponse {
  total: number;
  items: AIBacktestReport[];
}

// ── MH-15 Baseline Candidate Manager ──────────────────────────────────────

export type BaselineCandidateStatus =
  | "watchlist_candidate"
  | "baseline_candidate"
  | "rejected"
  | "needs_more_testing";

export interface BaselineCandidate {
  id: string;
  backtest_run_id: string | null;
  strategy_config_id: string | null;
  ai_backtest_report_id: string | null;
  asset: string;
  timeframe: string;
  strategy_type: string;
  parameters: Record<string, unknown>;
  metrics: Record<string, unknown>;
  status: BaselineCandidateStatus;
  review_notes: string | null;
  created_by: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface BaselineCandidateCreateRequest {
  backtest_run_id: string;
  strategy_config_id: string;
  ai_backtest_report_id?: string | null;
  status?: BaselineCandidateStatus;
  review_notes?: string | null;
  created_by?: string | null;
}

export interface BaselineCandidateUpdateRequest {
  status?: BaselineCandidateStatus;
  review_notes?: string | null;
  reviewed_by?: string | null;
}

export interface BaselineCandidateRejectRequest {
  reviewed_by?: string | null;
  review_notes?: string | null;
}

export interface BaselineCandidateListResponse {
  total: number;
  items: BaselineCandidate[];
}

// ── MH-16 Paper Validation Gate ───────────────────────────────────────────

export type PaperValidationStatus =
  | "pending"
  | "active"
  | "passed"
  | "failed"
  | "stopped";

export interface PaperValidationProgress {
  total_paper_trades: number;
  wins: number;
  losses: number;
  win_rate: number | null;
  profit_factor: number | null;
  total_return_pct: number | null;
  max_drawdown_pct: number | null;
  days_active: number;
  progress_trades_pct: number;
  progress_days_pct: number;
  pass_fail_status: string;
  reasons: string[];
}

export interface PaperValidationPlan {
  id: string;
  baseline_candidate_id: string;
  backtest_run_id: string | null;
  strategy_config_id: string | null;
  status: PaperValidationStatus;
  required_trades: number;
  minimum_days: number;
  target_profit_factor: number | null;
  max_drawdown_pct: number | null;
  max_daily_loss_pct: number | null;
  starting_paper_capital: number;
  backtest_metrics: Record<string, unknown> | null;
  paper_metrics: Record<string, unknown> | null;
  progress: Record<string, unknown> | null;
  pass_fail_reasons: string[] | Record<string, unknown> | null;
  started_at: string | null;
  completed_at: string | null;
  created_by: string | null;
  reviewed_by: string | null;
  review_notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface PaperValidationPlanCreateRequest {
  baseline_candidate_id: string;
  required_trades?: number;
  minimum_days?: number;
  target_profit_factor?: number | null;
  max_drawdown_pct?: number | null;
  max_daily_loss_pct?: number | null;
  starting_paper_capital?: number;
  created_by?: string | null;
  review_notes?: string | null;
}

export interface PaperValidationPlanUpdateRequest {
  status?: PaperValidationStatus;
  required_trades?: number;
  minimum_days?: number;
  target_profit_factor?: number | null;
  max_drawdown_pct?: number | null;
  max_daily_loss_pct?: number | null;
  starting_paper_capital?: number;
  paper_metrics?: Record<string, unknown> | null;
  reviewed_by?: string | null;
  review_notes?: string | null;
}

export interface PaperValidationPlanActionRequest {
  reviewed_by?: string | null;
  review_notes?: string | null;
}

export interface PaperValidationPlanListResponse {
  total: number;
  items: PaperValidationPlan[];
}

export interface PaperValidationEvent {
  id: string;
  paper_validation_plan_id: string;
  event_type: string;
  message: string;
  payload: Record<string, unknown> | null;
  created_at: string;
}

// ── MH-17 Paper Validation Evidence / Reconciliation ──────────────────────

export type PaperValidationEvidenceResult =
  | "win"
  | "loss"
  | "breakeven"
  | "open"
  | "unknown";

export type PaperValidationEvidenceConfidence =
  | "high"
  | "medium"
  | "low"
  | "manual";

export interface PaperValidationEvidence {
  id: string;
  paper_validation_plan_id: string;
  source_type: string;
  source_id: string | null;
  confidence: PaperValidationEvidenceConfidence;
  asset: string | null;
  timeframe: string | null;
  side: string | null;
  opened_at: string | null;
  closed_at: string | null;
  entry_price: number | null;
  exit_price: number | null;
  pnl_amount: number | null;
  pnl_pct: number | null;
  r_multiple: number | null;
  result: PaperValidationEvidenceResult;
  payload: Record<string, unknown> | null;
  notes: string | null;
  included_in_metrics: boolean;
  created_at: string;
  updated_at: string;
}

export interface PaperValidationEvidenceListResponse {
  total: number;
  items: PaperValidationEvidence[];
}

export interface PaperValidationManualEvidenceRequest {
  asset?: string | null;
  timeframe?: string | null;
  side?: string | null;
  opened_at?: string | null;
  closed_at?: string | null;
  entry_price?: number | null;
  exit_price?: number | null;
  pnl_amount?: number | null;
  pnl_pct?: number | null;
  r_multiple?: number | null;
  result?: PaperValidationEvidenceResult;
  notes?: string | null;
  payload?: Record<string, unknown> | null;
  included_in_metrics?: boolean;
}

export interface PaperValidationReconcileRequest {
  dry_run?: boolean;
  asset_filter?: string | null;
  timeframe_filter?: string | null;
  date_from?: string | null;
  date_to?: string | null;
}

export interface PaperValidationReconcileResponse {
  evidence_created: number;
  evidence_skipped: number;
  matched_source: string;
  warnings: string[];
  dry_run: boolean;
}

// ── MH-18: Dashboard & Readiness Review ────────────────────────────────────

export interface PaperValidationMetricDeltas {
  profit_factor_delta?: number | null;
  total_return_delta?: number | null;
  max_drawdown_delta?: number | null;
  win_rate_delta?: number | null;
}

export interface PaperValidationEvidenceSummary {
  total_evidence: number;
  included_evidence: number;
  excluded_evidence: number;
  manual_evidence_count: number;
  reconciled_evidence_count: number;
  high_confidence_count: number;
  medium_confidence_count: number;
  low_confidence_count: number;
}

export interface PaperValidationDashboardResponse {
  total_plans: number;
  pending_count: number;
  active_count: number;
  passed_count: number;
  failed_count: number;
  stopped_count: number;
  ready_for_review_count: number;
  average_progress_trades_pct: number;
  average_progress_days_pct: number;
  plans_needing_evidence: number;
  plans_with_low_confidence: number;
  plans_breaching_thresholds: number;
  recently_updated_plans: Array<{
    plan_id: string;
    status: string;
    updated_at?: string | null;
  }>;
  warnings: string[];
}

export interface PaperValidationReadinessResponse {
  plan_id: string;
  baseline_candidate_id: string;
  status: string;
  readiness_status: "not_started" | "collecting_evidence" | "ready_for_review" | "passed" | "failed" | "stopped";
  readiness_score: number;
  readiness_notes: string;
  progress_summary: Record<string, unknown>;
  backtest_metrics?: Record<string, unknown> | null;
  paper_metrics?: Record<string, unknown> | null;
  metric_deltas: PaperValidationMetricDeltas;
  evidence_summary: PaperValidationEvidenceSummary;
  warnings: string[];
  suggested_next_action: "keep_collecting" | "review_candidate" | "reject_candidate" | "investigate_data" | "stop_validation";
  recent_events: PaperValidationEvent[];
}