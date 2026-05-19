"use client";

import { useEffect, useState } from "react";
import {
  getModelVersions,
  promoteModelVersion,
  rollbackModelVersion,
  type ModelVersionRecord,
} from "../../lib/api";
import { useLivePolling } from "../../lib/hooks/useLivePolling";

export default function PromotionsPage() {
  const [models, setModels] = useState<ModelVersionRecord[]>([]);
  const [activeModelId, setActiveModelId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [actingModelId, setActingModelId] = useState<string | null>(null);
  const [rollingBack, setRollingBack] = useState(false);

  const load = () => {
    setLoading(true);
    return getModelVersions()
      .then((data) => {
        const items = data.items ?? [];
        setModels(items);
        setActiveModelId(items.find((model) => model.is_active)?.id ?? null);
        setError(null);
      })
      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    void load();
  }, []);
  useLivePolling(() => load(), 20000, { enabled: true, runImmediately: false });

  const candidates = models.filter((model) => !model.is_active);

  async function handlePromote(modelVersionId: string) {
    setActingModelId(modelVersionId);
    setActionMessage(null);
    try {
      const response = await promoteModelVersion(modelVersionId);
      setActionMessage(response.message);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setActingModelId(null);
    }
  }

  async function handleRollback() {
    setRollingBack(true);
    setActionMessage(null);
    try {
      const response = await rollbackModelVersion();
      setActionMessage(response.message);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setRollingBack(false);
    }
  }

  return (
    <main
      style={{
        minHeight: "100vh",
        padding: "32px 20px 64px",
        background: "var(--app-shell-bg)",
      }}
    >
      <div style={{ maxWidth: 980, margin: "0 auto", display: "grid", gap: 18 }}>
        <h1 style={{ margin: 0, color: "var(--text-strong)", fontSize: 32 }}>Promotion Queue</h1>
        <p style={{ margin: 0, color: "var(--text-muted)" }}>
          Promote an inactive model version to active or rollback to the previously active version.
        </p>

        {activeModelId ? (
          <div
            style={{
              border: "1px solid var(--surface-border)",
              borderRadius: 12,
              background: "var(--surface-fill)",
              padding: "12px 14px",
              color: "var(--text-body)",
              display: "grid",
              gap: 8,
            }}
          >
            <div style={{ fontWeight: 700 }}>Current active model</div>
            <div style={{ color: "var(--text-muted)", fontSize: 13 }}>{activeModelId}</div>
            <div>
              <button
                type="button"
                onClick={() => void handleRollback()}
                disabled={rollingBack}
                style={{
                  border: "1px solid var(--surface-border)",
                  borderRadius: 10,
                  padding: "8px 12px",
                  fontWeight: 700,
                  color: "var(--text-body)",
                  background: "var(--surface-soft)",
                  cursor: rollingBack ? "not-allowed" : "pointer",
                }}
              >
                {rollingBack ? "Rolling back..." : "Rollback to previous model"}
              </button>
            </div>
          </div>
        ) : null}

        {loading && <p style={{ margin: 0, color: "var(--text-muted)" }}>Loading candidates...</p>}
        {error ? (
          <p
            style={{
              margin: 0,
              padding: "12px 14px",
              borderRadius: 12,
              border: "1px solid var(--state-danger-border)",
              background: "var(--state-danger-soft)",
              color: "var(--state-danger)",
            }}
          >
            Error: {error}
          </p>
        ) : null}
        {actionMessage ? (
          <p
            style={{
              margin: 0,
              padding: "12px 14px",
              borderRadius: 12,
              border: "1px solid var(--state-success-border)",
              background: "var(--state-success-soft)",
              color: "var(--state-success)",
            }}
          >
            {actionMessage}
          </p>
        ) : null}

        {!loading && !error && candidates.length === 0 ? (
          <p style={{ margin: 0, color: "var(--text-muted)" }}>No inactive model versions available for promotion.</p>
        ) : null}

        <div style={{ display: "grid", gap: 12 }}>
          {candidates.map((candidate) => (
            <div
              key={candidate.id}
              style={{
                border: "1px solid var(--surface-border)",
                borderRadius: 14,
                background: "var(--surface-fill)",
                boxShadow: "var(--surface-shadow)",
                padding: "14px 16px",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: 12,
              }}
            >
              <div style={{ display: "grid", gap: 4 }}>
                <span style={{ color: "var(--text-strong)", fontWeight: 700 }}>{candidate.model_name}</span>
                <p style={{ margin: 0, color: "var(--text-muted)", fontSize: 13 }}>
                  {candidate.provider_name} | {candidate.id}
                </p>
                {candidate.notes ? (
                  <p style={{ margin: 0, color: "var(--text-muted)", fontSize: 13, fontStyle: "italic" }}>{candidate.notes}</p>
                ) : null}
              </div>

              <div style={{ display: "flex", gap: 8 }}>
                <button
                  type="button"
                  disabled={actingModelId === candidate.id}
                  onClick={() => void handlePromote(candidate.id)}
                  style={{
                    border: "none",
                    borderRadius: 10,
                    padding: "8px 12px",
                    background: "var(--state-success)",
                    color: "var(--surface-soft)",
                    fontWeight: 700,
                    cursor: actingModelId === candidate.id ? "not-allowed" : "pointer",
                  }}
                >
                  {actingModelId === candidate.id ? "Promoting..." : "Promote"}
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
