"use client";

import { useEffect, useMemo, useState } from "react";

import {
  cancelResearchJob,
  getResearchDataAssets,
  getResearchDataCoverage,
  getResearchDataGaps,
  getResearchDataImportRuns,
  getResearchDataProviders,
  getResearchDataQuality,
  getResearchJob,
  getResearchJobs,
  retryResearchJob,
  startResearchImportJob,
  startResearchQualityJob,
} from "../../lib/api";
import { getDataQualitySummary } from "../../lib/api/researchData";
import type {
  DataQualityUnreviewedSummary,
  ResearchDataAsset,
  ResearchDataGap,
  ResearchDataImportRun,
  ResearchDataProvider,
  ResearchDataQualityReport,
  ResearchJob,
} from "../../lib/types";
import styles from "../../styles/pages/data-centre.module.css";

type LoadState = "loading" | "ready" | "error";
type ApprovalFilter = "all" | "approved" | "rejected";

function formatDate(value: string | null): string {
  if (!value) return "-";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString();
}

function uniq(values: string[]): string[] {
  return Array.from(new Set(values)).sort((a, b) => a.localeCompare(b));
}

export default function DataCentrePage() {
  const [state, setState] = useState<LoadState>("loading");
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState<string | null>(null);

  const [assets, setAssets] = useState<ResearchDataAsset[]>([]);
  const [providers, setProviders] = useState<ResearchDataProvider[]>([]);
  const [coverage, setCoverage] = useState<ResearchDataAsset[]>([]);
  const [quality, setQuality] = useState<ResearchDataQualityReport[]>([]);
  const [gaps, setGaps] = useState<ResearchDataGap[]>([]);
  const [importRuns, setImportRuns] = useState<ResearchDataImportRun[]>([]);
  const [jobs, setJobs] = useState<ResearchJob[]>([]);
  const [selectedJob, setSelectedJob] = useState<ResearchJob | null>(null);
  const [qualitySummary, setQualitySummary] = useState<DataQualityUnreviewedSummary | null>(null);

  const [assetFilter, setAssetFilter] = useState<string>("all");
  const [timeframeFilter, setTimeframeFilter] = useState<string>("all");
  const [providerFilter, setProviderFilter] = useState<string>("all");
  const [approvalFilter, setApprovalFilter] = useState<ApprovalFilter>("all");

  const [importAsset, setImportAsset] = useState<string>("all");
  const [importTimeframe, setImportTimeframe] = useState<string>("1d");
  const [importProvider, setImportProvider] = useState<string>("yfinance");
  const [requestedYears, setRequestedYears] = useState<number>(20);
  const [dryRun, setDryRun] = useState<boolean>(true);

  const [qualityAsset, setQualityAsset] = useState<string>("all");
  const [qualityTimeframe, setQualityTimeframe] = useState<string>("1d");
  const [qualityProvider, setQualityProvider] = useState<string>("all");

  useEffect(() => {
    let active = true;

    async function loadAll() {
      setState("loading");
      setError(null);
      try {
        const [assetsResp, providersResp, coverageResp, qualityResp, gapsResp, importRunsResp, jobsResult] = await Promise.allSettled([
          getResearchDataAssets(),
          getResearchDataProviders(),
          getResearchDataCoverage(),
          getResearchDataQuality(),
          getResearchDataGaps(),
          getResearchDataImportRuns(),
          getResearchJobs(),
        ]);

        if (!active) return;

        if (
          assetsResp.status !== "fulfilled" ||
          providersResp.status !== "fulfilled" ||
          coverageResp.status !== "fulfilled" ||
          qualityResp.status !== "fulfilled" ||
          gapsResp.status !== "fulfilled" ||
          importRunsResp.status !== "fulfilled"
        ) {
          throw new Error("Failed to load Data Centre data.");
        }

        setAssets(assetsResp.value.items);
        setProviders(providersResp.value.providers);
        setCoverage(coverageResp.value.items);
        setQuality(qualityResp.value.items);
        setGaps(gapsResp.value.items);
        setImportRuns(importRunsResp.value.items);

        if (jobsResult.status === "fulfilled") {
          setJobs(jobsResult.value.items);
        } else {
          setJobs([]);
          setActionMessage("Research jobs are temporarily unavailable. Core Data Centre views are still loaded.");
        }
        setState("ready");
      } catch (err) {
        if (!active) return;
        const msg = err instanceof Error ? err.message : "Failed to load Data Centre data.";
        setError(msg);
        setState("error");
      }

      // Summary card — non-blocking, best effort
      try {
        const summary = await getDataQualitySummary();
        if (active) setQualitySummary(summary);
      } catch {
        // silently ignore — card just won't render
      }
    }

    void loadAll();
    return () => {
      active = false;
    };
  }, []);

  const assetOptions = useMemo(() => {
    const symbols = uniq([
      ...assets.map((a) => a.asset_symbol),
      ...quality.map((q) => q.asset_symbol),
      ...gaps.map((g) => g.asset_symbol),
      ...coverage.map((c) => c.asset_symbol),
    ]);
    return ["all", ...symbols];
  }, [assets, quality, gaps, coverage]);

  const timeframeOptions = useMemo(() => {
    const values = uniq([
      ...quality.map((q) => q.timeframe),
      ...gaps.map((g) => g.timeframe),
      ...coverage.flatMap((c) => c.timeframes),
    ]);
    return ["all", ...values];
  }, [quality, gaps, coverage]);

  const providerOptions = useMemo(() => {
    const values = uniq([
      ...providers.map((p) => p.name),
      ...quality.map((q) => q.provider ?? "unknown"),
      ...gaps.map((g) => g.provider ?? "unknown"),
      ...coverage.flatMap((c) => c.providers),
    ]);
    return ["all", ...values];
  }, [providers, quality, gaps, coverage]);

  useEffect(() => {
    if (importAsset === "all" && assetOptions.length > 1) setImportAsset(assetOptions[1]);
    if (qualityAsset === "all" && assetOptions.length > 1) setQualityAsset(assetOptions[1]);
    if (!timeframeOptions.includes(importTimeframe)) setImportTimeframe(timeframeOptions[1] ?? "1d");
    if (!timeframeOptions.includes(qualityTimeframe)) setQualityTimeframe(timeframeOptions[1] ?? "1d");
    if (!providerOptions.includes(importProvider)) setImportProvider(providerOptions.includes("yfinance") ? "yfinance" : providerOptions[1] ?? "yfinance");
    if (!providerOptions.includes(qualityProvider)) setQualityProvider("all");
  }, [assetOptions, timeframeOptions, providerOptions, importAsset, qualityAsset, importTimeframe, qualityTimeframe, importProvider, qualityProvider]);

  const filteredQuality = useMemo(() => {
    return quality.filter((row) => {
      if (assetFilter !== "all" && row.asset_symbol !== assetFilter) return false;
      if (timeframeFilter !== "all" && row.timeframe !== timeframeFilter) return false;
      const normalizedProvider = row.provider ?? "unknown";
      if (providerFilter !== "all" && normalizedProvider !== providerFilter) return false;
      if (approvalFilter === "approved" && row.approved_for_backtest !== true) return false;
      if (approvalFilter === "rejected" && row.approved_for_backtest !== false) return false;
      return true;
    });
  }, [quality, assetFilter, timeframeFilter, providerFilter, approvalFilter]);

  const filteredGaps = useMemo(() => {
    return gaps.filter((row) => {
      if (assetFilter !== "all" && row.asset_symbol !== assetFilter) return false;
      if (timeframeFilter !== "all" && row.timeframe !== timeframeFilter) return false;
      const normalizedProvider = row.provider ?? "unknown";
      if (providerFilter !== "all" && normalizedProvider !== providerFilter) return false;
      return true;
    });
  }, [gaps, assetFilter, timeframeFilter, providerFilter]);

  const coverageRows = useMemo(() => {
    return filteredQuality.filter((row) => {
      if (assetFilter !== "all" && row.asset_symbol !== assetFilter) return false;
      if (timeframeFilter !== "all" && row.timeframe !== timeframeFilter) return false;
      const normalizedProvider = row.provider ?? "unknown";
      if (providerFilter !== "all" && normalizedProvider !== providerFilter) return false;
      return true;
    });
  }, [filteredQuality, assetFilter, timeframeFilter, providerFilter]);

  const approvedDatasets = useMemo(
    () => quality.filter((row) => row.approved_for_backtest === true).length,
    [quality],
  );

  const openGaps = useMemo(() => gaps.filter((row) => row.status === "open").length, [gaps]);

  const latestImport = importRuns.length > 0 ? importRuns[0] : null;

  async function refreshJobs() {
    try {
      const jobsResp = await getResearchJobs();
      setJobs(jobsResp.items);
      setActionMessage("Job list refreshed.");
    } catch (err) {
      setActionMessage(err instanceof Error ? err.message : "Failed to refresh jobs.");
    }
  }

  async function handleStartImportJob() {
    if (importAsset === "all") {
      setActionMessage("Choose a specific asset before starting an import job.");
      return;
    }
    setSubmitting("import");
    try {
      const response = await startResearchImportJob({
        assets: [importAsset],
        timeframes: [importTimeframe],
        requested_years: requestedYears,
        providers: [importProvider],
        dry_run: dryRun,
      });
      setSelectedJob(response.job);
      setActionMessage(`Import job completed with status: ${response.job.status}`);
      await refreshJobs();
    } catch (err) {
      setActionMessage(err instanceof Error ? err.message : "Failed to start import job.");
    } finally {
      setSubmitting(null);
    }
  }

  async function handleStartQualityJob() {
    if (qualityAsset === "all") {
      setActionMessage("Choose a specific asset before starting a quality job.");
      return;
    }
    setSubmitting("quality");
    try {
      const response = await startResearchQualityJob({
        assets: [qualityAsset],
        timeframes: [qualityTimeframe],
        providers: qualityProvider === "all" ? undefined : [qualityProvider],
      });
      setSelectedJob(response.job);
      setActionMessage(`Quality job completed with status: ${response.job.status}`);
      await refreshJobs();
    } catch (err) {
      setActionMessage(err instanceof Error ? err.message : "Failed to start quality recalculation job.");
    } finally {
      setSubmitting(null);
    }
  }

  async function handleSelectJob(jobId: string) {
    try {
      const response = await getResearchJob(jobId);
      setSelectedJob(response.job);
    } catch (err) {
      setActionMessage(err instanceof Error ? err.message : "Failed to load job detail.");
    }
  }

  async function handleCancelJob(jobId: string) {
    setSubmitting(`cancel-${jobId}`);
    try {
      const response = await cancelResearchJob(jobId);
      setActionMessage(response.message);
      if (response.job) setSelectedJob(response.job);
      await refreshJobs();
    } catch (err) {
      setActionMessage(err instanceof Error ? err.message : "Failed to cancel job.");
    } finally {
      setSubmitting(null);
    }
  }

  async function handleRetryJob(jobId: string) {
    setSubmitting(`retry-${jobId}`);
    try {
      const response = await retryResearchJob(jobId);
      setActionMessage(response.message);
      if (response.job) setSelectedJob(response.job);
      await refreshJobs();
    } catch (err) {
      setActionMessage(err instanceof Error ? err.message : "Failed to retry job.");
    } finally {
      setSubmitting(null);
    }
  }

  return (
    <main className={styles.page}>
      <div className={styles.container}>
        <header className={styles.header}>
          <div>
            <h1 className={styles.title}>Data Centre</h1>
            <p className={styles.subtitle}>Historical data coverage, quality, gaps, and import readiness.</p>
          </div>
          <div className={styles.badge}>Operations panel</div>
        </header>

        <div className={styles.note}>Run MH-02 imports before expecting full coverage.</div>
        {qualitySummary && qualitySummary.unreviewed > 0 && (
          <div className={styles.qualityAlert} data-testid="dc-quality-alert">
            <span>
              ⚠ {qualitySummary.unreviewed} unreviewed data quality{" "}
              {qualitySummary.unreviewed === 1 ? "issue" : "issues"} detected.
            </span>
            <a href="/data-quality" className={styles.qualityAlertLink}>
              Review now →
            </a>
          </div>
        )}
        {actionMessage ? <div className={styles.info}>{actionMessage}</div> : null}

        <section className={styles.controls} aria-label="Data Centre filters">
          <select className={styles.select} value={assetFilter} onChange={(e) => setAssetFilter(e.target.value)}>
            {assetOptions.map((asset) => (
              <option key={asset} value={asset}>
                {asset === "all" ? "All assets" : asset}
              </option>
            ))}
          </select>

          <select className={styles.select} value={timeframeFilter} onChange={(e) => setTimeframeFilter(e.target.value)}>
            {timeframeOptions.map((tf) => (
              <option key={tf} value={tf}>
                {tf === "all" ? "All timeframes" : tf}
              </option>
            ))}
          </select>

          <select className={styles.select} value={providerFilter} onChange={(e) => setProviderFilter(e.target.value)}>
            {providerOptions.map((provider) => (
              <option key={provider} value={provider}>
                {provider === "all" ? "All providers" : provider}
              </option>
            ))}
          </select>

          <select
            className={styles.select}
            value={approvalFilter}
            onChange={(e) => setApprovalFilter(e.target.value as ApprovalFilter)}
          >
            <option value="all">All quality approvals</option>
            <option value="approved">Approved only</option>
            <option value="rejected">Rejected only</option>
          </select>

          <button className={styles.actionBtn} type="button" onClick={() => void refreshJobs()}>
            Refresh Jobs
          </button>
        </section>

        {state === "loading" && <div className={styles.loading}>Loading Data Centre datasets...</div>}
        {state === "error" && (
          <>
            <div className={styles.error}>
              Backend unavailable or request failed: {error ?? "Unknown error"}
            </div>

            <section className={styles.jobLayout} data-testid="research-jobs-panel">
              <section className={styles.panel} aria-label="Recent research jobs">
                <div className={styles.panelHeader}>
                  <h2 className={styles.panelTitle}>Recent Jobs</h2>
                  <span className={styles.panelSub}>Unavailable while backend data is offline</span>
                </div>
                <div className={styles.empty}>Job history will appear here once the backend is reachable.</div>
              </section>

              <section className={styles.panel} aria-label="Job controls">
                <div className={styles.panelHeader}>
                  <h2 className={styles.panelTitle}>Job Controls</h2>
                  <span className={styles.panelSub}>Controls remain visible even when live data is unavailable</span>
                </div>
                <div className={styles.formGrid}>
                  <div className={styles.formCard}>
                    <h3 className={styles.formTitle}>Import Controls</h3>
                    <button className={styles.primaryBtn} type="button" onClick={() => void handleStartImportJob()}>
                      Start Import Job
                    </button>
                  </div>

                  <div className={styles.formCard}>
                    <h3 className={styles.formTitle}>Quality Recalculation Controls</h3>
                    <button className={styles.primaryBtn} type="button" onClick={() => void handleStartQualityJob()}>
                      Start Quality Recalculation Job
                    </button>
                  </div>
                </div>
              </section>
            </section>
          </>
        )}

        {state === "ready" && (
          <>
            <section className={styles.summaryGrid} aria-label="System summary cards">
              <article className={styles.card}>
                <span className={styles.cardLabel}>Total Tracked Assets</span>
                <strong className={styles.cardValue}>{assets.length}</strong>
                <span className={styles.cardMeta}>{coverage.length} assets with coverage records</span>
              </article>
              <article className={styles.card}>
                <span className={styles.cardLabel}>Providers Available</span>
                <strong className={styles.cardValue}>{providers.length}</strong>
                <span className={styles.cardMeta}>From configured research catalogue</span>
              </article>
              <article className={styles.card}>
                <span className={styles.cardLabel}>Approved Datasets</span>
                <strong className={styles.cardValue}>{approvedDatasets}</strong>
                <span className={styles.cardMeta}>Quality score threshold applied</span>
              </article>
              <article className={styles.card}>
                <span className={styles.cardLabel}>Open Gaps</span>
                <strong className={styles.cardValue}>{openGaps}</strong>
                <span className={styles.cardMeta}>Detected missing-candle spans</span>
              </article>
              <article className={styles.card}>
                <span className={styles.cardLabel}>Latest Import Status</span>
                <strong className={styles.cardValue}>{latestImport?.status ?? "none"}</strong>
                <span className={styles.cardMeta}>
                  {latestImport ? `Started ${formatDate(latestImport.started_at)}` : "No import run recorded"}
                </span>
              </article>
            </section>

            <section className={styles.jobLayout} data-testid="research-jobs-panel">
              <section className={styles.panel} aria-label="Recent research jobs">
                <div className={styles.panelHeader}>
                  <h2 className={styles.panelTitle}>Recent Jobs</h2>
                  <span className={styles.panelSub}>{jobs.length} jobs</span>
                </div>
                {jobs.length === 0 ? (
                  <div className={styles.empty}>No jobs recorded yet.</div>
                ) : (
                  <div className={styles.tableWrap}>
                    <table className={styles.table}>
                      <thead>
                        <tr>
                          <th className={styles.th}>Job Type</th>
                          <th className={styles.th}>Status</th>
                          <th className={styles.th}>Progress</th>
                          <th className={styles.th}>Message</th>
                          <th className={styles.th}>Created</th>
                          <th className={styles.th}>Started</th>
                          <th className={styles.th}>Completed</th>
                          <th className={styles.th}>Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {jobs.map((job) => (
                          <tr key={job.id}>
                            <td className={styles.td}>{job.job_type}</td>
                            <td className={styles.td}>
                              <span className={`${styles.chip} ${job.status === "completed" ? styles.approved : job.status === "failed" ? styles.rejected : job.status === "partial" ? styles.warning : styles.neutral}`}>
                                {job.status}
                              </span>
                            </td>
                            <td className={`${styles.td} ${styles.right}`}>{job.progress_current}/{job.progress_total}</td>
                            <td className={`${styles.td} ${styles.muted}`}>{job.progress_message ?? "-"}</td>
                            <td className={`${styles.td} ${styles.muted}`}>{formatDate(job.created_at)}</td>
                            <td className={`${styles.td} ${styles.muted}`}>{formatDate(job.started_at)}</td>
                            <td className={`${styles.td} ${styles.muted}`}>{formatDate(job.completed_at)}</td>
                            <td className={styles.td}>
                              <div className={styles.inlineActions}>
                                <button className={styles.smallBtn} type="button" onClick={() => void handleSelectJob(job.id)}>View</button>
                                <button
                                  className={styles.smallBtn}
                                  type="button"
                                  onClick={() => void handleRetryJob(job.id)}
                                  disabled={!(["failed", "partial", "cancelled"].includes(job.status)) || submitting === `retry-${job.id}`}
                                >
                                  Retry
                                </button>
                                <button
                                  className={styles.smallBtn}
                                  type="button"
                                  onClick={() => void handleCancelJob(job.id)}
                                  disabled={job.status !== "queued" || submitting === `cancel-${job.id}`}
                                >
                                  Cancel
                                </button>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </section>

              <section className={styles.panel} aria-label="Job controls">
                <div className={styles.panelHeader}>
                  <h2 className={styles.panelTitle}>Job Controls</h2>
                  <span className={styles.panelSub}>Conservative start/retry/cancel actions</span>
                </div>
                <div className={styles.formGrid}>
                  <div className={styles.formCard}>
                    <h3 className={styles.formTitle}>Import Controls</h3>
                    <label className={styles.fieldLabel}>
                      Asset
                      <select className={styles.select} value={importAsset} onChange={(e) => setImportAsset(e.target.value)}>
                        {assetOptions.map((asset) => (
                          <option key={asset} value={asset}>{asset === "all" ? "Select asset" : asset}</option>
                        ))}
                      </select>
                    </label>
                    <label className={styles.fieldLabel}>
                      Timeframe
                      <select className={styles.select} value={importTimeframe} onChange={(e) => setImportTimeframe(e.target.value)}>
                        {timeframeOptions.filter((tf) => tf !== "all").map((tf) => (
                          <option key={tf} value={tf}>{tf}</option>
                        ))}
                      </select>
                    </label>
                    <label className={styles.fieldLabel}>
                      Provider
                      <select className={styles.select} value={importProvider} onChange={(e) => setImportProvider(e.target.value)}>
                        {providerOptions.filter((provider) => provider !== "all" && provider !== "unknown").map((provider) => (
                          <option key={provider} value={provider}>{provider}</option>
                        ))}
                      </select>
                    </label>
                    <label className={styles.fieldLabel}>
                      Requested Years
                      <input className={styles.input} type="number" min={1} max={20} value={requestedYears} onChange={(e) => setRequestedYears(Number(e.target.value))} />
                    </label>
                    <label className={styles.toggleRow}>
                      <input type="checkbox" checked={dryRun} onChange={(e) => setDryRun(e.target.checked)} />
                      Dry run
                    </label>
                    <button className={styles.primaryBtn} type="button" onClick={() => void handleStartImportJob()} disabled={submitting === "import"}>
                      Start Import Job
                    </button>
                  </div>

                  <div className={styles.formCard}>
                    <h3 className={styles.formTitle}>Quality Recalculation Controls</h3>
                    <label className={styles.fieldLabel}>
                      Asset
                      <select className={styles.select} value={qualityAsset} onChange={(e) => setQualityAsset(e.target.value)}>
                        {assetOptions.map((asset) => (
                          <option key={asset} value={asset}>{asset === "all" ? "Select asset" : asset}</option>
                        ))}
                      </select>
                    </label>
                    <label className={styles.fieldLabel}>
                      Timeframe
                      <select className={styles.select} value={qualityTimeframe} onChange={(e) => setQualityTimeframe(e.target.value)}>
                        {timeframeOptions.filter((tf) => tf !== "all").map((tf) => (
                          <option key={tf} value={tf}>{tf}</option>
                        ))}
                      </select>
                    </label>
                    <label className={styles.fieldLabel}>
                      Provider
                      <select className={styles.select} value={qualityProvider} onChange={(e) => setQualityProvider(e.target.value)}>
                        {providerOptions.map((provider) => (
                          <option key={provider} value={provider}>{provider === "all" ? "All providers" : provider}</option>
                        ))}
                      </select>
                    </label>
                    <button className={styles.primaryBtn} type="button" onClick={() => void handleStartQualityJob()} disabled={submitting === "quality"}>
                      Start Quality Recalculation Job
                    </button>
                  </div>
                </div>

                {selectedJob ? (
                  <div className={styles.detailCard}>
                    <h3 className={styles.formTitle}>Selected Job Detail</h3>
                    <div className={styles.detailGrid}>
                      <div><span className={styles.detailLabel}>ID</span><span>{selectedJob.id}</span></div>
                      <div><span className={styles.detailLabel}>Type</span><span>{selectedJob.job_type}</span></div>
                      <div><span className={styles.detailLabel}>Status</span><span>{selectedJob.status}</span></div>
                      <div><span className={styles.detailLabel}>Progress</span><span>{selectedJob.progress_current}/{selectedJob.progress_total}</span></div>
                      <div><span className={styles.detailLabel}>Message</span><span>{selectedJob.progress_message ?? "-"}</span></div>
                      <div><span className={styles.detailLabel}>Error</span><span>{selectedJob.error_message ?? "-"}</span></div>
                    </div>
                  </div>
                ) : null}
              </section>
            </section>

            <section className={styles.panel} aria-label="Coverage table">
              <div className={styles.panelHeader}>
                <h2 className={styles.panelTitle}>Coverage</h2>
                <span className={styles.panelSub}>{coverageRows.length} rows</span>
              </div>
              {coverageRows.length === 0 ? (
                <div className={styles.empty}>No coverage rows for current filters.</div>
              ) : (
                <div className={styles.tableWrap}>
                  <table className={styles.table}>
                    <thead>
                      <tr>
                        <th className={styles.th}>Asset</th>
                        <th className={styles.th}>Asset Class</th>
                        <th className={styles.th}>Provider</th>
                        <th className={styles.th}>Timeframe</th>
                        <th className={styles.th}>Available From</th>
                        <th className={styles.th}>Available To</th>
                        <th className={styles.th}>Candle Count</th>
                        <th className={styles.th}>Completeness</th>
                        <th className={styles.th}>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {coverageRows.map((row) => (
                        <tr key={`${row.asset_symbol}-${row.timeframe}-${row.provider ?? "unknown"}`}>
                          <td className={`${styles.td} ${styles.asset}`}>{row.asset_symbol}</td>
                          <td className={`${styles.td} ${styles.muted}`}>-</td>
                          <td className={styles.td}>{row.provider ?? "unknown"}</td>
                          <td className={styles.td}>{row.timeframe}</td>
                          <td className={`${styles.td} ${styles.muted}`}>{formatDate(row.earliest_bar_ts)}</td>
                          <td className={`${styles.td} ${styles.muted}`}>{formatDate(row.latest_bar_ts)}</td>
                          <td className={`${styles.td} ${styles.right}`}>{row.total_bars}</td>
                          <td className={`${styles.td} ${styles.right}`}>
                            {row.completeness_pct === null ? "-" : `${row.completeness_pct.toFixed(2)}%`}
                          </td>
                          <td className={styles.td}>
                            <span
                              className={`${styles.chip} ${
                                row.approved_for_backtest ? styles.approved : styles.warning
                              }`}
                            >
                              {row.approved_for_backtest ? "ready" : "review"}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            <section className={styles.panel} aria-label="Quality table">
              <div className={styles.panelHeader}>
                <h2 className={styles.panelTitle}>Quality</h2>
                <span className={styles.panelSub}>{filteredQuality.length} rows</span>
              </div>
              {filteredQuality.length === 0 ? (
                <div className={styles.empty}>No quality rows for current filters.</div>
              ) : (
                <div className={styles.tableWrap}>
                  <table className={styles.table}>
                    <thead>
                      <tr>
                        <th className={styles.th}>Asset</th>
                        <th className={styles.th}>Timeframe</th>
                        <th className={styles.th}>Provider</th>
                        <th className={styles.th}>Actual Bars</th>
                        <th className={styles.th}>Expected Bars</th>
                        <th className={styles.th}>Duplicates</th>
                        <th className={styles.th}>Bad Price Bars</th>
                        <th className={styles.th}>Spikes</th>
                        <th className={styles.th}>Quality Score</th>
                        <th className={styles.th}>Approved</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredQuality.map((row) => (
                        <tr key={`${row.asset_symbol}-${row.timeframe}-${row.provider ?? "unknown"}`}>
                          <td className={`${styles.td} ${styles.asset}`}>{row.asset_symbol}</td>
                          <td className={styles.td}>{row.timeframe}</td>
                          <td className={styles.td}>{row.provider ?? "unknown"}</td>
                          <td className={`${styles.td} ${styles.right}`}>{row.actual_bars ?? "-"}</td>
                          <td className={`${styles.td} ${styles.right}`}>{row.expected_bars ?? "-"}</td>
                          <td className={`${styles.td} ${styles.right}`}>{row.duplicate_bars}</td>
                          <td className={`${styles.td} ${styles.right}`}>{row.bad_price_bars}</td>
                          <td className={`${styles.td} ${styles.right}`}>{row.suspicious_spike_bars}</td>
                          <td className={`${styles.td} ${styles.right}`}>
                            {row.quality_score === null ? "-" : row.quality_score.toFixed(2)}
                          </td>
                          <td className={styles.td}>
                            <span
                              className={`${styles.chip} ${
                                row.approved_for_backtest ? styles.approved : styles.rejected
                              }`}
                            >
                              {row.approved_for_backtest ? "yes" : "no"}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            <section className={styles.panel} aria-label="Gaps table">
              <div className={styles.panelHeader}>
                <h2 className={styles.panelTitle}>Gaps</h2>
                <span className={styles.panelSub}>{filteredGaps.length} rows</span>
              </div>
              {filteredGaps.length === 0 ? (
                <div className={styles.empty}>No detected gaps for current filters.</div>
              ) : (
                <div className={styles.tableWrap}>
                  <table className={styles.table}>
                    <thead>
                      <tr>
                        <th className={styles.th}>Asset</th>
                        <th className={styles.th}>Timeframe</th>
                        <th className={styles.th}>Provider</th>
                        <th className={styles.th}>Gap Start</th>
                        <th className={styles.th}>Gap End</th>
                        <th className={styles.th}>Expected Missing</th>
                        <th className={styles.th}>Severity</th>
                        <th className={styles.th}>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredGaps.map((row) => (
                        <tr key={row.id}>
                          <td className={`${styles.td} ${styles.asset}`}>{row.asset_symbol}</td>
                          <td className={styles.td}>{row.timeframe}</td>
                          <td className={styles.td}>{row.provider ?? "unknown"}</td>
                          <td className={`${styles.td} ${styles.muted}`}>{formatDate(row.gap_start)}</td>
                          <td className={`${styles.td} ${styles.muted}`}>{formatDate(row.gap_end)}</td>
                          <td className={`${styles.td} ${styles.right}`}>{row.expected_candles_missing}</td>
                          <td className={styles.td}>
                            <span className={`${styles.chip} ${row.severity === "high" ? styles.rejected : row.severity === "medium" ? styles.warning : styles.neutral}`}>
                              {row.severity}
                            </span>
                          </td>
                          <td className={styles.td}>{row.status}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            <section className={styles.panel} aria-label="Import runs table">
              <div className={styles.panelHeader}>
                <h2 className={styles.panelTitle}>Import Runs</h2>
                <span className={styles.panelSub}>{importRuns.length} rows</span>
              </div>
              {importRuns.length === 0 ? (
                <div className={styles.empty}>No import runs recorded yet.</div>
              ) : (
                <div className={styles.tableWrap}>
                  <table className={styles.table}>
                    <thead>
                      <tr>
                        <th className={styles.th}>Run ID</th>
                        <th className={styles.th}>Status</th>
                        <th className={styles.th}>Requested Years</th>
                        <th className={styles.th}>Started At</th>
                        <th className={styles.th}>Completed At</th>
                        <th className={styles.th}>Total Candles Imported</th>
                        <th className={styles.th}>Failure Count</th>
                      </tr>
                    </thead>
                    <tbody>
                      {importRuns.map((run) => (
                        <tr key={run.batch_id}>
                          <td className={`${styles.td} ${styles.muted}`}>{run.batch_id.slice(0, 12)}...</td>
                          <td className={styles.td}>{run.status}</td>
                          <td className={`${styles.td} ${styles.right}`}>{run.requested_years}</td>
                          <td className={`${styles.td} ${styles.muted}`}>{formatDate(run.started_at)}</td>
                          <td className={`${styles.td} ${styles.muted}`}>{formatDate(run.completed_at)}</td>
                          <td className={`${styles.td} ${styles.right}`}>{run.total_candles_imported}</td>
                          <td className={`${styles.td} ${styles.right}`}>{run.failed_count}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          </>
        )}
      </div>
    </main>
  );
}
