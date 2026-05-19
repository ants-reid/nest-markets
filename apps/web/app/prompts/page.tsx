"use client";

import { useEffect, useState } from "react";

import { getPrompt, getPromptHistory, listPrompts, type PromptHistoryItem } from "../../lib/api";
import { useLivePolling } from "../../lib/hooks/useLivePolling";

function shellStyle(): React.CSSProperties {
  return {
    minHeight: "100vh",
    padding: "32px 20px 64px",
    background: "var(--app-shell-bg)",
  };
}

function panelStyle(): React.CSSProperties {
  return {
    display: "grid",
    gap: 12,
    padding: 22,
    borderRadius: 20,
    border: "1px solid var(--surface-border)",
    background: "var(--surface-fill)",
    boxShadow: "var(--surface-shadow)",
  };
}

function codeBlockStyle(): React.CSSProperties {
  return {
    fontFamily: "monospace",
    fontSize: 13,
    lineHeight: 1.6,
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
    padding: "16px 18px",
    borderRadius: 12,
    border: "1px solid var(--surface-border)",
    background: "var(--control-bg)",
    color: "var(--control-text)",
    maxHeight: 480,
    overflowY: "auto",
  };
}

export default function PromptsPage() {
  const [promptNames, setPromptNames] = useState<string[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [content, setContent] = useState<string | null>(null);
  const [history, setHistory] = useState<PromptHistoryItem[]>([]);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingContent, setLoadingContent] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listPrompts()
      .then((res) => setPromptNames(res.prompts))
      .catch(() => setError("Failed to load prompt list."))
      .finally(() => setLoadingList(false));
  }, []);

  useLivePolling(async () => {
    try {
      const res = await listPrompts();
      setPromptNames(res.prompts);
    } catch {
      // non-blocking
    }
  }, 30000, { enabled: true, runImmediately: false });

  useLivePolling(async () => {
    if (!selected) return;
    const [subdir, filename] = selected.split("/");
    try {
      const [promptRes, historyRes] = await Promise.all([getPrompt(subdir, filename), getPromptHistory(subdir, filename)]);
      setContent(promptRes.content);
      setHistory(historyRes);
    } catch {
      // non-blocking
    }
  }, 30000, { enabled: Boolean(selected), runImmediately: false });

  function handleSelect(name: string) {
    setSelected(name);
    setContent(null);
    setHistory([]);
    setLoadingContent(true);
    const [subdir, filename] = name.split("/");
    getPrompt(subdir, filename)
      .then((res) => setContent(res.content))
      .catch(() => setContent("Failed to load prompt content."))
      .finally(() => setLoadingContent(false));

    setLoadingHistory(true);
    getPromptHistory(subdir, filename)
      .then((res) => setHistory(res))
      .catch(() => setHistory([]))
      .finally(() => setLoadingHistory(false));
  }

  return (
    <main style={shellStyle()}>
      <div style={{ maxWidth: 1080, margin: "0 auto", display: "grid", gap: 24 }}>

        <section data-rs="panel-pad" style={panelStyle()}>
          <span style={{ color: "var(--state-info)", fontSize: 11, letterSpacing: 1.4, textTransform: "uppercase", fontWeight: 700 }}>
            Prompt Versioning
          </span>
          <h1 data-rs="hero-title" style={{ margin: 0, color: "var(--text-strong)", fontSize: 34, lineHeight: 1.08 }}>
            Prompts
          </h1>
          <p style={{ margin: 0, color: "var(--text-muted)", lineHeight: 1.55, maxWidth: 760 }}>
            Versioned prompt files served by the backend. Select a prompt to inspect its current content.
          </p>
        </section>

        <section style={{ display: "grid", gridTemplateColumns: "260px 1fr", gap: 16 }}>
          <div style={{ ...panelStyle(), alignContent: "start" }}>
            <span style={{ color: "var(--text-muted)", fontSize: 11, letterSpacing: 1.2, textTransform: "uppercase", fontWeight: 600 }}>
              Available Prompts
            </span>
            {loadingList && (
              <p style={{ margin: 0, color: "var(--text-muted)", fontSize: 14 }}>Loading…</p>
            )}
            {error && (
              <p style={{ margin: 0, color: "var(--state-danger)", fontSize: 14 }}>{error}</p>
            )}
            {promptNames.map((name) => (
              <button
                key={name}
                onClick={() => handleSelect(name)}
                style={{
                  width: "100%",
                  textAlign: "left",
                  padding: "9px 12px",
                  borderRadius: 10,
                  border: "1px solid var(--control-border)",
                  background: selected === name ? "var(--state-info-subtle)" : "var(--control-bg)",
                  color: selected === name ? "var(--state-info)" : "var(--control-text)",
                  fontSize: 13,
                  cursor: "pointer",
                  fontWeight: selected === name ? 600 : 400,
                }}
              >
                {name}
              </button>
            ))}
          </div>

          <div style={panelStyle()}>
            {!selected && (
              <p style={{ margin: 0, color: "var(--text-muted)", fontSize: 14 }}>
                Select a prompt from the list to view its content.
              </p>
            )}
            {selected && (
              <>
                <span style={{ color: "var(--text-strong)", fontSize: 13, fontWeight: 600 }}>{selected}</span>
                {loadingContent && (
                  <p style={{ margin: 0, color: "var(--text-muted)", fontSize: 14 }}>Loading…</p>
                )}
                {content !== null && !loadingContent && (
                  <>
                    <div style={codeBlockStyle()}>{content}</div>
                    <div style={{ display: "grid", gap: 10 }}>
                      <span style={{ color: "var(--text-strong)", fontSize: 13, fontWeight: 600 }}>
                        Version History
                      </span>
                      {loadingHistory && (
                        <p style={{ margin: 0, color: "var(--text-muted)", fontSize: 14 }}>Loading history…</p>
                      )}
                      {!loadingHistory && history.length === 0 && (
                        <p style={{ margin: 0, color: "var(--text-muted)", fontSize: 14 }}>
                          No persisted prompt history found.
                        </p>
                      )}
                      {!loadingHistory && history.length > 0 && (
                        <div style={{ overflowX: "auto" }}>
                          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                            <thead>
                              <tr>
                                <th style={{ textAlign: "left", padding: "8px 10px", color: "var(--text-muted)", borderBottom: "1px solid var(--surface-border)" }}>Version</th>
                                <th style={{ textAlign: "left", padding: "8px 10px", color: "var(--text-muted)", borderBottom: "1px solid var(--surface-border)" }}>Hash</th>
                                <th style={{ textAlign: "left", padding: "8px 10px", color: "var(--text-muted)", borderBottom: "1px solid var(--surface-border)" }}>Created</th>
                                <th style={{ textAlign: "left", padding: "8px 10px", color: "var(--text-muted)", borderBottom: "1px solid var(--surface-border)" }}>Active</th>
                              </tr>
                            </thead>
                            <tbody>
                              {history.map((item) => (
                                <tr key={item.id}>
                                  <td style={{ padding: "8px 10px", borderBottom: "1px solid var(--surface-border)", color: "var(--control-text)" }}>{item.version}</td>
                                  <td style={{ padding: "8px 10px", borderBottom: "1px solid var(--surface-border)", color: "var(--control-text)", fontFamily: "monospace" }}>{item.file_hash ?? "-"}</td>
                                  <td style={{ padding: "8px 10px", borderBottom: "1px solid var(--surface-border)", color: "var(--control-text)" }}>{new Date(item.created_at).toLocaleString()}</td>
                                  <td style={{ padding: "8px 10px", borderBottom: "1px solid var(--surface-border)", color: item.is_active ? "var(--state-info)" : "var(--text-muted)" }}>{item.is_active ? "yes" : "no"}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>
                  </>
                )}
              </>
            )}
          </div>
        </section>
      </div>
    </main>
  );
}
