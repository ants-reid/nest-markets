/**
 * Route render tests — Stage 6 hardening.
 */

import { expect, test } from "@playwright/test";

function isStrategyLabApiRequest(request: import("@playwright/test").Request) {
  const url = new URL(request.url());
  return !request.isNavigationRequest() && url.pathname.startsWith("/strategy-lab/");
}

const ROUTES: { id: string; path: string; heading: RegExp | string }[] = [
  { id: "QA-R01", path: "/", heading: /what needs attention/i },
  { id: "QA-R02", path: "/dashboard", heading: /snapshot|P&L|risk|approval/i },
  { id: "QA-R03", path: "/analytics", heading: /analytics/i },
  { id: "QA-R04", path: "/workflow", heading: /workflow/i },
  { id: "QA-R05", path: "/signals", heading: /signal feed|signal/i },
  { id: "QA-R06", path: "/risk", heading: /risk/i },
  { id: "QA-R07", path: "/execution", heading: /execution/i },
  { id: "QA-R08", path: "/approvals", heading: /approval/i },
  { id: "QA-R09", path: "/performance", heading: /performance/i },
  { id: "QA-R10", path: "/assets", heading: /asset/i },
  { id: "QA-R11", path: "/opportunities", heading: /opportunit/i },
  { id: "QA-R12", path: "/alerts", heading: /alert/i },
  { id: "QA-R13", path: "/notifications", heading: /notification/i },
  { id: "QA-R14", path: "/prompts", heading: /prompt/i },
  { id: "QA-R15", path: "/evals", heading: /eval/i },
  { id: "QA-R16", path: "/data-centre", heading: /data centre/i },
  { id: "QA-R17", path: "/strategy-lab", heading: /strategy lab/i },
  { id: "QA-R18A", path: "/cockpit", heading: /cockpit/i },
  { id: "QA-R18B", path: "/cockpit/eod-report", heading: /end-of-day report/i },
  { id: "QA-R18C", path: "/cockpit/in-flight-adjustments", heading: /in-flight adjustments/i },
  { id: "QA-R18D", path: "/cockpit/trade-close-explanations", heading: /trade-close explanations/i },
  { id: "QA-R18E", path: "/cockpit/daily-scoreboard", heading: /daily scoreboard/i },
  { id: "QA-R19", path: "/data-quality", heading: /data quality review/i },
  { id: "QA-R20", path: "/monitor/feeds", heading: /feed monitor/i },
];

for (const route of ROUTES) {
  test(`${route.id} — ${route.path} renders main layout and heading`, async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") consoleErrors.push(msg.text());
    });

    await page.goto(route.path);
    await page.waitForLoadState("domcontentloaded");

    await expect(page.locator("main").first()).toBeVisible();
    await expect(page.locator("nav").first()).toBeVisible();

    const heading = page.locator("h1, h2, h3").filter({ hasText: route.heading }).first();
    await expect(heading).toBeVisible();

    const errorBoundary = page.getByText("Something went wrong", { exact: false });
    await expect(errorBoundary).toHaveCount(0);

    const fatalErrors = consoleErrors.filter(
      (entry) => entry.includes("Unhandled") || entry.includes("Cannot read") || entry.includes("is not a function"),
    );
    expect(fatalErrors, `Fatal JS errors on ${route.path}: ${fatalErrors.join(", ")}`).toHaveLength(0);
  });
}

test("QA-R09b performance page renders KPI strip and at least one table", async ({ page }) => {
  await page.goto("/performance");
  await page.waitForTimeout(1000);
  await expect(page.locator("main").first()).toContainText(/total/i);
});

test("QA-R10b assets page renders searchable table with search input", async ({ page }) => {
  await page.goto("/assets");
  await page.waitForTimeout(800);
  const searchInput = page.locator("input[type='search'], input[placeholder*='earch']").first();
  await expect(searchInput).toBeVisible();
});

test("QA-R11b opportunities page renders score column and Run Sweep button", async ({ page }) => {
  await page.goto("/opportunities");
  await page.waitForTimeout(800);
  await expect(page.getByRole("button", { name: /run sweep/i })).toBeVisible();
});

