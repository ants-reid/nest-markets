"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

import { submitBrokerOrder, type BrokerOrderResult } from "../../../lib/api/broker";
import { ApiRequestError } from "../../../lib/api/core";
import {
  getPaperRecommendation,
  getPaperRecommendationRouteCheck,
  previewPaperRecommendationBrokerDryRun,
  type PaperRecommendationDetails,
  type PaperRecommendationBrokerDryRunPreview,
  type PaperRecommendationRouteCheck,
} from "../../../lib/api/paperRecommendations";
import {
  deriveManualPaperSubmitMissingContextTriage,
  deriveManualPaperSubmitPayloadFreshnessReview,
  deriveManualPaperSubmitReviewChain,
  type ManualPaperSubmitReviewChain,
} from "../../../lib/manualPaperSubmitReview";
import styles from "../../../styles/pages/manual-paper-submit-confirmation.module.css";

type ChecklistItem = {
  label: string;
  detail: string;
};

type PreviewField = {
  label: string;
  value: string;
  detail: string;
  missing: boolean;
};

type ReviewSection = {
  key: string;
  title: string;
  status: string;
  body: string;
  nextRequiredAction: string;
  nextRequiredActionDetail: string;
  blockedReasons: string[];
  missingData: string[];
  warnings: string[];
};

type PaperSubmitFailureDetail = {
  title: string;
  message: string;
  submitGate: string | null;
  decisionStatus: string | null;
  reasons: string[];
  kind: "blocked" | "failed";
};

type SubmitAttemptRecord = {
  ticker: string;
  side: string;
  quantity: number | null;
  orderType: string;
  limitPrice: number | null;
  timeInForce: string;
  estimatedNotional: number | null;
  recommendationId: string;
  correlationId: string;
  attemptedAtIso: string;
  brokerMode: string | null;
  brokerAccountMode: string | null;
  executionSource: string | null;
  preflightDecisionStatus: string | null;
  dryRunAllowedToSubmit: boolean | null;
  dryRunWouldBlock: boolean | null;
  routeCheckReference: string;
  dryRunReference: string;
};

function normalizeIdFragment(value: string): string {
  const normalized = value.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
  return normalized || "paper_submit";
}

function buildSubmitDecisionCorrelationId(recommendationId: string): string {
  const safeRecommendationId = normalizeIdFragment(recommendationId).slice(0, 48);
  return `manual_paper_submit_${safeRecommendationId}_${Date.now().toString(36)}`;
}

function normalizeBrokerSide(value: string | null): "BUY" | "SELL" | null {
  if (!value) return null;
  const normalized = value.toUpperCase();
  if (normalized === "BUY" || normalized === "SELL") {
    return normalized;
  }
  return null;
}

function normalizeBrokerOrderType(value: string | null): "MARKET" | "LIMIT" | "STOP" | "STOP_LIMIT" | "TRAIL" | null {
  if (!value) return null;
  const normalized = value.toUpperCase();
  if (
    normalized === "MARKET" ||
    normalized === "LIMIT" ||
    normalized === "STOP" ||
    normalized === "STOP_LIMIT" ||
    normalized === "TRAIL"
  ) {
    return normalized;
  }
  return null;
}

function buildBlockedSubmitDetail(error: unknown): PaperSubmitFailureDetail {
  if (error instanceof ApiRequestError && typeof error.responseBody === "object" && error.responseBody !== null) {
    const detailContainer = error.responseBody as { detail?: unknown };
    if (typeof detailContainer.detail === "object" && detailContainer.detail !== null) {
      const detail = detailContainer.detail as {
        code?: unknown;
        message?: unknown;
        submit_gate?: unknown;
        decision_status?: unknown;
        blocking_reasons?: Array<{ message?: unknown; code?: unknown }>;
      };
      const reasons = Array.isArray(detail.blocking_reasons)
        ? detail.blocking_reasons
            .map((item) => {
              const message = typeof item?.message === "string" ? item.message : null;
              const code = typeof item?.code === "string" ? item.code : null;
              return message ?? code;
            })
            .filter((value): value is string => Boolean(value))
        : [];

      return {
        title: detail.code === "paper_preflight_blocked" ? "Paper submit blocked" : "Paper submit failed",
        message:
          typeof detail.message === "string"
            ? detail.message
            : error.message,
        submitGate: typeof detail.submit_gate === "string" ? detail.submit_gate : null,
        decisionStatus: typeof detail.decision_status === "string" ? detail.decision_status : null,
        reasons,
        kind: detail.code === "paper_preflight_blocked" ? "blocked" : "failed",
      };
    }
  }

  return {
    title: "Paper submit failed",
    message: error instanceof Error ? error.message : "Paper submit failed unexpectedly.",
    submitGate: null,
    decisionStatus: null,
    reasons: [],
    kind: "failed",
  };
}

function buildSubmitPayload(
  recommendationId: string | null,
  recommendation: PaperRecommendationDetails | null,
  routeCheck: PaperRecommendationRouteCheck | null,
  preview: PaperRecommendationBrokerDryRunPreview | null,
  fallbackSymbol: string,
) {
  if (!recommendationId) return null;

  const submitDecisionCorrelationId = buildSubmitDecisionCorrelationId(recommendationId);

  const orderType = normalizeBrokerOrderType(
    routeCheck?.order_type ?? preview?.order_type ?? recommendation?.order_type ?? null,
  );
  const quantity = routeCheck?.quantity ?? preview?.quantity ?? recommendation?.quantity ?? null;
  const limitPrice = routeCheck?.limit_price ?? preview?.limit_price ?? recommendation?.limit_price ?? null;
  const limitPriceRequired = orderType === "LIMIT" || orderType === "STOP_LIMIT";
  const stopPriceRequired = orderType === "STOP" || orderType === "STOP_LIMIT";

  if (!orderType || quantity === null || quantity === undefined) {
    return null;
  }

  if (limitPriceRequired && (limitPrice === null || limitPrice === undefined)) {
    return null;
  }

  if (stopPriceRequired) {
    return null;
  }

  const symbol = routeCheck?.ticker ?? preview?.ticker ?? recommendation?.ticker ?? fallbackSymbol;
  const side = normalizeBrokerSide(routeCheck?.side ?? preview?.side ?? recommendation?.side ?? null);
  if (!symbol || !side) {
    return null;
  }

  return {
    ticker: symbol,
    side,
    quantity,
    order_type: orderType,
    limit_price: limitPriceRequired ? limitPrice ?? undefined : undefined,
    stop_price: undefined,
    tif: "DAY",
    client_order_id: submitDecisionCorrelationId,
    recommendation_id: recommendationId,
    account_mode: "paper",
    execution_source: "ibkr_paper",
    route_check_reference: routeCheck ? buildRouteCheckReference(routeCheck) : undefined,
    dry_run_reference: preview ? buildDryRunReference(preview) : undefined,
    submit_decision_correlation_id: submitDecisionCorrelationId,
  };
}

function formatMaybeNumber(value: number | null): string {
  if (value === null) return "missing";
  return value.toLocaleString("en-US", { maximumFractionDigits: 4 });
}

function buildRouteCheckReference(result: PaperRecommendationRouteCheck | null): string {
  if (!result) return "missing until recommendation route-check loads";
  return `${result.execution_source}:${result.route_check_status}`;
}

function buildDryRunReference(preview: PaperRecommendationBrokerDryRunPreview | null): string {
  if (!preview) return "missing until guarded dry-run preview loads";
  const preflightStatus = preview.preflight_decision?.decision_status ?? preview.dry_run_status;
  return `${preview.dry_run_execution_source ?? "broker_dry_run"}:${preflightStatus}`;
}

