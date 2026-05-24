"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  getRecentBrokerSubmitDecisions,
  type BrokerSubmitDecisionRow,
  type BrokerSubmitDecisionsResponse,
} from "../../../../lib/api/brokerSubmitDecisions";
import styles from "../../../../styles/pages/cockpit-audit-broker-submit-decisions.module.css";

const LIMIT_OPTIONS = [25, 50, 100, 200];
const INTENT_OPTIONS: ReadonlyArray<{ value: string; label: string }> = [
  { value: "", label: "any intent" },
  { value: "auto", label: "auto" },
  { value: "manual", label: "manual" },
  { value: "paper", label: "paper" },
];
const SOURCE_OPTIONS: ReadonlyArray<{ value: string; label: string }> = [
  { value: "", label: "any source" },
  { value: "dry_run", label: "dry_run" },
  { value: "submit_preflight", label: "submit_preflight" },
  { value: "submit_attempt", label: "submit_attempt" },
];
const STATUS_OPTIONS: ReadonlyArray<{ value: string; label: string }> = [
  { value: "", label: "any decision status" },
  { value: "allowed", label: "allowed" },
  { value: "advisory", label: "advisory" },
  { value: "would_block", label: "would_block" },
  { value: "blocked", label: "blocked" },
  { value: "error", label: "error" },
];
const BLOCK_OPTIONS: ReadonlyArray<{
  value: "any" | "blocked" | "passed";
  label: string;
}> = [
  { value: "any", label: "any outcome" },
  { value: "blocked", label: "would-block" },
  { value: "passed", label: "passed preflight" },
];

function formatTimestamp(value: string | null): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString();
}

function shortId(value: string | null): string {
  if (!value) return "—";
  return value.length > 8 ? `${value.slice(0, 8)}…` : value;
}

function formatCount(value: number): string {
  return value.toLocaleString("en-US");
}

function prettyLabel(value: string | null): string {
  if (!value) return "—";
  return value.replaceAll("_", " ");
}

function formatNumber(value: number | null): string {
  if (value === null) return "—";
  return value.toLocaleString("en-US", { maximumFractionDigits: 4 });
}

function formatRequestSummary(row: BrokerSubmitDecisionRow): string {
  const summary = row.request_summary;
  if (!summary) return "No safe order summary captured.";

  const parts = [summary.ticker, summary.side, summary.quantity !== null ? formatNumber(summary.quantity) : null, summary.order_type]
    .filter((value): value is string => Boolean(value));
  const headline = parts.length > 0 ? parts.join(" • ") : "Order summary available";
  if (summary.limit_price !== null) {
    return `${headline} @ ${formatNumber(summary.limit_price)}`;
  }
  if (summary.stop_price !== null) {
    return `${headline} stop ${formatNumber(summary.stop_price)}`;
  }
  return headline;
}

function outcomeClass(row: BrokerSubmitDecisionRow): string {
  if (row.would_block || row.decision_status === "would_block" || row.decision_status === "blocked") {
    return styles.badgeBlocked;
  }
  if (row.decision_status === "error") {
    return styles.badgeError;
  }
  return styles.badgePassed;
}

function outcomeLabel(row: BrokerSubmitDecisionRow): string {
  if (row.decision_status) return prettyLabel(row.decision_status);
  return row.would_block ? "would block" : "allowed";
}