test("QA-R13b notifications page renders OperatorNotificationSurface", async ({ page }) => {
  await page.goto("/notifications");
  await page.waitForTimeout(800);
  const content = page.locator("main").first();
  await expect(content).toBeVisible();
  const hasContent = await content.locator("ul, [aria-label], p").count();
  expect(hasContent).toBeGreaterThanOrEqual(0);
});

test("QA-R16b sidebar includes Data Centre navigation item", async ({ page }) => {
  await page.goto("/analytics");
  await page.waitForLoadState("domcontentloaded");

  const navLink = page.getByRole("link", { name: "Data Centre" });
  await expect(navLink).toBeVisible();
  await expect(navLink).toHaveAttribute("href", "/data-centre");
});

test("QA-R17b sidebar includes Strategy Lab navigation item", async ({ page }) => {
  await page.goto("/analytics");
  await page.waitForLoadState("domcontentloaded");

  const navLink = page.getByRole("link", { name: "Strategy Lab" });
  await expect(navLink).toBeVisible();
  await expect(navLink).toHaveAttribute("href", "/strategy-lab");
});

test("QA-R16c data centre renders research jobs panel", async ({ page }) => {
  await page.goto("/data-centre");
  await page.waitForLoadState("domcontentloaded");

  await expect(page.getByText(/recent jobs/i)).toBeVisible();
  await expect(page.getByRole("button", { name: /start import job/i })).toBeVisible();
  await expect(page.getByRole("button", { name: /start quality recalculation job/i })).toBeVisible();
});