function buildPayloadPreviewFields(
  recommendationId: string | null,
  result: PaperRecommendationRouteCheck | null,
  preview: PaperRecommendationBrokerDryRunPreview | null,
  fallbackSymbol: string,
): PreviewField[] {
  const orderType = (result?.order_type ?? preview?.order_type ?? "unknown").toUpperCase();
  const limitPriceRequired = orderType === "LIMIT" || orderType === "STOP_LIMIT";
  const stopPriceRequired = orderType === "STOP" || orderType === "STOP_LIMIT";
  const symbol = result?.ticker ?? preview?.ticker ?? fallbackSymbol;

  return [
    {
      label: "symbol",
      value: symbol || "missing",
      detail: "Future guarded paper submit would reuse the recommendation symbol.",
      missing: !symbol,
    },
    {
      label: "side",
      value: result?.side ?? preview?.side ?? "missing",
      detail: "Future guarded paper submit would reuse the persisted BUY or SELL recommendation side.",
      missing: !(result?.side ?? preview?.side),
    },
    {
      label: "quantity",
      value: result?.quantity !== null && result?.quantity !== undefined ? formatMaybeNumber(result.quantity) : "missing",
      detail: "The current guarded /broker/orders contract is quantity-based, not notional-only.",
      missing: result?.quantity === null || result?.quantity === undefined,
    },
    {
      label: "estimated_notional",
      value: preview?.estimated_notional !== null && preview?.estimated_notional !== undefined ? formatMaybeNumber(preview.estimated_notional) : "review-only context not loaded",
      detail: "Estimated notional stays review-only context and does not replace the current quantity contract.",
      missing: false,
    },
    {
      label: "order_type",
      value: result?.order_type ?? preview?.order_type ?? "missing",
      detail: "The future confirmation surface stays tied to the persisted recommendation order type.",
      missing: !(result?.order_type ?? preview?.order_type),
    },
    {
      label: "limit_price",
      value:
        result?.limit_price !== null && result?.limit_price !== undefined
          ? formatMaybeNumber(result.limit_price)
          : limitPriceRequired
            ? "missing"
            : "not required",
      detail: limitPriceRequired
        ? "Required later for LIMIT and STOP_LIMIT orders."
        : "Not required for the current order type.",
      missing: limitPriceRequired && (result?.limit_price === null || result?.limit_price === undefined),
    },
    {
      label: "stop_price",
      value: stopPriceRequired ? "missing" : "not required",
      detail: stopPriceRequired
        ? "STOP and STOP_LIMIT remain blocked later unless stop_price becomes part of the persisted recommendation payload."
        : "Not required for the current order type.",
      missing: stopPriceRequired,
    },
    {
      label: "time_in_force",
      value: "DAY default available later",
      detail: "The guarded broker request defaults to DAY unless an operator overrides it in a later enabled phase.",
      missing: false,
    },
    {
      label: "recommendation_id",
      value: recommendationId ?? "missing",
      detail: "Recommendation identity anchors the future confirmation and audit trail.",
      missing: !recommendationId,
    },
    {
      label: "route_check_reference",
      value: buildRouteCheckReference(result),
      detail: "Read-only route-check evidence already available in the current review chain.",
      missing: result === null,
    },
    {
      label: "dry_run_reference",
      value: buildDryRunReference(preview),
      detail: "Read-only guarded dry-run evidence already available when preview has run.",
      missing: preview === null,
    },
    {
      label: "approval_package_reference",
      value: recommendationId ? `review-chain:approval-package:${recommendationId}` : "generated later from review chain",
      detail: "Design-only reference to the existing review-only approval package evidence.",
      missing: !recommendationId,
    },
    {
      label: "preflight_contract_reference",
      value: recommendationId ? `review-chain:preflight-contract:${recommendationId}` : "generated later from review chain",
      detail: "Design-only reference to the existing review-only preflight contract evidence.",
      missing: !recommendationId,
    },
    {
      label: "submit_decision_correlation_id",
      value: recommendationId ? `future-submit-correlation:${recommendationId}` : "generated later at submit time",
      detail: "Correlation id is previewed here only and would be created later on the guarded submit path.",
      missing: !recommendationId,
    },
    {
      label: "account_mode",
      value: preview?.broker_account_mode ?? result?.broker_account_mode ?? "paper required",
      detail: "The future path remains guarded IBKR paper only and must block outside coherent paper mode.",
      missing: false,
    },
    {
      label: "execution_source",
      value: preview?.serious_paper_source ?? result?.serious_paper_source ?? "ibkr_paper",
      detail: "The future guarded route remains canonical IBKR paper only.",
      missing: false,
    },
  ];
}

const submitTimeChecks: ChecklistItem[] = [
  { label: "broker mode recheck", detail: "Block later unless broker mode still resolves coherently to paper." },
  { label: "trading control recheck", detail: "Re-run trading_control_service and block later if paper submit is no longer allowed." },
  { label: "risk limit recheck", detail: "Re-evaluate current risk-limit findings before any future guarded submit attempt." },
  { label: "broker preflight rerun", detail: "Run broker dry-run/preflight again at submit time before any broker execution." },
  { label: "route-check freshness recheck", detail: "Block later if route-check evidence is stale, missing, or no longer eligible." },
  { label: "dry-run freshness recheck", detail: "Block later if guarded dry-run evidence is stale, missing, blocked, or would-block." },
  { label: "recommendation payload freshness recheck", detail: "Block later if the recommendation changed after review or payload fields drifted." },
  { label: "source-label recheck", detail: "Reconfirm recommendation route-check, dry-run, and paper source labels still align with canonical IBKR paper routing." },
  { label: "live-lock recheck", detail: "Block later if any live-trading path appears or if live_order_submission_allowed becomes true." },
  { label: "final operator confirmation", detail: "Require the operator to explicitly confirm paper-only non-live submission expectations later." },
  { label: "append-only submit-decision persistence", detail: "Persist the later submit_preflight and submit_attempt records without mutating prior rows." },
];

const blockingStates: string[] = [
  "Broker mode is not paper.",
  "Live mode is detected.",
  "Broker or account mode is unknown.",
  "Route-check is stale, missing, or blocked.",
  "Dry-run preview is stale, missing, blocked, or not yet run.",
  "would_block is true.",
  "A blocking preflight finding exists.",
  "Required payload fields are missing.",
  "A source-label mismatch exists.",
  "The recommendation changed after review.",
  "Risk or broker preflight fails.",
  "An active trading halt exists.",
  "workers_allowed_to_submit becomes true.",
  "live_trading_enabled becomes true.",
  "Final operator confirmation is missing.",
];

const decisionPersistenceRequirements: ChecklistItem[] = [
  { label: "submit_preflight decision before submit", detail: "Persist the later preflight decision before any future guarded paper submit attempt." },
  { label: "submit_attempt decision after attempt", detail: "Persist the later attempt decision after broker execution is attempted on the existing guarded seam." },
  { label: "blocked_attempt decision if any guard blocks", detail: "Persist a blocked attempt decision when any submit-time guard prevents execution." },
  { label: "live_locked_attempt decision if live mode appears", detail: "Persist a live-locked attempt decision if live mode or live submit availability is detected later." },
  { label: "append-only behavior", detail: "Never overwrite prior decision rows; keep the decision trail append-only." },
  { label: "scrub secret-like fields", detail: "Continue sanitizing warning and reason payloads before any later persistence." },
  { label: "include correlation id", detail: "Attach a later correlation id so route-check, dry-run, and submit attempt evidence can be traced together." },
  { label: "include upstream review references where available", detail: "Carry route-check, dry-run, approval, and preflight review references forward into later decision records when available." },
];

const finalConfirmationWording =
  "I understand this is an IBKR paper order only. I understand submit-time checks will rerun. I understand this is not live trading. I understand no worker is allowed to submit this order. I understand the system must block if any guard fails.";

function formatDerivedStatus(status: string): string {
  return status.replaceAll("_", " ");
}

type OutcomeStatus = "allowed" | "blocked" | "failed";

function deriveOutcomeStatus(
  result: BrokerOrderResult | null,
  failure: PaperSubmitFailureDetail | null,
): OutcomeStatus {
  if (result) return "allowed";
  if (failure?.kind === "blocked") return "blocked";
  return "failed";
}

function describeOutcome(status: OutcomeStatus): { label: string; copy: string } {
  if (status === "allowed") {
    return {
      label: "Paper submit allowed",
      copy: "The guarded IBKR paper order was accepted by /broker/orders. No live order was placed.",
    };
  }
  if (status === "blocked") {
    return {
      label: "Paper submit blocked",
      copy: "The submit-time guards blocked the IBKR paper order. No paper order was placed and no live order was placed.",
    };
  }
  return {
    label: "Paper submit failed",
    copy: "The IBKR paper submit attempt failed before or during the broker call. No live order was placed.",
  };
}

