import type {
  PaperRecommendationBrokerDryRunPreview,
  PaperRecommendationRouteCheck,
} from "./api/paperRecommendations";

export type ManualPaperSubmitReadinessStatus =
  | "ready_for_future_manual_paper_submit"
  | "blocked"
  | "missing_context"
  | "dry_run_required"
  | "unknown";

export type ManualPaperSubmitReadinessReason = {
  code: string;
  label: string;
  satisfied: boolean;
};

export type ManualPaperSubmitReadiness = {
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

export type ManualPaperSubmitHandoffStatus =
  | "handoff_ready_for_future_manual_step"
  | "blocked"
  | "missing_context"
  | "dry_run_required"
  | "handoff_required"
  | "readiness_required"
  | "unknown";

export type ManualPaperSubmitHandoffReason = {
  code: string;
  label: string;
  satisfied: boolean;
};

export type ManualPaperSubmitHandoffPayloadField = {
  code: string;
  label: string;
  required: boolean;
  satisfied: boolean;
  value: string;
  detail: string;
};

export type ManualPaperSubmitHandoffReview = {
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

export type ManualPaperSubmitAuditPackageStatus =
  | "package_ready_for_future_manual_review"
  | "blocked"
  | "missing_context"
  | "dry_run_required"
  | "readiness_required"
  | "handoff_required"
  | "unknown";

export type ManualPaperSubmitAuditChecklistItem = {
  code: string;
  label: string;
  satisfied: boolean;
  detail: string;
};

export type ManualPaperSubmitAuditReference = {
  code: string;
  label: string;
  available: boolean;
  value: string;
  detail: string;
};

export type ManualPaperSubmitAuditSourceLabel = {
  code: string;
  label: string;
  value: string;
};

export type ManualPaperSubmitAuditPackage = {
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

export type ManualPaperSubmitApprovalPackageStatus =
  | "approval_package_ready_for_future_manual_review"
  | "blocked"
  | "missing_context"
  | "dry_run_required"
  | "readiness_required"
  | "handoff_required"
  | "audit_package_required"
  | "approval_not_available"
  | "unknown";

export type ManualPaperSubmitApprovalRequirement = {
  code: string;
  label: string;
  required: boolean;
  detail: string;
};

export type ManualPaperSubmitApprovalPackage = {
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

export type ManualPaperSubmitPreflightContractStatus =
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

export type ManualPaperSubmitPreflightRequirement = {
  code: string;
  label: string;
  required: boolean;
  detail: string;
};

export type ManualPaperSubmitPreflightContract = {
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

export type FutureManualSubmitDesignReviewStatus = "design_only_not_enabled";

export type FutureManualSubmitDesignReviewRequirement = {
  code: string;
  label: string;
  value: string;
  detail: string;
};

export type FutureManualSubmitDesignReview = {
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

export type GuardedSubmitDecisionReviewStatus =
  | "ready_for_future_decision_review"
  | "blocked"
  | "missing_context"
  | "dry_run_required"
  | "approval_required"
  | "preflight_contract_required"
  | "design_review_required"
  | "unknown";

export type GuardedSubmitDecisionReviewChecklistItem = {
  code: string;
  label: string;
  satisfied: boolean;
  detail: string;
};

export type GuardedSubmitDecisionReviewRequirement = {
  code: string;
  label: string;
  value: string;
  detail: string;
};

export type GuardedSubmitDecisionReview = {
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

export type GuardedOperatorActionReviewStatus =
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

export type GuardedOperatorActionReviewChecklistItem = {
  code: string;
  label: string;
  satisfied: boolean;
  detail: string;
};

export type GuardedOperatorActionReviewRequirement = {
  code: string;
  label: string;
  value: string;
  detail: string;
};

export type GuardedOperatorActionReview = {
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

export type FinalGuardedSubmitInteractionSpecStatus =
  | "interaction_spec_ready_for_future_phase"
  | "blocked"
  | "missing_context"
  | "dry_run_required"
  | "operator_action_review_required"
  | "unknown";

export type FinalGuardedSubmitInteractionSpecChecklistItem = {
  code: string;
  label: string;
  satisfied: boolean;
  detail: string;
};

export type FinalGuardedSubmitInteractionSpecRequirement = {
  code: string;
  label: string;
  value: string;
  detail: string;
};

export type FinalGuardedSubmitInteractionSpec = {
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

export type ManualPaperSubmitReviewChain = {
  readiness: ManualPaperSubmitReadiness | null;
  handoff: ManualPaperSubmitHandoffReview | null;
  auditPackage: ManualPaperSubmitAuditPackage | null;
  approvalPackage: ManualPaperSubmitApprovalPackage | null;
  preflightContract: ManualPaperSubmitPreflightContract | null;
  futureManualSubmitDesignReview: FutureManualSubmitDesignReview | null;
  submitDecisionReview: GuardedSubmitDecisionReview | null;
  operatorActionReview: GuardedOperatorActionReview | null;
  finalInteractionSpec: FinalGuardedSubmitInteractionSpec | null;
};

function formatMaybeNumber(value: number | null): string {
  if (value === null) return "unknown";
  return value.toLocaleString("en-US", { maximumFractionDigits: 4 });
}

function uniqueMessages(values: Array<string | null | undefined>): string[] {
  return values
    .map((value) => value?.trim())
    .filter((value): value is string => Boolean(value))
    .filter((value, index, all) => all.indexOf(value) === index);
}

export function buildManualConfirmationHref(recommendationId: string, symbol: string): string {
  return `/cockpit/manual-paper-submit-confirmation?recommendationId=${encodeURIComponent(recommendationId)}&symbol=${encodeURIComponent(symbol)}`;
}

export function deriveManualPaperSubmitReadiness(
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

export function deriveManualPaperSubmitHandoffReview(
  result: PaperRecommendationRouteCheck,
  preview: PaperRecommendationBrokerDryRunPreview | null,
  readiness: ManualPaperSubmitReadiness,
): ManualPaperSubmitHandoffReview {
  const preflightStatus = preview?.preflight_decision?.decision_status ?? null;
  const routeCheckEligible = result.route_check_status === "eligible";
  const dryRunExecuted = preview?.dry_run_executed === true;
  const dryRunPreviewNonBlocking =
    preview !== null &&
    preview.dry_run_executed &&
    preview.dry_run_only &&
    preview.dry_run_status === "ready" &&
    preview.would_block === false;
  const readinessReviewReady = readiness.status === "ready_for_future_manual_paper_submit";
  const resolvedRouteIsBrokerOrders =
    result.resolved_route === "/broker/orders" &&
    result.canonical_paper_route === "/broker/orders" &&
    (preview?.resolved_route ?? "/broker/orders") === "/broker/orders" &&
    (preview?.canonical_paper_route ?? "/broker/orders") === "/broker/orders";
  const brokerModePaper =
    result.broker_account_mode === "paper" &&
    result.broker_mode.paper_trading_enabled &&
    (preview?.broker_account_mode ?? "paper") === "paper";
  const liveLocked =
    result.live_state === "ibkr_live_locked" &&
    result.live_trading_enabled === false &&
    (preview?.live_trading_enabled ?? false) === false;
  const workersNonSubmitting =
    result.workers_allowed_to_submit === false &&
    (preview?.workers_allowed_to_submit ?? false) === false;
  const noSubmitControlPresent = true;
  const noOrderSubmitted = result.is_submit === false && (preview?.is_submit ?? false) === false;
  const advisoryReviewRequired =
    (preview?.preflight_decision?.advisory_count ?? 0) > 0 ||
    (preview?.warnings.length ?? 0) > 0;
  const blockedReasons = uniqueMessages([
    result.blocked_reason,
    preview?.blocked_reason,
    ...readiness.blockedReasons,
    ...(preview?.preflight_decision?.blocking_items.map((item) => item.message) ?? []),
    ...(preview?.preflight_decision?.would_block_items.map((item) => item.message) ?? []),
  ]);
  const missingData = uniqueMessages([...result.missing_data, ...(preview?.missing_data ?? []), ...readiness.missingData]);
  const warnings = uniqueMessages(preview?.warnings.map((warning) => warning.message) ?? []);

  const reasons: ManualPaperSubmitHandoffReason[] = [
    { code: "route_check_eligible", label: "Route-check eligible", satisfied: routeCheckEligible },
    {
      code: "dry_run_preview_non_blocking",
      label: "Guarded dry-run preview is non-blocking",
      satisfied: dryRunPreviewNonBlocking,
    },
    {
      code: "readiness_review_ready",
      label: "Readiness review is ready",
      satisfied: readinessReviewReady,
    },
    {
      code: "resolved_route_is_broker_orders",
      label: "Resolved route is /broker/orders",
      satisfied: resolvedRouteIsBrokerOrders,
    },
    { code: "broker_mode_paper", label: "Broker mode remains paper", satisfied: brokerModePaper },
    { code: "live_locked", label: "Live remains locked", satisfied: liveLocked },
    {
      code: "workers_non_submitting",
      label: "Workers remain non-submitting",
      satisfied: workersNonSubmitting,
    },
    {
      code: "no_submit_control_present",
      label: "No submit control is present",
      satisfied: noSubmitControlPresent,
    },
    { code: "no_order_submitted", label: "No order submitted", satisfied: noOrderSubmitted },
  ];

  const orderType = (result.order_type ?? preview?.order_type ?? "").toUpperCase();
  const limitPriceRequired = orderType === "LIMIT" || orderType === "STOP_LIMIT";
  const stopPriceRequired = orderType === "STOP" || orderType === "STOP_LIMIT";
  const futureManualSubmitRoute =
    routeCheckEligible &&
    dryRunPreviewNonBlocking &&
    readinessReviewReady &&
    resolvedRouteIsBrokerOrders &&
    brokerModePaper &&
    liveLocked &&
    workersNonSubmitting &&
    noOrderSubmitted
      ? "/broker/orders"
      : null;

  const requiredFuturePayloadFields: ManualPaperSubmitHandoffPayloadField[] = [
    {
      code: "symbol",
      label: "symbol",
      required: true,
      satisfied: Boolean(result.ticker),
      value: result.ticker ?? "missing",
      detail: "Future manual submit still needs the recommendation symbol.",
    },
    {
      code: "side",
      label: "side",
      required: true,
      satisfied: Boolean(result.side),
      value: result.side ?? "missing",
      detail: "Future manual submit still needs BUY or SELL.",
    },
    {
      code: "quantity",
      label: "quantity",
      required: true,
      satisfied: result.quantity !== null && result.quantity > 0,
      value: result.quantity !== null ? String(result.quantity) : "missing",
      detail: "The guarded /broker/orders request currently requires quantity rather than notional.",
    },
    {
      code: "order_type",
      label: "order_type",
      required: true,
      satisfied: Boolean(result.order_type),
      value: result.order_type ?? "missing",
      detail: "The future handoff stays tied to the persisted recommendation order type.",
    },
    {
      code: "limit_price",
      label: "limit_price",
      required: limitPriceRequired,
      satisfied: !limitPriceRequired || result.limit_price !== null,
      value: result.limit_price !== null ? String(result.limit_price) : "missing",
      detail: limitPriceRequired
        ? "Required later for LIMIT and STOP_LIMIT orders."
        : "Not required for the current order type.",
    },
    {
      code: "stop_price",
      label: "stop_price",
      required: stopPriceRequired,
      satisfied: !stopPriceRequired,
      value: stopPriceRequired ? "missing" : "not required",
      detail: stopPriceRequired
        ? "STOP and STOP_LIMIT handoff stays blocked because stop_price is not persisted on recommendations today."
        : "Not required for the current order type.",
    },
    {
      code: "time_in_force",
      label: "time_in_force",
      required: false,
      satisfied: true,
      value: "DAY default available later",
      detail: "The guarded broker order request defaults time-in-force to DAY unless an operator overrides it later.",
    },
    {
      code: "recommendation_correlation",
      label: "recommendation_id / client_order_id",
      required: false,
      satisfied: Boolean(result.recommendation_id),
      value: result.recommendation_id,
      detail: "Recommendation context is already available for future audit correlation, while client_order_id remains optional.",
    },
    {
      code: "risk_preflight_context",
      label: "risk / preflight context",
      required: false,
      satisfied: preview !== null,
      value: preview ? (preflightStatus ?? "evaluated") : "not evaluated yet",
      detail: preview
        ? "Dry-run preflight evidence exists, but broker preflight still reruns at actual guarded submit time."
        : "Guarded dry-run preview has not yet produced preflight context for future submit handoff.",
    },
  ];

  const hardSafetyBlocked =
    !brokerModePaper ||
    !resolvedRouteIsBrokerOrders ||
    !liveLocked ||
    !workersNonSubmitting ||
    !noOrderSubmitted ||
    preview?.would_block === true;

  let status: ManualPaperSubmitHandoffStatus = "unknown";
  if (result.route_check_status === "missing_context" || readiness.status === "missing_context") {
    status = "missing_context";
  } else if (result.route_check_status === "blocked") {
    status = "blocked";
  } else if (!routeCheckEligible) {
    status = "unknown";
  } else if (!dryRunExecuted) {
    status = "dry_run_required";
  } else if (missingData.length > 0) {
    status = "missing_context";
  } else if (dryRunPreviewNonBlocking && !hardSafetyBlocked && !readinessReviewReady) {
    status = "readiness_required";
  } else if (readinessReviewReady && advisoryReviewRequired) {
    status = "handoff_required";
  } else if (hardSafetyBlocked || readiness.status === "blocked") {
    status = "blocked";
  } else if (futureManualSubmitRoute === "/broker/orders") {
    status = "handoff_ready_for_future_manual_step";
  }

  let title = "Manual paper submit handoff is unknown";
  let body = "Handoff review only, no order submitted. Review the current route-check, dry-run, and readiness evidence before considering any future guarded manual submit path.";
  let nextRequiredAction = "no_action_available";
  let nextRequiredActionDetail = readiness.nextRequiredActionDetail;

  if (status === "missing_context") {
    title = "Missing context before handoff";
    body = "Handoff review only, no order submitted. Missing recommendation or payload context still blocks any future manual IBKR paper submit handoff.";
    nextRequiredAction = "fix_missing_context";
    nextRequiredActionDetail = missingData[0] ?? readiness.nextRequiredActionDetail;
  } else if (status === "blocked") {
    title = "Blocked before handoff";
    body = "Handoff review only, no order submitted. One or more current route, dry-run, paper-mode, or safety gates still block future manual paper submit handoff.";
    nextRequiredAction = "review_blocked_reason";
    nextRequiredActionDetail = blockedReasons[0] ?? readiness.nextRequiredActionDetail;
  } else if (status === "dry_run_required") {
    title = "Dry-run required first";
    body = "Handoff review only, no order submitted. Run the guarded broker dry-run preview before reviewing a future manual paper submit handoff.";
    nextRequiredAction = "run_guarded_dry_run";
    nextRequiredActionDetail = "Run the guarded broker dry-run preview before future manual paper handoff review can proceed.";
  } else if (status === "readiness_required") {
    title = "Readiness review required";
    body = "Handoff review only, no order submitted. Guarded dry-run evidence exists, but the readiness review has not yet cleared this recommendation for future manual paper handoff.";
    nextRequiredAction = "complete_readiness_review";
    nextRequiredActionDetail = readiness.nextRequiredActionDetail;
  } else if (status === "handoff_required") {
    title = "Handoff review required";
    body = "Handoff review only, no order submitted. Readiness cleared, but advisory dry-run evidence still needs operator handoff review before a future guarded manual paper submit package can be considered ready.";
    nextRequiredAction = "complete_handoff_review";
    nextRequiredActionDetail = warnings[0] ?? "Review advisory warnings and non-blocking preflight evidence before considering any future guarded manual paper submit step.";
  } else if (status === "handoff_ready_for_future_manual_step") {
    title = "Ready for future manual handoff";
    body = "Handoff review only, no order submitted. Future manual paper submit would still use guarded /broker/orders after operator review, with broker mode guard and preflight checks rerun at submit time.";
    nextRequiredAction = "future_manual_submit_handoff_available_after_review";
    nextRequiredActionDetail = "Future manual paper submit would still use guarded /broker/orders after operator review. No submit button is available here. Live trading remains locked and workers cannot submit.";
  }

  return {
    status,
    title,
    body,
    reasons,
    requiredFuturePayloadFields,
    blockedReasons,
    missingData,
    warnings,
    safetyGates: [
      "Broker mode guard and trading_control_service still run at submit time.",
      "Broker order request validation still runs on the guarded /broker/orders path.",
      "Broker preflight advisory and decision checks still rerun before any future manual submit.",
      "Live trading remains locked even if a client attempts to bypass this review surface.",
      "Workers remain non-submitting and gain no submit authority from this handoff review.",
    ],
    futureManualSubmitRoute,
    nextRequiredAction,
    nextRequiredActionDetail,
  };
}

export function deriveManualPaperSubmitAuditPackage(
  result: PaperRecommendationRouteCheck,
  preview: PaperRecommendationBrokerDryRunPreview | null,
  readiness: ManualPaperSubmitReadiness,
  handoff: ManualPaperSubmitHandoffReview,
): ManualPaperSubmitAuditPackage {
  const routeCheckEligible = result.route_check_status === "eligible";
  const dryRunCompleted = preview !== null && preview.dry_run_executed;
  const preflightStatus = preview?.preflight_decision?.decision_status ?? "not evaluated";
  const dryRunNonBlocking =
    preview !== null &&
    preview.dry_run_executed &&
    preview.dry_run_only &&
    preview.dry_run_status === "ready" &&
    preview.would_block === false &&
    ["allowed", "advisory"].includes(String(preflightStatus).toLowerCase());
  const readinessReady = readiness.status === "ready_for_future_manual_paper_submit";
  const handoffReady = handoff.status === "handoff_ready_for_future_manual_step";
  const resolvedRouteIsBrokerOrders =
    result.resolved_route === "/broker/orders" &&
    result.canonical_paper_route === "/broker/orders" &&
    (preview?.resolved_route ?? "/broker/orders") === "/broker/orders" &&
    (preview?.canonical_paper_route ?? "/broker/orders") === "/broker/orders";
  const brokerModePaper =
    result.broker_account_mode === "paper" &&
    result.broker_mode.paper_trading_enabled &&
    (preview?.broker_account_mode ?? "paper") === "paper";
  const liveLocked =
    result.live_state === "ibkr_live_locked" &&
    result.live_trading_enabled === false &&
    (preview?.live_trading_enabled ?? false) === false;
  const workersNonSubmitting =
    result.workers_allowed_to_submit === false &&
    (preview?.workers_allowed_to_submit ?? false) === false;
  const noSubmitControlPresent = true;
  const noOrderSubmitted = result.is_submit === false && (preview?.is_submit ?? false) === false;
  const blockedReasons = uniqueMessages([
    result.blocked_reason,
    preview?.blocked_reason,
    ...readiness.blockedReasons,
    ...handoff.blockedReasons,
    ...(preview?.preflight_decision?.blocking_items.map((item) => item.message) ?? []),
    ...(preview?.preflight_decision?.would_block_items.map((item) => item.message) ?? []),
  ]);
  const missingData = uniqueMessages([
    ...result.missing_data,
    ...(preview?.missing_data ?? []),
    ...readiness.missingData,
    ...handoff.missingData,
  ]);
  const warnings = uniqueMessages([
    ...readiness.warnings,
    ...handoff.warnings,
    ...(preview?.warnings.map((warning) => warning.message) ?? []),
  ]);

  const futurePayloadPreviewFields: ManualPaperSubmitHandoffPayloadField[] = [
    ...handoff.requiredFuturePayloadFields,
    {
      code: "estimated_notional",
      label: "quantity / estimated_notional",
      required: false,
      satisfied: result.quantity !== null || (preview?.estimated_notional ?? null) !== null,
      value:
        result.quantity !== null
          ? `${formatMaybeNumber(result.quantity)} shares`
          : (preview?.estimated_notional ?? null) !== null
            ? formatMaybeNumber(preview?.estimated_notional ?? null)
            : "missing",
      detail: "The guarded broker contract uses quantity; estimated notional remains review-only context.",
    },
    {
      code: "account_mode",
      label: "account_mode",
      required: true,
      satisfied: brokerModePaper,
      value: preview?.broker_account_mode ?? result.broker_account_mode,
      detail: "Future guarded manual submit remains paper-only and blocks outside coherent paper mode.",
    },
    {
      code: "execution_source",
      label: "execution_source",
      required: true,
      satisfied: (preview?.serious_paper_source ?? result.serious_paper_source) === "ibkr_paper",
      value: preview?.dry_run_execution_source ?? result.execution_source,
      detail: "This package is review-only; future guarded submit would still resolve through canonical IBKR paper routing.",
    },
    {
      code: "dry_run_decision_reference",
      label: "dry_run_decision_reference",
      required: false,
      satisfied: preview !== null,
      value: preview ? `${preview.dry_run_execution_source ?? "broker_dry_run"}:${preflightStatus}` : "not generated yet",
      detail: "Read-only reference to the current guarded dry-run evidence.",
    },
    {
      code: "broker_submit_decision_reference",
      label: "broker_submit_decision_reference",
      required: false,
      satisfied: false,
      value: "not generated in this review-only layer",
      detail: "A broker submit decision reference only exists during a future guarded /broker/orders submit review, not in this audit package.",
    },
  ];

  const missingPayloadFields = futurePayloadPreviewFields
    .filter((field) => field.required && !field.satisfied)
    .map((field) => field.label);

  const futureManualSubmitRoute = handoffReady && missingPayloadFields.length === 0 ? "/broker/orders" : null;

  const evidenceChecklist: ManualPaperSubmitAuditChecklistItem[] = [
    {
      code: "recommendation_loaded",
      label: "Recommendation loaded",
      satisfied: true,
      detail: `Recommendation ${result.recommendation_id} is loaded into this review-only package.`,
    },
    {
      code: "route_check_completed",
      label: "Route-check completed",
      satisfied: true,
      detail: "The current route-check evidence is present in this review surface.",
    },
    {
      code: "route_check_eligible",
      label: "Route-check eligible",
      satisfied: routeCheckEligible,
      detail: "The future guarded manual path only stays available when the recommendation is route-check eligible.",
    },
    {
      code: "dry_run_preview_completed",
      label: "Dry-run preview completed",
      satisfied: dryRunCompleted,
      detail: "The audit package expects guarded broker dry-run evidence before any future manual handoff review.",
    },
    {
      code: "dry_run_non_blocking",
      label: "Dry-run non-blocking",
      satisfied: dryRunNonBlocking,
      detail: "Preflight would-block and blocking findings must stay clear before the package can be ready.",
    },
    {
      code: "readiness_review_completed",
      label: "Readiness review completed",
      satisfied: true,
      detail: "Readiness is derived locally from route-check and dry-run evidence in this read-only panel.",
    },
    {
      code: "readiness_review_ready",
      label: "Readiness review ready",
      satisfied: readinessReady,
      detail: "The recommendation must pass readiness review before the audit package can progress beyond readiness-required.",
    },
    {
      code: "handoff_review_completed",
      label: "Handoff review completed",
      satisfied: true,
      detail: "Handoff review is derived locally and stays non-submitting.",
    },
    {
      code: "handoff_review_ready",
      label: "Handoff review ready",
      satisfied: handoffReady,
      detail: "The audit package only becomes ready when the current handoff review is ready and all required payload fields are available.",
    },
    {
      code: "resolved_route_is_broker_orders",
      label: "Resolved route is /broker/orders",
      satisfied: resolvedRouteIsBrokerOrders,
      detail: "The canonical future manual paper route remains guarded /broker/orders only when all paper-mode checks align.",
    },
    {
      code: "broker_mode_paper",
      label: "Broker mode paper",
      satisfied: brokerModePaper,
      detail: "The package fails closed outside coherent paper mode.",
    },
    {
      code: "live_locked",
      label: "Live locked",
      satisfied: liveLocked,
      detail: "Live trading remains locked in this review-only layer.",
    },
    {
      code: "workers_non_submitting",
      label: "Workers non-submitting",
      satisfied: workersNonSubmitting,
      detail: "Background workers gain no broker submit authority from this package.",
    },
    {
      code: "no_submit_control_present",
      label: "No submit control present",
      satisfied: noSubmitControlPresent,
      detail: "This surface exposes evidence only and does not render a submit button.",
    },
    {
      code: "no_order_submitted",
      label: "No order submitted",
      satisfied: noOrderSubmitted,
      detail: "No /broker/orders call is made from this panel and no order is submitted here.",
    },
  ];

  const sourceLabels: ManualPaperSubmitAuditSourceLabel[] = [
    { code: "route_execution_source", label: "route execution source", value: result.execution_source },
    {
      code: "resolved_execution_source",
      label: "resolved execution source",
      value: result.resolved_execution_source ?? "not resolved",
    },
    {
      code: "dry_run_execution_source",
      label: "dry-run execution source",
      value: preview?.dry_run_execution_source ?? "not run",
    },
    { code: "serious_paper_source", label: "serious paper source", value: preview?.serious_paper_source ?? result.serious_paper_source },
    { code: "balance_source", label: "balance source", value: preview?.balance_source ?? "not run" },
    { code: "fees_source", label: "fees source", value: preview?.fees_source ?? "not run" },
    { code: "fills_source", label: "fills source", value: preview?.fills_source ?? "not run" },
    { code: "positions_source", label: "positions source", value: preview?.positions_source ?? "not run" },
  ];

  const decisionReferences: ManualPaperSubmitAuditReference[] = [
    {
      code: "recommendation_reference",
      label: "recommendation reference",
      available: true,
      value: result.recommendation_id,
      detail: "Primary recommendation identity for future operator handoff correlation.",
    },
    {
      code: "route_check_reference",
      label: "route-check decision reference",
      available: true,
      value: `${result.execution_source}:${result.route_check_status}`,
      detail: "Read-only route-check decision reference from the current operator review chain.",
    },
    {
      code: "dry_run_reference",
      label: "dry-run decision reference",
      available: preview !== null,
      value: preview ? `${preview.dry_run_execution_source ?? "broker_dry_run"}:${preflightStatus}` : "not generated yet",
      detail: "Current guarded broker dry-run preview reference, if the preview has been executed.",
    },
    {
      code: "broker_submit_reference",
      label: "broker submit decision reference",
      available: false,
      value: "not surfaced before a future guarded submit step",
      detail: "A broker submit decision reference is intentionally unavailable in this non-submitting audit package.",
    },
  ];

  const hardBlocked =
    !brokerModePaper ||
    !resolvedRouteIsBrokerOrders ||
    !liveLocked ||
    !workersNonSubmitting ||
    !noOrderSubmitted ||
    (preview?.would_block ?? result.would_block) ||
    result.live_trading_enabled ||
    (preview?.live_trading_enabled ?? false);

  let status: ManualPaperSubmitAuditPackageStatus = "unknown";
  if (result.route_check_status === "blocked" || handoff.status === "blocked") {
    status = "blocked";
  } else if (
    result.route_check_status === "missing_context" ||
    readiness.status === "missing_context" ||
    handoff.status === "missing_context" ||
    missingData.length > 0 ||
    missingPayloadFields.length > 0
  ) {
    status = "missing_context";
  } else if (hardBlocked) {
    status = "blocked";
  } else if (!routeCheckEligible) {
    status = "unknown";
  } else if (!dryRunCompleted) {
    status = "dry_run_required";
  } else if (handoff.status === "readiness_required" || !readinessReady) {
    status = "readiness_required";
  } else if (handoff.status === "handoff_required" || !handoffReady) {
    status = "handoff_required";
  } else if (!readinessReady) {
    status = "readiness_required";
  } else if (futureManualSubmitRoute === "/broker/orders") {
    status = "package_ready_for_future_manual_review";
  }

  let title = "Manual paper submit audit package is unknown";
  let body = "Audit package only, no order submitted. Use this consolidated package to review route, dry-run, readiness, and handoff evidence before any future guarded manual paper submit step.";
  let nextRequiredAction = "no_action_available";
  let nextRequiredActionDetail = handoff.nextRequiredActionDetail;

  if (status === "missing_context") {
    title = "Missing context before audit package review";
    body = "Audit package only, no order submitted. Recommendation or payload context is still missing, so the future guarded manual paper submit package cannot be completed yet.";
    nextRequiredAction = "fix_missing_context";
    nextRequiredActionDetail = missingData[0] ?? missingPayloadFields[0] ?? handoff.nextRequiredActionDetail;
  } else if (status === "blocked") {
    title = "Blocked before audit package review";
    body = "Audit package only, no order submitted. Broker mode, live-lock, worker-submit, route, or preflight safety gates still block any future guarded manual paper submit handoff package.";
    nextRequiredAction = "review_blocked_reason";
    nextRequiredActionDetail = blockedReasons[0] ?? handoff.nextRequiredActionDetail;
  } else if (status === "dry_run_required") {
    title = "Dry-run required before audit package review";
    body = "Audit package only, no order submitted. The route-check is eligible, but a guarded broker dry-run preview is still required before the future manual paper submit package can be reviewed.";
    nextRequiredAction = "run_guarded_dry_run";
    nextRequiredActionDetail = "Run the guarded broker dry-run preview before relying on this manual paper submit audit package.";
  } else if (status === "readiness_required") {
    title = "Readiness review required before audit package review";
    body = "Audit package only, no order submitted. Dry-run evidence exists, but readiness review has not yet cleared this recommendation for future guarded manual paper submit review.";
    nextRequiredAction = "complete_readiness_review";
    nextRequiredActionDetail = readiness.nextRequiredActionDetail;
  } else if (status === "handoff_required") {
    title = "Handoff review required before audit package review";
    body = "Audit package only, no order submitted. Readiness is clear, but handoff review evidence still needs operator attention before this future guarded manual paper submit package can be considered ready.";
    nextRequiredAction = "complete_handoff_review";
    nextRequiredActionDetail = handoff.nextRequiredActionDetail;
  } else if (status === "package_ready_for_future_manual_review") {
    title = "Package ready for future manual review";
    body = "Audit package only, no order submitted. This consolidated package is ready for operator review before any future guarded manual paper submit step, which would still use /broker/orders with all existing broker-mode, trading-control, validation, and preflight checks rerun.";
    nextRequiredAction = "package_ready_for_future_manual_review";
    nextRequiredActionDetail = "Use this package for operator review only. No submit button is available here, no /broker/orders call was made from this surface, live trading remains locked, and workers cannot submit.";
  }

  return {
    status,
    title,
    body,
    evidenceChecklist,
    sourceLabels,
    decisionReferences,
    futurePayloadPreviewFields,
    missingPayloadFields,
    blockedReasons,
    missingData,
    warnings,
    futureManualSubmitRoute,
    nextRequiredAction,
    nextRequiredActionDetail,
  };
}

export function deriveManualPaperSubmitApprovalPackage(
  result: PaperRecommendationRouteCheck,
  preview: PaperRecommendationBrokerDryRunPreview | null,
  readiness: ManualPaperSubmitReadiness,
  handoff: ManualPaperSubmitHandoffReview,
  auditPackage: ManualPaperSubmitAuditPackage,
): ManualPaperSubmitApprovalPackage {
  const routeCheckEligible = result.route_check_status === "eligible";
  const dryRunCompleted = preview !== null && preview.dry_run_executed;
  const preflightStatus = preview?.preflight_decision?.decision_status ?? "not evaluated";
  const dryRunNonBlocking =
    preview !== null &&
    preview.dry_run_executed &&
    preview.dry_run_only &&
    preview.dry_run_status === "ready" &&
    preview.would_block === false &&
    ["allowed", "advisory"].includes(String(preflightStatus).toLowerCase());
  const readinessReviewReady = readiness.status === "ready_for_future_manual_paper_submit";
  const handoffReviewReady = handoff.status === "handoff_ready_for_future_manual_step";
  const auditPackageReady = auditPackage.status === "package_ready_for_future_manual_review";
  const resolvedRouteIsBrokerOrders =
    result.resolved_route === "/broker/orders" &&
    result.canonical_paper_route === "/broker/orders" &&
    (preview?.resolved_route ?? "/broker/orders") === "/broker/orders" &&
    (preview?.canonical_paper_route ?? "/broker/orders") === "/broker/orders";
  const brokerModePaper =
    result.broker_account_mode === "paper" &&
    result.broker_mode.paper_trading_enabled &&
    (preview?.broker_account_mode ?? "paper") === "paper";
  const liveLocked =
    result.live_state === "ibkr_live_locked" &&
    result.live_trading_enabled === false &&
    (preview?.live_trading_enabled ?? false) === false;
  const workersNonSubmitting =
    result.workers_allowed_to_submit === false &&
    (preview?.workers_allowed_to_submit ?? false) === false;
  const noSubmitControlPresent = true;
  const noOrderSubmitted = result.is_submit === false && (preview?.is_submit ?? false) === false;
  const futureSubmitRequiresManualApproval = true;
  const submitTimePreflightRequired = true;
  const submitTimeDecisionPersistenceRequired = true;
  const futureSubmitEligibilityConfirmed = preview?.allowed_to_submit !== false;
  const blockedReasons = uniqueMessages([
    result.blocked_reason,
    preview?.blocked_reason,
    ...readiness.blockedReasons,
    ...handoff.blockedReasons,
    ...auditPackage.blockedReasons,
    ...(preview?.preflight_decision?.blocking_items.map((item) => item.message) ?? []),
    ...(preview?.preflight_decision?.would_block_items.map((item) => item.message) ?? []),
  ]);
  const missingData = uniqueMessages([
    ...result.missing_data,
    ...(preview?.missing_data ?? []),
    ...readiness.missingData,
    ...handoff.missingData,
    ...auditPackage.missingData,
  ]);
  const warnings = uniqueMessages([
    ...readiness.warnings,
    ...handoff.warnings,
    ...auditPackage.warnings,
    ...(preview?.warnings.map((warning) => warning.message) ?? []),
  ]);
  const missingPayloadFields = [...auditPackage.missingPayloadFields];
  const futureManualSubmitRoute =
    auditPackageReady && missingPayloadFields.length === 0 ? "/broker/orders" : null;

  const evidenceChecklist: ManualPaperSubmitAuditChecklistItem[] = [
    {
      code: "recommendation_loaded",
      label: "Recommendation loaded",
      satisfied: true,
      detail: `Recommendation ${result.recommendation_id} is loaded into this approval package review.`,
    },
    {
      code: "route_check_completed",
      label: "Route-check completed",
      satisfied: true,
      detail: "The current route-check result is present in this approval package.",
    },
    {
      code: "route_check_eligible",
      label: "Route-check eligible",
      satisfied: routeCheckEligible,
      detail: "Future guarded manual submit still depends on a route-check eligible recommendation.",
    },
    {
      code: "dry_run_preview_completed",
      label: "Dry-run preview completed",
      satisfied: dryRunCompleted,
      detail: "The approval package expects guarded broker dry-run evidence before future manual review.",
    },
    {
      code: "dry_run_non_blocking",
      label: "Dry-run non-blocking",
      satisfied: dryRunNonBlocking,
      detail: "Would-block and blocking preflight findings must remain clear.",
    },
    {
      code: "readiness_review_completed",
      label: "Readiness review completed",
      satisfied: true,
      detail: "The readiness review is available in this review-only chain.",
    },
    {
      code: "readiness_review_ready",
      label: "Readiness review ready",
      satisfied: readinessReviewReady,
      detail: "Future manual review requires readiness review to be green.",
    },
    {
      code: "handoff_review_completed",
      label: "Handoff review completed",
      satisfied: true,
      detail: "Handoff review evidence is present and remains non-submitting.",
    },
    {
      code: "handoff_review_ready",
      label: "Handoff review ready",
      satisfied: handoffReviewReady,
      detail: "The approval package expects handoff review to be ready before final approval-style review is possible.",
    },
    {
      code: "audit_package_completed",
      label: "Audit package completed",
      satisfied: true,
      detail: "Audit package evidence is available in this review chain.",
    },
    {
      code: "audit_package_ready",
      label: "Audit package ready",
      satisfied: auditPackageReady,
      detail: "The current audit package must be ready before this approval package can become ready.",
    },
    {
      code: "resolved_route_is_broker_orders",
      label: "Resolved route is /broker/orders",
      satisfied: resolvedRouteIsBrokerOrders,
      detail: "The future guarded submit path remains /broker/orders only when all paper checks align.",
    },
    {
      code: "broker_mode_paper",
      label: "Broker mode paper",
      satisfied: brokerModePaper,
      detail: "The approval package fails closed outside coherent paper mode.",
    },
    {
      code: "live_locked",
      label: "Live locked",
      satisfied: liveLocked,
      detail: "Live trading remains locked in this approval package layer.",
    },
    {
      code: "workers_non_submitting",
      label: "Workers non-submitting",
      satisfied: workersNonSubmitting,
      detail: "Workers gain no submit authority from this approval package.",
    },
    {
      code: "no_submit_control_present",
      label: "No submit control present",
      satisfied: noSubmitControlPresent,
      detail: "This approval package is visibility-only and does not render a submit button.",
    },
    {
      code: "no_order_submitted",
      label: "No order submitted",
      satisfied: noOrderSubmitted,
      detail: "No /broker/orders call is made from this panel and no order is submitted here.",
    },
    {
      code: "future_submit_requires_manual_approval",
      label: "Future submit requires manual approval",
      satisfied: futureSubmitRequiresManualApproval,
      detail: "Any future guarded manual paper submit would still require an explicit operator step outside this surface.",
    },
    {
      code: "submit_time_preflight_required",
      label: "Submit-time preflight required",
      satisfied: submitTimePreflightRequired,
      detail: "Broker preflight would rerun at the actual guarded submit step.",
    },
    {
      code: "submit_time_decision_persistence_required",
      label: "Submit-time decision persistence required",
      satisfied: submitTimeDecisionPersistenceRequired,
      detail: "Submit-time decision logging would still be required on the guarded broker path.",
    },
  ];

  const futureManualApprovalRequirements: ManualPaperSubmitApprovalRequirement[] = [
    {
      code: "operator_manual_review_required",
      label: "operator_manual_review_required",
      required: true,
      detail: "A future guarded manual paper submit would still require explicit operator review outside this read-only surface.",
    },
    {
      code: "broker_mode_recheck_required",
      label: "broker_mode_recheck_required",
      required: true,
      detail: "Broker mode guard must be rechecked at actual guarded submit time.",
    },
    {
      code: "risk_preflight_rerun_required",
      label: "risk_preflight_rerun_required",
      required: true,
      detail: "Broker preflight advisory and decision services would rerun at the submit boundary.",
    },
    {
      code: "submit_decision_persistence_required",
      label: "submit_decision_persistence_required",
      required: true,
      detail: "Submit-time decision logging would still be required before any future guarded manual submit completes.",
    },
    {
      code: "final_payload_review_required",
      label: "final_payload_review_required",
      required: true,
      detail: "The final broker payload would still require operator review even after this approval package is green.",
    },
    {
      code: "live_lock_recheck_required",
      label: "live_lock_recheck_required",
      required: true,
      detail: "Live lock must still be rechecked at actual guarded submit time.",
    },
    {
      code: "worker_non_submission_recheck_required",
      label: "worker_non_submission_recheck_required",
      required: true,
      detail: "Worker non-submission posture must remain intact at the actual guarded submit boundary.",
    },
  ];

  const auditReferences: ManualPaperSubmitAuditReference[] = [
    {
      code: "recommendation_id",
      label: "recommendation_id",
      available: true,
      value: result.recommendation_id,
      detail: "Primary recommendation identity for future manual approval correlation.",
    },
    {
      code: "route_check_reference",
      label: "route_check_reference",
      available: true,
      value: `${result.execution_source}:${result.route_check_status}`,
      detail: "Read-only route-check evidence reference used by this approval package.",
    },
    {
      code: "dry_run_decision_reference",
      label: "dry_run_decision_reference",
      available: preview !== null,
      value: preview ? `${preview.dry_run_execution_source ?? "broker_dry_run"}:${preflightStatus}` : "not generated yet",
      detail: "Current guarded dry-run evidence reference, if the preview has been executed.",
    },
    {
      code: "broker_submit_decision_reference",
      label: "broker_submit_decision_reference",
      available: false,
      value: "not generated in this read-only approval package",
      detail: "A broker submit decision reference only exists during a future guarded /broker/orders submit review.",
    },
    {
      code: "audit_package_reference",
      label: "audit_package_reference",
      available: true,
      value: `${result.recommendation_id}:${auditPackage.status}`,
      detail: "Read-only reference to the immediately preceding audit package status.",
    },
  ];

  const hardBlocked =
    !brokerModePaper ||
    !resolvedRouteIsBrokerOrders ||
    !liveLocked ||
    !workersNonSubmitting ||
    !noOrderSubmitted ||
    (preview?.would_block ?? result.would_block) ||
    result.live_trading_enabled ||
    (preview?.live_trading_enabled ?? false);

  let status: ManualPaperSubmitApprovalPackageStatus = "unknown";
  if (
    result.route_check_status === "missing_context" ||
    handoff.status === "missing_context" ||
    auditPackage.status === "missing_context"
  ) {
    status = "missing_context";
  } else if (
    result.route_check_status === "blocked" ||
    handoff.status === "blocked" ||
    auditPackage.status === "blocked" ||
    hardBlocked
  ) {
    status = "blocked";
  } else if (missingData.length > 0 || missingPayloadFields.length > 0) {
    status = "missing_context";
  } else if (result.route_check_status === "unknown" || auditPackage.status === "unknown") {
    status = "approval_not_available";
  } else if (!dryRunCompleted || auditPackage.status === "dry_run_required") {
    status = "dry_run_required";
  } else if (!readinessReviewReady || auditPackage.status === "readiness_required") {
    status = "readiness_required";
  } else if (handoff.status === "handoff_required") {
    status = "audit_package_required";
  } else if (!auditPackageReady) {
    status = "audit_package_required";
  } else if (!futureSubmitEligibilityConfirmed) {
    status = "approval_not_available";
  } else if (futureManualSubmitRoute === "/broker/orders") {
    status = "approval_package_ready_for_future_manual_review";
  }

  let title = "Manual submit approval package is unknown";
  let body = "Approval package only, no order submitted. Use this read-only package to review the final approval-style evidence before any future guarded manual paper submit step.";
  let nextRequiredAction = "no_action_available";
  let nextRequiredActionDetail = auditPackage.nextRequiredActionDetail;

  if (status === "missing_context") {
    title = "Missing context before approval package review";
    body = "Approval package only, no order submitted. Recommendation or payload context is still missing, so future manual approval review cannot proceed yet.";
    nextRequiredAction = "fix_missing_context";
    nextRequiredActionDetail = missingData[0] ?? missingPayloadFields[0] ?? auditPackage.nextRequiredActionDetail;
  } else if (status === "blocked") {
    title = "Blocked before approval package review";
    body = "Approval package only, no order submitted. Broker mode, live-lock, worker-submit, route, or preflight safety gates still block any future guarded manual paper submit approval review.";
    nextRequiredAction = "review_blocked_reason";
    nextRequiredActionDetail = blockedReasons[0] ?? auditPackage.nextRequiredActionDetail;
  } else if (status === "approval_not_available") {
    title = "Approval package not available";
    body = "Approval package only, no order submitted. The current review chain does not yet expose a coherent approval posture for future guarded manual paper submit review.";
    nextRequiredAction = "no_action_available";
    nextRequiredActionDetail = auditPackage.nextRequiredActionDetail;
  } else if (status === "dry_run_required") {
    title = "Dry-run required before approval package review";
    body = "Approval package only, no order submitted. The route-check is eligible, but a guarded broker dry-run preview is still required before approval review can proceed.";
    nextRequiredAction = "run_guarded_dry_run";
    nextRequiredActionDetail = "Run the guarded broker dry-run preview before relying on this approval package.";
  } else if (status === "readiness_required") {
    title = "Readiness review required before approval package review";
    body = "Approval package only, no order submitted. Dry-run evidence exists, but readiness review has not yet cleared this recommendation for future guarded manual review.";
    nextRequiredAction = "complete_readiness_review";
    nextRequiredActionDetail = readiness.nextRequiredActionDetail;
  } else if (status === "audit_package_required") {
    title = "Audit package required before approval package review";
    body = "Approval package only, no order submitted. The approval layer depends on the current audit package being ready first, including its review of warnings, payload preview fields, and future guarded submit evidence.";
    nextRequiredAction = "complete_audit_package";
    nextRequiredActionDetail = auditPackage.nextRequiredActionDetail;
  } else if (status === "approval_package_ready_for_future_manual_review") {
    title = "Approval package ready for future manual review";
    body = "Approval package only, no order submitted. This consolidated approval-style package is ready for operator review before any future guarded manual paper submit step, which would still require guarded /broker/orders, rerun broker preflight, and submit-time decision logging.";
    nextRequiredAction = "approval_package_ready_for_future_manual_review";
    nextRequiredActionDetail = "Future manual paper submit would still require guarded /broker/orders, submit-time preflight reruns, submit-time decision logging, live-lock rechecks, and worker non-submission rechecks. No submit button is available here.";
  }

  return {
    status,
    title,
    body,
    evidenceChecklist,
    futureManualApprovalRequirements,
    auditReferences,
    futurePayloadPreviewFields: auditPackage.futurePayloadPreviewFields,
    missingPayloadFields,
    safetyReruns: [
      "Broker mode guard would rerun at actual guarded submit time.",
      "trading_control_service would rerun at actual guarded submit time.",
      "Broker request validation would rerun on the guarded /broker/orders path.",
      "Broker preflight advisory and decision services would rerun before any future guarded manual submit.",
      "Submit-time decision logging would still be required before a future guarded manual submit completes.",
      "Live lock would still be rechecked and workers would remain non-submitting.",
    ],
    blockedReasons,
    missingData,
    warnings,
    futureManualSubmitRoute,
    nextRequiredAction,
    nextRequiredActionDetail,
  };
}

export function deriveManualPaperSubmitPreflightContract(
  result: PaperRecommendationRouteCheck,
  preview: PaperRecommendationBrokerDryRunPreview | null,
  readiness: ManualPaperSubmitReadiness,
  handoff: ManualPaperSubmitHandoffReview,
  auditPackage: ManualPaperSubmitAuditPackage,
  approvalPackage: ManualPaperSubmitApprovalPackage,
): ManualPaperSubmitPreflightContract {
  const routeCheckEligible = result.route_check_status === "eligible";
  const dryRunCompleted = preview !== null && preview.dry_run_executed;
  const preflightStatus = preview?.preflight_decision?.decision_status ?? "not evaluated";
  const dryRunNonBlocking =
    preview !== null &&
    preview.dry_run_executed &&
    preview.dry_run_only &&
    preview.dry_run_status === "ready" &&
    preview.would_block === false &&
    ["allowed", "advisory"].includes(String(preflightStatus).toLowerCase());
  const readinessReady = readiness.status === "ready_for_future_manual_paper_submit";
  const handoffReady = handoff.status === "handoff_ready_for_future_manual_step";
  const auditPackageReady = auditPackage.status === "package_ready_for_future_manual_review";
  const approvalPackageReady = approvalPackage.status === "approval_package_ready_for_future_manual_review";
  const resolvedRouteIsBrokerOrders =
    result.resolved_route === "/broker/orders" &&
    result.canonical_paper_route === "/broker/orders" &&
    (preview?.resolved_route ?? "/broker/orders") === "/broker/orders" &&
    (preview?.canonical_paper_route ?? "/broker/orders") === "/broker/orders";
  const brokerModePaper =
    result.broker_account_mode === "paper" &&
    result.broker_mode.paper_trading_enabled &&
    (preview?.broker_account_mode ?? "paper") === "paper";
  const liveLocked =
    result.live_state === "ibkr_live_locked" &&
    result.live_trading_enabled === false &&
    (preview?.live_trading_enabled ?? false) === false;
  const workersNonSubmitting =
    result.workers_allowed_to_submit === false &&
    (preview?.workers_allowed_to_submit ?? false) === false;
  const noSubmitControlPresent = true;
  const noOrderSubmitted = result.is_submit === false && (preview?.is_submit ?? false) === false;
  const submitTimePreflightRequired = true;
  const submitTimeModeRecheckRequired = true;
  const submitTimeRiskRecheckRequired = true;
  const submitTimeDecisionPersistenceRequired = true;
  const submitTimeOperatorConfirmationRequired = true;
  const missingPayloadFields = [...approvalPackage.missingPayloadFields];
  const blockedReasons = uniqueMessages([
    result.blocked_reason,
    preview?.blocked_reason,
    ...readiness.blockedReasons,
    ...handoff.blockedReasons,
    ...auditPackage.blockedReasons,
    ...approvalPackage.blockedReasons,
    ...(preview?.preflight_decision?.blocking_items.map((item) => item.message) ?? []),
    ...(preview?.preflight_decision?.would_block_items.map((item) => item.message) ?? []),
  ]);
  const missingData = uniqueMessages([
    ...result.missing_data,
    ...(preview?.missing_data ?? []),
    ...readiness.missingData,
    ...handoff.missingData,
    ...auditPackage.missingData,
    ...approvalPackage.missingData,
  ]);
  const warnings = uniqueMessages([
    ...readiness.warnings,
    ...handoff.warnings,
    ...auditPackage.warnings,
    ...approvalPackage.warnings,
    ...(preview?.warnings.map((warning) => warning.message) ?? []),
  ]);
  const staleDataChecks = uniqueMessages([
    ...(preview?.warnings.map((warning) => warning.message) ?? []),
    ...readiness.staleDataWarnings,
    ...handoff.warnings,
  ]);
  const sourceLabelRechecks = uniqueMessages([
    `execution_source must remain ${preview?.resolved_execution_source ?? result.resolved_execution_source ?? "ibkr_paper"}`,
    `serious_paper_source must remain ${preview?.serious_paper_source ?? result.serious_paper_source}`,
    `canonical_paper_route must remain ${preview?.canonical_paper_route ?? result.canonical_paper_route}`,
    `broker_account_mode must remain ${preview?.broker_account_mode ?? result.broker_account_mode}`,
    `live_state must remain ${preview?.live_state ?? result.live_state}`,
    `positions_source would be rechecked as ${preview?.positions_source ?? "ibkr_paper"}`,
    `balance_source would be rechecked as ${preview?.balance_source ?? "ibkr_paper"}`,
  ]);
  const decisionLoggingRequirements = [
    "broker_submit_decision_service persistence would be required at the future guarded submit boundary.",
    "Submit-time decision status, blocked reasons, warnings, and preflight_json would be logged before any future guarded manual submit completes.",
    "Operator recommendation identity and future correlation identifiers would remain part of the guarded broker decision trail.",
  ];

  const finalPayloadReviewFields: ManualPaperSubmitHandoffPayloadField[] = [
    ...approvalPackage.futurePayloadPreviewFields,
    {
      code: "tif_review",
      label: "time_in_force review",
      required: false,
      satisfied: true,
      value: "DAY default would be rechecked",
      detail: "Submit-time time-in-force would still be reviewed even if the guarded broker path defaults to DAY.",
    },
    {
      code: "correlation_review",
      label: "recommendation_id / correlation_id",
      required: false,
      satisfied: true,
      value: result.recommendation_id,
      detail: "Recommendation identity would still be reviewed alongside any future guarded submit correlation id or client order id.",
    },
  ];

  const futureManualSubmitRoute =
    approvalPackageReady && missingPayloadFields.length === 0 ? "/broker/orders" : null;

  const evidenceChecklist: ManualPaperSubmitAuditChecklistItem[] = [
    {
      code: "recommendation_loaded",
      label: "Recommendation loaded",
      satisfied: true,
      detail: `Recommendation ${result.recommendation_id} is loaded into this preflight contract review.`,
    },
    {
      code: "route_check_completed",
      label: "Route-check completed",
      satisfied: true,
      detail: "The route-check evidence is present in this preflight contract.",
    },
    {
      code: "route_check_eligible",
      label: "Route-check eligible",
      satisfied: routeCheckEligible,
      detail: "Future guarded manual submit still depends on a route-check eligible recommendation.",
    },
    {
      code: "dry_run_preview_completed",
      label: "Dry-run preview completed",
      satisfied: dryRunCompleted,
      detail: "The preflight contract expects guarded broker dry-run evidence before future submit handoff.",
    },
    {
      code: "dry_run_non_blocking",
      label: "Dry-run non-blocking",
      satisfied: dryRunNonBlocking,
      detail: "Dry-run preflight findings must remain advisory-only or allowed before the contract can be ready.",
    },
    {
      code: "readiness_review_completed",
      label: "Readiness review completed",
      satisfied: true,
      detail: "Readiness review evidence is present in this read-only chain.",
    },
    {
      code: "readiness_review_ready",
      label: "Readiness review ready",
      satisfied: readinessReady,
      detail: "Readiness review must be ready before the preflight contract can progress.",
    },
    {
      code: "handoff_review_completed",
      label: "Handoff review completed",
      satisfied: true,
      detail: "Handoff review evidence is available in this preflight chain.",
    },
    {
      code: "handoff_review_ready",
      label: "Handoff review ready",
      satisfied: handoffReady,
      detail: "Handoff review must be ready before the preflight contract can progress.",
    },
    {
      code: "audit_package_completed",
      label: "Audit package completed",
      satisfied: true,
      detail: "Audit package evidence is available in this preflight chain.",
    },
    {
      code: "audit_package_ready",
      label: "Audit package ready",
      satisfied: auditPackageReady,
      detail: "Audit package must be ready before the preflight contract can progress.",
    },
    {
      code: "approval_package_completed",
      label: "Approval package completed",
      satisfied: true,
      detail: "Approval package evidence is available in this preflight chain.",
    },
    {
      code: "approval_package_ready",
      label: "Approval package ready",
      satisfied: approvalPackageReady,
      detail: "Approval package must be ready before the preflight contract can progress.",
    },
    {
      code: "resolved_route_is_broker_orders",
      label: "Resolved route is /broker/orders",
      satisfied: resolvedRouteIsBrokerOrders,
      detail: "The future guarded submit path must remain /broker/orders only when all paper checks align.",
    },
    {
      code: "broker_mode_paper",
      label: "Broker mode paper",
      satisfied: brokerModePaper,
      detail: "The contract fails closed outside coherent paper mode.",
    },
    {
      code: "live_locked",
      label: "Live locked",
      satisfied: liveLocked,
      detail: "Live trading remains locked in this preflight contract layer.",
    },
    {
      code: "workers_non_submitting",
      label: "Workers non-submitting",
      satisfied: workersNonSubmitting,
      detail: "Workers gain no broker submit authority from this preflight contract.",
    },
    {
      code: "no_submit_control_present",
      label: "No submit control present",
      satisfied: noSubmitControlPresent,
      detail: "This preflight contract is visibility-only and does not render a submit button.",
    },
    {
      code: "no_order_submitted",
      label: "No order submitted",
      satisfied: noOrderSubmitted,
      detail: "No /broker/orders call is made from this panel and no order is submitted here.",
    },
    {
      code: "submit_time_preflight_required",
      label: "Submit-time preflight required",
      satisfied: submitTimePreflightRequired,
      detail: "Broker preflight advisory and decision services would rerun at actual guarded submit time.",
    },
    {
      code: "submit_time_mode_recheck_required",
      label: "Submit-time mode recheck required",
      satisfied: submitTimeModeRecheckRequired,
      detail: "Broker mode and live-lock guards would rerun at actual guarded submit time.",
    },
    {
      code: "submit_time_risk_recheck_required",
      label: "Submit-time risk recheck required",
      satisfied: submitTimeRiskRecheckRequired,
      detail: "Trading-control and risk-limit checks would rerun at actual guarded submit time.",
    },
    {
      code: "submit_time_decision_persistence_required",
      label: "Submit-time decision persistence required",
      satisfied: submitTimeDecisionPersistenceRequired,
      detail: "Submit-time decision logging would still be required before any future guarded manual submit completes.",
    },
    {
      code: "submit_time_operator_confirmation_required",
      label: "Submit-time operator confirmation required",
      satisfied: submitTimeOperatorConfirmationRequired,
      detail: "A future guarded manual paper submit would still require explicit operator confirmation outside this read-only surface.",
    },
  ];

  const submitTimeRerunRequirements: ManualPaperSubmitPreflightRequirement[] = [
    {
      code: "broker_mode_recheck",
      label: "broker_mode_recheck",
      required: true,
      detail: "broker_mode_guard would rerun and must still resolve to coherent paper mode at actual guarded submit time.",
    },
    {
      code: "trading_control_recheck",
      label: "trading_control_recheck",
      required: true,
      detail: "trading_control_service would rerun before any future guarded manual submit can proceed.",
    },
    {
      code: "risk_limit_recheck",
      label: "risk_limit_recheck",
      required: true,
      detail: "Risk-limit and exposure checks would rerun at the actual guarded submit boundary.",
    },
    {
      code: "broker_preflight_rerun",
      label: "broker_preflight_rerun",
      required: true,
      detail: "broker_preflight_advisory_service and broker_preflight_decision_service would rerun at actual guarded submit time.",
    },
    {
      code: "dry_run_evidence_review",
      label: "dry_run_evidence_review",
      required: true,
      detail: "The latest dry-run evidence would still require operator review before any future guarded submit.",
    },
    {
      code: "payload_review",
      label: "payload_review",
      required: true,
      detail: "The final broker payload would still be reviewed before any future guarded manual submit.",
    },
    {
      code: "decision_persistence_required",
      label: "decision_persistence_required",
      required: true,
      detail: "broker_submit_decision persistence would still be required before any future guarded manual submit completes.",
    },
    {
      code: "live_lock_recheck",
      label: "live_lock_recheck",
      required: true,
      detail: "Live lock would still be rechecked and remain locked before any future guarded manual submit.",
    },
    {
      code: "source_label_recheck",
      label: "source_label_recheck",
      required: true,
      detail: "Execution-source and canonical paper source labels would still be rechecked at the guarded submit boundary.",
    },
    {
      code: "stale_data_recheck",
      label: "stale_data_recheck",
      required: true,
      detail: "Stale-data and advisory warnings would still be rechecked at actual guarded submit time.",
    },
    {
      code: "operator_confirmation_required",
      label: "operator_confirmation_required",
      required: true,
      detail: "A human operator would still need to confirm the guarded manual paper submit outside this read-only contract.",
    },
  ];

  const operatorConfirmations: ManualPaperSubmitPreflightRequirement[] = [
    {
      code: "confirm_payload_matches_recommendation",
      label: "confirm_payload_matches_recommendation",
      required: true,
      detail: "An operator would still need to confirm that the future broker payload still matches the approved recommendation context.",
    },
    {
      code: "confirm_live_remains_locked",
      label: "confirm_live_remains_locked",
      required: true,
      detail: "An operator would still need to confirm that live trading remains locked before any future guarded manual paper submit.",
    },
    {
      code: "confirm_workers_remain_non_submitting",
      label: "confirm_workers_remain_non_submitting",
      required: true,
      detail: "An operator would still need to confirm that workers remain non-submitting at the future guarded submit boundary.",
    },
    {
      code: "confirm_preflight_findings_accepted",
      label: "confirm_preflight_findings_accepted",
      required: true,
      detail: "An operator would still need to confirm that any advisory preflight findings remain acceptable before any future guarded manual submit.",
    },
  ];

  const hardBlocked =
    !brokerModePaper ||
    !resolvedRouteIsBrokerOrders ||
    !liveLocked ||
    !workersNonSubmitting ||
    !noOrderSubmitted ||
    (preview?.would_block ?? result.would_block) ||
    result.live_trading_enabled ||
    (preview?.live_trading_enabled ?? false);

  let status: ManualPaperSubmitPreflightContractStatus = "unknown";
  if (
    result.route_check_status === "missing_context" ||
    handoff.status === "missing_context" ||
    auditPackage.status === "missing_context" ||
    approvalPackage.status === "missing_context"
  ) {
    status = "missing_context";
  } else if (
    result.route_check_status === "blocked" ||
    handoff.status === "blocked" ||
    auditPackage.status === "blocked" ||
    approvalPackage.status === "blocked" ||
    hardBlocked
  ) {
    status = "blocked";
  } else if (missingData.length > 0 || missingPayloadFields.length > 0) {
    status = "missing_context";
  } else if (result.route_check_status === "unknown" || auditPackage.status === "unknown") {
    status = "preflight_not_available";
  } else if (!dryRunCompleted || approvalPackage.status === "dry_run_required") {
    status = "dry_run_required";
  } else if (!readinessReady || approvalPackage.status === "readiness_required") {
    status = "readiness_required";
  } else if (!handoffReady || handoff.status === "handoff_required") {
    status = "handoff_required";
  } else if (!auditPackageReady || approvalPackage.status === "audit_package_required") {
    status = "audit_package_required";
  } else if (approvalPackage.status === "approval_not_available" || !approvalPackageReady) {
    status = "approval_package_required";
  } else if (futureManualSubmitRoute === "/broker/orders") {
    status = "preflight_contract_ready_for_future_manual_step";
  }

  let title = "Guarded manual paper submit preflight contract is unknown";
  let body = "Preflight contract only, no order submitted. Use this read-only contract to review the final pre-submit checklist that would still need to be satisfied before any future guarded manual paper submit through /broker/orders.";
  let nextRequiredAction = "no_action_available";
  let nextRequiredActionDetail = approvalPackage.nextRequiredActionDetail;

  if (status === "missing_context") {
    title = "Missing context before preflight contract review";
    body = "Preflight contract only, no order submitted. Recommendation, dry-run, or payload context is still missing, so the final guarded pre-submit contract cannot be completed yet.";
    nextRequiredAction = "fix_missing_context";
    nextRequiredActionDetail = missingData[0] ?? missingPayloadFields[0] ?? approvalPackage.nextRequiredActionDetail;
  } else if (status === "blocked") {
    title = "Blocked before preflight contract";
    body = "Preflight contract only, no order submitted. Broker mode, live-lock, worker-submit, route, or preflight safety gates still block any future guarded manual paper submit preflight review.";
    nextRequiredAction = "review_blocked_reason";
    nextRequiredActionDetail = blockedReasons[0] ?? approvalPackage.nextRequiredActionDetail;
  } else if (status === "preflight_not_available") {
    title = "Preflight contract not available";
    body = "Preflight contract only, no order submitted. The current review chain does not yet expose a coherent pre-submit contract for future guarded manual paper submit review.";
    nextRequiredAction = "no_action_available";
    nextRequiredActionDetail = approvalPackage.nextRequiredActionDetail;
  } else if (status === "dry_run_required") {
    title = "Dry-run required before preflight contract";
    body = "Preflight contract only, no order submitted. The route-check is eligible, but a guarded broker dry-run preview is still required before this final pre-submit contract can be reviewed.";
    nextRequiredAction = "run_guarded_dry_run";
    nextRequiredActionDetail = "Run the guarded broker dry-run preview before relying on this preflight contract.";
  } else if (status === "readiness_required") {
    title = "Readiness review required before preflight contract";
    body = "Preflight contract only, no order submitted. Dry-run evidence exists, but readiness review has not yet cleared this recommendation for future guarded manual paper submit review.";
    nextRequiredAction = "complete_readiness_review";
    nextRequiredActionDetail = readiness.nextRequiredActionDetail;
  } else if (status === "handoff_required") {
    title = "Handoff review required before preflight contract";
    body = "Preflight contract only, no order submitted. Handoff review evidence still needs operator attention before the final guarded pre-submit contract can proceed.";
    nextRequiredAction = "complete_handoff_review";
    nextRequiredActionDetail = handoff.nextRequiredActionDetail;
  } else if (status === "audit_package_required") {
    title = "Audit package required before preflight contract";
    body = "Preflight contract only, no order submitted. The final pre-submit contract depends on the audit package being ready first.";
    nextRequiredAction = "complete_audit_package";
    nextRequiredActionDetail = auditPackage.nextRequiredActionDetail;
  } else if (status === "approval_package_required") {
    title = "Approval package required before preflight contract";
    body = "Preflight contract only, no order submitted. The final pre-submit contract depends on the approval package being ready first.";
    nextRequiredAction = "complete_approval_package";
    nextRequiredActionDetail = approvalPackage.nextRequiredActionDetail;
  } else if (status === "preflight_contract_ready_for_future_manual_step") {
    title = "Preflight contract ready for future manual step";
    body = "Preflight contract only, no order submitted. This final pre-submit checklist is ready for operator review before any future guarded manual paper submit step, which would still require guarded /broker/orders, submit-time preflight reruns, mode and risk rechecks, and decision logging.";
    nextRequiredAction = "preflight_contract_ready_for_future_manual_step";
    nextRequiredActionDetail = "Future manual paper submit would still require guarded /broker/orders, submit-time preflight would rerun, mode and risk checks would rerun, decision logging would be required, live trading remains locked, and workers cannot submit. No submit button is available here.";
  }

  return {
    status,
    title,
    body,
    evidenceChecklist,
    submitTimeRerunRequirements,
    operatorConfirmations,
    finalPayloadReviewFields,
    staleDataChecks,
    sourceLabelRechecks,
    decisionLoggingRequirements,
    missingPayloadFields,
    blockedReasons,
    missingData,
    warnings,
    futureManualSubmitRoute,
    brokerAccountMode: preview?.broker_account_mode ?? result.broker_account_mode,
    liveState: preview?.live_state ?? result.live_state,
    isCanonicalPaper: preview?.is_canonical_paper ?? result.is_canonical_paper,
    workersAllowedToSubmit: preview?.workers_allowed_to_submit ?? result.workers_allowed_to_submit,
    liveTradingEnabled: preview?.live_trading_enabled ?? result.live_trading_enabled,
    submittedOrder: !noOrderSubmitted,
    dryRunOnly: preview?.dry_run_only ?? false,
    approvalOnly: true,
    preflightContractOnly: true,
    wouldBlock: preview?.would_block ?? result.would_block,
    nextRequiredAction,
    nextRequiredActionDetail,
  };
}

export function deriveFutureManualSubmitDesignReview(
  result: PaperRecommendationRouteCheck,
  preview: PaperRecommendationBrokerDryRunPreview | null,
): FutureManualSubmitDesignReview {
  return {
    status: "design_only_not_enabled",
    title: "Future manual submit design review",
    body: "Design only, not enabled. This review maps the future guarded manual IBKR paper submit seam, submit-time checks, final operator confirmations, and decision logging requirements without adding any submit control or submit call.",
    futureSubmitRoute: "/broker/orders",
    existingBackendOwner: "POST /broker/orders -> broker.py -> BrokerService.submit_order",
    futureFrontendSurface: "/cockpit/in-flight-adjustments",
    futureFrontendOwner: "RecommendationRouteCheckPanel future guarded operator step",
    submitTimeChecks: [
      {
        code: "broker_mode_guard",
        label: "broker_mode_guard",
        value: "required later",
        detail: "The existing broker_mode_guard must still resolve to coherent paper mode immediately before any future guarded manual submit.",
      },
      {
        code: "trading_control_service",
        label: "trading_control_service",
        value: "required later",
        detail: "trading_control_service must rerun and keep live_order_submission_allowed false while paper order submission remains explicitly guarded.",
      },
      {
        code: "risk_limit_service",
        label: "risk_limit_service",
        value: "required later",
        detail: "risk_limit_service must rerun order notional, exposure, and position-cap checks at the existing submit boundary.",
      },
      {
        code: "trading_halt_service",
        label: "trading_halt_service",
        value: "required later",
        detail: "trading_halt_service must still allow paper continuation and fail closed for active halt states before submit.",
      },
      {
        code: "broker_preflight_decision_service",
        label: "broker_preflight_decision_service",
        value: "required later",
        detail: "broker_preflight_decision_service must rerun and keep would_block or blocking findings fail-closed at submit time.",
      },
      {
        code: "stale_data_and_source_labels",
        label: "stale_data_and_source_labels",
        value: "required later",
        detail: "The latest stale-data warnings and source labels must be rechecked so execution_source, serious_paper_source, canonical_paper_route, broker_account_mode, and live_state still match the guarded paper contract.",
      },
    ],
    finalOperatorConfirmations: [
      {
        code: "final_operator_confirmation_required",
        label: "final_operator_confirmation_required",
        value: "true",
        detail: "A human operator would still need to explicitly confirm the final payload and accept the latest preflight findings before any future guarded manual paper submit.",
      },
      {
        code: "submit_time_live_lock_recheck_required",
        label: "submit_time_live_lock_recheck_required",
        value: "true",
        detail: "An operator would still confirm that live remains locked and that this flow stays paper-only at actual submit time.",
      },
      {
        code: "submit_time_worker_submit_allowed",
        label: "submit_time_worker_submit_allowed",
        value: "false",
        detail: "Workers remain non-submitting; any future guarded paper submit stays operator-driven only.",
      },
    ],
    decisionRecords: [
      {
        code: "broker_submit_decision_row",
        label: "broker_submit_decision_row",
        value: "required later",
        detail: "BrokerSubmitDecision persistence must write the submit-time decision_status, allowed_to_submit flag, blocked reasons, warnings, source metadata, and submit gate JSON before a future guarded manual paper submit completes.",
      },
      {
        code: "audit_log_entry",
        label: "audit_log_entry",
        value: "required later",
        detail: "The existing broker route audit log must still record submit attempts, blocked states, and resulting broker_order_id or error metadata.",
      },
    ],
    lockedPayloadFields: [
      {
        code: "symbol_side_quantity",
        label: "symbol_side_quantity",
        value: `${result.ticker} ${result.side} ${result.quantity}`,
        detail: "Symbol, side, and quantity remain locked to the approved recommendation context and must still match the final guarded broker payload.",
      },
      {
        code: "order_type_and_prices",
        label: "order_type_and_prices",
        value: `${result.order_type}${result.limit_price === null ? "" : ` / ${result.limit_price}`}`,
        detail: "order_type, limit_price, and any future stop_price context must still pass request validation on the existing /broker/orders path.",
      },
      {
        code: "client_and_correlation_ids",
        label: "client_and_correlation_ids",
        value: result.recommendation_id,
        detail: "recommendation_id, client_order_id, and future correlation identifiers remain review fields so BrokerSubmitDecision and audit trails stay tied to the intended recommendation.",
      },
      {
        code: "account_and_route_labels",
        label: "account_and_route_labels",
        value: `${preview?.broker_account_mode ?? result.broker_account_mode} / /broker/orders`,
        detail: "broker_account_mode, canonical_paper_route, execution_source, and serious_paper_source remain locked review fields before any future submit enablement.",
      },
    ],
    blockStates: [
      "Block if route-check, dry-run preview, readiness review, handoff review, audit package, approval package, or preflight contract evidence is stale, missing, or blocked.",
      "Block if broker_mode_guard no longer resolves coherent paper mode.",
      "Block if trading_control_service or trading_halt_service reports live, halted, or unknown execution posture.",
      "Block if risk_limit_service, broker_preflight_decision_service, or request validation returns would_block, blocking, invalid, or unknown state.",
      "Block if source labels drift away from /broker/orders as the canonical paper route or if workers would be allowed to submit.",
    ],
    requiredTestsBeforeEnablement: [
      "Backend route tests must prove the future manual submit step still uses POST /broker/orders only and never creates a second submit seam.",
      "Backend service tests must prove submit-time broker mode, trading control, trading halt, risk, preflight, and BrokerSubmitDecision persistence rerun immediately before submit.",
      "Frontend tests must prove the cockpit review surface remains read-only until a later phase explicitly enables a guarded operator action.",
      "Responsive and browser tests must prove the review chain still has no horizontal overflow and still renders no submit-like controls in this phase.",
    ],
    intentionallyNotImplemented: [
      "No submit button was added in this block.",
      "No /broker/orders UI call was added in this block.",
      "No new BrokerService.submit_order path was added in this block.",
      "No worker or background submit path was added in this block.",
      "No live trading unlock or live submit enablement was added in this block.",
    ],
    finalOperatorConfirmationRequired: true,
    submitTimePreflightRerunRequired: true,
    submitTimeDecisionPersistenceRequired: true,
    submitTimeLiveLockRecheckRequired: true,
    submitTimeWorkerSubmitAllowed: false,
    submitButtonAvailable: false,
    orderSubmitted: false,
    enabledInThisPhase: false,
  };
}

export function deriveGuardedSubmitDecisionReview(
  result: PaperRecommendationRouteCheck,
  fallbackSymbol: string,
  preview: PaperRecommendationBrokerDryRunPreview | null,
  readiness: ManualPaperSubmitReadiness,
  handoff: ManualPaperSubmitHandoffReview,
  auditPackage: ManualPaperSubmitAuditPackage,
  approvalPackage: ManualPaperSubmitApprovalPackage,
  preflightContract: ManualPaperSubmitPreflightContract,
  futureManualSubmitDesignReview: FutureManualSubmitDesignReview,
): GuardedSubmitDecisionReview {
  const preflightDecisionStatus = String(preview?.preflight_decision?.decision_status ?? "unknown").toLowerCase();
  const routeCheckCompleted = result.route_check_status === "eligible";
  const routeMissingContext =
    result.route_check_status === "missing_context" ||
    result.missing_data.length > 0 ||
    !result.ticker ||
    !result.side ||
    result.quantity === null ||
    !result.order_type;
  const routeBlocked =
    result.route_check_status === "blocked" ||
    result.live_trading_enabled ||
    result.workers_allowed_to_submit ||
    result.live_state !== "ibkr_live_locked";
  const dryRunDecisionAvailable = preview !== null && preview.dry_run_executed;
  const dryRunNonBlocking =
    preview !== null &&
    preview.dry_run_executed &&
    preview.dry_run_only &&
    preview.mode_guard_ok === true &&
    preview.request_valid === true &&
    preview.would_block === false &&
    ["allowed", "advisory"].includes(preflightDecisionStatus);
  const readinessReviewReady = readiness.status === "ready_for_future_manual_paper_submit";
  const handoffReviewReady = handoff.status === "handoff_ready_for_future_manual_step";
  const auditPackageReady = auditPackage.status === "package_ready_for_future_manual_review";
  const approvalPackageReady = approvalPackage.status === "approval_package_ready_for_future_manual_review";
  const preflightContractReady = preflightContract.status === "preflight_contract_ready_for_future_manual_step";
  const submitDesignReviewReady = futureManualSubmitDesignReview.status === "design_only_not_enabled";
  const liveLocked =
    (preview?.live_state ?? preflightContract.liveState ?? result.live_state) === "ibkr_live_locked";
  const workersNonSubmitting =
    (preview?.workers_allowed_to_submit ?? result.workers_allowed_to_submit) === false;
  const noOrderSubmitted = result.is_submit === false && (preview?.is_submit ?? false) === false;
  const noSubmitControlPresent = true;
  const futureDecisionSourceDefined = true;
  const submitTimeDecisionPersistenceRequired = true;
  const secretScrubbingRequired = true;
  const futureSubmitRoute = preflightContractReady ? "/broker/orders" : null;
  const futureOrderCorrelationId = `manual_paper_submit:${result.recommendation_id}`;

  const blockedReasons = uniqueMessages([
    result.blocked_reason,
    preview?.blocked_reason,
    !liveLocked ? "Live remains fail-closed. Any live-mode attempt must be recorded as blocked and not submitted." : null,
    !workersNonSubmitting ? "Workers cannot gain broker submit authority. Any worker-submit-allowed posture must fail closed." : null,
    preview !== null && !dryRunNonBlocking
      ? "Dry-run evidence is present but still contains would-block, blocking, invalid, or unknown submit findings."
      : null,
    routeBlocked ? "Route-check safety posture is blocked before any future submit-decision review can be considered." : null,
  ]);

  const missingData = uniqueMessages([
    ...result.missing_data,
    ...(preview?.missing_data ?? []),
    routeMissingContext ? "Recommendation route-check context remains incomplete for future submit-decision review." : null,
    !dryRunDecisionAvailable ? "Guarded broker dry-run evidence is not yet available." : null,
  ]);

  const warnings = uniqueMessages([
    ...(preview?.warnings ?? []).map((entry) => entry.message),
    ...preflightContract.warnings,
    ...auditPackage.warnings,
  ]);

  let status: GuardedSubmitDecisionReviewStatus = "unknown";
  if (routeMissingContext || (preview?.dry_run_status ?? null) === "missing_context") {
    status = "missing_context";
  } else if (routeBlocked) {
    status = "blocked";
  } else if (!dryRunDecisionAvailable) {
    status = "dry_run_required";
  } else if (!dryRunNonBlocking || !liveLocked || !workersNonSubmitting || preflightContract.liveTradingEnabled) {
    status = "blocked";
  } else if (!approvalPackageReady) {
    status = "approval_required";
  } else if (!preflightContractReady) {
    status = "preflight_contract_required";
  } else if (!submitDesignReviewReady) {
    status = "design_review_required";
  } else if (
    routeCheckCompleted &&
    readinessReviewReady &&
    handoffReviewReady &&
    auditPackageReady &&
    approvalPackageReady &&
    preflightContractReady
  ) {
    status = "ready_for_future_decision_review";
  }

  let title = "Guarded operator submit-decision review is unknown";
  let body =
    "Submit-decision review only, no decision written and no order submitted. Use this read-only section to inspect what the existing guarded /broker/orders path would need to persist later.";
  let nextRequiredAction = "review_submit_decision_requirements";
  let nextRequiredActionDetail =
    "Use this section for operator review only. No decision write is performed now, no submit button is available here, and no /broker/orders call was made from this panel.";

  if (status === "missing_context") {
    title = "Missing context before submit-decision review";
    body =
      "Submit-decision review only, no decision written and no order submitted. Recommendation, route-check, or dry-run context is still incomplete, so the future submit-decision trail cannot be reviewed coherently yet.";
    nextRequiredAction = "complete_missing_context";
    nextRequiredActionDetail =
      "Complete the missing recommendation or review-chain context first. The submit-decision review stays fail-closed until that evidence exists.";
  } else if (status === "blocked") {
    title = "Blocked before submit-decision review";
    body =
      "Submit-decision review only, no decision written and no order submitted. Broker mode, live-lock, worker-submit, route, or dry-run preflight findings still block any future guarded manual paper submit decision trail.";
    nextRequiredAction = "resolve_blocking_safety_findings";
    nextRequiredActionDetail =
      "Resolve the blocking safety posture first. A future submit-decision review cannot proceed while any route, live-lock, worker-submit, or preflight fail-closed condition remains.";
  } else if (status === "dry_run_required") {
    title = "Dry-run required before submit-decision review";
    body =
      "Submit-decision review only, no decision written and no order submitted. The route-check is eligible, but the guarded broker dry-run decision evidence is still required before future submit-decision persistence can be reviewed.";
    nextRequiredAction = "run_guarded_broker_dry_run_preview";
    nextRequiredActionDetail =
      "Run the existing guarded broker dry-run preview first so the current dry-run decision source, would-block state, warnings, and scrubbed evidence can be reviewed.";
  } else if (status === "approval_required") {
    title = "Approval package required before submit-decision review";
    body =
      "Submit-decision review only, no decision written and no order submitted. The future decision trail depends on the approval package being ready first, because that package consolidates the last operator-facing approval evidence before submit time.";
    nextRequiredAction = "complete_approval_package_review";
    nextRequiredActionDetail =
      "Use the existing approval package to close the remaining upstream review gaps before relying on this future submit-decision review.";
  } else if (status === "preflight_contract_required") {
    title = "Preflight contract required before submit-decision review";
    body =
      "Submit-decision review only, no decision written and no order submitted. The future decision trail depends on the final preflight contract being ready first, because submit-time reruns and operator confirmations must already be defined.";
    nextRequiredAction = "complete_preflight_contract_review";
    nextRequiredActionDetail =
      "Use the existing preflight contract section to confirm the final rerun requirements, source-label rechecks, and operator confirmations before relying on future decision persistence requirements.";
  } else if (status === "design_review_required") {
    title = "Design review required before submit-decision review";
    body =
      "Submit-decision review only, no decision written and no order submitted. The future manual submit design review must still be present so the operator can see the intended guarded submit seam and later decision ownership.";
    nextRequiredAction = "complete_design_review";
    nextRequiredActionDetail =
      "Use the existing design review section first. The submit-decision review depends on the future /broker/orders seam and backend ownership already being mapped clearly.";
  } else if (status === "ready_for_future_decision_review") {
    title = "Submit-decision review ready for future decision review";
    body =
      "Submit-decision review only, no decision written and no order submitted. The current review chain is ready to show what the existing guarded /broker/orders path would persist later: a submit_preflight decision before submit, a submit_attempt decision at submit time, and blocked or live-locked attempt rows when guards fail closed.";
    nextRequiredAction = "review_future_submit_decision_trail";
    nextRequiredActionDetail =
      "Use this section to review the future decision trail only. Actual submit still stays on the existing guarded /broker/orders path, submit-time decision persistence would happen later, and no submit control is available here.";
  }

  return {
    status,
    title,
    body,
    evidenceChecklist: [
      {
        code: "route_check_completed",
        label: "route_check_completed",
        satisfied: routeCheckCompleted,
        detail: "The serious-paper route-check must already be eligible before a future submit-decision review can rely on the guarded paper path.",
      },
      {
        code: "dry_run_decision_available",
        label: "dry_run_decision_available",
        satisfied: dryRunDecisionAvailable,
        detail: "Existing dry-run decision evidence comes from BrokerService.dry_run_order with decision persistence enabled.",
      },
      {
        code: "dry_run_non_blocking",
        label: "dry_run_non_blocking",
        satisfied: dryRunNonBlocking,
        detail: "The latest dry-run decision must stay non-blocking, fail-closed on unknown, and keep would_block false before future submit review can proceed.",
      },
      {
        code: "readiness_review_ready",
        label: "readiness_review_ready",
        satisfied: readinessReviewReady,
        detail: "The existing readiness review must already be green before later decision review can be considered coherent.",
      },
      {
        code: "handoff_review_ready",
        label: "handoff_review_ready",
        satisfied: handoffReviewReady,
        detail: "The existing handoff review must already expose the future guarded /broker/orders route and payload context.",
      },
      {
        code: "audit_package_ready",
        label: "audit_package_ready",
        satisfied: auditPackageReady,
        detail: "The audit package must already consolidate the current source labels and decision references for later operator review.",
      },
      {
        code: "approval_package_ready",
        label: "approval_package_ready",
        satisfied: approvalPackageReady,
        detail: "The approval package must be ready before relying on a future submit-decision review.",
      },
      {
        code: "preflight_contract_ready",
        label: "preflight_contract_ready",
        satisfied: preflightContractReady,
        detail: "The preflight contract must already define submit-time reruns and operator confirmations before later decision persistence is credible.",
      },
      {
        code: "submit_design_review_ready",
        label: "submit_design_review_ready",
        satisfied: submitDesignReviewReady,
        detail: "The design review must already map the future guarded submit seam and backend owner.",
      },
      {
        code: "future_decision_source_defined",
        label: "future_decision_source_defined",
        satisfied: futureDecisionSourceDefined,
        detail: "The future submit source is defined as manual_paper_submit for this review layer.",
      },
      {
        code: "submit_time_decision_persistence_required",
        label: "submit_time_decision_persistence_required",
        satisfied: submitTimeDecisionPersistenceRequired,
        detail: "BrokerSubmitDecision persistence would still be required later at submit time.",
      },
      {
        code: "secret_scrubbing_required",
        label: "secret_scrubbing_required",
        satisfied: secretScrubbingRequired,
        detail: "Secret-like fields and raw portfolio context must stay scrubbed from decision payloads; warnings are reduced to safe audit fields only.",
      },
      {
        code: "live_locked",
        label: "live_locked",
        satisfied: liveLocked,
        detail: "Live remains locked. Any live-mode attempt would be recorded as a blocked submit attempt and never submitted.",
      },
      {
        code: "workers_non_submitting",
        label: "workers_non_submitting",
        satisfied: workersNonSubmitting,
        detail: "Workers cannot submit. Any future guarded paper submit remains operator-driven only.",
      },
      {
        code: "no_submit_control_present",
        label: "no_submit_control_present",
        satisfied: noSubmitControlPresent,
        detail: "This review surface remains read-only and renders no submit control.",
      },
      {
        code: "no_order_submitted",
        label: "no_order_submitted",
        satisfied: noOrderSubmitted,
        detail: "No order has been submitted from this review chain.",
      },
    ],
    existingDecisionWriters: [
      {
        code: "dry_run_writer",
        label: "BrokerService.dry_run_order -> BrokerPreflightDecisionService.persist_submit_decision -> BrokerSubmitDecisionService.persist",
        value: "source=dry_run before any submit",
        detail: "The guarded broker dry-run preview already writes a scrubbed append-only decision row today and never submits an order.",
      },
      {
        code: "submit_preflight_writer",
        label: "BrokerService.submit_order preflight path",
        value: "source=submit_preflight before broker submit",
        detail: "The existing guarded /broker/orders seam writes a pre-submit decision row before any broker execution attempt.",
      },
      {
        code: "submit_attempt_writer",
        label: "BrokerService.submit_order submit attempt path",
        value: "source=submit_attempt after guard/preflight outcome",
        detail: "The existing guarded /broker/orders seam writes a submit attempt row for allowed submits, blocked submits, fail-closed errors, and live-lock blocks.",
      },
    ],
    existingDecisionReaders: [
      {
        code: "recent_decision_route",
        label: "GET /broker/submit-decisions/recent",
        value: "audit-only reader",
        detail: "This read route returns recent append-only decision rows and never writes state.",
      },
      {
        code: "audit_surfaces",
        label: "/cockpit/audit and /cockpit/audit/broker-submit-decisions",
        value: "existing UI readers",
        detail: "Current UI readers expose the audit feed, but the in-flight review panel does not import that read helper today.",
      },
    ],
    futureDecisionRecords: [
      {
        code: "submit_preflight_decision_required",
        label: "submit_preflight_decision_required",
        value: "yes",
        detail: "A pre-submit decision row would need to be written before any future guarded manual paper submit proceeds.",
      },
      {
        code: "submit_attempt_decision_required",
        label: "submit_attempt_decision_required",
        value: "yes",
        detail: "A submit-attempt decision row would need to be written when the future guarded submit step actually evaluates the request.",
      },
      {
        code: "blocked_attempt_decision_required_if_any_guard_blocks",
        label: "blocked_attempt_decision_required_if_any_guard_blocks",
        value: "yes",
        detail: "If broker mode, trading control, request validation, risk, halt, or preflight blocks, the blocked attempt must still be recorded and fail closed.",
      },
      {
        code: "live_locked_attempt_record_required_if_live_mode",
        label: "live_locked_attempt_record_required_if_live_mode",
        value: "yes",
        detail: "A live-locked posture must still produce a blocked submit_attempt record with no broker order submission.",
      },
      {
        code: "dry_run_decision_reference",
        label: "dry_run_decision_reference",
        value: preview?.dry_run_executed ? "existing dry_run decision row" : "not available yet",
        detail: "The future submit trail would reference the latest dry_run decision evidence already produced by the guarded preview path.",
      },
      {
        code: "recommendation_id",
        label: "recommendation_id",
        value: result.recommendation_id,
        detail: "The future submit trail must stay tied to the reviewed recommendation.",
      },
      {
        code: "future_order_correlation_id",
        label: "future_order_correlation_id",
        value: futureOrderCorrelationId,
        detail: "A future correlation identifier would link the later submit_preflight row, submit_attempt row, and broker/audit logs.",
      },
      {
        code: "future_source",
        label: "future_source",
        value: "manual_paper_submit",
        detail: "The future operator-driven source label for this submit-decision trail would be manual_paper_submit.",
      },
      {
        code: "account_mode",
        label: "account_mode",
        value: "paper only",
        detail: "This review layer remains paper-only; live stays locked.",
      },
      {
        code: "execution_source",
        label: "execution_source",
        value: "ibkr_paper",
        detail: "The future guarded paper submit path still resolves to IBKR paper only when safe.",
      },
    ],
    persistedFieldChecklist: [
      {
        code: "source",
        label: "source",
        value: "required later",
        detail: "Persist the decision source label such as dry_run, submit_preflight, submit_attempt, or future manual_paper_submit correlation metadata.",
      },
      {
        code: "symbol",
        label: "symbol",
        value: result.ticker ?? fallbackSymbol,
        detail: "The intended symbol must remain tied to the recommendation context.",
      },
      {
        code: "side",
        label: "side",
        value: result.side ?? "unknown",
        detail: "The intended side must remain tied to the recommendation context.",
      },
      {
        code: "quantity_or_notional",
        label: "quantity/notional",
        value: result.quantity !== null ? String(result.quantity) : formatMaybeNumber(preview?.estimated_notional ?? null),
        detail: "Quantity or notional review must match the later guarded broker payload.",
      },
      {
        code: "order_type",
        label: "order_type",
        value: result.order_type ?? "unknown",
        detail: "The order type and any related price fields must still pass the existing request validation path.",
      },
      {
        code: "broker_account_mode",
        label: "broker_account_mode",
        value: preview?.broker_account_mode ?? result.broker_account_mode,
        detail: "The decision record must retain the paper-mode account context.",
      },
      {
        code: "execution_source",
        label: "execution_source",
        value: preview?.resolved_execution_source ?? result.resolved_execution_source ?? "ibkr_paper",
        detail: "The decision record must retain the resolved execution source and canonical paper route labels.",
      },
      {
        code: "would_block",
        label: "would_block",
        value: "required later",
        detail: "would_block remains a required persisted safety outcome and must fail closed on unknowns.",
      },
      {
        code: "blocking",
        label: "blocking",
        value: "required later",
        detail: "Blocking findings and counts must still be preserved in the decision payload.",
      },
      {
        code: "blocked_reasons",
        label: "blocked_reasons",
        value: "required later",
        detail: "Blocked reasons must be captured in scrubbed, append-only form.",
      },
      {
        code: "warnings",
        label: "warnings",
        value: "required later",
        detail: "Warnings must be persisted in scrubbed form with safe fields only.",
      },
      {
        code: "evidence",
        label: "evidence",
        value: "required later",
        detail: "The later decision trail must still link back to the current route-check, dry-run, and review-chain evidence.",
      },
      {
        code: "scrubbed_payload",
        label: "scrubbed_payload",
        value: "required later",
        detail: "Secret-like keys and raw portfolio context stay scrubbed; only capped safe message fields and additive source metadata are retained.",
      },
      {
        code: "created_at",
        label: "created_at",
        value: "required later",
        detail: "Append-only decision rows retain created_at for audit ordering.",
      },
      {
        code: "correlation_id",
        label: "correlation_id",
        value: futureOrderCorrelationId,
        detail: "Future decision rows should share correlation metadata with the later guarded submit attempt.",
      },
    ],
    reviewEvidenceLinks: [
      {
        code: "route_check_evidence",
        label: "route_check_evidence",
        value: result.route_check_status,
        detail: "Current route-check evidence establishes whether the canonical paper route is even eligible.",
      },
      {
        code: "dry_run_evidence",
        label: "dry_run_evidence",
        value: preview?.dry_run_status ?? "not run",
        detail: "Current dry-run evidence establishes today’s persisted dry_run decision posture.",
      },
      {
        code: "readiness_review_evidence",
        label: "readiness_review_evidence",
        value: readiness.status,
        detail: "Current readiness review confirms whether the recommendation is coherent for future manual paper submit review.",
      },
      {
        code: "handoff_review_evidence",
        label: "handoff_review_evidence",
        value: handoff.status,
        detail: "Current handoff review exposes the future guarded route and payload prerequisites.",
      },
      {
        code: "audit_package_evidence",
        label: "audit_package_evidence",
        value: auditPackage.status,
        detail: "Current audit package consolidates source labels and current decision references.",
      },
      {
        code: "approval_package_evidence",
        label: "approval_package_evidence",
        value: approvalPackage.status,
        detail: "Current approval package establishes whether final review evidence is ready.",
      },
      {
        code: "preflight_contract_evidence",
        label: "preflight_contract_evidence",
        value: preflightContract.status,
        detail: "Current preflight contract defines the reruns and operator confirmations that would still happen at submit time.",
      },
      {
        code: "design_review_evidence",
        label: "design_review_evidence",
        value: futureManualSubmitDesignReview.status,
        detail: "Current design review maps the future guarded submit seam and decision ownership.",
      },
    ],
    failClosedRules: [
      "would_block true blocks later submit decision creation and must be recorded as blocked.",
      "blocking true blocks later submit decision creation and must be recorded as blocked.",
      "unknown preflight status blocks later submit decision creation and must fail closed.",
      "live mode blocks and must be recorded as a blocked submit_attempt with no broker execution.",
      "missing payload or recommendation context blocks future decision creation.",
      "stale or missing route-check evidence blocks future decision creation.",
      "stale or missing dry-run evidence blocks future decision creation.",
      "live_trading_enabled true blocks later submit decision creation.",
      "workers_allowed_to_submit true blocks later submit decision creation.",
    ],
    blockedReasons,
    missingData,
    warnings,
    futureSubmitRoute,
    decisionPersistenceOwner:
      "BrokerPreflightDecisionService.persist_submit_decision -> BrokerSubmitDecisionService.persist",
    futureDecisionSource: "manual_paper_submit",
    futureOrderCorrelationId,
    dryRunDecisionReference: preview?.dry_run_executed ? "available from source=dry_run" : "not available yet",
    accountMode: "paper",
    executionSource: "ibkr_paper",
    liveState: preview?.live_state ?? preflightContract.liveState ?? result.live_state,
    workersAllowedToSubmit: preview?.workers_allowed_to_submit ?? result.workers_allowed_to_submit,
    liveTradingEnabled: preview?.live_trading_enabled ?? result.live_trading_enabled,
    submittedOrder: false,
    decisionWritePerformedNow: false,
    reviewOnly: true,
    noSubmitControlPresent,
    nextRequiredAction,
    nextRequiredActionDetail,
  };
}

export function deriveGuardedOperatorActionReview(
  result: PaperRecommendationRouteCheck,
  preview: PaperRecommendationBrokerDryRunPreview | null,
  readiness: ManualPaperSubmitReadiness,
  handoff: ManualPaperSubmitHandoffReview,
  auditPackage: ManualPaperSubmitAuditPackage,
  approvalPackage: ManualPaperSubmitApprovalPackage,
  preflightContract: ManualPaperSubmitPreflightContract,
  futureManualSubmitDesignReview: FutureManualSubmitDesignReview,
  submitDecisionReview: GuardedSubmitDecisionReview,
): GuardedOperatorActionReview {
  const preflightDecisionStatus = String(preview?.preflight_decision?.decision_status ?? "unknown").toLowerCase();
  const routeCheckCompleted = ["eligible", "blocked", "missing_context"].includes(result.route_check_status);
  const routeCheckEligible = result.route_check_status === "eligible";
  const routeMissingContext =
    result.route_check_status === "missing_context" ||
    result.missing_data.length > 0 ||
    !result.ticker ||
    !result.side ||
    result.quantity === null ||
    !result.order_type;
  const routeBlocked =
    result.route_check_status === "blocked" ||
    result.live_trading_enabled ||
    result.workers_allowed_to_submit ||
    result.live_state !== "ibkr_live_locked";
  const dryRunPreviewCompleted = preview !== null && preview.dry_run_executed;
  const dryRunNonBlocking =
    preview !== null &&
    preview.dry_run_executed &&
    preview.dry_run_only &&
    preview.mode_guard_ok === true &&
    preview.request_valid === true &&
    preview.would_block === false &&
    ["allowed", "advisory"].includes(preflightDecisionStatus);
  const readinessReviewReady = readiness.status === "ready_for_future_manual_paper_submit";
  const handoffReviewReady = handoff.status === "handoff_ready_for_future_manual_step";
  const auditPackageReady = auditPackage.status === "package_ready_for_future_manual_review";
  const approvalPackageReady = approvalPackage.status === "approval_package_ready_for_future_manual_review";
  const preflightContractReady = preflightContract.status === "preflight_contract_ready_for_future_manual_step";
  const designReviewReady = futureManualSubmitDesignReview.status === "design_only_not_enabled";
  const submitDecisionReviewReady = submitDecisionReview.status === "ready_for_future_decision_review";
  const canonicalRouteIsBrokerOrders =
    result.resolved_route === "/broker/orders" &&
    result.canonical_paper_route === "/broker/orders" &&
    (preview?.resolved_route ?? "/broker/orders") === "/broker/orders" &&
    (preview?.canonical_paper_route ?? "/broker/orders") === "/broker/orders";
  const brokerModePaper =
    result.broker_account_mode === "paper" &&
    result.broker_mode.paper_trading_enabled &&
    (preview?.broker_account_mode ?? result.broker_account_mode) === "paper";
  const liveLocked =
    (preview?.live_state ?? preflightContract.liveState ?? result.live_state) === "ibkr_live_locked";
  const workersNonSubmitting =
    (preview?.workers_allowed_to_submit ?? preflightContract.workersAllowedToSubmit ?? result.workers_allowed_to_submit) === false;
  const noSubmitControlPresent = true;
  const noOrderSubmitted = result.is_submit === false && (preview?.is_submit ?? false) === false;
  const submitTimeChecksRequired = true;
  const submitTimeDecisionLoggingRequired = true;
  const futureActionRoute = submitDecisionReviewReady ? "/broker/orders" : preflightContract.futureManualSubmitRoute;
  const futureActionName = "manual_ibkr_paper_submit";
  const actionAvailableNow = false;
  const wouldBlock =
    result.would_block ||
    (preview?.would_block ?? false) ||
    preflightContract.wouldBlock ||
    routeBlocked ||
    !liveLocked ||
    !workersNonSubmitting;

  const blockedReasons = uniqueMessages([
    result.blocked_reason,
    preview?.blocked_reason,
    ...preflightContract.blockedReasons,
    ...submitDecisionReview.blockedReasons,
    !liveLocked ? "Live trading remains fail-closed. Any live or unknown broker posture must keep the future action unavailable." : null,
    !workersNonSubmitting ? "Workers remain non-submitting. Any worker-submit-allowed posture must keep the future action unavailable." : null,
    !canonicalRouteIsBrokerOrders ? "The future manual paper action must stay pinned to guarded /broker/orders only when safe." : null,
  ]);

  const missingData = uniqueMessages([
    ...result.missing_data,
    ...(preview?.missing_data ?? []),
    ...preflightContract.missingData,
    ...submitDecisionReview.missingData,
    ...preflightContract.missingPayloadFields.map((field) => `Missing payload review field: ${field}`),
    routeMissingContext ? "Recommendation context is incomplete for a future manual operator action review." : null,
  ]);

  const warnings = uniqueMessages([
    ...auditPackage.warnings,
    ...approvalPackage.warnings,
    ...preflightContract.warnings,
    ...submitDecisionReview.warnings,
    ...(preview?.warnings ?? []).map((entry) => entry.message),
  ]);

  let status: GuardedOperatorActionReviewStatus = "unknown";
  if (routeMissingContext || (preview?.dry_run_status ?? null) === "missing_context") {
    status = "missing_context";
  } else if (routeBlocked) {
    status = "blocked";
  } else if (!dryRunPreviewCompleted) {
    status = "dry_run_required";
  } else if (!dryRunNonBlocking || !liveLocked || !workersNonSubmitting) {
    status = "blocked";
  } else if (!readinessReviewReady) {
    status = "readiness_required";
  } else if (!handoffReviewReady) {
    status = "handoff_required";
  } else if (!auditPackageReady) {
    status = "audit_package_required";
  } else if (!approvalPackageReady) {
    status = "approval_package_required";
  } else if (!preflightContractReady) {
    status = "preflight_contract_required";
  } else if (!designReviewReady) {
    status = "design_review_required";
  } else if (!submitDecisionReviewReady) {
    status = "submit_decision_review_required";
  } else if (!canonicalRouteIsBrokerOrders || !brokerModePaper) {
    status = "action_not_available";
  } else if (
    routeCheckEligible &&
    dryRunPreviewCompleted &&
    dryRunNonBlocking &&
    readinessReviewReady &&
    handoffReviewReady &&
    auditPackageReady &&
    approvalPackageReady &&
    preflightContractReady &&
    designReviewReady &&
    submitDecisionReviewReady
  ) {
    status = "action_review_ready_for_future_manual_step";
  }

  let title = "Guarded operator action review is unknown";
  let body =
    "Action review only, no order submitted. This read-only section shows what the future guarded manual paper action would be and why it stays unavailable in this phase.";
  let nextRequiredAction = "review_operator_action_requirements";
  let nextRequiredActionDetail =
    "Use this section for operator review only. Future manual paper submit would still use guarded /broker/orders when safe, but no submit button is available here and no decision is written now.";

  if (status === "missing_context") {
    title = "Missing context before operator action review";
    body =
      "Action review only, no order submitted. Recommendation, route-check, or review-chain context is still incomplete, so the future guarded operator action cannot be mapped safely yet.";
    nextRequiredAction = "fix_missing_context";
    nextRequiredActionDetail =
      "Complete the missing recommendation or review-chain context first. The future action stays unavailable and fail-closed until that evidence exists.";
  } else if (status === "blocked") {
    title = "Blocked before operator action review";
    body =
      "Action review only, no order submitted. Live-lock, worker-submit, route, or dry-run fail-closed findings still block any future guarded operator action.";
    nextRequiredAction = "review_blocked_reason";
    nextRequiredActionDetail =
      "Resolve the blocking safety posture first. The future action remains unavailable while any route, live-lock, worker-submit, or preflight fail-closed condition remains.";
  } else if (status === "dry_run_required") {
    title = "Dry-run required before operator action review";
    body =
      "Action review only, no order submitted. The route-check is eligible, but the guarded broker dry-run preview must run first so the future action can inherit current broker preflight evidence safely.";
    nextRequiredAction = "run_guarded_dry_run";
    nextRequiredActionDetail =
      "Run the existing guarded broker dry-run preview first. The future action cannot be reviewed coherently until the current non-submitting preflight evidence is present.";
  } else if (status === "readiness_required") {
    title = "Readiness review required before operator action review";
    body =
      "Action review only, no order submitted. The readiness review is not yet ready, so the future operator action remains unavailable.";
    nextRequiredAction = "complete_readiness_review";
    nextRequiredActionDetail =
      "Use the existing readiness review first so the later operator action remains tied to a coherent paper-mode recommendation context.";
  } else if (status === "handoff_required") {
    title = "Handoff review required before operator action review";
    body =
      "Action review only, no order submitted. The handoff review is not yet ready, so the future guarded action lacks a complete payload handoff.";
    nextRequiredAction = "complete_handoff_review";
    nextRequiredActionDetail =
      "Use the existing handoff review first so the later manual operator action inherits the guarded payload preview and operator handoff detail.";
  } else if (status === "audit_package_required") {
    title = "Audit package required before operator action review";
    body =
      "Action review only, no order submitted. The audit package is not yet ready, so the future action remains unavailable until the upstream review evidence is consolidated.";
    nextRequiredAction = "complete_audit_package";
    nextRequiredActionDetail =
      "Use the existing audit package first so the later action review inherits the consolidated source labels, decision references, and payload preview evidence.";
  } else if (status === "approval_package_required") {
    title = "Approval package required before operator action review";
    body =
      "Action review only, no order submitted. The approval package is not yet ready, so final operator approval evidence is still missing before any future guarded action could be considered.";
    nextRequiredAction = "complete_approval_package";
    nextRequiredActionDetail =
      "Use the existing approval package first. The future manual action remains unavailable until the approval review layer is ready.";
  } else if (status === "preflight_contract_required") {
    title = "Preflight contract required before operator action review";
    body =
      "Action review only, no order submitted. The preflight contract is not yet ready, so the submit-time reruns and final operator confirmations are not defined tightly enough for an action review.";
    nextRequiredAction = "complete_preflight_contract";
    nextRequiredActionDetail =
      "Use the existing preflight contract section first so the later action review stays grounded in the final submit-time reruns, confirmations, and fail-closed rules.";
  } else if (status === "design_review_required") {
    title = "Design review required before operator action review";
    body =
      "Action review only, no order submitted. The future manual submit design review must still map the canonical guarded seam before the future operator action can be reviewed coherently.";
    nextRequiredAction = "complete_design_review";
    nextRequiredActionDetail =
      "Use the existing design review section first so the future action remains tied to the existing guarded /broker/orders seam and backend owner.";
  } else if (status === "submit_decision_review_required") {
    title = "Submit-decision review required before operator action review";
    body =
      "Action review only, no order submitted. The future operator action still depends on the submit-decision review being ready first, because decision persistence and fail-closed attempt logging remain part of the canonical guarded submit seam.";
    nextRequiredAction = "complete_submit_decision_review";
    nextRequiredActionDetail =
      "Use the existing submit-decision review first so the future action remains tied to the required submit_preflight and submit_attempt decision trail.";
  } else if (status === "action_not_available") {
    title = "Action not available in this phase";
    body =
      "Action review only, no order submitted. The future manual paper action is mapped, but it is still intentionally unavailable in this phase and cannot be executed from this cockpit surface.";
    nextRequiredAction = "no_action_available";
    nextRequiredActionDetail =
      "Keep this surface review-only. Future manual paper submit would still use guarded /broker/orders when safe, but execution is intentionally unavailable now.";
  } else if (status === "action_review_ready_for_future_manual_step") {
    title = "Action review ready for future manual step";
    body =
      "Action review only, no order submitted. The current review chain is ready to show the future guarded manual operator action: manual IBKR paper submit through the existing /broker/orders seam, with final operator confirmations, submit-time reruns, and decision persistence still required later.";
    nextRequiredAction = "action_review_ready_for_future_manual_step";
    nextRequiredActionDetail =
      "This phase stops at operator visibility only. Future manual paper submit would still use guarded /broker/orders, but action_available_now remains false, no decision is written now, and no submit button is available here.";
  }

  return {
    status,
    title,
    body,
    evidenceChecklist: [
      {
        code: "route_check_completed",
        label: "route_check_completed",
        satisfied: routeCheckCompleted,
        detail: "The recommendation route-check must already exist before a future manual operator action can be reviewed.",
      },
      {
        code: "route_check_eligible",
        label: "route_check_eligible",
        satisfied: routeCheckEligible,
        detail: "The route-check must resolve the canonical serious-paper path before the future action can target guarded /broker/orders.",
      },
      {
        code: "dry_run_preview_completed",
        label: "dry_run_preview_completed",
        satisfied: dryRunPreviewCompleted,
        detail: "The existing guarded broker dry-run preview must already exist before the future action is reviewed.",
      },
      {
        code: "dry_run_non_blocking",
        label: "dry_run_non_blocking",
        satisfied: dryRunNonBlocking,
        detail: "The future action remains unavailable if the current dry-run evidence would block, is invalid, or is unknown.",
      },
      {
        code: "readiness_review_ready",
        label: "readiness_review_ready",
        satisfied: readinessReviewReady,
        detail: "Readiness review must already be ready before the future action is shown as coherent.",
      },
      {
        code: "handoff_review_ready",
        label: "handoff_review_ready",
        satisfied: handoffReviewReady,
        detail: "Handoff review must already expose the later guarded payload handoff.",
      },
      {
        code: "audit_package_ready",
        label: "audit_package_ready",
        satisfied: auditPackageReady,
        detail: "Audit package must already consolidate the upstream review evidence.",
      },
      {
        code: "approval_package_ready",
        label: "approval_package_ready",
        satisfied: approvalPackageReady,
        detail: "Approval package must already be ready before a future action is considered.",
      },
      {
        code: "preflight_contract_ready",
        label: "preflight_contract_ready",
        satisfied: preflightContractReady,
        detail: "Preflight contract must already define submit-time reruns and operator confirmations.",
      },
      {
        code: "design_review_ready",
        label: "design_review_ready",
        satisfied: designReviewReady,
        detail: "The design review must already map the future guarded submit seam.",
      },
      {
        code: "submit_decision_review_ready",
        label: "submit_decision_review_ready",
        satisfied: submitDecisionReviewReady,
        detail: "Submit-decision review must already map the later append-only decision trail.",
      },
      {
        code: "canonical_route_is_broker_orders",
        label: "canonical_route_is_broker_orders",
        satisfied: canonicalRouteIsBrokerOrders,
        detail: "The future manual paper action must stay pinned to guarded /broker/orders only when safe.",
      },
      {
        code: "broker_mode_paper",
        label: "broker_mode_paper",
        satisfied: brokerModePaper,
        detail: "The future manual action remains paper-only and must never unlock live mode.",
      },
      {
        code: "live_locked",
        label: "live_locked",
        satisfied: liveLocked,
        detail: "Live trading remains locked in this review phase.",
      },
      {
        code: "workers_non_submitting",
        label: "workers_non_submitting",
        satisfied: workersNonSubmitting,
        detail: "Workers remain non-submitting; the future manual action stays operator-driven only.",
      },
      {
        code: "no_submit_control_present",
        label: "no_submit_control_present",
        satisfied: noSubmitControlPresent,
        detail: "No submit control is rendered in this review surface.",
      },
      {
        code: "no_order_submitted",
        label: "no_order_submitted",
        satisfied: noOrderSubmitted,
        detail: "No order has been submitted from this review chain.",
      },
      {
        code: "submit_time_checks_required",
        label: "submit_time_checks_required",
        satisfied: submitTimeChecksRequired,
        detail: "Submit-time broker guard, trading-control, risk, halt, validation, and preflight checks would still rerun later.",
      },
      {
        code: "submit_time_decision_logging_required",
        label: "submit_time_decision_logging_required",
        satisfied: submitTimeDecisionLoggingRequired,
        detail: "Submit-time decision logging would still be required later on the existing guarded seam.",
      },
    ],
    futureActionDescription: [
      {
        code: "future_action_name",
        label: "future_action_name",
        value: futureActionName,
        detail: "The later operator-driven action would still be a manual IBKR paper submit.",
      },
      {
        code: "future_action_enabled_now",
        label: "future_action_enabled_now",
        value: "false",
        detail: "The future action is intentionally not enabled in this phase.",
      },
      {
        code: "future_action_route",
        label: "future_action_route",
        value: futureActionRoute ?? "not available",
        detail: "The actual future manual submit would still use guarded /broker/orders only when safe.",
      },
      {
        code: "future_action_requires_operator_confirmation",
        label: "future_action_requires_operator_confirmation",
        value: "true",
        detail: "Later execution would still require explicit operator confirmation.",
      },
      {
        code: "future_action_requires_submit_time_rechecks",
        label: "future_action_requires_submit_time_rechecks",
        value: "true",
        detail: "Later execution would still rerun submit-time safety checks.",
      },
      {
        code: "future_action_requires_decision_persistence",
        label: "future_action_requires_decision_persistence",
        value: "true",
        detail: "Later execution would still persist append-only decision rows on the canonical seam.",
      },
      {
        code: "future_action_worker_allowed",
        label: "future_action_worker_allowed",
        value: "false",
        detail: "Workers remain unable to submit broker orders.",
      },
      {
        code: "future_action_live_allowed",
        label: "future_action_live_allowed",
        value: "false",
        detail: "Live trading remains locked and cannot be enabled from this phase.",
      },
    ],
    finalOperatorConfirmations: preflightContract.operatorConfirmations.map((item) => ({
      code: item.code,
      label: item.label,
      value: item.required ? "required later" : "not required",
      detail: item.detail,
    })),
    finalPayloadPreview: preflightContract.finalPayloadReviewFields.map((item) => ({
      code: item.code,
      label: item.label,
      value: item.value,
      detail: item.detail,
    })),
    submitTimeChecks: preflightContract.submitTimeRerunRequirements.map((item) => ({
      code: item.code,
      label: item.label,
      value: item.required ? "required later" : "not required",
      detail: item.detail,
    })),
    futureDecisionRecords: submitDecisionReview.futureDecisionRecords,
    statesKeepingActionUnavailable: [
      ...futureManualSubmitDesignReview.blockStates,
      "Action review only. Future action is not enabled in this phase.",
      "Any live or unknown broker/account tuple must keep the action unavailable.",
      "Any worker-submit-allowed posture must keep the action unavailable.",
      "Any would_block, blocked, invalid, error, or unknown preflight outcome must keep the action unavailable.",
      "Any missing recommendation context or missing final payload field must keep the action unavailable.",
      "No submit button is available here and no /broker/orders call is made from this cockpit surface.",
    ],
    blockedReasons,
    missingData,
    warnings,
    futureActionName,
    futureActionRoute,
    submittedOrder: false,
    actionAvailableNow,
    actionReviewOnly: true,
    decisionWritePerformedNow: false,
    liveState: preview?.live_state ?? preflightContract.liveState ?? result.live_state,
    workersAllowedToSubmit: preview?.workers_allowed_to_submit ?? result.workers_allowed_to_submit,
    liveTradingEnabled: preview?.live_trading_enabled ?? result.live_trading_enabled,
    wouldBlock,
    noSubmitControlPresent,
    nextRequiredAction,
    nextRequiredActionDetail,
  };
}

export function deriveFinalGuardedSubmitInteractionSpec(
  result: PaperRecommendationRouteCheck,
  preview: PaperRecommendationBrokerDryRunPreview | null,
  preflightContract: ManualPaperSubmitPreflightContract,
  submitDecisionReview: GuardedSubmitDecisionReview,
  operatorActionReview: GuardedOperatorActionReview,
): FinalGuardedSubmitInteractionSpec {
  const routeMissingContext =
    result.route_check_status === "missing_context" ||
    preview?.dry_run_status === "missing_context" ||
    operatorActionReview.status === "missing_context";
  const routeBlocked = result.route_check_status === "blocked" || operatorActionReview.status === "blocked";
  const dryRunPreviewCompleted = preview !== null && preview.dry_run_executed;
  const operatorActionReviewReady = operatorActionReview.status === "action_review_ready_for_future_manual_step";
  const futureInteractionName = operatorActionReview.futureActionName;
  const canonicalRouteIsBrokerOrders =
    operatorActionReview.futureActionRoute === "/broker/orders" &&
    result.resolved_route === "/broker/orders" &&
    result.canonical_paper_route === "/broker/orders" &&
    (preview?.resolved_route ?? "/broker/orders") === "/broker/orders";
  const liveLocked = operatorActionReview.liveState === "ibkr_live_locked";
  const workersNonSubmitting = operatorActionReview.workersAllowedToSubmit === false;
  const actionAvailableNow = false;
  const interactionSpecReviewOnly = true;
  const decisionWritePerformedNow = false;
  const submittedOrder = false;
  const noSubmitControlPresent = true;
  const submitTimeChecksRerunLater = true;
  const futureInteractionRoute = operatorActionReviewReady && canonicalRouteIsBrokerOrders ? "/broker/orders" : null;

  const blockedReasons = uniqueMessages([
    ...operatorActionReview.blockedReasons,
    !canonicalRouteIsBrokerOrders
      ? "The final interaction spec must keep the future manual interaction pinned to guarded /broker/orders only when safe."
      : null,
    !liveLocked
      ? "Live trading remains fail-closed. Any live or unknown broker posture must keep the interaction spec read-only."
      : null,
    !workersNonSubmitting
      ? "Workers remain non-submitting. Any worker-submit-allowed posture must keep the interaction spec read-only."
      : null,
  ]);
  const missingData = uniqueMessages([
    ...operatorActionReview.missingData,
    ...preflightContract.missingData,
    ...preflightContract.missingPayloadFields.map((field) => `Missing interaction field: ${field}`),
  ]);
  const warnings = uniqueMessages([
    ...operatorActionReview.warnings,
    ...submitDecisionReview.warnings,
    ...preflightContract.warnings,
  ]);

  let status: FinalGuardedSubmitInteractionSpecStatus = "unknown";
  if (routeMissingContext) {
    status = "missing_context";
  } else if (routeBlocked || !liveLocked || !workersNonSubmitting) {
    status = "blocked";
  } else if (!dryRunPreviewCompleted) {
    status = "dry_run_required";
  } else if (!operatorActionReviewReady) {
    status = "operator_action_review_required";
  } else if (
    canonicalRouteIsBrokerOrders &&
    futureInteractionName === "manual_ibkr_paper_submit" &&
    operatorActionReview.actionAvailableNow === false &&
    operatorActionReview.decisionWritePerformedNow === false &&
    operatorActionReview.submittedOrder === false
  ) {
    status = "interaction_spec_ready_for_future_phase";
  }

  let title = "Final guarded submit interaction spec is unknown";
  let body =
    "Interaction spec only, no order submitted. This read-only section shows how a future guarded manual paper interaction would work while keeping action_available_now false in this phase.";
  let nextRequiredAction = "review_interaction_spec";
  let nextRequiredActionDetail =
    "Use this section for review only. Future manual paper submit would still use guarded /broker/orders when safe, but no submit button is available here and no decision is written now.";

  if (status === "missing_context") {
    title = "Missing context before final interaction spec";
    body =
      "Interaction spec only, no order submitted. Recommendation, dry-run, or review-chain context is still incomplete, so the final guarded manual interaction cannot be specified safely yet.";
    nextRequiredAction = "fix_missing_context";
    nextRequiredActionDetail =
      "Complete the missing recommendation or review-chain context first. The final interaction spec stays unavailable and fail-closed until that evidence exists.";
  } else if (status === "blocked") {
    title = "Blocked before final interaction spec";
    body =
      "Interaction spec only, no order submitted. Live-lock, worker-submit, route, or other fail-closed findings still block the future guarded manual interaction from being specified as ready.";
    nextRequiredAction = "review_blocked_reason";
    nextRequiredActionDetail =
      "Resolve the blocking safety posture first. The final interaction spec remains read-only while any route, live-lock, worker-submit, or preflight fail-closed condition remains.";
  } else if (status === "dry_run_required") {
    title = "Dry-run required before final interaction spec";
    body =
      "Interaction spec only, no order submitted. The route-check is eligible, but the guarded broker dry-run preview must run first so the final future interaction can inherit current broker preflight evidence safely.";
    nextRequiredAction = "run_guarded_dry_run";
    nextRequiredActionDetail =
      "Run the existing guarded broker dry-run preview first. The final interaction spec cannot be reviewed coherently until the current non-submitting preflight evidence is present.";
  } else if (status === "operator_action_review_required") {
    title = "Operator action review required before final interaction spec";
    body =
      "Interaction spec only, no order submitted. The final interaction spec still depends on the guarded operator action review being ready first, because the future action name, route, operator confirmations, rerun checks, and decision trail remain part of the canonical guarded submit seam.";
    nextRequiredAction = "complete_operator_action_review";
    nextRequiredActionDetail =
      "Use the existing operator action review first so the final interaction spec stays tied to manual_ibkr_paper_submit, guarded /broker/orders, submit-time reruns, and append-only decision persistence.";
  } else if (status === "interaction_spec_ready_for_future_phase") {
    title = "Final interaction spec ready for future phase";
    body =
      "Interaction spec only, no order submitted. The review chain is now ready to show exactly how a later approved guarded manual IBKR paper submit interaction would work while still stopping short of execution in this phase.";
    nextRequiredAction = "interaction_spec_ready_for_future_phase";
    nextRequiredActionDetail =
      "This phase stops at final interaction visibility only. Future manual paper submit would still use guarded /broker/orders, action_available_now remains false, no decision is written now, and no submit button is available here.";
  }

  return {
    status,
    title,
    body,
    evidenceChecklist: [
      {
        code: "dry_run_preview_completed",
        label: "dry_run_preview_completed",
        satisfied: dryRunPreviewCompleted,
        detail: "The existing guarded broker dry-run preview must already exist before the final interaction spec is coherent.",
      },
      {
        code: "operator_action_review_ready",
        label: "operator_action_review_ready",
        satisfied: operatorActionReviewReady,
        detail: "The operator action review must already be ready before the final interaction spec can describe the later manual interaction precisely.",
      },
      {
        code: "future_interaction_name_manual_ibkr_paper_submit",
        label: "future_interaction_name_manual_ibkr_paper_submit",
        satisfied: futureInteractionName === "manual_ibkr_paper_submit",
        detail: "The future interaction remains a manual IBKR paper submit only.",
      },
      {
        code: "future_interaction_route_guarded_broker_orders",
        label: "future_interaction_route_guarded_broker_orders",
        satisfied: canonicalRouteIsBrokerOrders,
        detail: "The later interaction must stay pinned to guarded /broker/orders only when safe.",
      },
      {
        code: "action_available_now_false",
        label: "action_available_now_false",
        satisfied: actionAvailableNow === false,
        detail: "The interaction remains unavailable in this phase.",
      },
      {
        code: "decision_write_performed_now_false",
        label: "decision_write_performed_now_false",
        satisfied: decisionWritePerformedNow === false,
        detail: "No decision row is written now from this read-only surface.",
      },
      {
        code: "submitted_order_false",
        label: "submitted_order_false",
        satisfied: submittedOrder === false,
        detail: "No order has been submitted from this interaction spec.",
      },
      {
        code: "submit_time_checks_rerun_later",
        label: "submit_time_checks_rerun_later",
        satisfied: submitTimeChecksRerunLater,
        detail: "Submit-time broker guard, trading-control, risk, halt, validation, and preflight checks would still rerun later.",
      },
      {
        code: "live_locked",
        label: "live_locked",
        satisfied: liveLocked,
        detail: "Live trading remains locked in this review phase.",
      },
      {
        code: "workers_non_submitting",
        label: "workers_non_submitting",
        satisfied: workersNonSubmitting,
        detail: "Workers remain non-submitting; the future interaction stays operator-driven only.",
      },
      {
        code: "no_submit_control_present",
        label: "no_submit_control_present",
        satisfied: noSubmitControlPresent,
        detail: "No submit control is rendered in this interaction spec surface.",
      },
    ],
    futureInteractionContract: [
      {
        code: "future_interaction_name",
        label: "future_interaction_name",
        value: futureInteractionName,
        detail: "The later operator-driven interaction would still be manual_ibkr_paper_submit.",
      },
      {
        code: "future_interaction_route",
        label: "future_interaction_route",
        value: futureInteractionRoute ?? "not available",
        detail: "The actual future manual submit would still use guarded /broker/orders only when safe.",
      },
      {
        code: "action_available_now",
        label: "action_available_now",
        value: actionAvailableNow ? "true" : "false",
        detail: "Execution remains intentionally unavailable in this phase.",
      },
      {
        code: "decision_write_performed_now",
        label: "decision_write_performed_now",
        value: decisionWritePerformedNow ? "true" : "false",
        detail: "No decision write occurs from this interaction spec.",
      },
      {
        code: "submitted_order",
        label: "submitted_order",
        value: submittedOrder ? "true" : "false",
        detail: "No order is submitted from this interaction spec.",
      },
      {
        code: "submit_time_checks_rerun_later",
        label: "submit_time_checks_rerun_later",
        value: submitTimeChecksRerunLater ? "true" : "false",
        detail: "Submit-time checks would rerun later on the canonical guarded seam.",
      },
      {
        code: "live_allowed_now",
        label: "live_allowed_now",
        value: "false",
        detail: "Live trading remains locked and cannot be enabled from this phase.",
      },
      {
        code: "workers_allowed_now",
        label: "workers_allowed_now",
        value: "false",
        detail: "Workers remain unable to submit broker orders.",
      },
    ],
    finalOperatorConfirmations: operatorActionReview.finalOperatorConfirmations.map((item) => ({
      code: item.code,
      label: item.label,
      value: item.value,
      detail: item.detail,
    })),
    finalPayloadPreview: operatorActionReview.finalPayloadPreview.map((item) => ({
      code: item.code,
      label: item.label,
      value: item.value,
      detail: item.detail,
    })),
    submitTimeChecks: operatorActionReview.submitTimeChecks.map((item) => ({
      code: item.code,
      label: item.label,
      value: item.value,
      detail: item.detail,
    })),
    futureDecisionRecords: operatorActionReview.futureDecisionRecords.map((item) => ({
      code: item.code,
      label: item.label,
      value: item.value,
      detail: item.detail,
    })),
    laterInteractionSequence: [
      "Review this interaction spec only. No submit button is available here and no /broker/orders call is made from this cockpit surface.",
      "A later approved phase could expose manual_ibkr_paper_submit only after the existing guarded operator action review is ready.",
      "That later interaction would still require explicit operator confirmation before any submit attempt.",
      "That later interaction would still rerun submit-time broker, trading-control, risk, halt, validation, and preflight checks.",
      "That later interaction would still persist append-only submit_preflight and submit_attempt decision rows on the canonical guarded seam.",
      "This phase stops before execution: no decision is written now, no order is submitted, live remains locked, and workers cannot submit.",
    ],
    statesKeepingInteractionReadOnly: [
      "Interaction spec only. The future manual interaction is not enabled in this phase.",
      "Any live or unknown broker/account tuple must keep the interaction spec read-only.",
      "Any worker-submit-allowed posture must keep the interaction spec read-only.",
      "Any would_block, blocked, invalid, error, or unknown preflight outcome must keep the interaction spec read-only.",
      "Any missing recommendation context or missing final payload field must keep the interaction spec read-only.",
      "No submit button is available here and no /broker/orders call is made from this cockpit surface.",
    ],
    blockedReasons,
    missingData,
    warnings,
    futureInteractionName,
    futureInteractionRoute,
    actionAvailableNow,
    interactionSpecReviewOnly,
    decisionWritePerformedNow,
    submittedOrder,
    liveState: operatorActionReview.liveState,
    workersAllowedToSubmit: operatorActionReview.workersAllowedToSubmit,
    liveTradingEnabled: operatorActionReview.liveTradingEnabled,
    submitTimeChecksRerunLater,
    noSubmitControlPresent,
    nextRequiredAction,
    nextRequiredActionDetail,
  };
}

export function deriveManualPaperSubmitReviewChain(
  result: PaperRecommendationRouteCheck | null,
  preview: PaperRecommendationBrokerDryRunPreview | null,
  fallbackSymbol: string,
): ManualPaperSubmitReviewChain {
  if (!result) {
    return {
      readiness: null,
      handoff: null,
      auditPackage: null,
      approvalPackage: null,
      preflightContract: null,
      futureManualSubmitDesignReview: null,
      submitDecisionReview: null,
      operatorActionReview: null,
      finalInteractionSpec: null,
    };
  }

  const readiness = deriveManualPaperSubmitReadiness(result, preview);
  const handoff = deriveManualPaperSubmitHandoffReview(result, preview, readiness);
  const auditPackage = deriveManualPaperSubmitAuditPackage(result, preview, readiness, handoff);
  const approvalPackage = deriveManualPaperSubmitApprovalPackage(result, preview, readiness, handoff, auditPackage);
  const preflightContract = deriveManualPaperSubmitPreflightContract(
    result,
    preview,
    readiness,
    handoff,
    auditPackage,
    approvalPackage,
  );
  const futureManualSubmitDesignReview = deriveFutureManualSubmitDesignReview(result, preview);
  const submitDecisionReview = deriveGuardedSubmitDecisionReview(
    result,
    fallbackSymbol,
    preview,
    readiness,
    handoff,
    auditPackage,
    approvalPackage,
    preflightContract,
    futureManualSubmitDesignReview,
  );
  const operatorActionReview = preview
    ? deriveGuardedOperatorActionReview(
        result,
        preview,
        readiness,
        handoff,
        auditPackage,
        approvalPackage,
        preflightContract,
        futureManualSubmitDesignReview,
        submitDecisionReview,
      )
    : null;
  const finalInteractionSpec =
    preview && operatorActionReview
      ? deriveFinalGuardedSubmitInteractionSpec(
          result,
          preview,
          preflightContract,
          submitDecisionReview,
          operatorActionReview,
        )
      : null;

  return {
    readiness,
    handoff,
    auditPackage,
    approvalPackage,
    preflightContract,
    futureManualSubmitDesignReview,
    submitDecisionReview,
    operatorActionReview,
    finalInteractionSpec,
  };
}