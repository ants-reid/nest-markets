"use client";

import Link from "next/link";
import { useState } from "react";

import {
  getPaperRecommendationRouteCheck,
  previewPaperRecommendationBrokerDryRun,
  type PaperRecommendationBrokerDryRunPreview,
  type PaperRecommendationRouteCheck,
} from "../lib/api/paperRecommendations";
import {
  buildManualConfirmationHref,
  deriveManualPaperSubmitReviewChain,
} from "../lib/manualPaperSubmitReview";
import styles from "./RecommendationRouteCheckPanel.module.css";

function statusClassName(status: string): string {
  if (
    status === "eligible" ||
    status === "ready" ||
    status === "interaction_spec_ready_for_future_phase" ||
    status === "action_review_ready_for_future_manual_step" ||
    status === "ready_for_future_decision_review" ||
    status === "approval_package_ready_for_future_manual_review" ||
    status === "preflight_contract_ready_for_future_manual_step" ||
    status === "package_ready_for_future_manual_review" ||
    status === "ready_for_future_manual_paper_submit" ||
    status === "handoff_ready_for_future_manual_step"
  ) {
    return styles.statusEligible;
  }
  if (status === "blocked") return styles.statusBlocked;
  if (
    status === "missing_context" ||
    status === "invalid" ||
    status === "dry_run_required" ||
    status === "approval_required" ||
    status === "approval_package_required" ||
    status === "audit_package_required" ||
    status === "action_not_available" ||
    status === "operator_action_review_required" ||
    status === "handoff_required" ||
    status === "preflight_contract_required" ||
    status === "design_review_required" ||
    status === "submit_decision_review_required" ||
    status === "readiness_required"
  ) {
    return styles.statusMissing;
  }
  return styles.statusUnknown;
}