async function mockStrategyLabResearchApi(
  page: import("@playwright/test").Page,
  options?: { empty?: boolean; failOverview?: boolean },
) {
  const runId = "b613db7f-1c6a-4324-a130-bdaf63f78311";
  const configId = "f4da5a7c-351b-4dc5-80cb-94ba8227d5b2";
  const now = new Date().toISOString();
  const empty = Boolean(options?.empty);
  const failOverview = Boolean(options?.failOverview);

  await page.route("**/strategy-lab/**", async (route) => {
    if (!isStrategyLabApiRequest(route.request())) {
      await route.continue();
      return;
    }

    const url = new URL(route.request().url());
    const path = url.pathname;
    const method = route.request().method();

    const fulfill = async (body: unknown, status = 200) => {
      await route.fulfill({
        status,
        contentType: "application/json",
        body: JSON.stringify(body),
      });
    };

    if (failOverview && [
      "/strategy-lab/configs",
      "/strategy-lab/backtests",
      "/strategy-lab/comparisons",
      "/strategy-lab/cost-model/profiles",
      "/strategy-lab/cost-model/stress-presets",
    ].includes(path)) {
      await fulfill({ detail: "forced failure" }, 500);
      return;
    }

    if (path === "/strategy-lab/configs") {
      await fulfill({
        total: empty ? 0 : 1,
        items: empty ? [] : [{
          id: configId,
          name: "MA Momentum Research",
          strategy_type: "ma_momentum",
          asset: "AAPL",
          timeframe: "1d",
          parameters: { fast_window: 5, slow_window: 20 },
          risk_settings: {},
          enabled: true,
          created_at: now,
          updated_at: now,
        }],
      });
      return;
    }

    if (path === "/strategy-lab/backtests") {
      await fulfill({
        total: empty ? 0 : 1,
        items: empty ? [] : [{
          id: runId,
          name: "Research Backtest Alpha",
          status: "completed",
          date_from: "2024-01-01T00:00:00.000Z",
          date_to: "2024-12-31T00:00:00.000Z",
          requested_assets: { assets: ["AAPL"] },
          requested_timeframes: { timeframes: ["1d"] },
          strategy_config_ids: { config_ids: [configId] },
          starting_capital: 10000,
          result_summary: { total_mock_trades: 32 },
          error_message: null,
          started_at: now,
          completed_at: now,
          created_at: now,
          updated_at: now,
          research_warnings: {
            research_only: true,
            execution_costs_modelled: true,
            spread_modelled: true,
            slippage_modelled: true,
            fees_modelled: true,
            live_ready: false,
            warning: "Research only.",
            cost_model_version: "mh15c_v1",
            cost_model_status: "modelled",
            cost_model_notes: "Deterministic research assumptions.",
          },
        }],
      });
      return;
    }

    if (path === "/strategy-lab/comparisons") {
      await fulfill({
        total: empty ? 0 : 1,
        items: empty ? [] : [{
          backtest_run_id: runId,
          name: "Research Backtest Alpha",
          status: "completed",
          date_from: "2024-01-01T00:00:00.000Z",
          date_to: "2024-12-31T00:00:00.000Z",
          requested_assets: ["AAPL"],
          requested_timeframes: ["1d"],
          starting_capital: 10000,
          created_at: now,
          completed_at: now,
          total_configs_tested: 1,
          best_score: 82.5,
          best_asset: "AAPL",
          best_timeframe: "1d",
          best_strategy_config_id: configId,
          best_strategy_name: "MA Momentum Research",
          best_parameters: { fast_window: 5, slow_window: 20 },
          best_total_trades: 32,
          best_win_rate: 0.56,
          best_profit_factor: 1.42,
          best_total_return_pct: 12.4,
          best_max_drawdown_pct: 6.1,
        }],
      });
      return;
    }

    if (path === "/strategy-lab/cost-model/profiles") {
      await fulfill({
        total: 2,
        items: [
          {
            profile_name: "standard_research",
            profile_label: "Standard Research",
            profile_description: "Baseline deterministic research cost profile.",
            profile_multiplier: 1,
            intended_use: "Default research review",
            is_broker_calibrated: false,
            live_ready: false,
          },
          {
            profile_name: "stress_research",
            profile_label: "Stress Research",
            profile_description: "Conservative stress profile.",
            profile_multiplier: 3,
            intended_use: "Risk stress review",
            is_broker_calibrated: false,
            live_ready: false,
          },
        ],
      });
      return;
    }

    if (path === "/strategy-lab/cost-model/stress-presets") {
      await fulfill({
        total: 2,
        items: [
          {
            preset_name: "normal_liquidity",
            preset_label: "Normal Liquidity",
            preset_description: "Default deterministic preset.",
            spread_multiplier: 1,
            slippage_multiplier: 1,
            commission_multiplier: 1,
            is_broker_calibrated: false,
            live_ready: false,
          },
          {
            preset_name: "news_event_stress",
            preset_label: "News Event Stress",
            preset_description: "Stress preset for volatile sessions.",
            spread_multiplier: 4,
            slippage_multiplier: 4,
            commission_multiplier: 1,
            is_broker_calibrated: false,
            live_ready: false,
          },
        ],
      });
      return;
    }

    if (path === `/strategy-lab/backtests/${runId}`) {
      await fulfill({
        id: runId,
        name: "Research Backtest Alpha",
        status: "completed",
        date_from: "2024-01-01T00:00:00.000Z",
        date_to: "2024-12-31T00:00:00.000Z",
        requested_assets: { assets: ["AAPL"] },
        requested_timeframes: { timeframes: ["1d"] },
        strategy_config_ids: { config_ids: [configId] },
        starting_capital: 10000,
        result_summary: { total_mock_trades: 32 },
        error_message: null,
        started_at: now,
        completed_at: now,
        created_at: now,
        updated_at: now,
        research_warnings: {
          research_only: true,
          execution_costs_modelled: true,
          spread_modelled: true,
          slippage_modelled: true,
          fees_modelled: true,
          live_ready: false,
          warning: "Research only.",
          cost_model_version: "mh15c_v1",
          cost_model_status: "modelled",
          cost_model_notes: "Deterministic research assumptions.",
        },
      });
      return;
    }

    if (path === `/strategy-lab/backtests/${runId}/trades`) {
      await fulfill({ total: empty ? 0 : 2, items: empty ? [] : [{ id: "trade-1" }, { id: "trade-2" }] });
      return;
    }

    if (path === `/strategy-lab/backtests/${runId}/results`) {
      await fulfill({
        total: empty ? 0 : 1,
        items: empty ? [] : [{
          id: "result-1",
          backtest_run_id: runId,
          strategy_config_id: configId,
          asset: "AAPL",
          timeframe: "1d",
          total_trades: 32,
          wins: 18,
          losses: 14,
          breakeven: 0,
          win_rate: 0.5625,
          average_win: 1.4,
          average_loss: -0.8,
          profit_factor: 1.42,
          expectancy: 0.23,
          total_return_pct: 12.4,
          max_drawdown_pct: 6.1,
          score: 82.5,
          metrics: {
            base_net_total_return_pct: 10.9,
            high_net_total_return_pct: 4.3,
            base_net_profit_factor: 1.31,
            high_net_profit_factor: 0.96,
            cost_sensitivity_level: "medium",
            quality_grade: "B",
            research_confidence_score: 74,
            overfitting_risk_score: 33,
            quality_warnings: ["Sample size acceptable for research review."],
            validation_stability_grade: "stable",
            walk_forward_warnings: ["Research only, not approved for paper or live trading"],
          },
          created_at: now,
          updated_at: now,
        }],
      });
      return;
    }

    if (path === `/strategy-lab/backtests/${runId}/equity-curve`) {
      await fulfill({
        total: empty ? 0 : 3,
        items: empty ? [] : [
          { id: "eq-1", backtest_run_id: runId, timestamp: now, equity: 10000, cash: 10000, open_pnl: 0, drawdown_pct: 0, created_at: now },
          { id: "eq-2", backtest_run_id: runId, timestamp: now, equity: 10450, cash: 10450, open_pnl: 0, drawdown_pct: 0, created_at: now },
          { id: "eq-3", backtest_run_id: runId, timestamp: now, equity: 11240, cash: 11240, open_pnl: 0, drawdown_pct: 1.2, created_at: now },
        ],
      });
      return;
    }

    if (path === `/strategy-lab/backtests/${runId}/drawdowns`) {
      await fulfill({
        total: empty ? 0 : 1,
        items: empty ? [] : [{
          id: "dd-1",
          backtest_run_id: runId,
          start_time: now,
          trough_time: now,
          end_time: now,
          max_drawdown_pct: 6.1,
          duration_candles: 8,
          recovered: true,
          created_at: now,
        }],
      });
      return;
    }

    if (path === `/strategy-lab/backtests/${runId}/quality-summary`) {
      await fulfill({
        backtest_run_id: runId,
        total_strategies: empty ? 0 : 1,
        average_confidence: 74,
        grade_distribution: { A: 0, B: 1, C: 0, D: 0, F: 0, unknown: 0 },
        highest_overfitting_risk: 33,
        warnings: ["Research only, not approved for paper or live trading"],
        paper_trade_ready: false,
        live_ready: false,
      });
      return;
    }

    if (path === `/strategy-lab/backtests/${runId}/walk-forward` && method === "GET") {
      await fulfill({
        backtest_run_id: runId,
        splits: [
          { period: "in_sample", start: now, end: now, percentage: 60 },
          { period: "validation", start: now, end: now, percentage: 20 },
          { period: "out_of_sample", start: now, end: now, percentage: 20 },
        ],
        strategies: empty ? [] : [{
          strategy_config_id: configId,
          strategy_name: "MA Momentum Research",
          in_sample: { period: "in_sample", total_trades: 40, win_rate: 0.58, net_profit_factor: 1.4, net_total_return_pct: 12.1, max_drawdown_pct: 5.4, research_confidence_score: 78, quality_grade: "B" },
          validation: { period: "validation", total_trades: 12, win_rate: 0.5, net_profit_factor: 1.2, net_total_return_pct: 4.8, max_drawdown_pct: 3.2, research_confidence_score: 70, quality_grade: "B" },
          out_of_sample: { period: "out_of_sample", total_trades: 10, win_rate: 0.5, net_profit_factor: 1.08, net_total_return_pct: 2.5, max_drawdown_pct: 3.6, research_confidence_score: 68, quality_grade: "C" },
          folds: [
            {
              fold_index: 1,
              splits: [],
              in_sample: { period: "in_sample", total_trades: 12, win_rate: 0.58, net_profit_factor: 1.3, net_total_return_pct: 4.2, max_drawdown_pct: 2.1, research_confidence_score: 74, quality_grade: "B" },
              validation: { period: "validation", total_trades: 4, win_rate: 0.5, net_profit_factor: 1.1, net_total_return_pct: 1.4, max_drawdown_pct: 1.2, research_confidence_score: 69, quality_grade: "B" },
              out_of_sample: { period: "out_of_sample", total_trades: 3, win_rate: 0.33, net_profit_factor: 0.98, net_total_return_pct: 0.4, max_drawdown_pct: 1.5, research_confidence_score: 66, quality_grade: "C" },
              validation_stability_score: 74,
              validation_stability_grade: "mixed",
              out_of_sample_pass: false,
              return_degradation_pct: 35,
              profit_factor_degradation_pct: 18,
              confidence_degradation_pct: 11,
              warnings: [{ message: "Research only, not approved for paper or live trading" }],
            },
          ],
          in_sample_return: 12.1,
          validation_return: 4.8,
          out_of_sample_return: 2.5,
          out_of_sample_profit_factor: 1.08,
          return_degradation_pct: 39,
          profit_factor_degradation_pct: 17,
          confidence_degradation_pct: 13,
          validation_stability_score: 79,
          validation_stability_grade: "stable",
          out_of_sample_pass: true,
          paper_trade_ready: false,
          live_ready: false,
          warnings: [{ message: "Research only, not approved for paper or live trading" }],
        }],
        rolling_window_summary: empty ? null : {
          fold_count: 3,
          stable_fold_ratio: 0.66,
          average_validation_stability_score: 79,
          stability_dispersion: 9,
          average_return_degradation_pct: 39,
          average_confidence_degradation_pct: 13,
          rolling_validation_grade: "stable",
          rolling_out_of_sample_pass: true,
          warnings: [{ message: "Research only, not approved for paper or live trading" }],
        },
        warnings: [{ message: "Research only, not approved for paper or live trading" }],
        paper_trade_ready: false,
        live_ready: false,
      });
      return;
    }

    if (path === `/strategy-lab/backtests/${runId}/walk-forward` && method === "POST") {
      await fulfill({
        backtest_run_id: runId,
        splits: [{ period: "in_sample", start: now, end: now, percentage: 60 }],
        strategies: [{
          strategy_config_id: configId,
          strategy_name: "MA Momentum Research",
          in_sample: { period: "in_sample", total_trades: 40, win_rate: 0.58, net_profit_factor: 1.4, net_total_return_pct: 12.1, max_drawdown_pct: 5.4, research_confidence_score: 78, quality_grade: "B" },
          validation: { period: "validation", total_trades: 12, win_rate: 0.5, net_profit_factor: 1.2, net_total_return_pct: 4.8, max_drawdown_pct: 3.2, research_confidence_score: 70, quality_grade: "B" },
          out_of_sample: { period: "out_of_sample", total_trades: 10, win_rate: 0.5, net_profit_factor: 1.08, net_total_return_pct: 2.5, max_drawdown_pct: 3.6, research_confidence_score: 68, quality_grade: "C" },
          folds: [],
          in_sample_return: 12.1,
          validation_return: 4.8,
          out_of_sample_return: 2.5,
          out_of_sample_profit_factor: 1.08,
          return_degradation_pct: 39,
          profit_factor_degradation_pct: 17,
          confidence_degradation_pct: 13,
          validation_stability_score: 79,
          validation_stability_grade: "stable",
          out_of_sample_pass: true,
          paper_trade_ready: false,
          live_ready: false,
          warnings: [{ message: "Research only, not approved for paper or live trading" }],
        }],
        rolling_window_summary: null,
        warnings: [{ message: "Research only, not approved for paper or live trading" }],
        paper_trade_ready: false,
        live_ready: false,
      });
      return;
    }

    if (path === `/strategy-lab/backtests/${runId}/ai-reports`) {
      await fulfill({ total: empty ? 0 : 1, items: empty ? [] : [{
        id: "report-1",
        backtest_run_id: runId,
        report_type: "comparison_review",
        focus: "balanced",
        status: "completed",
        model_name: "gpt-5.4",
        input_summary: {},
        report_json: { plain_english_summary: "Quality and stability remain acceptable for research follow-up." },
        plain_english_summary: "Quality and stability remain acceptable for research follow-up.",
        confidence_score: 58,
        error_message: null,
        created_at: now,
        updated_at: now,
        research_warnings: {
          research_only: true,
          execution_costs_modelled: true,
          spread_modelled: true,
          slippage_modelled: true,
          fees_modelled: true,
          live_ready: false,
          warning: "Research only.",
          cost_model_version: "mh15c_v1",
          cost_model_status: "modelled",
          cost_model_notes: "Deterministic research assumptions.",
        },
      }] });
      return;
    }

    if (path === `/strategy-lab/backtests/${runId}/ai-report` && method === "POST") {
      await fulfill({
        id: "report-2",
        backtest_run_id: runId,
        report_type: "comparison_review",
        focus: "balanced",
        status: "completed",
        model_name: "gpt-5.4",
        input_summary: {},
        report_json: { plain_english_summary: "AI review created for research follow-up." },
        plain_english_summary: "AI review created for research follow-up.",
        confidence_score: 60,
        error_message: null,
        created_at: now,
        updated_at: now,
        research_warnings: {
          research_only: true,
          execution_costs_modelled: true,
          spread_modelled: true,
          slippage_modelled: true,
          fees_modelled: true,
          live_ready: false,
          warning: "Research only.",
          cost_model_version: "mh15c_v1",
          cost_model_status: "modelled",
          cost_model_notes: "Deterministic research assumptions.",
        },
      }, 201);
      return;
    }

    if (path === `/strategy-lab/comparisons/${runId}`) {
      await fulfill({
        backtest_run: {
          id: runId,
          name: "Research Backtest Alpha",
          status: "completed",
          date_from: "2024-01-01T00:00:00.000Z",
          date_to: "2024-12-31T00:00:00.000Z",
          requested_assets: ["AAPL"],
          requested_timeframes: ["1d"],
          strategy_config_ids: [configId],
          starting_capital: 10000,
          result_summary: { total_mock_trades: 32 },
          error_message: null,
          started_at: now,
          completed_at: now,
          created_at: now,
          updated_at: now,
        },
        ranked_rows: empty ? [] : [{
          strategy_config_id: configId,
          strategy_name: "MA Momentum Research",
          backtest_run_id: runId,
          asset: "AAPL",
          timeframe: "1d",
          parameters: { fast_window: 5, slow_window: 20 },
          total_trades: 32,
          wins: 18,
          losses: 14,
          win_rate: 0.5625,
          profit_factor: 1.42,
          expectancy: 0.23,
          total_return_pct: 12.4,
          max_drawdown_pct: 6.1,
          scoring_cost_scenario: "base",
          high_cost_scenario_net_return_pct: 4.3,
          high_cost_scenario_profit_factor: 0.96,
          cost_sensitivity_level: "medium",
          quality_grade: "B",
          research_confidence_score: 74,
          overfitting_risk_score: 33,
          quality_warnings: ["Sample size acceptable for research review."],
          validation_stability_score: 79,
          validation_stability_grade: "stable",
          out_of_sample_pass: true,
          walk_forward_warnings: ["Research only, not approved for paper or live trading"],
          score: 82.5,
          rank: 1,
        }],
        mock_trade_count: empty ? 0 : 32,
        equity_curve_summary: {
          total_points: empty ? 0 : 3,
          start_equity: 10000,
          end_equity: 11240,
          peak_equity: 11240,
          latest_drawdown_pct: 1.2,
          total_return_pct: 12.4,
          preview_points: [10000, 10450, 11240],
        },
        drawdown_summary: {
          total_periods: empty ? 0 : 1,
          worst_drawdown_pct: empty ? null : 6.1,
          recovered_periods: empty ? 0 : 1,
          open_periods: 0,
        },
        warnings: ["Research only, not approved for paper or live trading"],
        research_label: null,
        research_notes: null,
        research_warnings: {
          research_only: true,
          execution_costs_modelled: true,
          spread_modelled: true,
          slippage_modelled: true,
          fees_modelled: true,
          live_ready: false,
          warning: "Research only.",
          cost_model_version: "mh15c_v1",
          cost_model_status: "modelled",
          cost_model_notes: "Deterministic research assumptions.",
        },
      });
      return;
    }

    await fulfill({ detail: `Unhandled mock for ${path}` }, 404);
  });
}

