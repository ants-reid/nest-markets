"use client";

import Link from "next/link";
import { useState } from "react";

import {
  getPaperRecommendationRouteCheck,
  previewPaperRecommendationBrokerDryRun,
  type PaperRecommendationBrokerDryRunPreview,
  type PaperRecommendationRouteCheck,
} from "../lib/api/paperRecommendations";
import styles from "./RecommendationRouteCheckPanel.module.css";

function statusClassName(status: string): string {
  if (status === "eligible" || status === "ready") return styles.statusEligible;
  if (status === "blocked") return styles.statusBlocked;
  if (status === "missing_context" || status === "invalid") return styles.statusMissing;
  return styles.statusUnknown;
}

function summaryClassName(status: string): string {
  if (status === "eligible" || status === "ready") return styles.summaryEligible;
  if (status === "blocked") return styles.summaryBlocked;
  if (status === "missing_context" || status === "invalid") return styles.summaryMissing;
  return styles.summaryUnknown;
}

function formatStatus(status: string): string {
  return status.replaceAll("_", " ");
}

function formatMaybeNumber(value: number | null): string {
  if (value === null) return "unknown";
  return value.toLocaleString("en-US", { maximumFractionDigits: 4 });
}

function formatBoolean(value: boolean | null): string {
  if (value === null) return "not evaluated";
  return value ? "yes" : "no";
}

function summaryCopy(result: PaperRecommendationRouteCheck): { title: string; body: string } {
  if (result.route_check_status === "eligible") {
    return {
      title: "Ready for guarded IBKR paper dry-run/manual review",
      body:
        "This recommendation is eligible for the canonical manual IBKR paper review path. Dry-run and submit still stay behind the existing guarded broker workflow.",
    };
  }

  if (result.route_check_status === "blocked") {
    return {
      title: "IBKR paper route-check is blocked",
      body: result.blocked_reason ?? "The broker paper route is not available in the current safety posture.",
    };
  }

  if (result.route_check_status === "missing_context") {
    return {
      title: "Recommendation is missing manual-review context",
      body:
        result.missing_data.length > 0
          ? "Resolve the listed recommendation gaps before manual IBKR paper review."
          : "Additional recommendation context is required before manual IBKR paper review.",
    };
  }

  return {
    title: "Route-check status is unknown",
    body: "Review broker paper readiness before using the manual IBKR paper workflow.",
  };
}

function dryRunSummaryCopy(result: PaperRecommendationBrokerDryRunPreview): { title: string; body: string } {
  if (!result.dry_run_executed) {
    if (result.dry_run_status === "missing_context") {
      return {
        title: "Dry-run preview is unavailable until recommendation context is complete",
        body: "The guarded broker dry-run was not executed. Complete the missing recommendation context first.",
      };
    }

    return {
      title: "Dry-run preview remains blocked",
      body: result.blocked_reason ?? "The guarded broker dry-run was not executed in the current safety posture.",
    };
  }

  if (result.dry_run_status === "invalid") {
    return {
      title: "Dry-run found invalid order details",
      body: "The preview stayed non-submitting and surfaced invalid recommendation fields that must be corrected first.",
    };
  }

  if (result.would_block) {
    return {
      title: "Dry-run surfaced preflight findings that still block progression",
      body:
        result.blocked_reason ??
        "The preview stayed non-submitting and flagged findings that must be resolved before the guarded manual paper path should be considered.",
    };
  }

  return {
    title: "Guarded broker dry-run completed with no order submitted",
    body:
      "This preview reused the existing broker dry-run path only. It did not place an order, and the guarded manual /broker/orders workflow remains the only paper submit path.",
  };
}

