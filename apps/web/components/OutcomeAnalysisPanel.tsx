"use client";

import { useEffect, useMemo, useState } from "react";

import { CompactBars } from "./CompactBars";
import { getExecutionJournalEntries, subscribeExecutionJournal, type ExecutionJournalEntry } from "../lib/api";
import type { PaperExecutionResponse } from "../lib/types";

interface OutcomeAnalysisPanelProps {
  executions: PaperExecutionResponse[];
  lifecycleDepths: Record<string, number>;
}

function panelStyle(): React.CSSProperties {
  return {
    display: "grid",
    gap: 12,
    padding: 18,
    borderRadius: 18,
    border: "1px solid var(--surface-border)",
    background: "var(--surface-fill)",
    boxShadow: "var(--surface-shadow)",
  };
}

function countBy<T extends string>(items: T[]): Record<T, number> {
  const result = {} as Record<T, number>;
  for (const item of items) {
    result[item] = (result[item] ?? 0) + 1;
  }
  return result;
}

export function OutcomeAnalysisPanel({ executions, lifecycleDepths }: OutcomeAnalysisPanelProps) {
  const [entries, setEntries] = useState<ExecutionJournalEntry[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadEntries() {
      try {
        const next = await getExecutionJournalEntries(executions);
        if (cancelled) return;
        setEntries(next);
        setErrorMessage(null);
      } catch (error) {
        if (cancelled) return;
        setErrorMessage(error instanceof Error ? error.message : "Failed to load journal outcomes.");
      }
    }

    void loadEntries();
    const unsubscribe = subscribeExecutionJournal(() => {
      void loadEntries();
    });

    return () => {
      cancelled = true;
      unsubscribe();
    };
  }, [executions]);

  const insights = useMemo(() => {
    const entryMap = new Map<string, ExecutionJournalEntry>();
    for (const entry of entries) {
      entryMap.set(entry.executionId, entry);
    }

    const withJournal = executions.filter((execution) => entryMap.has(execution.execution_id));
    const journaled = withJournal.map((execution) => ({ execution, entry: entryMap.get(execution.execution_id)! }));

    const outcomeCounts = countBy(journaled.map((item) => item.entry.outcomeTag));
    const sideCounts = countBy(journaled.map((item) => item.execution.side.toLowerCase()));
    const assetCounts = countBy(journaled.map((item) => item.execution.asset.toUpperCase()));
    const tagCounts = countBy(journaled.flatMap((item) => item.entry.tags.length > 0 ? item.entry.tags : ["untagged"]));

    const worked = journaled.filter((item) => item.entry.outcomeTag === "worked" || item.entry.outcomeTag === "partial");
    const failed = journaled.filter((item) => item.entry.outcomeTag === "stopped_out" || item.entry.outcomeTag === "invalidated");

    const workedSummary = worked.length === 0
      ? "No positive outcome-tagged notes yet."
      : `Worked best in ${countBy(worked.map((item) => item.execution.side.toLowerCase())).buy ? "buy-side" : "current mix"} setups with tags like ${[...new Set(worked.flatMap((item) => item.entry.tags))].slice(0, 3).join(", ") || "none"}.`;

    const failedSummary = failed.length === 0
      ? "No failed outcome-tagged notes yet."
      : `Failed outcomes are clustering around ${[...new Set(failed.map((item) => item.execution.asset.toUpperCase()))].slice(0, 3).join(", ")} and tags like ${[...new Set(failed.flatMap((item) => item.entry.tags))].slice(0, 3).join(", ") || "none"}.`;

    const averageDepth = journaled.length === 0
      ? 0
      : journaled.reduce((sum, item) => sum + (lifecycleDepths[item.execution.execution_id] ?? 0), 0) / journaled.length;

    return {
      journaledCount: journaled.length,
      unjournaledCount: Math.max(0, executions.length - journaled.length),
      outcomeCounts,
      sideCounts,
      assetCounts,
      tagCounts,
      workedSummary,
      failedSummary,
      averageDepth,
    };
  }, [entries, executions, lifecycleDepths]);

  const outcomeItems = Object.entries(insights.outcomeCounts)
    .sort(([, a], [, b]) => b - a)
    .map(([label, value]) => ({ label, value, color: label === "worked" ? "var(--state-success)" : label === "partial" ? "var(--state-warning)" : "var(--state-danger)" }));

  const tagItems = Object.entries(insights.tagCounts)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 8)
    .map(([label, value]) => ({ label, value, color: "var(--state-info)" }));

  const sideItems = Object.entries(insights.sideCounts)
    .sort(([, a], [, b]) => b - a)
    .map(([label, value]) => ({ label, value, color: label.includes("sell") || label.includes("short") ? "var(--state-danger)" : "var(--state-success)" }));

  const assetItems = Object.entries(insights.assetCounts)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 6)
    .map(([label, value]) => ({ label, value, color: "var(--state-warning)" }));

  return (
    <section style={{ display: "grid", gap: 14 }}>
      {errorMessage ? <p style={{ margin: 0, color: "var(--state-danger)", fontSize: 12 }}>{errorMessage}</p> : null}
      <div style={{ display: "grid", gap: 12, gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))" }}>
        <article style={panelStyle()}>
          <span style={{ color: "var(--text-muted)", fontSize: 11, textTransform: "uppercase", letterSpacing: 1.1 }}>Journaled executions</span>
          <strong style={{ color: "var(--accent-highlight)", fontSize: 26, fontVariantNumeric: "tabular-nums" }}>{insights.journaledCount}</strong>
        </article>
        <article style={panelStyle()}>
          <span style={{ color: "var(--text-muted)", fontSize: 11, textTransform: "uppercase", letterSpacing: 1.1 }}>Still unjournaled</span>
          <strong style={{ color: "var(--state-danger)", fontSize: 26, fontVariantNumeric: "tabular-nums" }}>{insights.unjournaledCount}</strong>
        </article>
        <article style={panelStyle()}>
          <span style={{ color: "var(--text-muted)", fontSize: 11, textTransform: "uppercase", letterSpacing: 1.1 }}>Avg lifecycle depth</span>
          <strong style={{ color: "var(--state-info)", fontSize: 26, fontVariantNumeric: "tabular-nums" }}>{insights.averageDepth.toFixed(2)}</strong>
        </article>
      </div>

      <div style={{ display: "grid", gap: 14, gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))" }}>
        <CompactBars title="Outcome Breakdown" subtitle="By saved outcome tag" items={outcomeItems} />
        <CompactBars title="By Tag Summary" subtitle="Most-used operator tags" items={tagItems} />
        <CompactBars title="By Side Summary" subtitle="Journaled outcomes by side" items={sideItems} />
        <CompactBars title="By Asset Summary" subtitle="Journaled outcomes by asset" items={assetItems} />
      </div>

      <div style={{ display: "grid", gap: 14, gridTemplateColumns: "1fr 1fr" }}>
        <article style={panelStyle()}>
          <h3 style={{ margin: 0, color: "var(--text-strong)", fontSize: 18 }}>What Worked</h3>
          <p style={{ margin: 0, color: "var(--text-muted)", fontSize: 13, lineHeight: 1.6 }}>{insights.workedSummary}</p>
        </article>
        <article style={panelStyle()}>
          <h3 style={{ margin: 0, color: "var(--text-strong)", fontSize: 18 }}>What Failed</h3>
          <p style={{ margin: 0, color: "var(--text-muted)", fontSize: 13, lineHeight: 1.6 }}>{insights.failedSummary}</p>
        </article>
      </div>
    </section>
  );
}
