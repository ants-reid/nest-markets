"use client";

import { useEffect, useState } from "react";
import { getModelVersions, type ModelVersionRecord } from "../../lib/api";

export default function ModelsPage() {
  const [models, setModels] = useState<ModelVersionRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getModelVersions()
      .then((data) => {
        setModels(data.items ?? []);
        setError(null);
      })
      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setLoading(false));
  }, []);

  return (
    <main
      style={{
        minHeight: "100vh",
        padding: "32px 20px 64px",
        background: "var(--app-shell-bg)",
      }}
    >
      <div style={{ maxWidth: 980, margin: "0 auto", display: "grid", gap: 18 }}>
        <h1 style={{ margin: 0, fontSize: 32, color: "var(--text-strong)" }}>Model Registry</h1>
        <p style={{ margin: 0, color: "var(--text-muted)" }}>
          Registered model versions, including active state and metadata.
        </p>

        {loading && <p style={{ margin: 0, color: "var(--text-muted)" }}>Loading models...</p>}
        {error && (
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
            Failed to load models: {error}
          </p>
        )}

        {!loading && !error && models.length === 0 && (
          <p style={{ margin: 0, color: "var(--text-muted)" }}>No model versions registered yet.</p>
        )}

        <div style={{ display: "grid", gap: 12 }}>
          {models.map((m) => (
            <div
              key={m.id}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: 16,
                border: "1px solid var(--surface-border)",
                borderRadius: 14,
                background: "var(--surface-fill)",
                boxShadow: "var(--surface-shadow)",
                padding: "16px 18px",
              }}
            >
              <div style={{ display: "grid", gap: 4 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ color: "var(--text-strong)", fontWeight: 700 }}>{m.model_name}</span>
                  {m.alias_name ? (
                    <span style={{ color: "var(--text-muted)", fontSize: 12 }}>({m.alias_name})</span>
                  ) : null}
                </div>
                <p style={{ margin: 0, color: "var(--text-muted)", fontSize: 13 }}>
                  {m.provider_name} | registered {m.created_at.slice(0, 10)}
                </p>
                {m.notes ? (
                  <p style={{ margin: 0, color: "var(--text-muted)", fontSize: 13, fontStyle: "italic" }}>{m.notes}</p>
                ) : null}
              </div>
              <span
                style={{
                  borderRadius: 999,
                  padding: "4px 10px",
                  fontSize: 12,
                  fontWeight: 700,
                  background: m.is_active ? "var(--state-success-soft)" : "var(--surface-soft)",
                  color: m.is_active ? "var(--state-success)" : "var(--text-muted)",
                  border: "1px solid var(--surface-border)",
                }}
              >
                {m.is_active ? "Active" : "Inactive"}
              </span>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