function summaryClassName(status: string): string {
  if (
    status === "eligible" ||
    status === "ready" ||
    status === "interaction_spec_ready_for_future_phase" ||
    status === "action_review_ready_for_future_manual_step" ||
    status === "ready_for_future_decision_review" ||
    status === "approval_package_ready_for_future_manual_review" ||
    status === "preflight_contract_ready_for_future_manual_step" ||
    status === "package_ready_for_future_manual_review" ||
    status === "ready_for_future_manual_paper_submit" ||
    status === "handoff_ready_for_future_manual_step"
  ) {
    return styles.summaryEligible;
  }
  if (status === "blocked") return styles.summaryBlocked;
  if (
    status === "missing_context" ||
    status === "invalid" ||
    status === "dry_run_required" ||
    status === "approval_required" ||
    status === "approval_package_required" ||
    status === "audit_package_required" ||
    status === "action_not_available" ||
    status === "operator_action_review_required" ||
    status === "handoff_required" ||
    status === "preflight_contract_required" ||
    status === "design_review_required" ||
    status === "submit_decision_review_required" ||
    status === "readiness_required"
  ) {
    return styles.summaryMissing;
  }
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

type ManualPaperSubmitHandoffStatus =
  | "handoff_ready_for_future_manual_step"
  | "blocked"
  | "missing_context"
  | "dry_run_required"
  | "handoff_required"
  | "readiness_required"
  | "unknown";

type ManualPaperSubmitHandoffReason = {
  code: string;
  label: string;
  satisfied: boolean;
};

type ManualPaperSubmitHandoffPayloadField = {
  code: string;
  label: string;
  required: boolean;
  satisfied: boolean;
  value: string;
  detail: string;
};

type ManualPaperSubmitHandoffReview = {
  status: ManualPaperSubmitHandoffStatus;
  title: string;
  body: string;
  reasons: ManualPaperSubmitHandoffReason[];
  requiredFuturePayloadFields: ManualPaperSubmitHandoffPayloadField[];
  blockedReasons: string[];
  missingData: string[];
  warnings: string[];
  safetyGates: string[];
  futureManualSubmitRoute: string | null;
  nextRequiredAction: string;
  nextRequiredActionDetail: string;
};

type ManualPaperSubmitAuditPackageStatus =
  | "package_ready_for_future_manual_review"
  | "blocked"
  | "missing_context"
  | "dry_run_required"
  | "readiness_required"
  | "handoff_required"
  | "unknown";

type ManualPaperSubmitAuditChecklistItem = {
  code: string;
  label: string;
  satisfied: boolean;
  detail: string;
};

type ManualPaperSubmitAuditReference = {
  code: string;
  label: string;
  available: boolean;
  value: string;
  detail: string;
};

type ManualPaperSubmitAuditSourceLabel = {
  code: string;
  label: string;
  value: string;
};

type ManualPaperSubmitAuditPackage = {
  status: ManualPaperSubmitAuditPackageStatus;
  title: string;
  body: string;
  evidenceChecklist: ManualPaperSubmitAuditChecklistItem[];
  sourceLabels: ManualPaperSubmitAuditSourceLabel[];
  decisionReferences: ManualPaperSubmitAuditReference[];
  futurePayloadPreviewFields: ManualPaperSubmitHandoffPayloadField[];
  missingPayloadFields: string[];
  blockedReasons: string[];
  missingData: string[];
  warnings: string[];
  futureManualSubmitRoute: string | null;
  nextRequiredAction: string;
  nextRequiredActionDetail: string;
};

type ManualPaperSubmitApprovalPackageStatus =
  | "approval_package_ready_for_future_manual_review"
  | "blocked"
  | "missing_context"
  | "dry_run_required"
  | "readiness_required"
  | "handoff_required"
  | "audit_package_required"
  | "approval_not_available"
  | "unknown";

type ManualPaperSubmitApprovalRequirement = {
  code: string;
  label: string;
  required: boolean;
  detail: string;
};

type ManualPaperSubmitApprovalPackage = {
  status: ManualPaperSubmitApprovalPackageStatus;
  title: string;
  body: string;
  evidenceChecklist: ManualPaperSubmitAuditChecklistItem[];
  futureManualApprovalRequirements: ManualPaperSubmitApprovalRequirement[];
  auditReferences: ManualPaperSubmitAuditReference[];
  futurePayloadPreviewFields: ManualPaperSubmitHandoffPayloadField[];
  missingPayloadFields: string[];
  safetyReruns: string[];
  blockedReasons: string[];
  missingData: string[];
  warnings: string[];
  futureManualSubmitRoute: string | null;
  nextRequiredAction: string;
  nextRequiredActionDetail: string;
};

type ManualPaperSubmitPreflightContractStatus =
  | "preflight_contract_ready_for_future_manual_step"
  | "blocked"
  | "missing_context"
  | "dry_run_required"
  | "readiness_required"
  | "handoff_required"
  | "audit_package_required"
  | "approval_package_required"
  | "preflight_not_available"
  | "unknown";

type ManualPaperSubmitPreflightRequirement = {
  code: string;
  label: string;
  required: boolean;
  detail: string;
};

type ManualPaperSubmitPreflightContract = {
  status: ManualPaperSubmitPreflightContractStatus;
  title: string;
  body: string;
  evidenceChecklist: ManualPaperSubmitAuditChecklistItem[];
  submitTimeRerunRequirements: ManualPaperSubmitPreflightRequirement[];
  operatorConfirmations: ManualPaperSubmitPreflightRequirement[];
  finalPayloadReviewFields: ManualPaperSubmitHandoffPayloadField[];
  staleDataChecks: string[];
  sourceLabelRechecks: string[];
  decisionLoggingRequirements: string[];
  missingPayloadFields: string[];
  blockedReasons: string[];
  missingData: string[];
  warnings: string[];
  futureManualSubmitRoute: string | null;
  brokerAccountMode: string;
  liveState: string;
  isCanonicalPaper: boolean;
  workersAllowedToSubmit: boolean;
  liveTradingEnabled: boolean;
  submittedOrder: boolean;
  dryRunOnly: boolean;
  approvalOnly: boolean;
  preflightContractOnly: boolean;
  wouldBlock: boolean;
  nextRequiredAction: string;
  nextRequiredActionDetail: string;
};

type FutureManualSubmitDesignReviewStatus = "design_only_not_enabled";

type FutureManualSubmitDesignReviewRequirement = {
  code: string;
  label: string;
  value: string;
  detail: string;
};

type FutureManualSubmitDesignReview = {
  status: FutureManualSubmitDesignReviewStatus;
  title: string;
  body: string;
  futureSubmitRoute: string;
  existingBackendOwner: string;
  futureFrontendSurface: string;
  futureFrontendOwner: string;
  submitTimeChecks: FutureManualSubmitDesignReviewRequirement[];
  finalOperatorConfirmations: FutureManualSubmitDesignReviewRequirement[];
  decisionRecords: FutureManualSubmitDesignReviewRequirement[];
  lockedPayloadFields: FutureManualSubmitDesignReviewRequirement[];
  blockStates: string[];
  requiredTestsBeforeEnablement: string[];
  intentionallyNotImplemented: string[];
  finalOperatorConfirmationRequired: boolean;
  submitTimePreflightRerunRequired: boolean;
  submitTimeDecisionPersistenceRequired: boolean;
  submitTimeLiveLockRecheckRequired: boolean;
  submitTimeWorkerSubmitAllowed: boolean;
  submitButtonAvailable: boolean;
  orderSubmitted: boolean;
  enabledInThisPhase: boolean;
};

type GuardedSubmitDecisionReviewStatus =
  | "ready_for_future_decision_review"
  | "blocked"
  | "missing_context"
  | "dry_run_required"
  | "approval_required"
  | "preflight_contract_required"
  | "design_review_required"
  | "unknown";

type GuardedSubmitDecisionReviewChecklistItem = {
  code: string;
  label: string;
  satisfied: boolean;
  detail: string;
};

type GuardedSubmitDecisionReviewRequirement = {
  code: string;
  label: string;
  value: string;
  detail: string;
};

type GuardedSubmitDecisionReview = {
  status: GuardedSubmitDecisionReviewStatus;
  title: string;
  body: string;
  evidenceChecklist: GuardedSubmitDecisionReviewChecklistItem[];
  existingDecisionWriters: GuardedSubmitDecisionReviewRequirement[];
  existingDecisionReaders: GuardedSubmitDecisionReviewRequirement[];
  futureDecisionRecords: GuardedSubmitDecisionReviewRequirement[];
  persistedFieldChecklist: GuardedSubmitDecisionReviewRequirement[];
  reviewEvidenceLinks: GuardedSubmitDecisionReviewRequirement[];
  failClosedRules: string[];
  blockedReasons: string[];
  missingData: string[];
  warnings: string[];
  futureSubmitRoute: string | null;
  decisionPersistenceOwner: string;
  futureDecisionSource: string;
  futureOrderCorrelationId: string;
  dryRunDecisionReference: string;
  accountMode: string;
  executionSource: string;
  liveState: string;
  workersAllowedToSubmit: boolean;
  liveTradingEnabled: boolean;
  submittedOrder: boolean;
  decisionWritePerformedNow: boolean;
  reviewOnly: boolean;
  noSubmitControlPresent: boolean;
  nextRequiredAction: string;
  nextRequiredActionDetail: string;
};

type GuardedOperatorActionReviewStatus =
  | "action_review_ready_for_future_manual_step"
  | "blocked"
  | "missing_context"
  | "dry_run_required"
  | "readiness_required"
  | "handoff_required"
  | "audit_package_required"
  | "approval_package_required"
  | "preflight_contract_required"
  | "design_review_required"
  | "submit_decision_review_required"
  | "action_not_available"
  | "unknown";

type GuardedOperatorActionReviewChecklistItem = {
  code: string;
  label: string;
  satisfied: boolean;
  detail: string;
};

type GuardedOperatorActionReviewRequirement = {
  code: string;
  label: string;
  value: string;
  detail: string;
};

type GuardedOperatorActionReview = {
  status: GuardedOperatorActionReviewStatus;
  title: string;
  body: string;
  evidenceChecklist: GuardedOperatorActionReviewChecklistItem[];
  futureActionDescription: GuardedOperatorActionReviewRequirement[];
  finalOperatorConfirmations: GuardedOperatorActionReviewRequirement[];
  finalPayloadPreview: GuardedOperatorActionReviewRequirement[];
  submitTimeChecks: GuardedOperatorActionReviewRequirement[];
  futureDecisionRecords: GuardedOperatorActionReviewRequirement[];
  statesKeepingActionUnavailable: string[];
  blockedReasons: string[];
  missingData: string[];
  warnings: string[];
  futureActionName: string;
  futureActionRoute: string | null;
  submittedOrder: boolean;
  actionAvailableNow: boolean;
  actionReviewOnly: boolean;
  decisionWritePerformedNow: boolean;
  liveState: string;
  workersAllowedToSubmit: boolean;
  liveTradingEnabled: boolean;
  wouldBlock: boolean;
  noSubmitControlPresent: boolean;
  nextRequiredAction: string;
  nextRequiredActionDetail: string;
};

type FinalGuardedSubmitInteractionSpecStatus =
  | "interaction_spec_ready_for_future_phase"
  | "blocked"
  | "missing_context"
  | "dry_run_required"
  | "operator_action_review_required"
  | "unknown";

type FinalGuardedSubmitInteractionSpecChecklistItem = {
  code: string;
  label: string;
  satisfied: boolean;
  detail: string;
};

type FinalGuardedSubmitInteractionSpecRequirement = {
  code: string;
  label: string;
  value: string;
  detail: string;
};

type FinalGuardedSubmitInteractionSpec = {
  status: FinalGuardedSubmitInteractionSpecStatus;
  title: string;
  body: string;
  evidenceChecklist: FinalGuardedSubmitInteractionSpecChecklistItem[];
  futureInteractionContract: FinalGuardedSubmitInteractionSpecRequirement[];
  finalOperatorConfirmations: FinalGuardedSubmitInteractionSpecRequirement[];
  finalPayloadPreview: FinalGuardedSubmitInteractionSpecRequirement[];
  submitTimeChecks: FinalGuardedSubmitInteractionSpecRequirement[];
  futureDecisionRecords: FinalGuardedSubmitInteractionSpecRequirement[];
  laterInteractionSequence: string[];
  statesKeepingInteractionReadOnly: string[];
  blockedReasons: string[];
  missingData: string[];
  warnings: string[];
  futureInteractionName: string;
  futureInteractionRoute: string | null;
  actionAvailableNow: boolean;
  interactionSpecReviewOnly: boolean;
  decisionWritePerformedNow: boolean;
  submittedOrder: boolean;
  liveState: string;
  workersAllowedToSubmit: boolean;
  liveTradingEnabled: boolean;
  submitTimeChecksRerunLater: boolean;
  noSubmitControlPresent: boolean;
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

function formatHandoffStatus(status: ManualPaperSubmitHandoffStatus): string {
  if (status === "handoff_ready_for_future_manual_step") return "ready for future manual handoff";
  if (status === "dry_run_required") return "dry-run required first";
  if (status === "handoff_required") return "handoff review required";
  if (status === "readiness_required") return "readiness review required";
  return formatStatus(status);
}

function formatAuditPackageStatus(status: ManualPaperSubmitAuditPackageStatus): string {
  if (status === "package_ready_for_future_manual_review") return "package ready for future manual review";
  if (status === "dry_run_required") return "dry-run required first";
  if (status === "readiness_required") return "readiness review required";
  if (status === "handoff_required") return "handoff review required";
  return formatStatus(status);
}

function formatApprovalPackageStatus(status: ManualPaperSubmitApprovalPackageStatus): string {
  if (status === "approval_package_ready_for_future_manual_review") {
    return "approval package ready for future manual review";
  }
  if (status === "dry_run_required") return "dry-run required first";
  if (status === "readiness_required") return "readiness review required";
  if (status === "handoff_required") return "handoff review required";
  if (status === "audit_package_required") return "audit package required first";
  if (status === "approval_not_available") return "approval not available";
  return formatStatus(status);
}

function formatPreflightContractStatus(status: ManualPaperSubmitPreflightContractStatus): string {
  if (status === "preflight_contract_ready_for_future_manual_step") {
    return "preflight contract ready for future manual step";
  }
  if (status === "dry_run_required") return "dry-run required first";
  if (status === "readiness_required") return "readiness review required";
  if (status === "handoff_required") return "handoff review required";
  if (status === "audit_package_required") return "audit package required first";
  if (status === "approval_package_required") return "approval package required first";
  if (status === "preflight_not_available") return "preflight not available";
  return formatStatus(status);
}

function formatFutureManualSubmitDesignReviewStatus(
  status: FutureManualSubmitDesignReviewStatus,
): string {
  if (status === "design_only_not_enabled") return "design only, not enabled";
  return formatStatus(status);
}

function formatGuardedSubmitDecisionReviewStatus(
  status: GuardedSubmitDecisionReviewStatus,
): string {
  if (status === "ready_for_future_decision_review") return "ready for future decision review";
  if (status === "dry_run_required") return "dry-run required first";
  if (status === "approval_required") return "approval package required first";
  if (status === "preflight_contract_required") return "preflight contract required first";
  if (status === "design_review_required") return "design review required first";
  return formatStatus(status);
}

function formatGuardedOperatorActionReviewStatus(
  status: GuardedOperatorActionReviewStatus,
): string {
  if (status === "action_review_ready_for_future_manual_step") {
    return "action review ready for future manual step";
  }
  if (status === "dry_run_required") return "dry-run required first";
  if (status === "readiness_required") return "readiness review required first";
  if (status === "handoff_required") return "handoff review required first";
  if (status === "audit_package_required") return "audit package required first";
  if (status === "approval_package_required") return "approval package required first";
  if (status === "preflight_contract_required") return "preflight contract required first";
  if (status === "design_review_required") return "design review required first";
  if (status === "submit_decision_review_required") return "submit-decision review required first";
  if (status === "action_not_available") return "action not available";
  return formatStatus(status);
}

function formatFinalGuardedSubmitInteractionSpecStatus(
  status: FinalGuardedSubmitInteractionSpecStatus,
): string {
  if (status === "interaction_spec_ready_for_future_phase") {
    return "interaction spec ready for future phase";
  }
  if (status === "dry_run_required") return "dry-run required first";
  if (status === "operator_action_review_required") return "operator action review required first";
  return formatStatus(status);
}

function formatRequiredFutureRoute(route: string | null): string {
  return route ?? "not available";
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
  const reviewChain = deriveManualPaperSubmitReviewChain(result, preview, symbol);
  const {
    readiness,
    handoff,
    auditPackage,
    approvalPackage,
    preflightContract,
    futureManualSubmitDesignReview,
    submitDecisionReview,
    operatorActionReview,
    finalInteractionSpec: finalGuardedSubmitInteractionSpec,
  } = reviewChain;

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

          {handoff ? (
            <section
              className={styles.subpanel}
              data-testid={`recommendation-submit-handoff-${recommendationId}`}
              aria-label={`Manual paper submit handoff review for ${symbol}`}
            >
              <div className={styles.previewHeader}>
                <div className={styles.titleWrap}>
                  <p className={styles.eyebrow}>Handoff review</p>
                  <h5 className={styles.previewTitle}>Manual paper submit handoff review</h5>
                  <p className={styles.subtitle}>
                    Handoff review only, no order submitted. Future manual paper submit would still use guarded /broker/orders and no submit button is available here.
                  </p>
                </div>
                <span
                  className={`${styles.statusPill} ${statusClassName(handoff.status)}`}
                  data-testid={`recommendation-submit-handoff-status-${recommendationId}`}
                >
                  {formatHandoffStatus(handoff.status)}
                </span>
              </div>

              <div
                className={`${styles.summary} ${summaryClassName(handoff.status)}`}
                data-testid={`recommendation-submit-handoff-summary-${recommendationId}`}
              >
                <p className={styles.summaryTitle}>{handoff.title}</p>
                <p className={styles.summaryText}>{handoff.body}</p>
              </div>

              <div className={styles.grid}>
                <div className={styles.field}>
                  <span className={styles.label}>Next required action</span>
                  <span className={styles.value}>{formatStatus(handoff.nextRequiredAction)}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>Future manual submit route</span>
                  <span className={`${styles.value} ${styles.mono}`}>{formatRequiredFutureRoute(handoff.futureManualSubmitRoute)}</span>
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
                  <span className={styles.label}>Workers allowed to submit</span>
                  <span className={styles.value}>{preview?.workers_allowed_to_submit ?? result.workers_allowed_to_submit ? "yes" : "no"}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>No order submitted</span>
                  <span className={styles.value}>{result.is_submit === false && (preview?.is_submit ?? false) === false ? "yes" : "no"}</span>
                </div>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Handoff reasons</h5>
                <ul className={styles.list}>
                  {handoff.reasons.map((reason) => (
                    <li key={reason.code}>
                      {reason.label}: {reason.satisfied ? "yes" : "no"}
                    </li>
                  ))}
                </ul>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Required future payload fields</h5>
                <ul className={styles.list}>
                  {handoff.requiredFuturePayloadFields.map((field) => (
                    <li key={field.code}>
                      {field.label}: {field.required ? "required" : "optional"} · {field.satisfied ? "ready" : "missing"} · {field.value}. {field.detail}
                    </li>
                  ))}
                </ul>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Safety gates that still run at submit time</h5>
                <ul className={styles.list}>
                  {handoff.safetyGates.map((gate) => (
                    <li key={gate}>{gate}</li>
                  ))}
                </ul>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Blocked reasons</h5>
                {handoff.blockedReasons.length === 0 ? (
                  <p className={styles.emptyText}>No blocked reasons surfaced in the current handoff review.</p>
                ) : (
                  <ul className={styles.list}>
                    {handoff.blockedReasons.map((entry) => (
                      <li key={entry}>{entry}</li>
                    ))}
                  </ul>
                )}
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Missing context</h5>
                {handoff.missingData.length === 0 ? (
                  <p className={styles.emptyText}>No missing context surfaced in the current handoff review.</p>
                ) : (
                  <ul className={styles.list}>
                    {handoff.missingData.map((entry) => (
                      <li key={entry}>{entry}</li>
                    ))}
                  </ul>
                )}
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Warnings</h5>
                {handoff.warnings.length === 0 ? (
                  <p className={styles.emptyText}>No warnings surfaced in the current handoff review.</p>
                ) : (
                  <ul className={styles.list}>
                    {handoff.warnings.map((entry) => (
                      <li key={entry}>{entry}</li>
                    ))}
                  </ul>
                )}
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Next required action detail</h5>
                <p className={styles.emptyText}>{handoff.nextRequiredActionDetail}</p>
              </div>

              <p className={styles.helperText}>
                Handoff review only, no order submitted. No submit button is available here, no /broker/orders call was made from this surface, live trading remains locked, and workers cannot submit.
              </p>
            </section>
          ) : null}

          {auditPackage && readiness && handoff ? (
            <section
              className={styles.subpanel}
              data-testid={`recommendation-submit-audit-package-${recommendationId}`}
              aria-label={`Manual paper submit audit package for ${symbol}`}
            >
              <div className={styles.previewHeader}>
                <div className={styles.titleWrap}>
                  <p className={styles.eyebrow}>Audit package</p>
                  <h5 className={styles.previewTitle}>Manual paper submit audit package</h5>
                  <p className={styles.subtitle}>
                    Audit package only, no order submitted. Use this consolidated review package before any future manual IBKR paper submit handoff. No submit button is available here.
                  </p>
                </div>
                <span
                  className={`${styles.statusPill} ${statusClassName(auditPackage.status)}`}
                  data-testid={`recommendation-submit-audit-package-status-${recommendationId}`}
                >
                  {formatAuditPackageStatus(auditPackage.status)}
                </span>
              </div>

              <div
                className={`${styles.summary} ${summaryClassName(auditPackage.status)}`}
                data-testid={`recommendation-submit-audit-package-summary-${recommendationId}`}
              >
                <p className={styles.summaryTitle}>{auditPackage.title}</p>
                <p className={styles.summaryText}>{auditPackage.body}</p>
              </div>

              <div className={styles.grid}>
                <div className={styles.field}>
                  <span className={styles.label}>Recommendation ID</span>
                  <span className={`${styles.value} ${styles.mono}`}>{result.recommendation_id}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>Asset / symbol</span>
                  <span className={styles.value}>{result.ticker ?? symbol}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>Side</span>
                  <span className={styles.value}>{result.side ?? "unknown"}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>Quantity / notional</span>
                  <span className={styles.value}>
                    {result.quantity !== null
                      ? `${formatMaybeNumber(result.quantity)} shares`
                      : (preview?.estimated_notional ?? null) !== null
                        ? formatMaybeNumber(preview?.estimated_notional ?? null)
                        : "unknown"}
                  </span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>Order type</span>
                  <span className={styles.value}>{result.order_type ?? "unknown"}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>Route-check result</span>
                  <span className={styles.value}>{formatStatus(result.route_check_status)}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>Dry-run preview result</span>
                  <span className={styles.value}>{preview ? formatStatus(preview.dry_run_status) : "not run"}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>Readiness review result</span>
                  <span className={styles.value}>{formatReadinessStatus(readiness.status)}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>Handoff review result</span>
                  <span className={styles.value}>{formatHandoffStatus(handoff.status)}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>Broker mode</span>
                  <span className={styles.value}>{preview?.broker_mode.mode ?? result.broker_mode.mode}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>Resolved future route</span>
                  <span className={`${styles.value} ${styles.mono}`}>{formatRequiredFutureRoute(auditPackage.futureManualSubmitRoute)}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>Live-lock state</span>
                  <span className={styles.value}>{preview?.live_state ?? result.live_state}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>Workers allowed to submit</span>
                  <span className={styles.value}>{preview?.workers_allowed_to_submit ?? result.workers_allowed_to_submit ? "yes" : "no"}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>Preflight / would block</span>
                  <span className={styles.value}>{preview ? `${preview.preflight_decision?.decision_status ?? "not evaluated"} · would block ${preview.would_block ? "yes" : "no"}` : `not evaluated · would block ${result.would_block ? "yes" : "no"}`}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>No order submitted</span>
                  <span className={styles.value}>{result.is_submit === false && (preview?.is_submit ?? false) === false ? "yes" : "no"}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>Next required action</span>
                  <span className={styles.value}>{formatStatus(auditPackage.nextRequiredAction)}</span>
                </div>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Evidence checklist</h5>
                <ul className={styles.list}>
                  {auditPackage.evidenceChecklist.map((item) => (
                    <li key={item.code}>
                      {item.label}: {item.satisfied ? "yes" : "no"}. {item.detail}
                    </li>
                  ))}
                </ul>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Source labels</h5>
                <ul className={styles.list}>
                  {auditPackage.sourceLabels.map((label) => (
                    <li key={label.code}>
                      {label.label}: {label.value}
                    </li>
                  ))}
                </ul>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Audit and decision references</h5>
                <ul className={styles.list}>
                  {auditPackage.decisionReferences.map((reference) => (
                    <li key={reference.code}>
                      {reference.label}: {reference.value}. {reference.detail}
                    </li>
                  ))}
                </ul>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Future /broker/orders payload preview fields</h5>
                <ul className={styles.list}>
                  {auditPackage.futurePayloadPreviewFields.map((field) => (
                    <li key={field.code}>
                      {field.label}: {field.required ? "required" : "optional"} · {field.satisfied ? "ready" : "missing"} · {field.value}. {field.detail}
                    </li>
                  ))}
                </ul>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Missing payload fields</h5>
                {auditPackage.missingPayloadFields.length === 0 ? (
                  <p className={styles.emptyText}>No required payload fields are currently missing in this audit package.</p>
                ) : (
                  <ul className={styles.list}>
                    {auditPackage.missingPayloadFields.map((field) => (
                      <li key={field}>{field}</li>
                    ))}
                  </ul>
                )}
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Blocked reasons</h5>
                {auditPackage.blockedReasons.length === 0 ? (
                  <p className={styles.emptyText}>No blocked reasons surfaced in the current audit package.</p>
                ) : (
                  <ul className={styles.list}>
                    {auditPackage.blockedReasons.map((entry) => (
                      <li key={entry}>{entry}</li>
                    ))}
                  </ul>
                )}
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Missing context</h5>
                {auditPackage.missingData.length === 0 ? (
                  <p className={styles.emptyText}>No missing context surfaced in the current audit package.</p>
                ) : (
                  <ul className={styles.list}>
                    {auditPackage.missingData.map((entry) => (
                      <li key={entry}>{entry}</li>
                    ))}
                  </ul>
                )}
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Warnings</h5>
                {auditPackage.warnings.length === 0 ? (
                  <p className={styles.emptyText}>No warnings surfaced in the current audit package.</p>
                ) : (
                  <ul className={styles.list}>
                    {auditPackage.warnings.map((entry) => (
                      <li key={entry}>{entry}</li>
                    ))}
                  </ul>
                )}
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Next required action detail</h5>
                <p className={styles.emptyText}>{auditPackage.nextRequiredActionDetail}</p>
              </div>

              <p className={styles.helperText}>
                Audit package only, no order submitted. Future manual paper submit would still use guarded /broker/orders. No submit button is available here. Live trading remains locked. Workers cannot submit. Use this package for review before a future manual paper submit step.
              </p>
            </section>
          ) : null}

          {approvalPackage && auditPackage && readiness && handoff ? (
            <section
              className={styles.subpanel}
              data-testid={`recommendation-submit-approval-package-${recommendationId}`}
              aria-label={`Manual submit approval package for ${symbol}`}
            >
              <div className={styles.previewHeader}>
                <div className={styles.titleWrap}>
                  <p className={styles.eyebrow}>Approval package</p>
                  <h5 className={styles.previewTitle}>Manual submit approval package</h5>
                  <p className={styles.subtitle}>
                    Approval package only, no order submitted. Future manual paper submit would still require guarded /broker/orders, and no submit button is available here.
                  </p>
                </div>
                <span
                  className={`${styles.statusPill} ${statusClassName(approvalPackage.status)}`}
                  data-testid={`recommendation-submit-approval-package-status-${recommendationId}`}
                >
                  {formatApprovalPackageStatus(approvalPackage.status)}
                </span>
              </div>

              <div
                className={`${styles.summary} ${summaryClassName(approvalPackage.status)}`}
                data-testid={`recommendation-submit-approval-package-summary-${recommendationId}`}
              >
                <p className={styles.summaryTitle}>{approvalPackage.title}</p>
                <p className={styles.summaryText}>{approvalPackage.body}</p>
              </div>

              <div className={styles.grid}>
                <div className={styles.field}>
                  <span className={styles.label}>Recommendation ID</span>
                  <span className={`${styles.value} ${styles.mono}`}>{result.recommendation_id}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>Route-check result used</span>
                  <span className={styles.value}>{formatStatus(result.route_check_status)}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>Dry-run result used</span>
                  <span className={styles.value}>{preview ? formatStatus(preview.dry_run_status) : "not run"}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>Readiness result used</span>
                  <span className={styles.value}>{formatReadinessStatus(readiness.status)}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>Handoff result used</span>
                  <span className={styles.value}>{formatHandoffStatus(handoff.status)}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>Audit package result used</span>
                  <span className={styles.value}>{formatAuditPackageStatus(auditPackage.status)}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>Future manual submit route</span>
                  <span className={`${styles.value} ${styles.mono}`}>{formatRequiredFutureRoute(approvalPackage.futureManualSubmitRoute)}</span>
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
                  <span className={styles.label}>Workers allowed to submit</span>
                  <span className={styles.value}>{preview?.workers_allowed_to_submit ?? result.workers_allowed_to_submit ? "yes" : "no"}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>No order submitted</span>
                  <span className={styles.value}>{result.is_submit === false && (preview?.is_submit ?? false) === false ? "yes" : "no"}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>Approval only</span>
                  <span className={styles.value}>yes</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>Dry-run only</span>
                  <span className={styles.value}>{preview?.dry_run_only ?? false ? "yes" : "no"}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>Next required action</span>
                  <span className={styles.value}>{formatStatus(approvalPackage.nextRequiredAction)}</span>
                </div>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Approval and evidence checklist</h5>
                <ul className={styles.list}>
                  {approvalPackage.evidenceChecklist.map((item) => (
                    <li key={item.code}>
                      {item.label}: {item.satisfied ? "yes" : "no"}. {item.detail}
                    </li>
                  ))}
                </ul>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Future manual approval requirements</h5>
                <ul className={styles.list}>
                  {approvalPackage.futureManualApprovalRequirements.map((item) => (
                    <li key={item.code}>
                      {item.label}: {item.required ? "required later" : "not required"}. {item.detail}
                    </li>
                  ))}
                </ul>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Audit references</h5>
                <ul className={styles.list}>
                  {approvalPackage.auditReferences.map((reference) => (
                    <li key={reference.code}>
                      {reference.label}: {reference.value}. {reference.detail}
                    </li>
                  ))}
                </ul>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Final future payload preview</h5>
                <ul className={styles.list}>
                  {approvalPackage.futurePayloadPreviewFields.map((field) => (
                    <li key={field.code}>
                      {field.label}: {field.required ? "required" : "optional"} · {field.satisfied ? "ready" : "missing"} · {field.value}. {field.detail}
                    </li>
                  ))}
                </ul>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Missing payload fields</h5>
                {approvalPackage.missingPayloadFields.length === 0 ? (
                  <p className={styles.emptyText}>No required payload fields are currently missing in this approval package.</p>
                ) : (
                  <ul className={styles.list}>
                    {approvalPackage.missingPayloadFields.map((field) => (
                      <li key={field}>{field}</li>
                    ))}
                  </ul>
                )}
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Safety gates that would rerun at actual submit time</h5>
                <ul className={styles.list}>
                  {approvalPackage.safetyReruns.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Blocked reasons</h5>
                {approvalPackage.blockedReasons.length === 0 ? (
                  <p className={styles.emptyText}>No blocked reasons surfaced in the current approval package.</p>
                ) : (
                  <ul className={styles.list}>
                    {approvalPackage.blockedReasons.map((entry) => (
                      <li key={entry}>{entry}</li>
                    ))}
                  </ul>
                )}
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Missing context</h5>
                {approvalPackage.missingData.length === 0 ? (
                  <p className={styles.emptyText}>No missing context surfaced in the current approval package.</p>
                ) : (
                  <ul className={styles.list}>
                    {approvalPackage.missingData.map((entry) => (
                      <li key={entry}>{entry}</li>
                    ))}
                  </ul>
                )}
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Warnings</h5>
                {approvalPackage.warnings.length === 0 ? (
                  <p className={styles.emptyText}>No warnings surfaced in the current approval package.</p>
                ) : (
                  <ul className={styles.list}>
                    {approvalPackage.warnings.map((entry) => (
                      <li key={entry}>{entry}</li>
                    ))}
                  </ul>
                )}
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Next required action detail</h5>
                <p className={styles.emptyText}>{approvalPackage.nextRequiredActionDetail}</p>
              </div>

              <p className={styles.helperText}>
                Approval package only, no order submitted. Future manual paper submit would still require guarded /broker/orders. No submit button is available here. Submit-time preflight would rerun. Submit-time decision logging would be required. Live trading remains locked. Workers cannot submit.
              </p>
            </section>
          ) : null}

          {preflightContract && approvalPackage && auditPackage && readiness && handoff ? (
            <section
              className={styles.subpanel}
              data-testid={`recommendation-submit-preflight-contract-${recommendationId}`}
              aria-label={`Guarded manual paper submit preflight contract for ${symbol}`}
            >
              <div className={styles.previewHeader}>
                <div className={styles.titleWrap}>
                  <p className={styles.eyebrow}>Preflight contract</p>
                  <h5 className={styles.previewTitle}>Guarded manual paper submit preflight contract</h5>
                  <p className={styles.subtitle}>
                    Preflight contract only, no order submitted. Future manual paper submit would still require guarded /broker/orders, and no submit button is available here.
                  </p>
                </div>
                <span
                  className={`${styles.statusPill} ${statusClassName(preflightContract.status)}`}
                  data-testid={`recommendation-submit-preflight-contract-status-${recommendationId}`}
                >
                  {formatPreflightContractStatus(preflightContract.status)}
                </span>
              </div>

              <div
                className={`${styles.summary} ${summaryClassName(preflightContract.status)}`}
                data-testid={`recommendation-submit-preflight-contract-summary-${recommendationId}`}
              >
                <p className={styles.summaryTitle}>{preflightContract.title}</p>
                <p className={styles.summaryText}>{preflightContract.body}</p>
              </div>

              <div className={styles.grid}>
                <div className={styles.field}>
                  <span className={styles.label}>Recommendation ID</span>
                  <span className={`${styles.value} ${styles.mono}`}>{result.recommendation_id}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>Route-check result used</span>
                  <span className={styles.value}>{formatStatus(result.route_check_status)}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>Dry-run result used</span>
                  <span className={styles.value}>{preview ? formatStatus(preview.dry_run_status) : "not run"}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>Readiness result used</span>
                  <span className={styles.value}>{formatReadinessStatus(readiness.status)}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>Handoff result used</span>
                  <span className={styles.value}>{formatHandoffStatus(handoff.status)}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>Audit package result used</span>
                  <span className={styles.value}>{formatAuditPackageStatus(auditPackage.status)}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>Approval package result used</span>
                  <span className={styles.value}>{formatApprovalPackageStatus(approvalPackage.status)}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>Future manual submit route</span>
                  <span className={`${styles.value} ${styles.mono}`}>{formatRequiredFutureRoute(preflightContract.futureManualSubmitRoute)}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>Broker account mode</span>
                  <span className={styles.value}>{preflightContract.brokerAccountMode}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>Live state</span>
                  <span className={styles.value}>{preflightContract.liveState}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>Would block</span>
                  <span className={styles.value}>{preflightContract.wouldBlock ? "yes" : "no"}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>Submitted order</span>
                  <span className={styles.value}>{preflightContract.submittedOrder ? "yes" : "no"}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>Workers allowed to submit</span>
                  <span className={styles.value}>{preflightContract.workersAllowedToSubmit ? "yes" : "no"}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>Live trading enabled</span>
                  <span className={styles.value}>{preflightContract.liveTradingEnabled ? "yes" : "no"}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>Is canonical paper</span>
                  <span className={styles.value}>{preflightContract.isCanonicalPaper ? "yes" : "no"}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>Dry-run only</span>
                  <span className={styles.value}>{preflightContract.dryRunOnly ? "yes" : "no"}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>Approval only</span>
                  <span className={styles.value}>{preflightContract.approvalOnly ? "yes" : "no"}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>Preflight contract only</span>
                  <span className={styles.value}>{preflightContract.preflightContractOnly ? "yes" : "no"}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>Next required action</span>
                  <span className={styles.value}>{formatStatus(preflightContract.nextRequiredAction)}</span>
                </div>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Preflight contract checklist</h5>
                <ul className={styles.list}>
                  {preflightContract.evidenceChecklist.map((item) => (
                    <li key={item.code}>
                      {item.label}: {item.satisfied ? "yes" : "no"}. {item.detail}
                    </li>
                  ))}
                </ul>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Submit-time rerun requirements</h5>
                <ul className={styles.list}>
                  {preflightContract.submitTimeRerunRequirements.map((item) => (
                    <li key={item.code}>
                      {item.label}: {item.required ? "required later" : "not required"}. {item.detail}
                    </li>
                  ))}
                </ul>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Operator confirmations required later</h5>
                <ul className={styles.list}>
                  {preflightContract.operatorConfirmations.map((item) => (
                    <li key={item.code}>
                      {item.label}: {item.required ? "required later" : "not required"}. {item.detail}
                    </li>
                  ))}
                </ul>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Final payload review</h5>
                <ul className={styles.list}>
                  {preflightContract.finalPayloadReviewFields.map((field) => (
                    <li key={field.code}>
                      {field.label}: {field.required ? "required" : "optional"} · {field.satisfied ? "ready" : "missing"} · {field.value}. {field.detail}
                    </li>
                  ))}
                </ul>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Source label rechecks</h5>
                <ul className={styles.list}>
                  {preflightContract.sourceLabelRechecks.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Stale-data checks</h5>
                {preflightContract.staleDataChecks.length === 0 ? (
                  <p className={styles.emptyText}>No stale-data checks are currently surfaced by the preflight contract.</p>
                ) : (
                  <ul className={styles.list}>
                    {preflightContract.staleDataChecks.map((entry) => (
                      <li key={entry}>{entry}</li>
                    ))}
                  </ul>
                )}
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Decision logging requirements</h5>
                <ul className={styles.list}>
                  {preflightContract.decisionLoggingRequirements.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Missing payload fields</h5>
                {preflightContract.missingPayloadFields.length === 0 ? (
                  <p className={styles.emptyText}>No required payload fields are currently missing in this preflight contract.</p>
                ) : (
                  <ul className={styles.list}>
                    {preflightContract.missingPayloadFields.map((field) => (
                      <li key={field}>{field}</li>
                    ))}
                  </ul>
                )}
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Blocked reasons</h5>
                {preflightContract.blockedReasons.length === 0 ? (
                  <p className={styles.emptyText}>No blocked reasons surfaced in the current preflight contract.</p>
                ) : (
                  <ul className={styles.list}>
                    {preflightContract.blockedReasons.map((entry) => (
                      <li key={entry}>{entry}</li>
                    ))}
                  </ul>
                )}
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Missing context</h5>
                {preflightContract.missingData.length === 0 ? (
                  <p className={styles.emptyText}>No missing context surfaced in the current preflight contract.</p>
                ) : (
                  <ul className={styles.list}>
                    {preflightContract.missingData.map((entry) => (
                      <li key={entry}>{entry}</li>
                    ))}
                  </ul>
                )}
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Warnings</h5>
                {preflightContract.warnings.length === 0 ? (
                  <p className={styles.emptyText}>No warnings surfaced in the current preflight contract.</p>
                ) : (
                  <ul className={styles.list}>
                    {preflightContract.warnings.map((entry) => (
                      <li key={entry}>{entry}</li>
                    ))}
                  </ul>
                )}
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Next required action detail</h5>
                <p className={styles.emptyText}>{preflightContract.nextRequiredActionDetail}</p>
              </div>

              <p className={styles.helperText}>
                Preflight contract only, no order submitted. Future manual paper submit would still require guarded /broker/orders. Submit-time preflight would rerun. Submit-time mode and risk checks would rerun. Submit-time decision logging would be required. No submit button is available here. Live trading remains locked. Workers cannot submit.
              </p>
            </section>
          ) : null}

          {futureManualSubmitDesignReview ? (
            <section
              className={styles.subpanel}
              data-testid={`recommendation-future-manual-submit-design-review-${recommendationId}`}
              aria-label={`Future manual submit design review for ${symbol}`}
            >
              <div className={styles.previewHeader}>
                <div className={styles.titleWrap}>
                  <p className={styles.eyebrow}>Design review</p>
                  <h5 className={styles.previewTitle}>Future manual submit design review</h5>
                  <p className={styles.subtitle}>
                    Design only, not enabled. This section documents the future guarded manual IBKR paper submit path without adding any submit control.
                  </p>
                </div>
                <span
                  className={`${styles.statusPill} ${styles.statusUnknown}`}
                  data-testid={`recommendation-future-manual-submit-design-review-status-${recommendationId}`}
                >
                  {formatFutureManualSubmitDesignReviewStatus(futureManualSubmitDesignReview.status)}
                </span>
              </div>

              <div
                className={`${styles.summary} ${styles.summaryUnknown}`}
                data-testid={`recommendation-future-manual-submit-design-review-summary-${recommendationId}`}
              >
                <p className={styles.summaryTitle}>{futureManualSubmitDesignReview.title}</p>
                <p className={styles.summaryText}>{futureManualSubmitDesignReview.body}</p>
              </div>

              <div className={styles.grid}>
                <div className={styles.field}>
                  <span className={styles.label}>Future submit route</span>
                  <span className={`${styles.value} ${styles.mono}`}>{futureManualSubmitDesignReview.futureSubmitRoute}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>Future submit status</span>
                  <span className={styles.value}>{futureManualSubmitDesignReview.status}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>Existing backend owner</span>
                  <span className={styles.value}>{futureManualSubmitDesignReview.existingBackendOwner}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>Future frontend surface</span>
                  <span className={styles.value}>{futureManualSubmitDesignReview.futureFrontendSurface}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>final_operator_confirmation_required</span>
                  <span className={styles.value}>{futureManualSubmitDesignReview.finalOperatorConfirmationRequired ? "true" : "false"}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>submit_time_preflight_rerun_required</span>
                  <span className={styles.value}>{futureManualSubmitDesignReview.submitTimePreflightRerunRequired ? "true" : "false"}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>submit_time_decision_persistence_required</span>
                  <span className={styles.value}>{futureManualSubmitDesignReview.submitTimeDecisionPersistenceRequired ? "true" : "false"}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>submit_time_live_lock_recheck_required</span>
                  <span className={styles.value}>{futureManualSubmitDesignReview.submitTimeLiveLockRecheckRequired ? "true" : "false"}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>submit_time_worker_submit_allowed</span>
                  <span className={styles.value}>{futureManualSubmitDesignReview.submitTimeWorkerSubmitAllowed ? "true" : "false"}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>submit_button_available</span>
                  <span className={styles.value}>{futureManualSubmitDesignReview.submitButtonAvailable ? "true" : "false"}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>order_submitted</span>
                  <span className={styles.value}>{futureManualSubmitDesignReview.orderSubmitted ? "true" : "false"}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>enabled_in_this_phase</span>
                  <span className={styles.value}>{futureManualSubmitDesignReview.enabledInThisPhase ? "true" : "false"}</span>
                </div>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Submit-time checks would rerun</h5>
                <ul className={styles.list}>
                  {futureManualSubmitDesignReview.submitTimeChecks.map((entry) => (
                    <li key={entry.code}>
                      {entry.label}: {entry.value}. {entry.detail}
                    </li>
                  ))}
                </ul>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Final operator confirmations required later</h5>
                <ul className={styles.list}>
                  {futureManualSubmitDesignReview.finalOperatorConfirmations.map((entry) => (
                    <li key={entry.code}>
                      {entry.label}: {entry.value}. {entry.detail}
                    </li>
                  ))}
                </ul>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Decision logging would be required</h5>
                <ul className={styles.list}>
                  {futureManualSubmitDesignReview.decisionRecords.map((entry) => (
                    <li key={entry.code}>
                      {entry.label}: {entry.value}. {entry.detail}
                    </li>
                  ))}
                </ul>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Locked payload fields to review later</h5>
                <ul className={styles.list}>
                  {futureManualSubmitDesignReview.lockedPayloadFields.map((entry) => (
                    <li key={entry.code}>
                      {entry.label}: {entry.value}. {entry.detail}
                    </li>
                  ))}
                </ul>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>States that must block future submit</h5>
                <ul className={styles.list}>
                  {futureManualSubmitDesignReview.blockStates.map((entry) => (
                    <li key={entry}>{entry}</li>
                  ))}
                </ul>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Tests required before any later enablement</h5>
                <ul className={styles.list}>
                  {futureManualSubmitDesignReview.requiredTestsBeforeEnablement.map((entry) => (
                    <li key={entry}>{entry}</li>
                  ))}
                </ul>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Intentionally not implemented in this phase</h5>
                <ul className={styles.list}>
                  {futureManualSubmitDesignReview.intentionallyNotImplemented.map((entry) => (
                    <li key={entry}>{entry}</li>
                  ))}
                </ul>
              </div>

              <p className={styles.helperText}>
                Design only, not enabled. No submit button available. No /broker/orders call was made from this panel. Decision logging would be required later. Submit-time checks would rerun. Live remains locked. Workers cannot submit.
              </p>
            </section>
          ) : null}

          {submitDecisionReview ? (
            <section
              className={styles.subpanel}
              data-testid={`recommendation-submit-decision-review-${recommendationId}`}
              aria-label={`Guarded operator submit-decision review for ${symbol}`}
            >
              <div className={styles.previewHeader}>
                <div className={styles.titleWrap}>
                  <p className={styles.eyebrow}>Submit-decision review</p>
                  <h5 className={styles.previewTitle}>Guarded operator submit-decision review</h5>
                  <p className={styles.subtitle}>
                    Submit-decision review only, no decision written. This section shows what the existing guarded manual paper submit path would need to persist later without adding any submit control.
                  </p>
                </div>
                <span
                  className={`${styles.statusPill} ${statusClassName(submitDecisionReview.status)}`}
                  data-testid={`recommendation-submit-decision-review-status-${recommendationId}`}
                >
                  {formatGuardedSubmitDecisionReviewStatus(submitDecisionReview.status)}
                </span>
              </div>

              <div
                className={`${styles.summary} ${summaryClassName(submitDecisionReview.status)}`}
                data-testid={`recommendation-submit-decision-review-summary-${recommendationId}`}
              >
                <p className={styles.summaryTitle}>{submitDecisionReview.title}</p>
                <p className={styles.summaryText}>{submitDecisionReview.body}</p>
              </div>

              <div className={styles.grid}>
                <div className={styles.field}>
                  <span className={styles.label}>submit_decision_review_status</span>
                  <span className={styles.value}>{submitDecisionReview.status}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>decision persistence owner</span>
                  <span className={styles.value}>{submitDecisionReview.decisionPersistenceOwner}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>future submit route</span>
                  <span className={`${styles.value} ${styles.mono}`}>{formatRequiredFutureRoute(submitDecisionReview.futureSubmitRoute)}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>future source</span>
                  <span className={styles.value}>{submitDecisionReview.futureDecisionSource}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>future_order_correlation_id</span>
                  <span className={`${styles.value} ${styles.mono}`}>{submitDecisionReview.futureOrderCorrelationId}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>dry_run_decision_reference</span>
                  <span className={styles.value}>{submitDecisionReview.dryRunDecisionReference}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>account_mode</span>
                  <span className={styles.value}>{submitDecisionReview.accountMode}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>execution_source</span>
                  <span className={styles.value}>{submitDecisionReview.executionSource}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>live_state</span>
                  <span className={styles.value}>{submitDecisionReview.liveState}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>workers_allowed_to_submit</span>
                  <span className={styles.value}>{submitDecisionReview.workersAllowedToSubmit ? "true" : "false"}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>live_trading_enabled</span>
                  <span className={styles.value}>{submitDecisionReview.liveTradingEnabled ? "true" : "false"}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>submitted_order</span>
                  <span className={styles.value}>{submitDecisionReview.submittedOrder ? "true" : "false"}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>decision_write_performed_now</span>
                  <span className={styles.value}>{submitDecisionReview.decisionWritePerformedNow ? "true" : "false"}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>review_only</span>
                  <span className={styles.value}>{submitDecisionReview.reviewOnly ? "true" : "false"}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>no_submit_control_present</span>
                  <span className={styles.value}>{submitDecisionReview.noSubmitControlPresent ? "true" : "false"}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>next required action</span>
                  <span className={styles.value}>{formatStatus(submitDecisionReview.nextRequiredAction)}</span>
                </div>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Decision evidence checklist</h5>
                <ul className={styles.list}>
                  {submitDecisionReview.evidenceChecklist.map((item) => (
                    <li key={item.code}>
                      {item.label}: {item.satisfied ? "yes" : "no"}. {item.detail}
                    </li>
                  ))}
                </ul>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Existing decision writers</h5>
                <ul className={styles.list}>
                  {submitDecisionReview.existingDecisionWriters.map((item) => (
                    <li key={item.code}>
                      {item.label}: {item.value}. {item.detail}
                    </li>
                  ))}
                </ul>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Existing decision readers</h5>
                <ul className={styles.list}>
                  {submitDecisionReview.existingDecisionReaders.map((item) => (
                    <li key={item.code}>
                      {item.label}: {item.value}. {item.detail}
                    </li>
                  ))}
                </ul>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Future decision records</h5>
                <ul className={styles.list}>
                  {submitDecisionReview.futureDecisionRecords.map((item) => (
                    <li key={item.code}>
                      {item.label}: {item.value}. {item.detail}
                    </li>
                  ))}
                </ul>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Persisted field checklist</h5>
                <ul className={styles.list}>
                  {submitDecisionReview.persistedFieldChecklist.map((item) => (
                    <li key={item.code}>
                      {item.label}: {item.value}. {item.detail}
                    </li>
                  ))}
                </ul>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Review evidence links</h5>
                <ul className={styles.list}>
                  {submitDecisionReview.reviewEvidenceLinks.map((item) => (
                    <li key={item.code}>
                      {item.label}: {item.value}. {item.detail}
                    </li>
                  ))}
                </ul>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Fail-closed rules</h5>
                <ul className={styles.list}>
                  {submitDecisionReview.failClosedRules.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Blocked reasons</h5>
                {submitDecisionReview.blockedReasons.length === 0 ? (
                  <p className={styles.emptyText}>No blocked reasons surfaced in the current submit-decision review.</p>
                ) : (
                  <ul className={styles.list}>
                    {submitDecisionReview.blockedReasons.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                )}
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Missing context</h5>
                {submitDecisionReview.missingData.length === 0 ? (
                  <p className={styles.emptyText}>No missing context surfaced in the current submit-decision review.</p>
                ) : (
                  <ul className={styles.list}>
                    {submitDecisionReview.missingData.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                )}
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Warnings</h5>
                {submitDecisionReview.warnings.length === 0 ? (
                  <p className={styles.emptyText}>No warnings surfaced in the current submit-decision review.</p>
                ) : (
                  <ul className={styles.list}>
                    {submitDecisionReview.warnings.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                )}
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Next required action detail</h5>
                <p className={styles.emptyText}>{submitDecisionReview.nextRequiredActionDetail}</p>
              </div>

              <p className={styles.helperText}>
                Submit-decision review only, no decision written. Future manual paper submit would persist decisions later on the existing guarded /broker/orders path. No submit button is available here. No order submitted. Live trading remains locked. Workers cannot submit.
              </p>
            </section>
          ) : null}

          {operatorActionReview ? (
            <section
              className={styles.subpanel}
              data-testid={`recommendation-operator-action-review-${recommendationId}`}
              aria-label={`Guarded operator action review for ${symbol}`}
            >
              <div className={styles.previewHeader}>
                <div className={styles.titleWrap}>
                  <p className={styles.eyebrow}>Operator action review</p>
                  <h5 className={styles.previewTitle}>Guarded operator action review</h5>
                  <p className={styles.subtitle}>
                    Action review only, no order submitted. This section shows the future guarded manual paper action, what still blocks it, and why no execution is available in this phase.
                  </p>
                </div>
                <span
                  className={`${styles.statusPill} ${statusClassName(operatorActionReview.status)}`}
                  data-testid={`recommendation-operator-action-review-status-${recommendationId}`}
                >
                  {formatGuardedOperatorActionReviewStatus(operatorActionReview.status)}
                </span>
              </div>

              <div
                className={`${styles.summary} ${summaryClassName(operatorActionReview.status)}`}
                data-testid={`recommendation-operator-action-review-summary-${recommendationId}`}
              >
                <p className={styles.summaryTitle}>{operatorActionReview.title}</p>
                <p className={styles.summaryText}>{operatorActionReview.body}</p>
              </div>

              <div className={styles.grid}>
                <div className={styles.field}>
                  <span className={styles.label}>operator_action_review_status</span>
                  <span className={styles.value}>{operatorActionReview.status}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>future_action_name</span>
                  <span className={styles.value}>{operatorActionReview.futureActionName}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>future_action_route</span>
                  <span className={`${styles.value} ${styles.mono}`}>{formatRequiredFutureRoute(operatorActionReview.futureActionRoute)}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>submitted_order</span>
                  <span className={styles.value}>{operatorActionReview.submittedOrder ? "true" : "false"}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>action_available_now</span>
                  <span className={styles.value}>{operatorActionReview.actionAvailableNow ? "true" : "false"}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>action_review_only</span>
                  <span className={styles.value}>{operatorActionReview.actionReviewOnly ? "true" : "false"}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>decision_write_performed_now</span>
                  <span className={styles.value}>{operatorActionReview.decisionWritePerformedNow ? "true" : "false"}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>live_state</span>
                  <span className={styles.value}>{operatorActionReview.liveState}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>workers_allowed_to_submit</span>
                  <span className={styles.value}>{operatorActionReview.workersAllowedToSubmit ? "true" : "false"}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>live_trading_enabled</span>
                  <span className={styles.value}>{operatorActionReview.liveTradingEnabled ? "true" : "false"}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>would_block</span>
                  <span className={styles.value}>{operatorActionReview.wouldBlock ? "true" : "false"}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>no_submit_control_present</span>
                  <span className={styles.value}>{operatorActionReview.noSubmitControlPresent ? "true" : "false"}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>next required action</span>
                  <span className={styles.value}>{formatStatus(operatorActionReview.nextRequiredAction)}</span>
                </div>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Action evidence checklist</h5>
                <ul className={styles.list}>
                  {operatorActionReview.evidenceChecklist.map((item) => (
                    <li key={item.code}>
                      {item.label}: {item.satisfied ? "yes" : "no"}. {item.detail}
                    </li>
                  ))}
                </ul>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Future action description</h5>
                <ul className={styles.list}>
                  {operatorActionReview.futureActionDescription.map((item) => (
                    <li key={item.code}>
                      {item.label}: {item.value}. {item.detail}
                    </li>
                  ))}
                </ul>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Final operator confirmations</h5>
                <ul className={styles.list}>
                  {operatorActionReview.finalOperatorConfirmations.map((item) => (
                    <li key={item.code}>
                      {item.label}: {item.value}. {item.detail}
                    </li>
                  ))}
                </ul>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Future /broker/orders payload preview fields</h5>
                <ul className={styles.list}>
                  {operatorActionReview.finalPayloadPreview.map((item) => (
                    <li key={item.code}>
                      {item.label}: {item.value}. {item.detail}
                    </li>
                  ))}
                </ul>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Submit-time checks that rerun later</h5>
                <ul className={styles.list}>
                  {operatorActionReview.submitTimeChecks.map((item) => (
                    <li key={item.code}>
                      {item.label}: {item.value}. {item.detail}
                    </li>
                  ))}
                </ul>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Future submit-decision records</h5>
                <ul className={styles.list}>
                  {operatorActionReview.futureDecisionRecords.map((item) => (
                    <li key={item.code}>
                      {item.label}: {item.value}. {item.detail}
                    </li>
                  ))}
                </ul>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>States keeping action unavailable</h5>
                <ul className={styles.list}>
                  {operatorActionReview.statesKeepingActionUnavailable.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Blocked reasons</h5>
                {operatorActionReview.blockedReasons.length === 0 ? (
                  <p className={styles.emptyText}>No blocked reasons surfaced in the current operator action review.</p>
                ) : (
                  <ul className={styles.list}>
                    {operatorActionReview.blockedReasons.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                )}
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Missing context</h5>
                {operatorActionReview.missingData.length === 0 ? (
                  <p className={styles.emptyText}>No missing context surfaced in the current operator action review.</p>
                ) : (
                  <ul className={styles.list}>
                    {operatorActionReview.missingData.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                )}
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Warnings</h5>
                {operatorActionReview.warnings.length === 0 ? (
                  <p className={styles.emptyText}>No warnings surfaced in the current operator action review.</p>
                ) : (
                  <ul className={styles.list}>
                    {operatorActionReview.warnings.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                )}
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Next required action detail</h5>
                <p className={styles.emptyText}>{operatorActionReview.nextRequiredActionDetail}</p>
              </div>

              <p className={styles.helperText}>
                Action review only, no order submitted. Future action is not enabled in this phase. Future manual paper submit would still use guarded /broker/orders. No submit button is available here. No decision is written now. Live trading remains locked. Workers cannot submit.
              </p>
            </section>
          ) : null}

          {finalGuardedSubmitInteractionSpec ? (
            <section
              className={styles.subpanel}
              data-testid={`recommendation-final-guarded-submit-interaction-spec-${recommendationId}`}
              aria-label={`Final guarded submit interaction spec for ${symbol}`}
            >
              <div className={styles.previewHeader}>
                <div className={styles.titleWrap}>
                  <p className={styles.eyebrow}>Submit interaction spec</p>
                  <h5 className={styles.previewTitle}>Final guarded operator submit interaction spec</h5>
                  <p className={styles.subtitle}>
                    Interaction spec only, no order submitted. This section shows exactly how a future guarded manual paper submit interaction would work while keeping action_available_now false in this phase.
                  </p>
                </div>
                <span
                  className={`${styles.statusPill} ${statusClassName(finalGuardedSubmitInteractionSpec.status)}`}
                  data-testid={`recommendation-final-guarded-submit-interaction-spec-status-${recommendationId}`}
                >
                  {formatFinalGuardedSubmitInteractionSpecStatus(finalGuardedSubmitInteractionSpec.status)}
                </span>
              </div>

              <div
                className={`${styles.summary} ${summaryClassName(finalGuardedSubmitInteractionSpec.status)}`}
                data-testid={`recommendation-final-guarded-submit-interaction-spec-summary-${recommendationId}`}
              >
                <p className={styles.summaryTitle}>{finalGuardedSubmitInteractionSpec.title}</p>
                <p className={styles.summaryText}>{finalGuardedSubmitInteractionSpec.body}</p>
              </div>

              <div className={styles.grid}>
                <div className={styles.field}>
                  <span className={styles.label}>final_guarded_submit_interaction_spec_status</span>
                  <span className={styles.value}>{finalGuardedSubmitInteractionSpec.status}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>future_interaction_name</span>
                  <span className={styles.value}>{finalGuardedSubmitInteractionSpec.futureInteractionName}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>future_interaction_route</span>
                  <span className={`${styles.value} ${styles.mono}`}>{formatRequiredFutureRoute(finalGuardedSubmitInteractionSpec.futureInteractionRoute)}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>action_available_now</span>
                  <span className={styles.value}>{finalGuardedSubmitInteractionSpec.actionAvailableNow ? "true" : "false"}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>interaction_spec_review_only</span>
                  <span className={styles.value}>{finalGuardedSubmitInteractionSpec.interactionSpecReviewOnly ? "true" : "false"}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>decision_write_performed_now</span>
                  <span className={styles.value}>{finalGuardedSubmitInteractionSpec.decisionWritePerformedNow ? "true" : "false"}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>submitted_order</span>
                  <span className={styles.value}>{finalGuardedSubmitInteractionSpec.submittedOrder ? "true" : "false"}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>live_state</span>
                  <span className={styles.value}>{finalGuardedSubmitInteractionSpec.liveState}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>workers_allowed_to_submit</span>
                  <span className={styles.value}>{finalGuardedSubmitInteractionSpec.workersAllowedToSubmit ? "true" : "false"}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>live_trading_enabled</span>
                  <span className={styles.value}>{finalGuardedSubmitInteractionSpec.liveTradingEnabled ? "true" : "false"}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>submit_time_checks_rerun_later</span>
                  <span className={styles.value}>{finalGuardedSubmitInteractionSpec.submitTimeChecksRerunLater ? "true" : "false"}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>no_submit_control_present</span>
                  <span className={styles.value}>{finalGuardedSubmitInteractionSpec.noSubmitControlPresent ? "true" : "false"}</span>
                </div>
                <div className={styles.field}>
                  <span className={styles.label}>next required action</span>
                  <span className={styles.value}>{formatStatus(finalGuardedSubmitInteractionSpec.nextRequiredAction)}</span>
                </div>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Interaction evidence checklist</h5>
                <ul className={styles.list}>
                  {finalGuardedSubmitInteractionSpec.evidenceChecklist.map((item) => (
                    <li key={item.code}>
                      {item.label}: {item.satisfied ? "yes" : "no"}. {item.detail}
                    </li>
                  ))}
                </ul>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Future interaction contract</h5>
                <ul className={styles.list}>
                  {finalGuardedSubmitInteractionSpec.futureInteractionContract.map((item) => (
                    <li key={item.code}>
                      {item.label}: {item.value}. {item.detail}
                    </li>
                  ))}
                </ul>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Final operator confirmations</h5>
                <ul className={styles.list}>
                  {finalGuardedSubmitInteractionSpec.finalOperatorConfirmations.map((item) => (
                    <li key={item.code}>
                      {item.label}: {item.value}. {item.detail}
                    </li>
                  ))}
                </ul>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Future /broker/orders payload preview fields</h5>
                <ul className={styles.list}>
                  {finalGuardedSubmitInteractionSpec.finalPayloadPreview.map((item) => (
                    <li key={item.code}>
                      {item.label}: {item.value}. {item.detail}
                    </li>
                  ))}
                </ul>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Submit-time checks that rerun later</h5>
                <ul className={styles.list}>
                  {finalGuardedSubmitInteractionSpec.submitTimeChecks.map((item) => (
                    <li key={item.code}>
                      {item.label}: {item.value}. {item.detail}
                    </li>
                  ))}
                </ul>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Future submit-decision records</h5>
                <ul className={styles.list}>
                  {finalGuardedSubmitInteractionSpec.futureDecisionRecords.map((item) => (
                    <li key={item.code}>
                      {item.label}: {item.value}. {item.detail}
                    </li>
                  ))}
                </ul>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Later interaction sequence</h5>
                <ul className={styles.list}>
                  {finalGuardedSubmitInteractionSpec.laterInteractionSequence.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>States keeping interaction read-only</h5>
                <ul className={styles.list}>
                  {finalGuardedSubmitInteractionSpec.statesKeepingInteractionReadOnly.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>

              <div className={styles.navLinks}>
                <Link
                  href={buildManualConfirmationHref(result.recommendation_id, result.ticker ?? symbol)}
                  className={styles.linkPill}
                >
                  Manual IBKR paper submit confirmation
                </Link>
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Blocked reasons</h5>
                {finalGuardedSubmitInteractionSpec.blockedReasons.length === 0 ? (
                  <p className={styles.emptyText}>No blocked reasons surfaced in the current final interaction spec.</p>
                ) : (
                  <ul className={styles.list}>
                    {finalGuardedSubmitInteractionSpec.blockedReasons.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                )}
              </div>
                                Interaction spec only, no order submitted. Future manual paper submit would still use guarded /broker/orders. Open the dedicated confirmation surface for the design-only final confirmation layout. No submit button is available here. No decision is written now. Live trading remains locked. Workers cannot submit.
              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Missing context</h5>
                {finalGuardedSubmitInteractionSpec.missingData.length === 0 ? (
                  <p className={styles.emptyText}>No missing context surfaced in the current final interaction spec.</p>
                ) : (
                  <ul className={styles.list}>
                    {finalGuardedSubmitInteractionSpec.missingData.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                )}
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Warnings</h5>
                {finalGuardedSubmitInteractionSpec.warnings.length === 0 ? (
                  <p className={styles.emptyText}>No warnings surfaced in the current final interaction spec.</p>
                ) : (
                  <ul className={styles.list}>
                    {finalGuardedSubmitInteractionSpec.warnings.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                )}
              </div>

              <div className={styles.listBlock}>
                <h5 className={styles.listTitle}>Next required action detail</h5>
                <p className={styles.emptyText}>{finalGuardedSubmitInteractionSpec.nextRequiredActionDetail}</p>
              </div>

              <p className={styles.helperText}>
                Interaction spec only, no order submitted. Future manual paper submit would still use guarded /broker/orders only when safe. No submit button is available here. No /broker/orders call is made from this cockpit surface. No decision is written now. Submit-time checks would rerun later. Live trading remains locked. Workers cannot submit.
              </p>
            </section>
          ) : null}
        </>
      ) : null}
    </section>
  );
}