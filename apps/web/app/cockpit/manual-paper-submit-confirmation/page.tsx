"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

import {
  getPaperRecommendationRouteCheck,
  previewPaperRecommendationBrokerDryRun,
  type PaperRecommendationBrokerDryRunPreview,
  type PaperRecommendationRouteCheck,
} from "../../../lib/api/paperRecommendations";
import {
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
  const [routeCheck, setRouteCheck] = useState<PaperRecommendationRouteCheck | null>(null);
  const [dryRunPreview, setDryRunPreview] = useState<PaperRecommendationBrokerDryRunPreview | null>(null);

  useEffect(() => {
    if (!recommendationId) {
      setRouteCheck(null);
      setDryRunPreview(null);
      setError(null);
      return;
    }

    const activeRecommendationId = recommendationId;

    let cancelled = false;

    async function load(): Promise<void> {
      setLoading(true);
      setError(null);

      try {
        const nextRouteCheck = await getPaperRecommendationRouteCheck(activeRecommendationId);
        if (cancelled) return;
        setRouteCheck(nextRouteCheck);

        if (nextRouteCheck.route_check_status === "eligible") {
          const nextDryRunPreview = await previewPaperRecommendationBrokerDryRun(activeRecommendationId);
          if (cancelled) return;
          setDryRunPreview(nextDryRunPreview);
        } else {
          setDryRunPreview(null);
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

  return (
    <main
      className={styles.page}
      data-testid="cockpit-manual-paper-submit-confirmation-page"
    >
      <div className={styles.container}>
        <header className={styles.header}>
          <div className={styles.titleWrap}>
            <p className={styles.eyebrow}>Design only, not enabled</p>
            <h1 className={styles.title}>Manual IBKR paper submit confirmation</h1>
            <p className={styles.subtitle}>
              Paper submit, final confirmation required. This surface previews a future dedicated guarded confirmation step without adding any executable submit control.
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
            <h2 className={styles.heroTitle}>design_only_not_enabled</h2>
            <p className={styles.heroSubtitle}>
              No order has been submitted. No live trading path has been enabled. No worker authority has been expanded.
            </p>
          </div>
          <div className={styles.heroMeta}>
            <span className={styles.statusPill}>Paper only</span>
            <span className={styles.statusPill}>No live trading</span>
          </div>
        </section>

        <div className={styles.banner} data-testid="cockpit-manual-paper-submit-confirmation-paper-banner">
          <strong>Paper mode only.</strong> This page is read-only and non-executable. It must not call <span className={styles.mono}>/broker/orders</span> and must not submit any order in this phase.
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
            <div className={styles.field}><span className={styles.label}>confirmation_surface_status</span><span className={styles.value}>design_only_not_enabled</span></div>
            <div className={styles.field}><span className={styles.label}>submit_enabled_now</span><span className={styles.value}>false</span></div>
            <div className={styles.field}><span className={styles.label}>order_submitted</span><span className={styles.value}>false</span></div>
            <div className={styles.field}><span className={styles.label}>live_trading_enabled</span><span className={styles.value}>{liveTradingEnabled ? "true" : "false"}</span></div>
            <div className={styles.field}><span className={styles.label}>workers_allowed_to_submit</span><span className={styles.value}>{workersAllowedToSubmit ? "true" : "false"}</span></div>
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
            This is a review-only preview of what a later guarded paper confirmation surface would pass to the existing submit seam. No payload is posted in this phase.
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

        <section className={styles.sectionCard} data-testid="cockpit-manual-paper-submit-confirmation-disabled-placeholder">
          <h2 className={styles.sectionTitle}>Disabled placeholder</h2>
          <p className={styles.sectionSubtitle}>
            Not enabled in this phase. This placeholder is intentionally disabled and has no click handler, no submit path, and no broker call.
          </p>
          <div className={styles.placeholderRow}>
            <button
              type="button"
              disabled
              aria-disabled="true"
              className={styles.disabledButton}
              data-testid="manual-paper-submit-disabled-button"
            >
              Submit not enabled in this phase
            </button>
            <Link href="/cockpit/in-flight-adjustments" className={styles.linkPill}>
              Cancel / return to review
            </Link>
          </div>
        </section>
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