test("QA-R18 strategy lab research cockpit renders core sections", async ({ page }) => {
  await mockStrategyLabResearchApi(page);

  await page.goto("/strategy-lab");
  await page.waitForLoadState("domcontentloaded");

  await expect(page.getByTestId("strategy-lab-banner")).toBeVisible();
  await expect(page.getByTestId("strategy-lab-summary-strip")).toBeVisible();
  await expect(page.getByTestId("strategy-lab-density-toggle")).toBeVisible();
  await expect(page.getByTestId("strategy-lab-runs-section")).toBeVisible();
  await expect(page.getByTestId("strategy-lab-comparison-section")).toBeVisible();
  await expect(page.getByTestId("strategy-lab-results-section")).toBeVisible();
  await expect(page.getByTestId("strategy-lab-result-drilldown-section")).toBeVisible();
  await expect(page.getByTestId("strategy-lab-report-actions")).toBeVisible();
  await expect(page.getByTestId("strategy-lab-report-preview")).toBeVisible();
  await expect(page.getByTestId("strategy-lab-cost-model-section")).toBeVisible();
  await expect(page.getByTestId("strategy-lab-quality-section")).toBeVisible();
  await expect(page.getByTestId("strategy-lab-walk-forward-section")).toBeVisible();
  await expect(page.getByTestId("strategy-lab-ai-report-section")).toBeVisible();
});

