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

type ManualPaperSubmitReadinessStatus =
  | "ready_for_future_manual_paper_submit"
  | "blocked"
  | "missing_context"
  | "dry_run_required"
  | "unknown";

type ManualPaperSubmitReadinessReason = {
  code: string;
  label: string;
  satisfied: boolean;
};

type ManualPaperSubmitReadiness = {
  status: ManualPaperSubmitReadinessStatus;
  title: string;
  body: string;
  reasons: ManualPaperSubmitReadinessReason[];
  blockedReasons: string[];
  missingData: string[];
  warnings: string[];
  staleDataWarnings: string[];
  nextRequiredAction: string;
  nextRequiredActionDetail: string;
};

function readinessStatusClassName(status: ManualPaperSubmitReadinessStatus): string {
  if (status === "ready_for_future_manual_paper_submit") return styles.statusEligible;
  if (status === "blocked") return styles.statusBlocked;
  if (status === "missing_context" || status === "dry_run_required") return styles.statusMissing;
  return styles.statusUnknown;
}

function formatReadinessStatus(status: ManualPaperSubmitReadinessStatus): string {
  if (status === "ready_for_future_manual_paper_submit") return "ready for future manual paper submit";
  if (status === "dry_run_required") return "dry-run required";
  return formatStatus(status);
}

function uniqueMessages(values: Array<string | null | undefined>): string[] {
  return values
    .map((value) => value?.trim())
    .filter((value): value is string => Boolean(value))
    .filter((value, index, all) => all.indexOf(value) === index);
}

