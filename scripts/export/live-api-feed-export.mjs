#!/usr/bin/env node

import fs from "node:fs/promises";
import path from "node:path";

const API_BASE_URL =
  process.env.API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "http://127.0.0.1:8000";

const DEFAULT_OUTPUT_PATH = path.resolve(process.cwd(), "exports/live-api-feed-snapshot.json");
const OUTPUT_PATH = process.argv[2] ? path.resolve(process.cwd(), process.argv[2]) : DEFAULT_OUTPUT_PATH;

const EXPORT_TIMEFRAME = process.env.EXPORT_TIMEFRAME || "1h";
const NEWS_LIMIT = Number(process.env.EXPORT_NEWS_LIMIT || 10);
const MAX_MATRIX_ASSETS = Number(process.env.EXPORT_MAX_MATRIX_ASSETS || 40);
const OPPORTUNITIES_LIMIT = Number(process.env.EXPORT_OPPORTUNITIES_LIMIT || 50);
const EXECUTION_HISTORY_LIMIT = Number(process.env.EXPORT_EXEC_HISTORY_LIMIT || 50);

const DEFAULT_RISK_CONTEXT = {
  spread_bps: 10,
  daily_drawdown_pct: 0.5,
  consecutive_losses: 0,
  minutes_since_last_loss: null,
  correlated_exposure_count: 0,
  open_positions_count: 0,
  session_allowed: true,
  kill_switch_active: false,
  market_quality_flag: true,
  account_equity: 50000,
  requested_execution_mode: "paper",
};

function sanitizeNumber(value, fallback = null) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function safeError(error, context = {}) {
  if (error instanceof Error) {
    return {
      message: error.message,
      name: error.name,
      ...context,
    };
  }
  return {
    message: String(error),
    ...context,
  };
}