function describeNextStep(status: OutcomeStatus): { headline: string; actions: string[] } {
  if (status === "allowed") {
    return {
      headline: "Review timeline and monitor paper account",
      actions: [
        "Review the broker submit decision timeline for the persisted preflight and attempt rows.",
        "Monitor the IBKR paper account for fills and follow-up adjustments.",
        "Return to the cockpit hub when monitoring is handed off.",
      ],
    };
  }
  if (status === "blocked") {
    return {
      headline: "Resolve blockers and rerun review",
      actions: [
        "Open the broker submit decision timeline to inspect the blocked-attempt row and reasons.",
        "Fix the missing context surfaced on this page (rerun route-check and guarded dry-run as required).",
        "Rerun the dry-run before any further paper submit attempt.",
        "Return to the in-flight review for the originating recommendation.",
      ],
    };
  }
  return {
    headline: "Check broker/API status and timeline before retry",
    actions: [
      "Check broker and API status before another paper submit attempt.",
      "Open the broker submit decision timeline to confirm whether a preflight or attempt row was persisted.",
      "Rerun the dry-run before any further paper submit attempt.",
      "Return to the in-flight review for the originating recommendation.",
    ],
  };
}

function formatOutcomeNumber(value: number | null): string {
  if (value === null || value === undefined) return "unavailable";
  return value.toLocaleString("en-US", { maximumFractionDigits: 4 });
}

function buildTimelineHref(correlationId: string, recommendationId: string): string {
  const params = new URLSearchParams();
  if (correlationId) params.set("correlation_id", correlationId);
  if (recommendationId) params.set("recommendation_id", recommendationId);
  const qs = params.toString();
  return qs
    ? `/cockpit/audit/broker-submit-decisions?${qs}`
    : "/cockpit/audit/broker-submit-decisions";
}

