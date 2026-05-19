"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import {
  getExecutionJournalEntries,
  subscribeExecutionJournal,
  type ExecutionJournalEntry,
} from "../lib/api";
import type { PaperExecutionResponse } from "../lib/types";

interface JournalAttentionWidgetProps {
  recentExecutions: PaperExecutionResponse[];
}

function relativeTimeLabel(isoTimestamp: string): string {
  const timestamp = Date.parse(isoTimestamp);
  if (Number.isNaN(timestamp)) {
    return "saved recently";
  }

  const deltaMinutes = Math.max(0, Math.round((Date.now() - timestamp) / 60000));
  if (deltaMinutes < 1) return "just now";
  if (deltaMinutes < 60) return `${deltaMinutes}m ago`;
  const hours = Math.round(deltaMinutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  return `${days}d ago`;
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

export function JournalAttentionWidget({ recentExecutions }: JournalAttentionWidgetProps) {
  const [entries, setEntries] = useState<ExecutionJournalEntry[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadEntries() {
      try {
        const next = await getExecutionJournalEntries(recentExecutions);
        if (cancelled) return;
        setEntries(next);
        setErrorMessage(null);
      } catch (error) {
        if (cancelled) return;
        setErrorMessage(error instanceof Error ? error.message : "Failed to load journal attention.");
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
  }, [recentExecutions]);

  const entryByExecutionId = useMemo(() => {
    const map = new Map<string, ExecutionJournalEntry>();
    for (const entry of entries) {
      map.set(entry.executionId, entry);
    }
    return map;
  }, [entries]);

  const untaggedExecutions = useMemo(() => {
    return recentExecutions
      .filter((execution) => {
        const entry = entryByExecutionId.get(execution.execution_id);
        return !entry || (entry.tags.length === 0 && entry.note.trim().length === 0);
      })
      .slice(0, 4);
  }, [entryByExecutionId, recentExecutions]);

  const latestNotes = useMemo(() => {
    return [...entries]
      .filter((entry) => entry.note.trim().length > 0)
      .sort((a, b) => Date.parse(b.updatedAt) - Date.parse(a.updatedAt))
      .slice(0, 3);
  }, [entries]);

  return (
    <article style={panelStyle()}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        <div style={{ display: "grid", gap: 4 }}>
          <h2 style={{ margin: 0, color: "var(--text-strong)", fontSize: 20 }}>Journal Attention</h2>
          <p style={{ margin: 0, color: "var(--text-muted)", fontSize: 12 }}>
            Backend-backed journal notes and execution review attention.
          </p>
        </div>
        <Link href="/execution" style={{ color: "var(--state-info)", fontSize: 12, textDecoration: "none", fontWeight: 700 }}>
          Open execution journaling
        </Link>
      </div>

      <div style={{ display: "grid", gap: 10, gridTemplateColumns: "1fr 1fr" }}>
        {errorMessage ? <div style={{ color: "var(--state-danger)", fontSize: 12 }}>{errorMessage}</div> : null}
        <section style={{ display: "grid", gap: 8 }}>
          <span style={{ color: "var(--text-muted)", fontSize: 11, textTransform: "uppercase", letterSpacing: 1.1, fontWeight: 700 }}>
            Untagged Recent Executions
          </span>
          {untaggedExecutions.length === 0 ? (
            <div style={{ color: "var(--state-success)", fontSize: 12 }}>Recent executions have at least one note or tag.</div>
          ) : (
            untaggedExecutions.map((execution) => (
              <Link
                key={execution.execution_id}
                href={`/execution?executionId=${encodeURIComponent(execution.execution_id)}&asset=${encodeURIComponent(execution.asset)}&status=${encodeURIComponent(execution.status)}`}
                style={{
                  textDecoration: "none",
                  display: "grid",
                  gap: 4,
                  padding: "10px 12px",
                  borderRadius: 10,
                  border: "1px solid var(--surface-border)",
                  background: "var(--surface-soft)",
                }}
              >
                <span style={{ color: "var(--text-body)", fontSize: 12 }}>{execution.asset}</span>
                <span style={{ color: "var(--text-muted)", fontSize: 11, fontVariantNumeric: "tabular-nums" }}>
                  {execution.execution_id.slice(0, 8)}...{execution.execution_id.slice(-4)}
                </span>
              </Link>
            ))
          )}
        </section>

        <section style={{ display: "grid", gap: 8 }}>
          <span style={{ color: "var(--text-muted)", fontSize: 11, textTransform: "uppercase", letterSpacing: 1.1, fontWeight: 700 }}>
            Latest Notes Preview
          </span>
          {latestNotes.length === 0 ? (
            <div style={{ color: "var(--text-muted)", fontSize: 12 }}>No journal notes saved yet.</div>
          ) : (
            latestNotes.map((entry) => (
              <Link
                key={entry.executionId}
                href={`/execution?executionId=${encodeURIComponent(entry.executionId)}`}
                style={{
                  textDecoration: "none",
                  display: "grid",
                  gap: 4,
                  padding: "10px 12px",
                  borderRadius: 10,
                  border: "1px solid var(--surface-border)",
                  background: "var(--surface-soft)",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                  <span style={{ color: "var(--accent-highlight)", fontSize: 11, fontWeight: 700 }}>{entry.outcomeTag}</span>
                  <span style={{ color: "var(--text-muted)", fontSize: 11 }}>{relativeTimeLabel(entry.updatedAt)}</span>
                </div>
                <span style={{ color: "var(--text-body)", fontSize: 12, lineHeight: 1.4 }}>
                  {entry.note.length > 84 ? `${entry.note.slice(0, 84)}...` : entry.note}
                </span>
              </Link>
            ))
          )}
        </section>
      </div>
    </article>
  );
}