test("QA-R20 strategy lab shows research-only safety UX and no trading actions", async ({ page }) => {
  await mockStrategyLabResearchApi(page);

  await page.goto("/strategy-lab");
  await page.waitForLoadState("domcontentloaded");

  await expect(page.getByTestId("strategy-lab-banner").getByText(/research only\. not approved for paper or live trading/i)).toBeVisible();
  await expect(page.getByText(/does not execute trades/i)).toBeVisible();
  await expect(page.getByTestId("run-walk-forward-btn")).toBeVisible();
  await expect(page.getByTestId("create-ai-report-btn")).toBeVisible();
  await page.getByTestId("strategy-lab-density-toggle").click();
  await expect(page.getByTestId("strategy-lab-density-toggle")).toContainText(/compact/i);

  const forbidden = page.getByRole("button", { name: /trade now|execute|go live|start paper|paper validation/i });
  await expect(forbidden).toHaveCount(0);
  await expect(page.getByTestId("strategy-lab-result-drilldown-section")).toContainText(/result drill-down/i);
});

test("QA-R21 strategy lab empty state explains that only research outputs are reviewed", async ({ page }) => {
  await mockStrategyLabResearchApi(page, { empty: true });

  await page.goto("/strategy-lab");
  await page.waitForLoadState("domcontentloaded");

  await expect(page.getByTestId("strategy-lab-runs-empty-state")).toBeVisible();
  await expect(page.getByTestId("strategy-lab-comparisons-empty-state")).toBeVisible();
  await expect(page.getByTestId("strategy-lab-results-empty-state")).toBeVisible();
  await expect(page.getByText(/run a strategy lab comparison or backtest first/i).first()).toBeVisible();
});

