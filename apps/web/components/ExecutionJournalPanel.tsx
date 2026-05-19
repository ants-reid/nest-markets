"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import {
  getExecutionJournalEntry,
  saveExecutionJournalEntry,
  subscribeExecutionJournal,
  type ExecutionJournalEntry,
  type JournalOutcomeTag,
} from "../lib/api";
import type { PaperExecutionResponse } from "../lib/types";

interface ExecutionJournalPanelProps {
  detail: PaperExecutionResponse | null;
  selectedExecutionId: string | null;
}

const OUTCOME_OPTIONS: JournalOutcomeTag[] = [
  "untagged",
  "worked",
  "partial",
  "stopped_out",
  "expired",
  "invalidated",
];

function panelInnerStyle(): React.CSSProperties {
  return {
    display: "grid",
    gap: 12,
  };
}

function inputStyle(): React.CSSProperties {
  return {
    width: "100%",
    borderRadius: 10,
    border: "1px solid var(--control-border)",
    background: "var(--control-bg)",
    color: "var(--control-text)",
    padding: "10px 12px",
    fontSize: 13,
  };
}

function tagPillStyle(active: boolean): React.CSSProperties {
  return {
    borderRadius: 999,
    border: `1px solid ${active ? "var(--state-success-border)" : "var(--control-border)"}`,
    background: active ? "var(--state-success-soft)" : "var(--control-bg)",
    color: active ? "var(--state-success)" : "var(--text-body)",
    padding: "5px 9px",
    fontSize: 11,
    fontWeight: 700,
    cursor: "pointer",
  };
}