function deriveManualPaperSubmitReadiness(
  result: PaperRecommendationRouteCheck,
  preview: PaperRecommendationBrokerDryRunPreview | null,
): ManualPaperSubmitReadiness {
  const preflightStatus = preview?.preflight_decision?.decision_status ?? null;
  const dryRunPassed =
    preview !== null &&
    preview.dry_run_executed &&
    preview.dry_run_only &&
    preview.dry_run_status === "ready";
  const preflightNonBlocking =
    preview !== null &&
    preflightStatus !== null &&
    ["allowed", "advisory"].includes(preflightStatus) &&
    preview.would_block === false;
  const liveLocked =
    result.live_state === "ibkr_live_locked" &&
    result.live_trading_enabled === false &&
    (preview?.live_trading_enabled ?? false) === false;
  const workersNonSubmitting =
    result.workers_allowed_to_submit === false &&
    (preview?.workers_allowed_to_submit ?? false) === false;
  const brokerModePaper =
    result.broker_account_mode === "paper" &&
    result.broker_mode.paper_trading_enabled &&
    (preview?.broker_account_mode ?? "paper") === "paper";
  const resolvedRouteIsBrokerOrders =
    result.resolved_route === "/broker/orders" &&
    result.canonical_paper_route === "/broker/orders" &&
    (preview?.resolved_route ?? "/broker/orders") === "/broker/orders" &&
    (preview?.canonical_paper_route ?? "/broker/orders") === "/broker/orders";
  const routeCheckPassed = result.route_check_status === "eligible";
  const sourceLabelsCorrect =
    result.execution_source === "recommendation_route_check" &&
    result.serious_paper_source === "ibkr_paper" &&
    (preview?.dry_run_execution_source ?? "broker_dry_run") === "broker_dry_run" &&
    (preview?.serious_paper_source ?? "ibkr_paper") === "ibkr_paper";
  const noSubmitControlPresent = true;
  const blockedReasons = uniqueMessages([
    result.blocked_reason,
    preview?.blocked_reason,
    ...(preview?.preflight_decision?.blocking_items.map((item) => item.message) ?? []),
    ...(preview?.preflight_decision?.would_block_items.map((item) => item.message) ?? []),
  ]);
  const missingData = uniqueMessages([...result.missing_data, ...(preview?.missing_data ?? [])]);
  const warnings = uniqueMessages(preview?.warnings.map((warning) => warning.message) ?? []);
  const staleDataWarnings = warnings.filter((warning) => /stale/i.test(warning));

  const reasons: ManualPaperSubmitReadinessReason[] = [
    { code: "route_check_passed", label: "Route-check passed", satisfied: routeCheckPassed },
    { code: "broker_mode_paper", label: "Broker mode coherently paper", satisfied: brokerModePaper },
    {
      code: "resolved_route_is_broker_orders",
      label: "Resolved route is /broker/orders",
      satisfied: resolvedRouteIsBrokerOrders,
    },
    { code: "dry_run_passed", label: "Guarded broker dry-run passed", satisfied: dryRunPassed },
    {
      code: "preflight_non_blocking",
      label: "Broker preflight is non-blocking",
      satisfied: preflightNonBlocking,
    },
    { code: "source_labels_correct", label: "Source labels are correct", satisfied: sourceLabelsCorrect },
    { code: "live_locked", label: "Live remains locked", satisfied: liveLocked },
    { code: "workers_non_submitting", label: "Workers remain non-submitting", satisfied: workersNonSubmitting },
    {
      code: "no_submit_control_present",
      label: "No submit control is present",
      satisfied: noSubmitControlPresent,
    },
  ];

  let status: ManualPaperSubmitReadinessStatus = "unknown";
  if (result.route_check_status === "missing_context" || preview?.dry_run_status === "missing_context") {
    status = "missing_context";
  } else if (result.route_check_status === "blocked") {
    status = "blocked";
  } else if (result.route_check_status !== "eligible") {
    status = "unknown";
  } else if (preview === null) {
    status = "dry_run_required";
  } else if (
    blockedReasons.length > 0 ||
    missingData.length > 0 ||
    !brokerModePaper ||
    !resolvedRouteIsBrokerOrders ||
    !liveLocked ||
    !workersNonSubmitting ||
    !dryRunPassed ||
    !preflightNonBlocking ||
    !sourceLabelsCorrect
  ) {
    status = missingData.length > 0 ? "missing_context" : "blocked";
  } else {
    status = "ready_for_future_manual_paper_submit";
  }

  let title = "Manual IBKR paper submit readiness is unknown";
  let body = "Readiness only, no order submitted. Review the route-check and dry-run evidence before any future manual handoff.";
  let nextRequiredAction = "no_action_available";
  let nextRequiredActionDetail = result.next_required_action;

  if (status === "missing_context") {
    title = "Missing context before manual paper handoff";
    body = "Readiness only, no order submitted. Fix the missing recommendation or dry-run context before any future manual IBKR paper submit handoff can be considered.";
    nextRequiredAction = "fix_missing_context";
    nextRequiredActionDetail = missingData[0] ?? preview?.next_required_action ?? result.next_required_action;
  } else if (status === "blocked") {
    title = "Blocked before manual paper handoff";
    body = "Readiness only, no order submitted. One or more route, dry-run, source, or safety gates are still blocking a future manual IBKR paper submit handoff.";
    nextRequiredAction = "review_blocked_reason";
    nextRequiredActionDetail = blockedReasons[0] ?? preview?.next_required_action ?? result.next_required_action;
  } else if (status === "dry_run_required") {
    title = "Dry-run required first";
    body = "Readiness only, no order submitted. The recommendation passed route-check, but guarded broker dry-run evidence is still required before future manual IBKR paper handoff review.";
    nextRequiredAction = "run_guarded_dry_run";
    nextRequiredActionDetail = "Run the guarded broker dry-run preview before reviewing future manual paper handoff readiness.";
  } else if (status === "ready_for_future_manual_paper_submit") {
    title = "Ready for future manual paper handoff";
    body = "Readiness only, no order submitted. This recommendation has cleared the current route-check and guarded dry-run gates for a future manual IBKR paper submit handoff review.";
    nextRequiredAction = "future_manual_submit_handoff_available_after_review";
    nextRequiredActionDetail = "Future manual paper submit would still use guarded /broker/orders after operator review. Live trading remains locked and workers cannot submit.";
  }

  return {
    status,
    title,
    body,
    reasons,
    blockedReasons,
    missingData,
    warnings,
    staleDataWarnings,
    nextRequiredAction,
    nextRequiredActionDetail,
  };
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
  const readiness = result ? deriveManualPaperSubmitReadiness(result, preview) : null;

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

          {readiness ? (
            <section
              className={styles.subpanel}
              data-testid={`recommendation-submit-readiness-${recommendationId}`}
              aria-label={`Manual IBKR paper submit readiness for ${symbol}`}
            >
              <div className={styles.previewHeader}>
                <div className={styles.titleWrap}>
                  <p className={styles.eyebrow}>Readiness review</p>
                  <h5 className={styles.previewTitle}>Manual IBKR paper submit readiness</h5>
                  <p className={styles.subtitle}>
                    Readiness only, no order submitted. Future manual paper submit would still use the guarded /broker/orders path.
                  </p>
                </div>
                <span
                  className={`${styles.statusPill} ${readinessStatusClassName(readiness.status)}`}
                  data-testid={`recommendation-submit-readiness-status-${recommendationId}`}
                >
                  {formatReadinessStatus(readiness.status)}
                </span>
              </div>

              <div
                className={`${styles.summary} ${summaryClassName(readiness.status)}`}
                data-testid={`recommendation-submit-readiness-summary-${recommendationId}`}
              >
                <p className={styles.summaryTitle}>{readiness.title}</p>
                <p className={styles.summaryText}>{readiness.body}</p>
              </div>

              <div className={styles.grid}>
                <div className={styles.field}>
                  <span className={styles.label}>Next required action</span>
                  <span className={styles.value}>{formatStatus(readiness.nextRequiredAction)}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>Resolved route</span>
                  <span className={`${styles.value} ${styles.mono}`}>{result.resolved_route ?? preview?.resolved_route ?? "not resolved"}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>Broker account mode</span>
                  <span className={styles.value}>{preview?.broker_account_mode ?? result.broker_account_mode}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>Live state</span>
                  <span className={styles.value}>{preview?.live_state ?? result.live_state}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>Would block</span>
                  <span className={styles.value}>{preview?.would_block ?? result.would_block ? "yes" : "no"}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>Allowed to submit</span>
                  <span className={styles.value}>{formatBoolean(preview?.allowed_to_submit ?? null)}</span>
                </div>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Readiness reasons</h5>
                <ul className={styles.list}>
                  {readiness.reasons.map((reason) => (
                    <li key={reason.code}>
                      {reason.label}: {reason.satisfied ? "yes" : "no"}
                    </li>
                  ))}
                </ul>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Blocked reasons</h5>
                {readiness.blockedReasons.length === 0 ? (
                  <p className={styles.emptyText}>No blocked reasons surfaced in the current readiness review.</p>
                ) : (
                  <ul className={styles.list}>
                    {readiness.blockedReasons.map((entry) => (
                      <li key={entry}>{entry}</li>
                    ))}
                  </ul>
                )}
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Missing context</h5>
                {readiness.missingData.length === 0 ? (
                  <p className={styles.emptyText}>No missing context surfaced in the current readiness review.</p>
                ) : (
                  <ul className={styles.list}>
                    {readiness.missingData.map((entry) => (
                      <li key={entry}>{entry}</li>
                    ))}
                  </ul>
                )}
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Warnings and stale data</h5>
                <p className={styles.emptyText}>
                  {readiness.warnings.length === 0
                    ? "No warnings surfaced."
                    : `${readiness.warnings.length} warning${readiness.warnings.length === 1 ? "" : "s"} surfaced.`}
                </p>
                <p className={styles.emptyText}>
                  {readiness.staleDataWarnings.length === 0
                    ? "No stale-data warnings surfaced."
                    : `${readiness.staleDataWarnings.length} stale-data warning${readiness.staleDataWarnings.length === 1 ? "" : "s"} surfaced.`}
                </p>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Next required action detail</h5>
                <p className={styles.emptyText}>{readiness.nextRequiredActionDetail}</p>
              </div>

              <p className={styles.helperText}>
                No order submitted. No submit button was added here. Future manual paper submit would still use guarded /broker/orders. Live trading remains locked. Workers cannot submit.
              </p>
            </section>
          ) : null}
        </>
      ) : null}
    </section>
  );
}