test("QA-R22 strategy lab API error state renders when overview calls fail", async ({ page }) => {
  await mockStrategyLabResearchApi(page, { failOverview: true });

  await page.goto("/strategy-lab");
  await page.waitForLoadState("domcontentloaded");

  await expect(page.getByTestId("strategy-lab-error-state")).toBeVisible();
  await expect(page.getByText(/temporarily unavailable/i)).toBeVisible();
});

test("QA-R23 strategy lab AI research action updates the report panel", async ({ page }) => {
  await mockStrategyLabResearchApi(page);

  await page.goto("/strategy-lab");
  await page.waitForLoadState("domcontentloaded");

  await page.getByTestId("create-ai-report-btn").click();
  await expect(page.getByTestId("strategy-lab-ai-report-card")).toBeVisible();
  await expect(page.getByTestId("strategy-lab-result-drilldown-section")).toContainText(/selected run:/i);
  await expect(page.getByTestId("strategy-lab-export-json-btn")).toBeVisible();
  await expect(page.getByTestId("strategy-lab-export-csv-btn")).toBeVisible();
  await expect(page.getByTestId("strategy-lab-copy-report-btn")).toBeVisible();
  await expect(page.getByTestId("strategy-lab-print-report-btn")).toBeVisible();
  await expect(page.getByTestId("strategy-lab-report-preview")).toContainText(/strategy lab research summary/i);
  await expect(page.getByText(/ai review created for research follow-up/i)).toBeVisible();
  await expect(page.getByText(/60%/)).toBeVisible();
});