export function RecommendationRouteCheckPanel({
  recommendationId,
  symbol,
}: {
  recommendationId: string;
  symbol: string;
}) {
  const [result, setResult] = useState<PaperRecommendationRouteCheck | null>(null);
  const [preview, setPreview] = useState<PaperRecommendationBrokerDryRunPreview | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const response = await getPaperRecommendationRouteCheck(recommendationId);
      setResult(response);
      if (response.route_check_status !== "eligible") {
        setPreview(null);
        setPreviewError(null);
      }
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : String(loadError));
    } finally {
      setLoading(false);
    }
  }

  async function loadPreview() {
    setPreviewLoading(true);
    setPreviewError(null);
    try {
      const response = await previewPaperRecommendationBrokerDryRun(recommendationId);
      setPreview(response);
    } catch (loadError) {
      setPreviewError(loadError instanceof Error ? loadError.message : String(loadError));
    } finally {
      setPreviewLoading(false);
    }
  }

  const summary = result ? summaryCopy(result) : null;
  const previewSummary = preview ? dryRunSummaryCopy(preview) : null;
  const blockingFindings = preview?.preflight_decision
    ? [...preview.preflight_decision.blocking_items, ...preview.preflight_decision.would_block_items]
    : [];

  return (
    <section
      className={styles.panel}
      data-testid={`recommendation-route-check-panel-${recommendationId}`}
      aria-label={`Recommendation route check for ${symbol}`}
    >
      <div className={styles.header}>
        <div className={styles.titleWrap}>
          <p className={styles.eyebrow}>Operator route review</p>
          <h4 className={styles.title}>IBKR paper route-check</h4>
          <p className={styles.subtitle}>
            Review whether this recommendation can proceed to the guarded manual IBKR paper dry-run workflow.
          </p>
        </div>
        {result ? (
          <span
            className={`${styles.statusPill} ${statusClassName(result.route_check_status)}`}
            data-testid={`recommendation-route-check-status-${recommendationId}`}
          >
            {formatStatus(result.route_check_status)}
          </span>
        ) : null}
      </div>

      <div className={styles.controls}>
        <button
          type="button"
          className={styles.button}
          onClick={() => void load()}
          disabled={loading}
          data-testid={`recommendation-route-check-trigger-${recommendationId}`}
        >
          {loading
            ? "Loading route-check…"
            : result
              ? "Refresh IBKR paper route-check"
              : "Review IBKR paper route-check"}
        </button>
        {result?.route_check_status === "eligible" ? (
          <button
            type="button"
            className={`${styles.button} ${styles.secondaryButton}`}
            onClick={() => void loadPreview()}
            disabled={previewLoading}
            data-testid={`recommendation-dry-run-preview-trigger-${recommendationId}`}
          >
            {previewLoading
              ? "Loading guarded dry-run…"
              : preview
                ? "Refresh guarded broker dry-run"
                : "Run guarded broker dry-run preview"}
          </button>
        ) : null}
      </div>

      {error ? (
        <div
          className={styles.inlineError}
          data-testid={`recommendation-route-check-error-${recommendationId}`}
          role="alert"
        >
          {error}
        </div>
      ) : null}

      {result ? (
        <>
          <div
            className={`${styles.summary} ${summaryClassName(result.route_check_status)}`}
            data-testid={`recommendation-route-check-summary-${recommendationId}`}
          >
            <p className={styles.summaryTitle}>{summary?.title}</p>
            <p className={styles.summaryText}>{summary?.body}</p>
          </div>

          <div className={styles.grid}>
            <div className={styles.field}>
              <span className={styles.label}>Recommendation ID</span>
              <span className={`${styles.value} ${styles.mono}`}>{result.recommendation_id}</span>
            </div>
            <div className={styles.field}>
              <span className={styles.label}>Recommendation status</span>
              <span className={styles.value}>{result.recommendation_status}</span>
            </div>
            <div className={styles.field}>
              <span className={styles.label}>Symbol</span>
              <span className={styles.value}>{result.ticker ?? symbol}</span>
            </div>
            <div className={styles.field}>
              <span className={styles.label}>Side</span>
              <span className={styles.value}>{result.side ?? "unknown"}</span>
            </div>
            <div className={styles.field}>
              <span className={styles.label}>Quantity</span>
              <span className={styles.value}>{formatMaybeNumber(result.quantity)}</span>
            </div>
            <div className={styles.field}>
              <span className={styles.label}>Order type</span>
              <span className={styles.value}>{result.order_type ?? "unknown"}</span>
            </div>
            <div className={styles.field}>
              <span className={styles.label}>Execution source</span>
              <span className={styles.value}>{result.execution_source}</span>
            </div>
            <div className={styles.field}>
              <span className={styles.label}>Resolved execution source</span>
              <span className={styles.value}>{result.resolved_execution_source ?? "not resolved"}</span>
            </div>
            <div className={styles.field}>
              <span className={styles.label}>Resolved route</span>
              <span className={`${styles.value} ${styles.mono}`}>{result.resolved_route ?? "not resolved"}</span>
            </div>
            <div className={styles.field}>
              <span className={styles.label}>Canonical paper route</span>
              <span className={`${styles.value} ${styles.mono}`}>{result.canonical_paper_route}</span>
            </div>
            <div className={styles.field}>
              <span className={styles.label}>Serious paper source</span>
              <span className={styles.value}>{result.serious_paper_source}</span>
            </div>
            <div className={styles.field}>
              <span className={styles.label}>Canonical paper</span>
              <span className={styles.value}>{result.is_canonical_paper ? "yes" : "no"}</span>
            </div>
            <div className={styles.field}>
              <span className={styles.label}>Broker account mode</span>
              <span className={styles.value}>{result.broker_account_mode}</span>
            </div>
            <div className={styles.field}>
              <span className={styles.label}>Live state</span>
              <span className={styles.value}>{result.live_state}</span>
            </div>
            <div className={styles.field}>
              <span className={styles.label}>Would block</span>
              <span className={styles.value}>{result.would_block ? "yes" : "no"}</span>
            </div>
            <div className={styles.field}>
              <span className={styles.label}>Workers allowed to submit</span>
              <span className={styles.value}>{result.workers_allowed_to_submit ? "yes" : "no"}</span>
            </div>
            <div className={styles.field}>
              <span className={styles.label}>Live trading enabled</span>
              <span className={styles.value}>{result.live_trading_enabled ? "yes" : "no"}</span>
            </div>
            <div className={styles.field}>
              <span className={styles.label}>Broker mode</span>
              <span className={styles.value}>
                {result.broker_mode.mode} · paper trading {result.broker_mode.paper_trading_enabled ? "enabled" : "disabled"}
              </span>
            </div>
          </div>

          {result.blocked_reason ? (
            <div className={styles.listBlock}>
              <h5 className={styles.listTitle}>Blocked reason</h5>
              <p className={styles.emptyText}>{result.blocked_reason}</p>
            </div>
          ) : null}

          <div className={styles.listBlock}>
            <h5 className={styles.listTitle}>Missing data</h5>
            {result.missing_data.length === 0 ? (
              <p className={styles.emptyText}>No missing recommendation context flagged.</p>
            ) : (
              <ul className={styles.list}>
                {result.missing_data.map((entry) => (
                  <li key={entry}>{entry}</li>
                ))}
              </ul>
            )}
          </div>

          <div className={styles.listBlock}>
            <h5 className={styles.listTitle}>Next required action</h5>
            <p className={styles.emptyText}>{result.next_required_action}</p>
          </div>

          <div className={styles.navLinks}>
            <Link href="/broker#broker-overview" className={styles.linkPill}>
              Review broker paper readiness
            </Link>
            {result.route_check_status === "eligible" ? (
              <Link href="/broker#broker-execution" className={styles.linkPill}>
                Open guarded broker dry-run
              </Link>
            ) : null}
            {result.route_check_status === "eligible" ? (
              <Link href="/broker#broker-execution" className={styles.linkPill}>
                View manual paper route
              </Link>
            ) : null}
          </div>

          <p className={styles.helperText}>
            This panel is read-only. Actual broker submit still stays on the existing guarded /broker/orders manual paper workflow.
          </p>

          <section
            className={styles.subpanel}
            data-testid={`recommendation-dry-run-preview-${recommendationId}`}
            aria-label={`Guarded broker dry-run preview for ${symbol}`}
          >
            <div className={styles.previewHeader}>
              <div className={styles.titleWrap}>
                <p className={styles.eyebrow}>Guarded preview</p>
                <h5 className={styles.previewTitle}>Broker dry-run review</h5>
                <p className={styles.subtitle}>
                  This preview stays non-submitting and only reuses the existing broker dry-run path when the route-check is eligible.
                </p>
              </div>
              {preview ? (
                <span
                  className={`${styles.statusPill} ${statusClassName(preview.dry_run_status)}`}
                  data-testid={`recommendation-dry-run-preview-status-${recommendationId}`}
                >
                  {formatStatus(preview.dry_run_status)}
                </span>
              ) : null}
            </div>

            {result.route_check_status !== "eligible" ? (
              <p className={styles.helperText}>
                Dry-run preview stays unavailable until the recommendation is route-check eligible.
              </p>
            ) : null}

            {previewError ? (
              <div
                className={styles.inlineError}
                data-testid={`recommendation-dry-run-preview-error-${recommendationId}`}
                role="alert"
              >
                {previewError}
              </div>
            ) : null}

            {preview ? (
              <>
                <div
                  className={`${styles.summary} ${summaryClassName(preview.dry_run_status)}`}
                  data-testid={`recommendation-dry-run-preview-summary-${recommendationId}`}
                >
                  <p className={styles.summaryTitle}>{previewSummary?.title}</p>
                  <p className={styles.summaryText}>{previewSummary?.body}</p>
                </div>

                <div className={styles.grid}>
                  <div className={styles.field}>
                    <span className={styles.label}>Dry-run only</span>
                    <span className={styles.value}>{preview.dry_run_only ? "yes" : "no"}</span>
                  </div>
                  <div className={styles.field}>
                    <span className={styles.label}>Dry-run executed</span>
                    <span className={styles.value}>{preview.dry_run_executed ? "yes" : "no"}</span>
                  </div>
                  <div className={styles.field}>
                    <span className={styles.label}>Allowed to submit</span>
                    <span className={styles.value}>{formatBoolean(preview.allowed_to_submit)}</span>
                  </div>
                  <div className={styles.field}>
                    <span className={styles.label}>Would block</span>
                    <span className={styles.value}>{preview.would_block ? "yes" : "no"}</span>
                  </div>
                  <div className={styles.field}>
                    <span className={styles.label}>Mode guard ok</span>
                    <span className={styles.value}>{formatBoolean(preview.mode_guard_ok)}</span>
                  </div>
                  <div className={styles.field}>
                    <span className={styles.label}>Request valid</span>
                    <span className={styles.value}>{formatBoolean(preview.request_valid)}</span>
                  </div>
                  <div className={styles.field}>
                    <span className={styles.label}>Dry-run execution source</span>
                    <span className={styles.value}>{preview.dry_run_execution_source ?? "not run"}</span>
                  </div>
                  <div className={styles.field}>
                    <span className={styles.label}>Balance source</span>
                    <span className={styles.value}>{preview.balance_source ?? "not run"}</span>
                  </div>
                  <div className={styles.field}>
                    <span className={styles.label}>Positions source</span>
                    <span className={styles.value}>{preview.positions_source ?? "not run"}</span>
                  </div>
                  <div className={styles.field}>
                    <span className={styles.label}>Preflight decision</span>
                    <span className={styles.value}>{preview.preflight_decision?.decision_status ?? "not evaluated"}</span>
                  </div>
                  <div className={styles.field}>
                    <span className={styles.label}>Estimated notional</span>
                    <span className={styles.value}>{formatMaybeNumber(preview.estimated_notional)}</span>
                  </div>
                  <div className={styles.field}>
                    <span className={styles.label}>Paper path note</span>
                    <span className={styles.value}>{preview.paper_path_note ?? "No additional paper-path note surfaced."}</span>
                  </div>
                </div>

                <div className={styles.listBlock}>
                  <h5 className={styles.listTitle}>Dry-run issues</h5>
                  {preview.issues.length === 0 ? (
                    <p className={styles.emptyText}>No validation issues surfaced.</p>
                  ) : (
                    <ul className={styles.list}>
                      {preview.issues.map((entry) => (
                        <li key={`${entry.code}-${entry.message}`}>{entry.message}</li>
                      ))}
                    </ul>
                  )}
                </div>

                <div className={styles.listBlock}>
                  <h5 className={styles.listTitle}>Blocking findings</h5>
                  {blockingFindings.length === 0 ? (
                    <p className={styles.emptyText}>No blocking or would-block preflight findings surfaced.</p>
                  ) : (
                    <ul className={styles.list}>
                      {blockingFindings.map((entry) => (
                        <li key={`${entry.classification}-${entry.code}`}>{entry.message}</li>
                      ))}
                    </ul>
                  )}
                </div>

                <div className={styles.listBlock}>
                  <h5 className={styles.listTitle}>Warnings</h5>
                  {preview.warnings.length === 0 ? (
                    <p className={styles.emptyText}>No advisory warnings surfaced.</p>
                  ) : (
                    <ul className={styles.list}>
                      {preview.warnings.map((entry) => (
                        <li key={`${entry.code}-${entry.message}`}>{entry.message}</li>
                      ))}
                    </ul>
                  )}
                </div>

                <div className={styles.listBlock}>
                  <h5 className={styles.listTitle}>Next required action</h5>
                  <p className={styles.emptyText}>{preview.next_required_action}</p>
                </div>
              </>
            ) : result.route_check_status === "eligible" ? (
              <p className={styles.helperText}>
                Run the guarded broker dry-run preview to inspect the existing non-submitting preflight result before any manual paper submit step.
              </p>
            ) : null}
          </section>
        </>
      ) : null}
    </section>
  );
}