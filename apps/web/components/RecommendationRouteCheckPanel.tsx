"use client";

import Link from "next/link";
import { useState } from "react";

import {
  getPaperRecommendationRouteCheck,
  type PaperRecommendationRouteCheck,
} from "../lib/api/paperRecommendations";
import styles from "./RecommendationRouteCheckPanel.module.css";

function statusClassName(status: string): string {
  if (status === "eligible") return styles.statusEligible;
  if (status === "blocked") return styles.statusBlocked;
  if (status === "missing_context") return styles.statusMissing;
  return styles.statusUnknown;
}

function summaryClassName(status: string): string {
  if (status === "eligible") return styles.summaryEligible;
  if (status === "blocked") return styles.summaryBlocked;
  if (status === "missing_context") return styles.summaryMissing;
  return styles.summaryUnknown;
}

function formatStatus(status: string): string {
  return status.replaceAll("_", " ");
}

function formatMaybeNumber(value: number | null): string {
  if (value === null) return "unknown";
  return value.toLocaleString("en-US", { maximumFractionDigits: 4 });
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

export function RecommendationRouteCheckPanel({
  recommendationId,
  symbol,
}: {
  recommendationId: string;
  symbol: string;
}) {
  const [result, setResult] = useState<PaperRecommendationRouteCheck | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const response = await getPaperRecommendationRouteCheck(recommendationId);
      setResult(response);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : String(loadError));
    } finally {
      setLoading(false);
    }
  }

  const summary = result ? summaryCopy(result) : null;

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
        </>
      ) : null}
    </section>
  );
}