function MessageList({
  title,
  items,
  emptyMessage,
}: {
  title: string;
  items: BrokerSubmitDecisionRow["warnings"];
  emptyMessage: string;
}) {
  return (
    <section className={styles.inlineSection}>
      <h3 className={styles.inlineTitle}>{title}</h3>
      {items.length === 0 ? (
        <p className={styles.emptyInline}>{emptyMessage}</p>
      ) : (
        <ul className={styles.messageList}>
          {items.map((item, index) => (
            <li key={`${title}-${item.code ?? item.message ?? index}`} className={styles.messageItem}>
              <span className={styles.messageHead}>
                {item.code ?? "note"}
                {item.classification ? ` • ${prettyLabel(item.classification)}` : ""}
                {item.severity ? ` • ${item.severity}` : ""}
              </span>
              <span className={styles.messageBody}>{item.message ?? "No message recorded."}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function DecisionCard({ row }: { row: BrokerSubmitDecisionRow }) {
  return (
    <article className={styles.card} data-testid="broker-submit-decision-card">
      <div className={styles.cardHeader}>
        <div>
          <p className={styles.cardEyebrow}>{row.source ?? "unknown source"}</p>
          <h2 className={styles.cardTitle}>{formatRequestSummary(row)}</h2>
          <p className={styles.cardSubtitle}>
            {row.decision_reason ?? row.blocked_reason_text ?? "No decision reason recorded."}
          </p>
        </div>
        <div className={styles.cardBadges}>
          <span className={outcomeClass(row)}>{outcomeLabel(row)}</span>
          <span className={styles.badgeNeutral}>{row.intent}</span>
        </div>
      </div>

      <div className={styles.metaGrid}>
        <div className={styles.metaItem}><span className={styles.metaLabel}>created</span><span className={styles.metaValue}>{formatTimestamp(row.created_at)}</span></div>
        <div className={styles.metaItem}><span className={styles.metaLabel}>submit gate</span><span className={styles.metaValue}>{prettyLabel(row.submit_gate)}</span></div>
        <div className={styles.metaItem}><span className={styles.metaLabel}>broker order</span><span className={`${styles.metaValue} ${styles.mono}`}>{row.broker_order_id ?? "—"}</span></div>
        <div className={styles.metaItem}><span className={styles.metaLabel}>recommendation</span><span className={`${styles.metaValue} ${styles.mono}`}>{row.recommendation_id ?? "—"}</span></div>
        <div className={styles.metaItem}><span className={styles.metaLabel}>correlation</span><span className={`${styles.metaValue} ${styles.mono}`}>{row.correlation_id ?? "—"}</span></div>
        <div className={styles.metaItem}><span className={styles.metaLabel}>signal</span><span className={`${styles.metaValue} ${styles.mono}`}>{row.signal_id ?? "—"}</span></div>
      </div>

      <div className={styles.detailGrid}>
        <section className={styles.inlineSection}>
          <h3 className={styles.inlineTitle}>Routing and mode</h3>
          <ul className={styles.kvList}>
            <li><span className={styles.kvKey}>execution source</span><span className={styles.kvValue}>{row.execution_source ?? row.execution_mode ?? "—"}</span></li>
            <li><span className={styles.kvKey}>paper source</span><span className={styles.kvValue}>{row.serious_paper_source ?? "—"}</span></li>
            <li><span className={styles.kvKey}>canonical route</span><span className={`${styles.kvValue} ${styles.mono}`}>{row.canonical_paper_route ?? "—"}</span></li>
            <li><span className={styles.kvKey}>broker account mode</span><span className={styles.kvValue}>{row.broker_account_mode ?? row.account_mode ?? "—"}</span></li>
            <li><span className={styles.kvKey}>live state</span><span className={styles.kvValue}>{row.live_state ?? "—"}</span></li>
          </ul>
        </section>

        <section className={styles.inlineSection}>
          <h3 className={styles.inlineTitle}>Review references</h3>
          <ul className={styles.kvList}>
            <li><span className={styles.kvKey}>route-check reference</span><span className={`${styles.kvValue} ${styles.mono}`}>{row.route_check_reference ?? "—"}</span></li>
            <li><span className={styles.kvKey}>dry-run reference</span><span className={`${styles.kvValue} ${styles.mono}`}>{row.dry_run_reference ?? "—"}</span></li>
            <li><span className={styles.kvKey}>risk profile</span><span className={`${styles.kvValue} ${styles.mono}`}>{row.risk_profile_id ?? "—"}</span></li>
            <li><span className={styles.kvKey}>risk block reason</span><span className={styles.kvValue}>{row.risk_block_reason ?? "—"}</span></li>
          </ul>
        </section>
      </div>

      <MessageList
        title="Blocked reasons"
        items={row.blocked_reasons}
        emptyMessage="No blocking or would-block reasons were recorded for this row."
      />
      <MessageList
        title="Warnings"
        items={row.warnings}
        emptyMessage="No warnings were recorded for this row."
      />
    </article>
  );
}

export default function BrokerSubmitDecisionsAuditPage() {
  const [snapshot, setSnapshot] =
    useState<BrokerSubmitDecisionsResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);

  const [limit, setLimit] = useState<number>(25);
  const [intent, setIntent] = useState<string>("");
  const [source, setSource] = useState<string>("");
  const [decisionStatus, setDecisionStatus] = useState<string>("");
  const [blockFilter, setBlockFilter] = useState<"any" | "blocked" | "passed">(
    "any",
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const wouldBlock =
        blockFilter === "any" ? null : blockFilter === "blocked";
      const resp = await getRecentBrokerSubmitDecisions({
        limit,
        intent: intent || null,
        wouldBlock,
        source: source || null,
        decisionStatus: decisionStatus || null,
      });
      setSnapshot(resp);
      setLastRefreshed(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, [limit, intent, source, decisionStatus, blockFilter]);

  useEffect(() => {
    void load();
  }, [load]);

  const items = snapshot?.items;
  const advisory = snapshot?.advisory ?? null;
  const summary = useMemo(() => {
    const currentItems = items ?? [];
    const blocked = currentItems.filter((item) => item.would_block).length;
    const allowed = currentItems.filter((item) => !item.would_block).length;
    const submitAttempts = currentItems.filter((item) => item.source === "submit_attempt").length;
    const linkedRecommendations = new Set(
      currentItems
        .map((item) => item.recommendation_id)
        .filter((value): value is string => Boolean(value)),
    ).size;
    return {
      visible: currentItems.length,
      blocked,
      allowed,
      submitAttempts,
      linkedRecommendations,
    };
  }, [items]);

  return (
    <main className={styles.page} data-testid="broker-submit-decisions-timeline-page">
      <div className={styles.container}>
        <header className={styles.header}>
          <div>
            <p className={styles.eyebrow}>Read-only paper submit history</p>
            <h1 className={styles.title}>Broker submit decision timeline</h1>
            <p className={styles.subtitle}>
              Read-only timeline of dry-run decisions, submit preflight gates,
              and paper submit outcomes emitted by the guarded broker seam.
              This page never submits, retries, or alters any order.
            </p>
          </div>
          <div className={styles.headerActions}>
            <Link href="/cockpit" className={styles.linkPill}>
              Cockpit hub
            </Link>
            <Link href="/cockpit/audit" className={styles.linkPill}>
              Audit hub
            </Link>
            <button
              type="button"
              className={styles.refreshButton}
              onClick={() => {
                void load();
              }}
              disabled={loading}
            >
              {loading ? "Refreshing…" : "Refresh"}
            </button>
            {lastRefreshed && (
              <span className={styles.refreshTimestamp}>
                refreshed {lastRefreshed.toLocaleTimeString()}
              </span>
            )}
          </div>
        </header>

        <section className={styles.filters}>
          <label className={styles.filterLabel} htmlFor="limit">
            Limit
          </label>
          <select
            id="limit"
            className={styles.filterSelect}
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
          >
            {LIMIT_OPTIONS.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>

          <label className={styles.filterLabel} htmlFor="intent">
            Intent
          </label>
          <select
            id="intent"
            className={styles.filterSelect}
            value={intent}
            onChange={(e) => setIntent(e.target.value)}
          >
            {INTENT_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>

          <label className={styles.filterLabel} htmlFor="source">
            Source
          </label>
          <select
            id="source"
            className={styles.filterSelect}
            value={source}
            onChange={(e) => setSource(e.target.value)}
          >
            {SOURCE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>

          <label className={styles.filterLabel} htmlFor="block">
            Outcome
          </label>
          <select
            id="block"
            className={styles.filterSelect}
            value={blockFilter}
            onChange={(e) =>
              setBlockFilter(e.target.value as "any" | "blocked" | "passed")
            }
          >
            {BLOCK_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>

          <label className={styles.filterLabel} htmlFor="decision-status">
            Status
          </label>
          <select
            id="decision-status"
            className={styles.filterSelect}
            value={decisionStatus}
            onChange={(e) => setDecisionStatus(e.target.value)}
          >
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </section>

        {advisory && <div className={styles.advisory}>{advisory}</div>}

        <div className={styles.driftLockNotice}>
          Drift lock: this page is strictly read-only. It only reads the
          append-only decision log and cannot submit, cancel, approve, or rerun
          any broker action.
        </div>

        <section className={styles.summaryGrid} data-testid="broker-submit-decisions-summary">
          <article className={styles.summaryCard}><span className={styles.summaryLabel}>Visible rows</span><span className={styles.summaryValue}>{formatCount(summary.visible)}</span></article>
          <article className={styles.summaryCard}><span className={styles.summaryLabel}>Would-block rows</span><span className={styles.summaryValue}>{formatCount(summary.blocked)}</span></article>
          <article className={styles.summaryCard}><span className={styles.summaryLabel}>Allowed/advisory rows</span><span className={styles.summaryValue}>{formatCount(summary.allowed)}</span></article>
          <article className={styles.summaryCard}><span className={styles.summaryLabel}>Submit attempts</span><span className={styles.summaryValue}>{formatCount(summary.submitAttempts)}</span></article>
          <article className={styles.summaryCard}><span className={styles.summaryLabel}>Linked recommendations</span><span className={styles.summaryValue}>{formatCount(summary.linkedRecommendations)}</span></article>
        </section>

        {error && <div className={styles.errorBanner}>{error}</div>}

        {!error && (items?.length ?? 0) === 0 && !loading ? (
          <div className={styles.empty}>
            No broker submit decisions matched the current filters. The timeline
            remains read-only and will populate as dry-runs, preflight checks,
            and paper submit attempts are evaluated.
          </div>
        ) : (
          <section className={styles.cardList} data-testid="broker-submit-decisions-item-list">
            {(items ?? []).map((row) => (
              <DecisionCard key={row.id} row={row} />
            ))}
          </section>
        )}
      </div>
    </main>
  );
}