function OperatorOutcomeView({
  attempt,
  result,
  failure,
}: {
  attempt: SubmitAttemptRecord;
  result: BrokerOrderResult | null;
  failure: PaperSubmitFailureDetail | null;
}) {
  const status = deriveOutcomeStatus(result, failure);
  const outcomeCopy = describeOutcome(status);
  const nextStep = describeNextStep(status);
  const timelineHref = buildTimelineHref(attempt.correlationId, attempt.recommendationId);
  const responseBrokerMode = result?.broker_mode?.mode ?? attempt.brokerMode ?? "unknown";
  const liveExecutionEnabled = result?.broker_mode?.live_execution_enabled ?? false;
  const paperTradingEnabled = result?.broker_mode?.paper_trading_enabled ?? null;
  const responseStatus = result?.status ?? (failure ? failure.decisionStatus ?? "no_broker_status" : "no_broker_status");
  const brokerOrderId = result?.broker_order_id ?? "not_assigned";
  const filledQty = result?.filled_quantity ?? null;
  const filledPrice = result?.filled_price ?? null;
  const errorMessage = result?.error_message ?? failure?.message ?? null;
  const reasons = failure?.reasons ?? [];

  return (
    <section
      className={styles.sectionCard}
      data-testid="manual-paper-submit-outcome-view"
      data-outcome-status={status}
    >
      <div className={styles.outcomeHeader}>
        <div>
          <p className={styles.eyebrow}>Paper submit outcome</p>
          <h2 className={styles.sectionTitle} data-testid="manual-paper-submit-outcome-status">
            {outcomeCopy.label}
          </h2>
          <p className={styles.sectionSubtitle}>{outcomeCopy.copy}</p>
        </div>
        <div className={styles.heroMeta}>
          <span className={styles.statusPill} data-testid="manual-paper-submit-outcome-paper-only-badge">Paper only</span>
          <span className={styles.statusPill} data-testid="manual-paper-submit-outcome-live-locked-badge">Live remains locked</span>
          <span className={styles.statusPill} data-testid="manual-paper-submit-outcome-workers-badge">Workers cannot submit</span>
          <span className={styles.statusPill} data-testid="manual-paper-submit-outcome-no-live-order-badge">No live order was placed</span>
        </div>
      </div>

      <div className={styles.subsection} data-testid="manual-paper-submit-outcome-attempt-details">
        <h3 className={styles.subsectionTitle}>Attempt details</h3>
        <div className={styles.grid}>
          <div className={styles.field}><span className={styles.label}>symbol</span><span className={styles.value}>{attempt.ticker}</span></div>
          <div className={styles.field}><span className={styles.label}>side</span><span className={styles.value}>{attempt.side}</span></div>
          <div className={styles.field}><span className={styles.label}>quantity</span><span className={styles.value}>{formatOutcomeNumber(attempt.quantity)}</span></div>
          <div className={styles.field}><span className={styles.label}>order_type</span><span className={styles.value}>{attempt.orderType}</span></div>
          <div className={styles.field}><span className={styles.label}>time_in_force</span><span className={styles.value}>{attempt.timeInForce}</span></div>
          <div className={styles.field}><span className={styles.label}>limit_price</span><span className={styles.value}>{attempt.limitPrice === null ? "not required" : formatOutcomeNumber(attempt.limitPrice)}</span></div>
          <div className={styles.field}><span className={styles.label}>estimated_notional</span><span className={styles.value}>{formatOutcomeNumber(attempt.estimatedNotional)}</span></div>
          <div className={styles.field}><span className={styles.label}>recommendation_id</span><span className={`${styles.value} ${styles.mono}`} data-testid="manual-paper-submit-outcome-recommendation-id">{attempt.recommendationId}</span></div>
          <div className={styles.field}><span className={styles.label}>correlation_id</span><span className={`${styles.value} ${styles.mono}`} data-testid="manual-paper-submit-outcome-correlation-id">{attempt.correlationId}</span></div>
          <div className={styles.field}><span className={styles.label}>attempted_at</span><span className={styles.value}>{attempt.attemptedAtIso}</span></div>
        </div>
      </div>

      <div className={styles.subsection} data-testid="manual-paper-submit-outcome-guard-result">
        <h3 className={styles.subsectionTitle}>Guard result</h3>
        <p className={styles.sectionSubtitle}>
          Submit-time checks reran on /broker/orders. The values below reflect the guarded review evidence that gated the submit attempt and the broker mode returned by the response when available.
        </p>
        <div className={styles.grid}>
          <div className={styles.field}><span className={styles.label}>outcome_status</span><span className={styles.value}>{status}</span></div>
          <div className={styles.field}><span className={styles.label}>broker_mode</span><span className={styles.value}>{responseBrokerMode}</span></div>
          <div className={styles.field}><span className={styles.label}>broker_account_mode</span><span className={styles.value}>{attempt.brokerAccountMode ?? "unknown"}</span></div>
          <div className={styles.field}><span className={styles.label}>execution_source</span><span className={styles.value}>{attempt.executionSource ?? "unknown"}</span></div>
          <div className={styles.field}><span className={styles.label}>preflight_decision_status</span><span className={styles.value}>{attempt.preflightDecisionStatus ?? "unknown"}</span></div>
          <div className={styles.field}><span className={styles.label}>dry_run_allowed_to_submit</span><span className={styles.value}>{attempt.dryRunAllowedToSubmit === null ? "unknown" : attempt.dryRunAllowedToSubmit ? "true" : "false"}</span></div>
          <div className={styles.field}><span className={styles.label}>dry_run_would_block</span><span className={styles.value}>{attempt.dryRunWouldBlock === null ? "unknown" : attempt.dryRunWouldBlock ? "true" : "false"}</span></div>
          <div className={styles.field}><span className={styles.label}>response_status</span><span className={styles.value}>{responseStatus}</span></div>
          <div className={styles.field}><span className={styles.label}>broker_order_id</span><span className={`${styles.value} ${styles.mono}`}>{brokerOrderId}</span></div>
          <div className={styles.field}><span className={styles.label}>filled_quantity</span><span className={styles.value}>{formatOutcomeNumber(filledQty)}</span></div>
          <div className={styles.field}><span className={styles.label}>filled_price</span><span className={styles.value}>{formatOutcomeNumber(filledPrice)}</span></div>
          <div className={styles.field}><span className={styles.label}>live_execution_enabled</span><span className={styles.value}>{liveExecutionEnabled ? "true" : "false"}</span></div>
          <div className={styles.field}><span className={styles.label}>paper_trading_enabled</span><span className={styles.value}>{paperTradingEnabled === null ? "unknown" : paperTradingEnabled ? "true" : "false"}</span></div>
          {failure?.submitGate ? (
            <div className={styles.field}><span className={styles.label}>submit_gate</span><span className={styles.value}>{failure.submitGate}</span></div>
          ) : null}
          {failure?.decisionStatus ? (
            <div className={styles.field}><span className={styles.label}>response_decision_status</span><span className={styles.value}>{failure.decisionStatus}</span></div>
          ) : null}
          <div className={styles.field}><span className={styles.label}>route_check_reference</span><span className={`${styles.value} ${styles.mono}`}>{attempt.routeCheckReference}</span></div>
          <div className={styles.field}><span className={styles.label}>dry_run_reference</span><span className={`${styles.value} ${styles.mono}`}>{attempt.dryRunReference}</span></div>
        </div>
      </div>

      {reasons.length > 0 ? (
        <div className={styles.subsection} data-testid="manual-paper-submit-outcome-blocked-reasons">
          <h3 className={styles.subsectionTitle}>Blocked reasons</h3>
          <ul className={styles.list}>
            {reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        </div>
      ) : (
        <div className={styles.subsection} data-testid="manual-paper-submit-outcome-blocked-reasons">
          <h3 className={styles.subsectionTitle}>Blocked reasons</h3>
          <p className={styles.emptyText}>No blocking reasons were returned with this outcome.</p>
        </div>
      )}

      {errorMessage && status !== "allowed" ? (
        <div className={styles.subsection} data-testid="manual-paper-submit-outcome-warning">
          <h3 className={styles.subsectionTitle}>Warning</h3>
          <p className={styles.sectionSubtitle}>{errorMessage}</p>
        </div>
      ) : null}

      <div className={styles.subsection} data-testid="manual-paper-submit-outcome-timeline-link">
        <h3 className={styles.subsectionTitle}>Broker submit decision timeline</h3>
        <p className={styles.sectionSubtitle}>
          The append-only decision trail records preflight and attempt rows for this correlation id. The timeline view stays read-only — it has no submit, rerun, approve, or delete controls.
        </p>
        <div className={styles.placeholderRow}>
          <Link href={timelineHref} className={styles.linkPill} data-testid="manual-paper-submit-outcome-timeline-href">
            View full submit decision timeline
          </Link>
          <Link href="/cockpit/in-flight-adjustments" className={styles.linkPill}>
            Return to in-flight review
          </Link>
          <Link href="/cockpit" className={styles.linkPill}>
            Return to cockpit
          </Link>
        </div>
      </div>

      <div className={styles.subsection} data-testid="manual-paper-submit-outcome-next-step">
        <h3 className={styles.subsectionTitle}>{nextStep.headline}</h3>
        <ul className={styles.list}>
          {nextStep.actions.map((action) => (
            <li key={action}>{action}</li>
          ))}
        </ul>
        <p className={styles.emptyText}>
          No automatic resubmission will occur. Live trading remains locked. Workers remain non-submitting.
        </p>
      </div>
    </section>
  );
}

function buildReviewSections(reviewChain: ManualPaperSubmitReviewChain): ReviewSection[] {
  const sections: Array<ReviewSection | null> = [
    reviewChain.readiness
      ? {
          key: "readiness",
          title: "Readiness status",
          status: reviewChain.readiness.status,
          body: reviewChain.readiness.body,
          nextRequiredAction: reviewChain.readiness.nextRequiredAction,
          nextRequiredActionDetail: reviewChain.readiness.nextRequiredActionDetail,
          blockedReasons: reviewChain.readiness.blockedReasons,
          missingData: reviewChain.readiness.missingData,
          warnings: reviewChain.readiness.warnings,
        }
      : null,
    reviewChain.handoff
      ? {
          key: "handoff",
          title: "Handoff status",
          status: reviewChain.handoff.status,
          body: reviewChain.handoff.body,
          nextRequiredAction: reviewChain.handoff.nextRequiredAction,
          nextRequiredActionDetail: reviewChain.handoff.nextRequiredActionDetail,
          blockedReasons: reviewChain.handoff.blockedReasons,
          missingData: reviewChain.handoff.missingData,
          warnings: reviewChain.handoff.warnings,
        }
      : null,
    reviewChain.auditPackage
      ? {
          key: "audit-package",
          title: "Audit package status",
          status: reviewChain.auditPackage.status,
          body: reviewChain.auditPackage.body,
          nextRequiredAction: reviewChain.auditPackage.nextRequiredAction,
          nextRequiredActionDetail: reviewChain.auditPackage.nextRequiredActionDetail,
          blockedReasons: reviewChain.auditPackage.blockedReasons,
          missingData: reviewChain.auditPackage.missingData,
          warnings: reviewChain.auditPackage.warnings,
        }
      : null,
    reviewChain.approvalPackage
      ? {
          key: "approval-package",
          title: "Approval package status",
          status: reviewChain.approvalPackage.status,
          body: reviewChain.approvalPackage.body,
          nextRequiredAction: reviewChain.approvalPackage.nextRequiredAction,
          nextRequiredActionDetail: reviewChain.approvalPackage.nextRequiredActionDetail,
          blockedReasons: reviewChain.approvalPackage.blockedReasons,
          missingData: reviewChain.approvalPackage.missingData,
          warnings: reviewChain.approvalPackage.warnings,
        }
      : null,
    reviewChain.preflightContract
      ? {
          key: "preflight-contract",
          title: "Preflight contract status",
          status: reviewChain.preflightContract.status,
          body: reviewChain.preflightContract.body,
          nextRequiredAction: reviewChain.preflightContract.nextRequiredAction,
          nextRequiredActionDetail: reviewChain.preflightContract.nextRequiredActionDetail,
          blockedReasons: reviewChain.preflightContract.blockedReasons,
          missingData: reviewChain.preflightContract.missingData,
          warnings: reviewChain.preflightContract.warnings,
        }
      : null,
    reviewChain.futureManualSubmitDesignReview
      ? {
          key: "design-review",
          title: "Design review status",
          status: reviewChain.futureManualSubmitDesignReview.status,
          body: reviewChain.futureManualSubmitDesignReview.body,
          nextRequiredAction: "design_only_not_enabled",
          nextRequiredActionDetail:
            "Future manual paper submit would still use guarded /broker/orders and remains not enabled in this phase.",
          blockedReasons: [],
          missingData: [],
          warnings: [],
        }
      : null,
    reviewChain.submitDecisionReview
      ? {
          key: "submit-decision-review",
          title: "Submit-decision review status",
          status: reviewChain.submitDecisionReview.status,
          body: reviewChain.submitDecisionReview.body,
          nextRequiredAction: reviewChain.submitDecisionReview.nextRequiredAction,
          nextRequiredActionDetail: reviewChain.submitDecisionReview.nextRequiredActionDetail,
          blockedReasons: reviewChain.submitDecisionReview.blockedReasons,
          missingData: reviewChain.submitDecisionReview.missingData,
          warnings: reviewChain.submitDecisionReview.warnings,
        }
      : null,
    reviewChain.operatorActionReview
      ? {
          key: "operator-action-review",
          title: "Operator action review status",
          status: reviewChain.operatorActionReview.status,
          body: reviewChain.operatorActionReview.body,
          nextRequiredAction: reviewChain.operatorActionReview.nextRequiredAction,
          nextRequiredActionDetail: reviewChain.operatorActionReview.nextRequiredActionDetail,
          blockedReasons: reviewChain.operatorActionReview.blockedReasons,
          missingData: reviewChain.operatorActionReview.missingData,
          warnings: reviewChain.operatorActionReview.warnings,
        }
      : null,
    reviewChain.finalInteractionSpec
      ? {
          key: "final-interaction-spec",
          title: "Final interaction spec status",
          status: reviewChain.finalInteractionSpec.status,
          body: reviewChain.finalInteractionSpec.body,
          nextRequiredAction: reviewChain.finalInteractionSpec.nextRequiredAction,
          nextRequiredActionDetail: reviewChain.finalInteractionSpec.nextRequiredActionDetail,
          blockedReasons: reviewChain.finalInteractionSpec.blockedReasons,
          missingData: reviewChain.finalInteractionSpec.missingData,
          warnings: reviewChain.finalInteractionSpec.warnings,
        }
      : null,
  ];

  return sections.filter((section): section is ReviewSection => section !== null);
}

function ManualPaperSubmitConfirmationSurface() {
  const searchParams = useSearchParams();
  const recommendationId = searchParams.get("recommendationId");
  const fallbackSymbol = searchParams.get("symbol") ?? "unknown";

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recommendation, setRecommendation] = useState<PaperRecommendationDetails | null>(null);
  const [routeCheck, setRouteCheck] = useState<PaperRecommendationRouteCheck | null>(null);
  const [dryRunPreview, setDryRunPreview] = useState<PaperRecommendationBrokerDryRunPreview | null>(null);
  const [routeCheckObservedAt, setRouteCheckObservedAt] = useState<string | null>(null);
  const [dryRunObservedAt, setDryRunObservedAt] = useState<string | null>(null);
  const [finalConfirmationChecked, setFinalConfirmationChecked] = useState(false);
  const [submitPending, setSubmitPending] = useState(false);
  const [submitResult, setSubmitResult] = useState<BrokerOrderResult | null>(null);
  const [submitFailure, setSubmitFailure] = useState<PaperSubmitFailureDetail | null>(null);
  const [submitAttempt, setSubmitAttempt] = useState<SubmitAttemptRecord | null>(null);

  useEffect(() => {
    if (!recommendationId) {
      setRecommendation(null);
      setRouteCheck(null);
      setDryRunPreview(null);
      setRouteCheckObservedAt(null);
      setDryRunObservedAt(null);
      setError(null);
      setFinalConfirmationChecked(false);
      setSubmitPending(false);
      setSubmitResult(null);
      setSubmitFailure(null);
      setSubmitAttempt(null);
      return;
    }

    const activeRecommendationId = recommendationId;

    let cancelled = false;

    async function load(): Promise<void> {
      setLoading(true);
      setError(null);
      setSubmitResult(null);
      setSubmitFailure(null);
      setSubmitAttempt(null);
      setFinalConfirmationChecked(false);

      try {
        const nextRecommendation = await getPaperRecommendation(activeRecommendationId);
        if (cancelled) return;
        setRecommendation(nextRecommendation);

        const nextRouteCheck = await getPaperRecommendationRouteCheck(activeRecommendationId);
        if (cancelled) return;
        setRouteCheck(nextRouteCheck);
        setRouteCheckObservedAt(new Date().toISOString());

        if (nextRouteCheck.route_check_status === "eligible") {
          const nextDryRunPreview = await previewPaperRecommendationBrokerDryRun(activeRecommendationId);
          if (cancelled) return;
          setDryRunPreview(nextDryRunPreview);
          setDryRunObservedAt(new Date().toISOString());
        } else {
          setDryRunPreview(null);
          setDryRunObservedAt(null);
        }
      } catch (loadError) {
        if (cancelled) return;
        setError(loadError instanceof Error ? loadError.message : String(loadError));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void load();

    return () => {
      cancelled = true;
    };
  }, [recommendationId]);

  const payloadPreviewFields = buildPayloadPreviewFields(
    recommendationId,
    routeCheck,
    dryRunPreview,
    fallbackSymbol,
  );
  const missingPayloadFields = payloadPreviewFields.filter((field) => field.missing).map((field) => field.label);
  const effectiveSymbol = routeCheck?.ticker ?? dryRunPreview?.ticker ?? fallbackSymbol;
  const liveTradingEnabled = dryRunPreview?.live_trading_enabled ?? routeCheck?.live_trading_enabled ?? false;
  const workersAllowedToSubmit = dryRunPreview?.workers_allowed_to_submit ?? routeCheck?.workers_allowed_to_submit ?? false;
  const reviewChain = deriveManualPaperSubmitReviewChain(routeCheck, dryRunPreview, fallbackSymbol);
  const freshnessReview = deriveManualPaperSubmitPayloadFreshnessReview(reviewChain, routeCheck, dryRunPreview, {
    recommendation,
    routeCheckObservedAt,
    dryRunObservedAt,
  });
  const missingContextTriage = deriveManualPaperSubmitMissingContextTriage(
    reviewChain,
    routeCheck,
    dryRunPreview,
    freshnessReview,
  );
  const reviewSections = buildReviewSections(reviewChain);
  const blockedReasons = Array.from(
    new Set(
      reviewSections.flatMap((section) => section.blockedReasons),
    ),
  );
  const missingContext = Array.from(
    new Set([
      ...reviewSections.flatMap((section) => section.missingData),
      ...payloadPreviewFields.filter((field) => field.missing).map((field) => field.label),
    ]),
  );
  const warnings = Array.from(
    new Set(reviewSections.flatMap((section) => section.warnings)),
  );
  const readinessStatus = reviewChain.readiness?.status ?? "not_available";
  const handoffStatus = reviewChain.handoff?.status ?? "not_available";
  const auditPackageStatus = reviewChain.auditPackage?.status ?? "not_available";
  const approvalPackageStatus = reviewChain.approvalPackage?.status ?? "not_available";
  const preflightContractStatus = reviewChain.preflightContract?.status ?? "not_available";
  const routeCheckStatus = routeCheck?.route_check_status ?? "missing_context";
  const dryRunStatus = dryRunPreview?.dry_run_status ?? (recommendationId ? "not_loaded" : "missing_context");
  const submitPayload = buildSubmitPayload(recommendationId, recommendation, routeCheck, dryRunPreview, fallbackSymbol);
  const canonicalSubmitRouteReady =
    routeCheck?.resolved_route === "/broker/orders" &&
    routeCheck?.canonical_paper_route === "/broker/orders" &&
    dryRunPreview?.resolved_route === "/broker/orders" &&
    dryRunPreview?.canonical_paper_route === "/broker/orders";
  const paperOnlyRouteReady =
    (dryRunPreview?.serious_paper_source ?? routeCheck?.serious_paper_source) === "ibkr_paper" &&
    (dryRunPreview?.broker_account_mode ?? routeCheck?.broker_account_mode) === "paper";
  const preflightDecisionReady =
    dryRunPreview?.preflight_decision?.decision_status === "allowed" ||
    dryRunPreview?.preflight_decision?.decision_status === "advisory";
  const gateFailures = [
    !recommendationId ? "Recommendation id is required." : null,
    loading ? "Review context is still loading." : null,
    error ? "Review context failed to load." : null,
    routeCheck === null ? "Route-check evidence is required." : null,
    dryRunPreview === null ? "Guarded broker dry-run evidence is required." : null,
    routeCheckStatus !== "eligible" ? "Route-check must remain eligible for paper submit." : null,
    dryRunStatus !== "ready" ? "Guarded broker dry-run must remain ready." : null,
    dryRunPreview?.allowed_to_submit !== true ? "Guarded broker dry-run must still allow paper submit." : null,
    dryRunPreview?.would_block ? "Guarded broker dry-run would block submit." : null,
    liveTradingEnabled ? "Live trading must remain locked." : null,
    workersAllowedToSubmit ? "Workers must remain non-submitting." : null,
    !canonicalSubmitRouteReady ? "The canonical paper route must remain /broker/orders only." : null,
    !paperOnlyRouteReady ? "Broker mode and execution source must remain coherent paper-only IBKR routing." : null,
    reviewChain.preflightContract?.status !== "preflight_contract_ready_for_future_manual_step"
      ? "Preflight contract must stay ready for the manual step."
      : null,
    freshnessReview.status !== "freshness_ready_for_future_manual_review"
      ? "Freshness review must stay clear before submit."
      : null,
    missingContextTriage.status !== "triage_clear_for_future_review"
      ? "Missing-context triage must stay clear before submit."
      : null,
    blockedReasons.length > 0 ? "Blocking review reasons must be cleared before submit." : null,
    missingPayloadFields.length > 0 ? `Missing payload fields: ${missingPayloadFields.join(", ")}.` : null,
    !preflightDecisionReady ? "Dry-run preflight decision must remain allowed or advisory only." : null,
    submitPayload === null ? "The reviewed order payload is incomplete for the existing /broker/orders contract." : null,
    submitResult ? "This order has already been submitted from the current confirmation view." : null,
  ].filter((value): value is string => value !== null);
  const canSubmit = gateFailures.length === 0 && finalConfirmationChecked && !submitPending;
  const surfaceStatus = submitResult ? "paper_order_submitted" : "paper_only_confirmation_control";

  async function handleSubmit(): Promise<void> {
    if (!canSubmit || submitPayload === null) {
      return;
    }

    const attemptRecord: SubmitAttemptRecord = {
      ticker: submitPayload.ticker,
      side: submitPayload.side,
      quantity: typeof submitPayload.quantity === "number" ? submitPayload.quantity : null,
      orderType: submitPayload.order_type,
      limitPrice: typeof submitPayload.limit_price === "number" ? submitPayload.limit_price : null,
      timeInForce: submitPayload.tif ?? "DAY",
      estimatedNotional: dryRunPreview?.estimated_notional ?? null,
      recommendationId: submitPayload.recommendation_id,
      correlationId: submitPayload.submit_decision_correlation_id,
      attemptedAtIso: new Date().toISOString(),
      brokerMode:
        dryRunPreview?.broker_mode?.mode ?? routeCheck?.broker_mode?.mode ?? null,
      brokerAccountMode:
        dryRunPreview?.broker_account_mode ?? routeCheck?.broker_account_mode ?? null,
      executionSource:
        dryRunPreview?.serious_paper_source ?? routeCheck?.serious_paper_source ?? null,
      preflightDecisionStatus: dryRunPreview?.preflight_decision?.decision_status ?? null,
      dryRunAllowedToSubmit: dryRunPreview?.allowed_to_submit ?? null,
      dryRunWouldBlock: dryRunPreview?.would_block ?? null,
      routeCheckReference: buildRouteCheckReference(routeCheck),
      dryRunReference: buildDryRunReference(dryRunPreview),
    };

    setSubmitPending(true);
    setSubmitFailure(null);
    setSubmitAttempt(attemptRecord);

    try {
      const result = await submitBrokerOrder(submitPayload);
      setSubmitResult(result);
      setFinalConfirmationChecked(false);
    } catch (submitError) {
      setSubmitFailure(buildBlockedSubmitDetail(submitError));
    } finally {
      setSubmitPending(false);
    }
  }

  return (
    <main
      className={styles.page}
      data-testid="cockpit-manual-paper-submit-confirmation-page"
    >
      <div className={styles.container}>
        <header className={styles.header}>
          <div className={styles.titleWrap}>
            <p className={styles.eyebrow}>Paper-only guarded manual submit</p>
            <h1 className={styles.title}>Manual IBKR paper submit confirmation</h1>
            <p className={styles.subtitle}>
              Paper submit, final confirmation required. This is the only cockpit surface allowed to submit a guarded IBKR paper order, and it reruns backend checks through /broker/orders.
            </p>
          </div>

          <div className={styles.headerLinks}>
            <Link href="/cockpit/in-flight-adjustments" className={styles.linkPill}>
              Cancel / return to review
            </Link>
            <Link href="/cockpit" className={styles.linkPill}>
              Cockpit hub
            </Link>
          </div>
        </header>

        <section className={styles.heroCard} data-testid="cockpit-manual-paper-submit-confirmation-status">
          <div>
            <p className={styles.heroEyebrow}>Surface status</p>
            <h2 className={styles.heroTitle}>{surfaceStatus}</h2>
            <p className={styles.heroSubtitle}>
              {submitResult
                ? "Paper order submitted through the existing guarded broker seam. Live remains locked and workers remain non-submitting."
                : "No live trading path has been enabled and no worker authority has been expanded. Submit stays paper-only and fail-closed."}
            </p>
          </div>
          <div className={styles.heroMeta}>
            <span className={styles.statusPill}>Paper only</span>
            <span className={styles.statusPill}>No live trading</span>
          </div>
        </section>

        <div className={styles.banner} data-testid="cockpit-manual-paper-submit-confirmation-paper-banner">
          <strong>Paper mode only.</strong> This page is the only executable manual confirmation surface. It may call <span className={styles.mono}>/broker/orders</span> only after explicit final confirmation and only while all paper-only guards remain clear.
        </div>

        {error ? (
          <div className={styles.inlineError} role="alert" data-testid="cockpit-manual-paper-submit-confirmation-error">
            {error}
          </div>
        ) : null}

        {!recommendationId ? (
          <section className={styles.sectionCard}>
            <h2 className={styles.sectionTitle}>Recommendation context</h2>
            <p className={styles.sectionSubtitle}>
              No recommendation id was provided. The design surface still renders safely, but route-check and guarded dry-run evidence cannot be loaded until a recommendation is selected from the in-flight review chain.
            </p>
          </section>
        ) : null}

        <section className={styles.sectionCard} data-testid="cockpit-manual-paper-submit-confirmation-surface-status-grid">
          <h2 className={styles.sectionTitle}>Surface status</h2>
          <div className={styles.grid}>
            <div className={styles.field}><span className={styles.label}>confirmation_surface_status</span><span className={styles.value}>{surfaceStatus}</span></div>
            <div className={styles.field}><span className={styles.label}>submit_enabled_now</span><span className={styles.value}>{canSubmit ? "true" : "false"}</span></div>
            <div className={styles.field}><span className={styles.label}>order_submitted</span><span className={styles.value}>{submitResult ? "true" : "false"}</span></div>
            <div className={styles.field}><span className={styles.label}>live_trading_enabled</span><span className={styles.value}>{liveTradingEnabled ? "true" : "false"}</span></div>
            <div className={styles.field}><span className={styles.label}>workers_allowed_to_submit</span><span className={styles.value}>{workersAllowedToSubmit ? "true" : "false"}</span></div>
            <div className={styles.field}><span className={styles.label}>final_confirmation_checked</span><span className={styles.value}>{finalConfirmationChecked ? "true" : "false"}</span></div>
            <div className={styles.field}><span className={styles.label}>recommendation_id</span><span className={`${styles.value} ${styles.mono}`}>{recommendationId ?? "not provided"}</span></div>
            <div className={styles.field}><span className={styles.label}>symbol</span><span className={styles.value}>{effectiveSymbol}</span></div>
            <div className={styles.field}><span className={styles.label}>loading_review_context</span><span className={styles.value}>{loading ? "true" : "false"}</span></div>
            <div className={styles.field}><span className={styles.label}>route_check_status</span><span className={styles.value}>{routeCheckStatus}</span></div>
            <div className={styles.field}><span className={styles.label}>dry_run_status</span><span className={styles.value}>{dryRunStatus}</span></div>
            <div className={styles.field}><span className={styles.label}>readiness_status</span><span className={styles.value}>{readinessStatus}</span></div>
            <div className={styles.field}><span className={styles.label}>handoff_status</span><span className={styles.value}>{handoffStatus}</span></div>
            <div className={styles.field}><span className={styles.label}>audit_package_status</span><span className={styles.value}>{auditPackageStatus}</span></div>
            <div className={styles.field}><span className={styles.label}>approval_package_status</span><span className={styles.value}>{approvalPackageStatus}</span></div>
            <div className={styles.field}><span className={styles.label}>preflight_contract_status</span><span className={styles.value}>{preflightContractStatus}</span></div>
          </div>
        </section>

        <section className={styles.sectionCard} data-testid="cockpit-manual-paper-submit-confirmation-review-statuses">
          <h2 className={styles.sectionTitle}>Read-only confirmation preview</h2>
          <p className={styles.sectionSubtitle}>
            Future manual paper submit would still use guarded /broker/orders. The statuses below are derived from the existing read-only recommendation review chain where evidence is available.
          </p>
          {reviewSections.length === 0 ? (
            <p className={styles.emptyText}>Review-chain status is unavailable until recommendation context is loaded.</p>
          ) : (
            <div className={styles.grid}>
              {reviewSections.map((section) => (
                <div key={section.key} className={styles.field} data-testid={`cockpit-manual-paper-submit-confirmation-${section.key}-status`}>
                  <span className={styles.label}>{section.title}</span>
                  <span className={styles.value}>{formatDerivedStatus(section.status)}</span>
                  <span className={styles.label}>{section.body}</span>
                  <span className={styles.value}>next_required_action: {section.nextRequiredAction}</span>
                  <span className={styles.label}>{section.nextRequiredActionDetail}</span>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className={styles.sectionCard} data-testid="cockpit-manual-paper-submit-confirmation-payload-freshness-review">
          <h2 className={styles.sectionTitle}>Payload freshness review</h2>
          <p className={styles.sectionSubtitle}>
            Freshness review gates the live control fail-closed. Submit stays paper-only, reruns checks on the backend seam, and remains blocked if any freshness evidence drifts.
          </p>
          <div className={styles.grid}>
            <div className={styles.field}><span className={styles.label}>payload_freshness_status</span><span className={styles.value}>{freshnessReview.status}</span></div>
            <div className={styles.field}><span className={styles.label}>recommendation_payload_fresh</span><span className={styles.value}>{freshnessReview.recommendationPayloadFresh ? "true" : "false"}</span></div>
            <div className={styles.field}><span className={styles.label}>route_check_fresh</span><span className={styles.value}>{freshnessReview.routeCheckFresh ? "true" : "false"}</span></div>
            <div className={styles.field}><span className={styles.label}>dry_run_fresh</span><span className={styles.value}>{freshnessReview.dryRunFresh ? "true" : "false"}</span></div>
            <div className={styles.field}><span className={styles.label}>approval_package_fresh</span><span className={styles.value}>{freshnessReview.approvalPackageFresh ? "true" : "false"}</span></div>
            <div className={styles.field}><span className={styles.label}>preflight_contract_fresh</span><span className={styles.value}>{freshnessReview.preflightContractFresh ? "true" : "false"}</span></div>
            <div className={styles.field}><span className={styles.label}>final_payload_fields_aligned</span><span className={styles.value}>{freshnessReview.finalPayloadFieldsAligned ? "true" : "false"}</span></div>
            <div className={styles.field}><span className={styles.label}>source_labels_coherent</span><span className={styles.value}>{freshnessReview.sourceLabelsCoherent ? "true" : "false"}</span></div>
            <div className={styles.field}><span className={styles.label}>broker_mode_still_paper</span><span className={styles.value}>{freshnessReview.brokerModeStillPaper ? "true" : "false"}</span></div>
            <div className={styles.field}><span className={styles.label}>upstream_state_drifted</span><span className={styles.value}>{freshnessReview.upstreamStateDrifted ? "true" : "false"}</span></div>
            <div className={styles.field}><span className={styles.label}>submit_enabled_now</span><span className={styles.value}>{canSubmit ? "true" : "false"}</span></div>
            <div className={styles.field}><span className={styles.label}>order_submitted</span><span className={styles.value}>{submitResult ? "true" : "false"}</span></div>
            <div className={styles.field}><span className={styles.label}>live_trading_enabled</span><span className={styles.value}>{freshnessReview.liveTradingEnabled ? "true" : "false"}</span></div>
            <div className={styles.field}><span className={styles.label}>workers_allowed_to_submit</span><span className={styles.value}>{freshnessReview.workersAllowedToSubmit ? "true" : "false"}</span></div>
            <div className={styles.field}><span className={styles.label}>freshness_window_description</span><span className={styles.value}>{freshnessReview.freshnessWindowDescription}</span></div>
            <div className={styles.field}><span className={styles.label}>recommendation_timestamp_reference</span><span className={styles.value}>{freshnessReview.recommendationTimestampReference}</span></div>
            <div className={styles.field}><span className={styles.label}>route_check_timestamp_reference</span><span className={styles.value}>{freshnessReview.routeCheckTimestampReference}</span></div>
            <div className={styles.field}><span className={styles.label}>dry_run_timestamp_reference</span><span className={styles.value}>{freshnessReview.dryRunTimestampReference}</span></div>
            <div className={styles.field}><span className={styles.label}>approval_timestamp_reference</span><span className={styles.value}>{freshnessReview.approvalTimestampReference}</span></div>
            <div className={styles.field}><span className={styles.label}>preflight_timestamp_reference</span><span className={styles.value}>{freshnessReview.preflightTimestampReference}</span></div>
            <div className={styles.field}><span className={styles.label}>next_required_action</span><span className={styles.value}>{freshnessReview.nextRequiredAction}</span></div>
          </div>
          <div className={styles.subsection}>
            <h3 className={styles.subsectionTitle}>{freshnessReview.title}</h3>
            <p className={styles.sectionSubtitle}>{freshnessReview.body}</p>
            <p className={styles.emptyText}>{freshnessReview.nextRequiredActionDetail}</p>
          </div>
          <div className={styles.subsection}>
            <h3 className={styles.subsectionTitle}>rerun_required</h3>
            {freshnessReview.rerunRequired.length === 0 ? (
              <p className={styles.emptyText}>No reruns are currently surfaced beyond the mandatory later submit-time route-check and guarded dry-run reruns.</p>
            ) : (
              <ul className={styles.list}>
                {freshnessReview.rerunRequired.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            )}
          </div>
          <div className={styles.subsection}>
            <h3 className={styles.subsectionTitle}>rerun_reasons</h3>
            {freshnessReview.rerunReasons.length === 0 ? (
              <p className={styles.emptyText}>No extra rerun reasons are currently surfaced by the shared freshness review.</p>
            ) : (
              <ul className={styles.list}>
                {freshnessReview.rerunReasons.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            )}
          </div>
          <div className={styles.subsection}>
            <h3 className={styles.subsectionTitle}>missing_freshness_fields</h3>
            {freshnessReview.missingFreshnessFields.length === 0 ? (
              <p className={styles.emptyText}>No missing timestamp or freshness fields are currently surfaced.</p>
            ) : (
              <ul className={styles.list}>
                {freshnessReview.missingFreshnessFields.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            )}
          </div>
          <div className={styles.subsection}>
            <h3 className={styles.subsectionTitle}>stale_evidence</h3>
            {freshnessReview.staleEvidence.length === 0 ? (
              <p className={styles.emptyText}>No stale evidence is currently surfaced by the shared freshness review.</p>
            ) : (
              <ul className={styles.list}>
                {freshnessReview.staleEvidence.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            )}
          </div>
        </section>

        <section className={styles.sectionCard} data-testid="cockpit-manual-paper-submit-confirmation-missing-context-triage">
          <h2 className={styles.sectionTitle}>Missing-context triage</h2>
          <p className={styles.sectionSubtitle}>
            Missing-context triage gates the live control fail-closed. Live trading remains locked and workers cannot submit.
          </p>
          <div className={styles.grid}>
            <div className={styles.field}><span className={styles.label}>missing_context_triage_status</span><span className={styles.value}>{missingContextTriage.status}</span></div>
            <div className={styles.field}><span className={styles.label}>next_required_review_action</span><span className={styles.value}>{missingContextTriage.nextRequiredReviewAction}</span></div>
            <div className={styles.field}><span className={styles.label}>submit_enabled_now</span><span className={styles.value}>{canSubmit ? "true" : "false"}</span></div>
            <div className={styles.field}><span className={styles.label}>order_submitted</span><span className={styles.value}>{submitResult ? "true" : "false"}</span></div>
            <div className={styles.field}><span className={styles.label}>live_trading_enabled</span><span className={styles.value}>{missingContextTriage.liveTradingEnabled ? "true" : "false"}</span></div>
            <div className={styles.field}><span className={styles.label}>workers_allowed_to_submit</span><span className={styles.value}>{missingContextTriage.workersAllowedToSubmit ? "true" : "false"}</span></div>
          </div>
          <div className={styles.subsection}>
            <h3 className={styles.subsectionTitle}>{missingContextTriage.title}</h3>
            <p className={styles.sectionSubtitle}>{missingContextTriage.body}</p>
            <p className={styles.emptyText}>{missingContextTriage.nextRequiredReviewActionDetail}</p>
          </div>
          <div className={styles.subsection}>
            <h3 className={styles.subsectionTitle}>rerun_required</h3>
            {missingContextTriage.rerunRequired.length === 0 ? (
              <p className={styles.emptyText}>No rerun requirements are currently surfaced by the shared triage helper.</p>
            ) : (
              <ul className={styles.list}>
                {missingContextTriage.rerunRequired.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            )}
          </div>
          <div className={styles.subsection}>
            <h3 className={styles.subsectionTitle}>rerun_reasons</h3>
            {missingContextTriage.rerunReasons.length === 0 ? (
              <p className={styles.emptyText}>No rerun reasons are currently surfaced by the shared triage helper.</p>
            ) : (
              <ul className={styles.list}>
                {missingContextTriage.rerunReasons.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            )}
          </div>
          {missingContextTriage.triageGroups.map((group) => (
            <div key={group.code} className={styles.subsection}>
              <h3 className={styles.subsectionTitle}>{group.title}</h3>
              {group.items.length === 0 ? (
                <p className={styles.emptyText}>No issues are currently surfaced in this triage bucket.</p>
              ) : (
                <ul className={styles.list}>
                  {group.items.map((item) => (
                    <li key={`${group.code}-${item}`}>{item}</li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </section>

        <section className={styles.sectionCard} data-testid="cockpit-manual-paper-submit-confirmation-context-gaps">
          <h2 className={styles.sectionTitle}>Missing context, blocked reasons, and warnings</h2>
          <div className={styles.subsection}>
            <h3 className={styles.subsectionTitle}>missing_context</h3>
            {missingContext.length === 0 ? (
              <p className={styles.emptyText}>No missing context is currently surfaced from the read-only review chain.</p>
            ) : (
              <ul className={styles.list}>
                {missingContext.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            )}
          </div>
          <div className={styles.subsection}>
            <h3 className={styles.subsectionTitle}>blocked_reasons</h3>
            {blockedReasons.length === 0 ? (
              <p className={styles.emptyText}>No blocking reasons are currently surfaced from the read-only review chain.</p>
            ) : (
              <ul className={styles.list}>
                {blockedReasons.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            )}
          </div>
          <div className={styles.subsection}>
            <h3 className={styles.subsectionTitle}>warnings</h3>
            {warnings.length === 0 ? (
              <p className={styles.emptyText}>No warnings are currently surfaced from the read-only review chain.</p>
            ) : (
              <ul className={styles.list}>
                {warnings.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            )}
          </div>
        </section>

        <section className={styles.sectionCard} data-testid="cockpit-manual-paper-submit-confirmation-future-route">
          <h2 className={styles.sectionTitle}>Future route</h2>
          <div className={styles.grid}>
            <div className={styles.field}><span className={styles.label}>future_submit_route</span><span className={`${styles.value} ${styles.mono}`}>/broker/orders</span></div>
            <div className={styles.field}><span className={styles.label}>route_type</span><span className={styles.value}>guarded_ibkr_paper_only</span></div>
            <div className={styles.field}><span className={styles.label}>execution_source</span><span className={styles.value}>ibkr_paper</span></div>
            <div className={styles.field}><span className={styles.label}>account_mode_required</span><span className={styles.value}>paper</span></div>
            <div className={styles.field}><span className={styles.label}>route_check_reference</span><span className={styles.value}>{buildRouteCheckReference(routeCheck)}</span></div>
            <div className={styles.field}><span className={styles.label}>dry_run_reference</span><span className={styles.value}>{buildDryRunReference(dryRunPreview)}</span></div>
          </div>
        </section>

        <section className={styles.sectionCard} data-testid="cockpit-manual-paper-submit-confirmation-payload-preview">
          <h2 className={styles.sectionTitle}>Future payload preview</h2>
          <p className={styles.sectionSubtitle}>
            This is the reviewed payload context for the guarded paper submit control. The backend still reruns validation and preflight before any broker attempt.
          </p>
          <ul className={styles.list}>
            {payloadPreviewFields.map((field) => (
              <li key={field.label}>
                <span className={styles.listKey}>{field.label}:</span> {field.value}. {field.detail}
              </li>
            ))}
          </ul>
          <div className={styles.subsection}>
            <h3 className={styles.subsectionTitle}>missing_payload_fields</h3>
            {missingPayloadFields.length === 0 ? (
              <p className={styles.emptyText}>No required payload fields are currently missing for the existing quantity-based guarded contract.</p>
            ) : (
              <ul className={styles.list}>
                {missingPayloadFields.map((field) => (
                  <li key={field}>{field}</li>
                ))}
              </ul>
            )}
          </div>
        </section>

        <section className={styles.sectionCard} data-testid="cockpit-manual-paper-submit-confirmation-rerun-checklist">
          <h2 className={styles.sectionTitle}>Submit-time checks will rerun</h2>
          <ul className={styles.list}>
            {submitTimeChecks.map((item) => (
              <li key={item.label}>
                <span className={styles.listKey}>{item.label}:</span> {item.detail}
              </li>
            ))}
          </ul>
        </section>

        <section className={styles.sectionCard} data-testid="cockpit-manual-paper-submit-confirmation-blocking-states">
          <h2 className={styles.sectionTitle}>Blocking states</h2>
          <ul className={styles.list}>
            {blockingStates.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>

        <section className={styles.sectionCard} data-testid="cockpit-manual-paper-submit-confirmation-decision-persistence">
          <h2 className={styles.sectionTitle}>Decision persistence requirements</h2>
          <ul className={styles.list}>
            {decisionPersistenceRequirements.map((item) => (
              <li key={item.label}>
                <span className={styles.listKey}>{item.label}:</span> {item.detail}
              </li>
            ))}
          </ul>
        </section>

        <section className={styles.sectionCard} data-testid="cockpit-manual-paper-submit-confirmation-wording-preview">
          <h2 className={styles.sectionTitle}>Confirmation wording preview</h2>
          <blockquote className={styles.quote}>{finalConfirmationWording}</blockquote>
        </section>

        <section className={styles.sectionCard} data-testid="cockpit-manual-paper-submit-confirmation-submit-control">
          <h2 className={styles.sectionTitle}>Guarded paper submit control</h2>
          <p className={styles.sectionSubtitle}>
            Paper only. Final confirmation is required. Submit-time checks will rerun through the existing guarded /broker/orders seam with append-only decision persistence.
          </p>
          <label className={styles.checkboxRow}>
            <input
              type="checkbox"
              checked={finalConfirmationChecked}
              onChange={(event) => setFinalConfirmationChecked(event.target.checked)}
              disabled={submitPending || submitResult !== null}
              data-testid="manual-paper-submit-confirmation-checkbox"
            />
            <span>{finalConfirmationWording}</span>
          </label>

          <p className={styles.emptyText}>Submit paper order, checks will rerun. No auto-submit. No worker submit. No live unlock.</p>

          {gateFailures.length > 0 ? (
            <div className={styles.subsection} data-testid="manual-paper-submit-gate-failures">
              <h3 className={styles.subsectionTitle}>Submit is currently blocked</h3>
              <ul className={styles.list}>
                {gateFailures.map((failure) => (
                  <li key={failure}>{failure}</li>
                ))}
              </ul>
            </div>
          ) : null}

          {submitFailure ? (
            <div className={styles.inlineError} role="alert" data-testid="manual-paper-submit-error-state">
              <strong>{submitFailure.title}</strong>
              <p className={styles.sectionSubtitle}>{submitFailure.message}</p>
              {submitFailure.submitGate || submitFailure.decisionStatus ? (
                <p className={styles.emptyText}>
                  submit_gate={submitFailure.submitGate ?? "unknown"}; decision_status={submitFailure.decisionStatus ?? "unknown"}
                </p>
              ) : null}
              {submitFailure.reasons.length > 0 ? (
                <ul className={styles.list}>
                  {submitFailure.reasons.map((reason) => (
                    <li key={reason}>{reason}</li>
                  ))}
                </ul>
              ) : null}
            </div>
          ) : null}

          {submitResult ? (
            <div className={styles.successBanner} role="status" data-testid="manual-paper-submit-success-state">
              <strong>Paper order submitted.</strong>
              <p className={styles.sectionSubtitle}>
                Broker order {submitResult.broker_order_id} returned status {submitResult.status}. The submit path remained paper-only through /broker/orders.
              </p>
            </div>
          ) : null}

          <div className={styles.placeholderRow}>
            <button
              type="button"
              disabled={!canSubmit}
              className={canSubmit ? styles.primaryButton : styles.disabledButton}
              data-testid="manual-paper-submit-button"
              onClick={() => {
                void handleSubmit();
              }}
            >
              {submitPending ? "Submitting IBKR paper order..." : "Submit IBKR paper order"}
            </button>
            <Link href="/cockpit/in-flight-adjustments" className={styles.linkPill}>
              Cancel / return to review
            </Link>
          </div>
        </section>

        {submitAttempt && (submitResult || submitFailure) ? (
          <OperatorOutcomeView
            attempt={submitAttempt}
            result={submitResult}
            failure={submitFailure}
          />
        ) : null}
      </div>
    </main>
  );
}

export default function ManualPaperSubmitConfirmationPage() {
  return (
    <Suspense fallback={<main className={styles.page}><div className={styles.container}><section className={styles.sectionCard}><h1 className={styles.title}>Manual IBKR paper submit confirmation</h1><p className={styles.sectionSubtitle}>Loading design-only confirmation surface…</p></section></div></main>}>
      <ManualPaperSubmitConfirmationSurface />
    </Suspense>
  );
}