export function ExecutionJournalPanel({ detail, selectedExecutionId }: ExecutionJournalPanelProps) {
  const [entry, setEntry] = useState<ExecutionJournalEntry | null>(null);
  const [note, setNote] = useState("");
  const [tagDraft, setTagDraft] = useState<string>("");
  const [outcomeTag, setOutcomeTag] = useState<JournalOutcomeTag>("untagged");
  const [isSaving, setIsSaving] = useState(false);
  const [isSaved, setIsSaved] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  // Collision guard: each save invocation captures a sequence number.
  // If a newer save starts before this one resolves, the stale response is discarded.
  const saveSequenceRef = useRef(0);

  useEffect(() => {
    let cancelled = false;

    async function loadEntry() {
      if (!selectedExecutionId) {
        setEntry(null);
        setNote("");
        setTagDraft("");
        setOutcomeTag("untagged");
        setErrorMessage(null);
        return;
      }

      setIsLoading(true);
      setErrorMessage(null);

      try {
        const next = await getExecutionJournalEntry(selectedExecutionId, {
          asset: detail?.asset,
          status: detail?.status,
        });
        if (cancelled) return;
        setEntry(next);
        setNote(next?.note ?? "");
        setTagDraft("");
        setOutcomeTag(next?.outcomeTag ?? "untagged");
      } catch (error) {
        if (cancelled) return;
        setErrorMessage(error instanceof Error ? error.message : "Failed to load journal entry.");
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void loadEntry();

    return () => {
      cancelled = true;
    };
  }, [detail?.asset, detail?.status, selectedExecutionId]);

  useEffect(() => {
    const unsubscribe = subscribeExecutionJournal(() => {
      if (!selectedExecutionId) return;
      void getExecutionJournalEntry(selectedExecutionId, {
        asset: detail?.asset,
        status: detail?.status,
      })
        .then((next) => {
          setEntry(next);
          setNote(next?.note ?? "");
          setOutcomeTag(next?.outcomeTag ?? "untagged");
          setErrorMessage(null);
        })
        .catch((error) => {
          setErrorMessage(error instanceof Error ? error.message : "Failed to refresh journal entry.");
        });
    });
    return unsubscribe;
  }, [detail?.asset, detail?.status, selectedExecutionId]);

  const tags = useMemo(() => entry?.tags ?? [], [entry]);

  async function save(next: { tags?: string[]; outcomeTag?: JournalOutcomeTag; note?: string } = {}) {
    if (!selectedExecutionId) return;

    const tagsToPersist = next.tags ?? tags;
    const outcomeToPersist = next.outcomeTag ?? outcomeTag;
    const noteToPersist = next.note ?? note;

    saveSequenceRef.current += 1;
    const thisSeq = saveSequenceRef.current;

    setIsSaving(true);
    setErrorMessage(null);
    try {
      const saved = await saveExecutionJournalEntry({
        executionId: selectedExecutionId,
        asset: detail?.asset,
        status: detail?.status,
        note: noteToPersist,
        tags: tagsToPersist,
        outcomeTag: outcomeToPersist,
      });
      // Discard stale response if a newer save has already been issued
      if (saveSequenceRef.current !== thisSeq) return;
      setEntry(saved);
      setNote(saved.note);
      setOutcomeTag(saved.outcomeTag);
      setIsSaved(true);
      window.setTimeout(() => setIsSaved(false), 1800);
    } catch (error) {
      if (saveSequenceRef.current !== thisSeq) return;
      setErrorMessage(error instanceof Error ? error.message : "Failed to save journal entry.");
    } finally {
      if (saveSequenceRef.current === thisSeq) {
        setIsSaving(false);
      }
    }
  }

  function addTag() {
    const cleaned = tagDraft.trim().toLowerCase();
    if (!cleaned || tags.includes(cleaned)) return;
    const nextTags = [...tags, cleaned].slice(0, 6);
    setTagDraft("");
    save({ tags: nextTags });
  }

  function removeTag(tag: string) {
    save({ tags: tags.filter((item) => item !== tag) });
  }

  return (
    <div style={panelInnerStyle()}>
      <h3 style={{ margin: 0, color: "var(--text-strong)", fontSize: 20 }}>Journal</h3>
      <p style={{ margin: "6px 0 0", color: "var(--text-muted)", fontSize: 13 }}>
        Backend-backed notes and outcome tags for this paper execution.
      </p>

      {!selectedExecutionId ? (
        <p style={{ marginTop: 10, color: "var(--text-muted)" }}>Select an execution to capture journal context.</p>
      ) : (
        <>
          {isLoading ? <p style={{ margin: 0, color: "var(--text-muted)", fontSize: 12 }}>Loading journal entry...</p> : null}
          {!isLoading && !entry && !errorMessage ? (
            <div style={{
              padding: "14px 16px",
              borderRadius: 10,
              border: "1px dashed var(--control-border)",
              background: "var(--surface-soft)",
              color: "var(--text-muted)",
              fontSize: 13,
              lineHeight: 1.6,
            }}>
              No journal entry for this execution yet. Tag an outcome or add a note and click <strong style={{ color: "var(--text-body)" }}>Save journal</strong> to create one.
            </div>
          ) : null}
          {errorMessage ? <p style={{ margin: 0, color: "var(--state-danger)", fontSize: 12 }}>{errorMessage}</p> : null}
          <div style={{ display: "grid", gap: 8 }}>
            <span style={{ color: "var(--text-muted)", fontSize: 11, textTransform: "uppercase", letterSpacing: 1.1, fontWeight: 700 }}>
              Outcome Tag
            </span>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {OUTCOME_OPTIONS.map((option) => (
                <button
                  key={option}
                  type="button"
                  onClick={() => {
                    setOutcomeTag(option);
                    save({ outcomeTag: option });
                  }}
                  style={tagPillStyle(outcomeTag === option)}
                >
                  {option}
                </button>
              ))}
            </div>
          </div>

          <label style={{ display: "grid", gap: 8 }}>
            <span style={{ color: "var(--text-muted)", fontSize: 11, textTransform: "uppercase", letterSpacing: 1.1, fontWeight: 700 }}>
              Note
            </span>
            <textarea
              value={note}
              onChange={(event) => setNote(event.target.value)}
              rows={5}
              placeholder="What worked, what failed, or what to watch next?"
              style={{ ...inputStyle(), resize: "vertical", minHeight: 120, fontFamily: "inherit" }}
            />
          </label>

          <div style={{ display: "grid", gap: 8 }}>
            <span style={{ color: "var(--text-muted)", fontSize: 11, textTransform: "uppercase", letterSpacing: 1.1, fontWeight: 700 }}>
              Tags
            </span>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {tags.length === 0 ? <span style={{ color: "var(--text-muted)", fontSize: 12 }}>No tags yet.</span> : null}
              {tags.map((tag) => (
                <button key={tag} type="button" onClick={() => removeTag(tag)} style={tagPillStyle(false)}>
                  {tag} ×
                </button>
              ))}
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <input
                value={tagDraft}
                onChange={(event) => setTagDraft(event.target.value)}
                placeholder="Add tag, e.g. breakout"
                style={inputStyle()}
              />
              <button type="button" onClick={addTag} style={tagPillStyle(true)}>
                Add
              </button>
            </div>
          </div>

          <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
            <span style={{ color: isSaved ? "var(--state-success)" : isSaving ? "var(--state-warning)" : "var(--text-muted)", fontSize: 12 }}>
              {isSaved
                ? "Saved to backend"
                : isSaving
                  ? "Saving..."
                  : entry
                    ? `Last saved ${new Date(entry.updatedAt).toLocaleString()}`
                    : "No journal entry yet — save to create one"}
            </span>
            <button
              type="button"
              onClick={() => void save()}
              disabled={isSaving}
              style={{ ...tagPillStyle(true), opacity: isSaving ? 0.5 : 1, cursor: isSaving ? "not-allowed" : "pointer" }}
            >
              {isSaving ? "Saving…" : "Save journal"}
            </button>
          </div>

          <div style={{ padding: "12px 14px", borderRadius: 10, border: "1px solid var(--surface-border)", background: "var(--surface-soft)" }}>
            <p style={{ margin: 0, color: "var(--text-muted)", fontSize: 12, lineHeight: 1.5 }}>
              Persisted via backend contract:
              <span style={{ color: "var(--text-body)" }}> GET /execution/paper/{'{id}'}/journal </span>
              and
              <span style={{ color: "var(--text-body)" }}> PUT /execution/paper/{'{id}'}/journal</span>.
            </p>
          </div>
        </>
      )}
    </div>
  );
}