async function apiRequest(routePath, options = {}) {
  const url = `${API_BASE_URL}${routePath}`;
  const response = await fetch(url, {
    method: options.method || "GET",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    body: options.body ? JSON.stringify(options.body) : undefined,
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(`HTTP ${response.status} ${response.statusText}${message ? `: ${message}` : ""}`);
  }

  return response.json();
}

async function safeApiRequest(routePath, options = {}) {
  try {
    const data = await apiRequest(routePath, options);
    return { ok: true, data, routePath };
  } catch (error) {
    return { ok: false, error: safeError(error, { routePath }) };
  }
}

function splitPromptPath(promptPath) {
  const raw = String(promptPath || "").trim();
  if (!raw || !raw.includes("/")) return null;
  const parts = raw.split("/").filter(Boolean);
  if (parts.length < 2) return null;
  return {
    subdir: parts.slice(0, -1).join("/"),
    filename: parts[parts.length - 1],
  };
}

function pickLatestPrice(asset, opportunitiesByAsset, marketStatusRows) {
  const topOpportunity = opportunitiesByAsset.get(asset)?.[0] || null;
  if (topOpportunity) {
    const low = sanitizeNumber(topOpportunity.entry_low);
    const high = sanitizeNumber(topOpportunity.entry_high);
    if (low !== null && high !== null) return (low + high) / 2;
  }

  const firstStatus = marketStatusRows[0] || null;
  if (firstStatus && firstStatus.last_bar_ts) {
    // No explicit last price in market-data/status; keep null if unavailable.
    return null;
  }

  return null;
}

async function buildSnapshot() {
  const baseFeeds = {
    health: await safeApiRequest("/health"),
    scheduler_status: await safeApiRequest("/market-data/auto-paper/scheduler/status"),
    kill_switch: await safeApiRequest("/market-data/auto-paper/kill-switch"),
    auto_paper_history: await safeApiRequest("/market-data/auto-paper/history?limit=200"),
    assets: await safeApiRequest("/assets?active_only=false"),
    opportunities: await safeApiRequest(`/opportunities?limit=${OPPORTUNITIES_LIMIT}`),
    market_data_status: await safeApiRequest("/market-data/status"),
    performance_stats: await safeApiRequest("/performance-stats"),
    regime: await safeApiRequest("/regime/current"),
    execution_paper: await safeApiRequest("/execution/paper?limit=200&offset=0"),
    execution_positions: await safeApiRequest("/execution/positions"),
    alerts_rules: await safeApiRequest("/approvals/alerts/rules"),
    alerts_active: await safeApiRequest("/approvals/alerts/active"),
    alerts_notifications: await safeApiRequest("/approvals/alerts/notifications"),
    broker_account: await safeApiRequest("/broker/account"),
    broker_positions: await safeApiRequest("/broker/positions"),
    prompts: await safeApiRequest("/prompts"),
  };

  const assets = baseFeeds.assets.ok && Array.isArray(baseFeeds.assets.data.items)
    ? baseFeeds.assets.data.items
    : [];

  const opportunities = baseFeeds.opportunities.ok && Array.isArray(baseFeeds.opportunities.data.items)
    ? baseFeeds.opportunities.data.items
    : [];

  const marketStatusItems = baseFeeds.market_data_status.ok && Array.isArray(baseFeeds.market_data_status.data.items)
    ? baseFeeds.market_data_status.data.items
    : [];

  const symbols = assets
    .map((a) => String(a.symbol || "").toUpperCase())
    .filter(Boolean);

  const executionRows = baseFeeds.execution_paper.ok && Array.isArray(baseFeeds.execution_paper.data)
    ? baseFeeds.execution_paper.data.slice(0, Math.max(0, EXECUTION_HISTORY_LIMIT))
    : [];

  const executionHistory = {};
  for (const row of executionRows) {
    const executionId = String(row.execution_id || "");
    if (!executionId) continue;
    // eslint-disable-next-line no-await-in-loop
    executionHistory[executionId] = await safeApiRequest(`/execution/paper/${executionId}/history`);
  }

  const newsByAsset = {};
  for (const symbol of symbols) {
    // eslint-disable-next-line no-await-in-loop
    newsByAsset[symbol] = await safeApiRequest(`/market-data/news/${encodeURIComponent(symbol)}?limit=${NEWS_LIMIT}`);
  }

  const promptDetails = {};
  const promptHistory = {};
  const promptNames =
    baseFeeds.prompts.ok && Array.isArray(baseFeeds.prompts.data.prompts) ? baseFeeds.prompts.data.prompts : [];

  for (const promptPath of promptNames) {
    const parsed = splitPromptPath(promptPath);
    if (!parsed) {
      promptDetails[promptPath] = {
        ok: false,
        error: { message: "Prompt path format is not subdir/filename and could not be fetched." },
      };
      promptHistory[promptPath] = {
        ok: false,
        error: { message: "Prompt path format is not subdir/filename and could not be fetched." },
      };
      continue;
    }

    // eslint-disable-next-line no-await-in-loop
    promptDetails[promptPath] = await safeApiRequest(
      `/prompts/${encodeURIComponent(parsed.subdir)}/${encodeURIComponent(parsed.filename)}`,
    );
    // eslint-disable-next-line no-await-in-loop
    promptHistory[promptPath] = await safeApiRequest(
      `/prompts/${encodeURIComponent(parsed.subdir)}/${encodeURIComponent(parsed.filename)}/history`,
    );
  }

  const opportunitiesByAsset = new Map();
  for (const opp of opportunities) {
    const symbol = String(opp.asset || "").toUpperCase();
    if (!symbol) continue;
    if (!opportunitiesByAsset.has(symbol)) opportunitiesByAsset.set(symbol, []);
    opportunitiesByAsset.get(symbol).push(opp);
  }

  for (const [symbol, rows] of opportunitiesByAsset.entries()) {
    rows.sort((a, b) => Number(b.score || 0) - Number(a.score || 0));
    opportunitiesByAsset.set(symbol, rows);
  }

  const matrixSymbols = symbols.slice(0, Math.max(0, MAX_MATRIX_ASSETS));
  const perAssetSignalRisk = {};

  for (const symbol of matrixSymbols) {
    const statusRows = marketStatusItems.filter((row) => String(row.asset_symbol || "").toUpperCase() === symbol);
    const latestPrice = pickLatestPrice(symbol, opportunitiesByAsset, statusRows);

    if (latestPrice === null) {
      perAssetSignalRisk[symbol] = {
        ok: false,
        error: {
          message: "Skipped signal/risk generation because latest price could not be inferred from live feeds.",
        },
        market_status_rows: statusRows,
        top_opportunity: opportunitiesByAsset.get(symbol)?.[0] || null,
      };
      continue;
    }

    // eslint-disable-next-line no-await-in-loop
    const signalResult = await safeApiRequest("/signals/generate", {
      method: "POST",
      body: {
        asset: symbol,
        timeframe: EXPORT_TIMEFRAME,
        latest_price: latestPrice,
        feature_snapshot: { source: "export-live-api-feed" },
        catalyst_context: { mode: "live_export" },
      },
    });

    let riskResult = { ok: false, error: { message: "Risk not evaluated because signal generation failed." } };

    if (signalResult.ok) {
      // eslint-disable-next-line no-await-in-loop
      riskResult = await safeApiRequest("/risk/evaluate", {
        method: "POST",
        body: {
          signal: signalResult.data,
          risk_context: DEFAULT_RISK_CONTEXT,
        },
      });
    }

    perAssetSignalRisk[symbol] = {
      ok: signalResult.ok && riskResult.ok,
      latest_price_used: latestPrice,
      market_status_rows: statusRows,
      top_opportunity: opportunitiesByAsset.get(symbol)?.[0] || null,
      signal: signalResult,
      risk: riskResult,
    };
  }

  const exportData = {
    metadata: {
      generated_at: new Date().toISOString(),
      api_base_url: API_BASE_URL,
      export_timeframe: EXPORT_TIMEFRAME,
      news_limit_per_asset: NEWS_LIMIT,
      matrix_asset_count: matrixSymbols.length,
      max_matrix_assets: MAX_MATRIX_ASSETS,
      opportunities_limit: OPPORTUNITIES_LIMIT,
      execution_history_limit: EXECUTION_HISTORY_LIMIT,
      notes: [
        "All sections capture live API responses at export time.",
        "Errors are retained inline per route for troubleshooting.",
        "Per-asset signal/risk rows may fail if the live signal endpoint is unavailable or provider credentials are missing.",
      ],
    },
    feeds: baseFeeds,
    execution_history: executionHistory,
    per_asset_news: newsByAsset,
    prompt_details: promptDetails,
    prompt_history: promptHistory,
    per_asset_signal_risk: perAssetSignalRisk,
  };

  await fs.mkdir(path.dirname(OUTPUT_PATH), { recursive: true });
  await fs.writeFile(OUTPUT_PATH, `${JSON.stringify(exportData, null, 2)}\n`, "utf8");

  return {
    outputPath: OUTPUT_PATH,
    symbolCount: symbols.length,
    matrixCount: matrixSymbols.length,
  };
}

async function main() {
  try {
    const summary = await buildSnapshot();
    console.log(`Live API feed export written to ${summary.outputPath}`);
    console.log(`Assets included: ${summary.symbolCount}`);
    console.log(`Per-asset signal/risk rows attempted: ${summary.matrixCount}`);
  } catch (error) {
    console.error("Export failed:", safeError(error));
    process.exitCode = 1;
  }
}

void main();
