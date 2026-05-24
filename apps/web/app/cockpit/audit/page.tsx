"use client";

// MH-OBS-AUDIT-INDEX — Cockpit audit hub (read-only).
//
// Lists every cockpit audit tile with a one-line description and a live
// row count fetched from the underlying read-only endpoint (`limit=1` is
// enough — the count returned is the response envelope's recent-window
// count). Pure navigation + read-only fetch surface.
//
// Drift-lock guarantee: this page never issues a mutating request, never
// surfaces a trading toggle, and does not change any worker, broker,
// trading_control, or risk behaviour.

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { getRecentBrokerSubmitDecisions } from "../../../lib/api/brokerSubmitDecisions";
import { getRecentLLMLogs } from "../../../lib/api/llmLogs";
import { getRecentNewsInDecisionLog } from "../../../lib/api/newsInDecisionLog";
import { getRecentRiskDecisions } from "../../../lib/api/riskDecisions";
import { getWorkerRunLogOverview } from "../../../lib/api/workerRunLog";
import styles from "../../../styles/pages/cockpit-audit-index.module.css";

interface AuditTile {
  href: string;
  title: string;
  description: string;
  countLabel: string;
  loadCount: () => Promise<number>;
}

const TILES: ReadonlyArray<AuditTile> = [
  {
    href: "/cockpit/audit/broker-submit-decisions",
    title: "Broker Submit Decisions",
    description:
      "Read-only broker submit decision timeline covering dry-runs, submit preflight gates, blocked attempts, and paper submit outcomes.",
    countLabel: "rows in latest window",
    loadCount: async () => {
      const resp = await getRecentBrokerSubmitDecisions({ limit: 200 });
      return resp.count;
    },
  },
  {
    href: "/cockpit/audit/news-in-decision-log",
    title: "News-in-Decision Audit Log",
    description:
      "Audit log of news items consumed by future decision pipelines (MH-NEWS-08-A2). Empty until MH-NEWS-08-B writer ships.",
    countLabel: "rows in latest window",
    loadCount: async () => {
      const resp = await getRecentNewsInDecisionLog({ limit: 200 });
      return resp.count;
    },
  },
  {
    href: "/cockpit/audit/risk-decisions",
    title: "Risk Decisions Audit",
    description:
      "Read-only view of the deterministic risk-engine decision table (MH-RISK-AUDIT-A). Populated by the existing risk evaluator.",
    countLabel: "rows in latest window",
    loadCount: async () => {
      const resp = await getRecentRiskDecisions({ limit: 200 });
      return resp.count;
    },
  },
  {
    href: "/cockpit/audit/llm-logs",
    title: "LLM Logs Audit",
    description:
      "Read-only view of redacted LLM round-trips (MH-150). Previews are redacted at write time.",
    countLabel: "rows in latest window",
    loadCount: async () => {
      const resp = await getRecentLLMLogs({ limit: 200 });
      return resp.count;
    },
  },
  {
    href: "/cockpit/audit/worker-run-log",
    title: "Worker Run Log Audit",
    description:
      "Read-only view of recent auto-paper worker runs and retention status (MH-158-A).",
    countLabel: "entries in latest window",
    loadCount: async () => {
      const resp = await getWorkerRunLogOverview(200);
      return resp.totals.returned;
    },
  },
];

interface CountState {
  status: "loading" | "ready" | "error";
  value: number | null;
  error: string | null;
}

const INITIAL_COUNT: CountState = {
  status: "loading",
  value: null,
  error: null,
};

export default function CockpitAuditIndexPage() {
  const [counts, setCounts] = useState<Record<string, CountState>>(() =>
    Object.fromEntries(TILES.map((t) => [t.href, INITIAL_COUNT])),
  );
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);
  const [refreshing, setRefreshing] = useState<boolean>(false);

  const load = useCallback(async () => {
    setRefreshing(true);
    setCounts(
      Object.fromEntries(TILES.map((t) => [t.href, INITIAL_COUNT])),
    );
    const results = await Promise.allSettled(
      TILES.map((tile) => tile.loadCount()),
    );
    const next: Record<string, CountState> = {};
    TILES.forEach((tile, i) => {
      const r = results[i];
      if (r.status === "fulfilled") {
        next[tile.href] = { status: "ready", value: r.value, error: null };
      } else {
        next[tile.href] = {
          status: "error",
          value: null,
          error: r.reason instanceof Error ? r.reason.message : String(r.reason),
        };
      }
    });
    setCounts(next);
    setLastRefreshed(new Date());
    setRefreshing(false);
  }, []);

  useEffect(() => {
    void load();
    // Initial load only; subsequent refreshes are user-driven.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <main className={styles.page}>
      <div className={styles.container}>
        <header className={styles.header}>
          <div>
            <h1 className={styles.title}>Cockpit · Audit</h1>
            <p className={styles.subtitle}>
              Read-only audit surfaces. Each tile links to a dedicated page
              backed by a read-only API endpoint. No tile modifies any
              decision, order, news record, or trading state.
            </p>
          </div>
          <div className={styles.headerActions}>
            <Link href="/cockpit" className={styles.linkPill}>
              ← Cockpit hub
            </Link>
            <button
              type="button"
              className={styles.refreshButton}
              onClick={() => void load()}
              disabled={refreshing}
            >
              {refreshing ? "Refreshing…" : "Refresh"}
            </button>
            {lastRefreshed && (
              <span className={styles.refreshTimestamp}>
                refreshed {lastRefreshed.toLocaleTimeString()}
              </span>
            )}
          </div>
        </header>

        <div className={styles.driftLockNotice}>
          Drift lock: every linked page is strictly read-only and surfaces
          audit trails without exposing trading controls. Auto-paper, auto,
          and live trading remain OFF.
        </div>

        <div className={styles.tileGrid}>
          {TILES.map((tile) => {
            const c = counts[tile.href] ?? INITIAL_COUNT;
            return (
              <Link key={tile.href} href={tile.href} className={styles.tile}>
                <div className={styles.tileHead}>
                  <h2 className={styles.tileTitle}>{tile.title}</h2>
                  <span className={styles.tileBadge}>read-only</span>
                </div>
                <p className={styles.tileDesc}>{tile.description}</p>
                <div className={styles.tileFoot}>
                  <span className={styles.countLabel}>{tile.countLabel}</span>
                  <span className={styles.countValue}>
                    {c.status === "loading" && "…"}
                    {c.status === "ready" && (c.value ?? 0)}
                    {c.status === "error" && "error"}
                  </span>
                </div>
                {c.status === "error" && c.error && (
                  <div className={styles.tileError} title={c.error}>
                    {c.error}
                  </div>
                )}
              </Link>
            );
          })}
        </div>
      </div>
    </main>
  );
}
