"use client";

import { useLearningMode, type SkillLevel } from "../lib/learningMode";

const LEVELS: { value: SkillLevel; label: string; desc: string }[] = [
  {
    value: "beginner",
    label: "Beginner",
    desc: "Plain-language explanations for every trading concept.",
  },
  {
    value: "intermediate",
    label: "Intermediate",
    desc: "Key definitions with brief context — assumes basic market knowledge.",
  },
  {
    value: "experienced",
    label: "Experienced",
    desc: "Concise reminders — for traders who know the basics.",
  },
  {
    value: "expert",
    label: "Expert",
    desc: "Technical precision — no hand-holding.",
  },
];

interface LearningModePanelProps {
  onClose: () => void;
}

export function LearningModePanel({ onClose }: LearningModePanelProps) {
  const { enabled, level, toggle, setLevel } = useLearningMode();

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Learning Mode settings"
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 300,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "var(--overlay-backdrop)",
      }}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        style={{
          background: "var(--surface-fill)",
          border: "1px solid var(--surface-border)",
          borderRadius: 16,
          padding: 28,
          width: "min(480px, 92vw)",
          boxShadow: "var(--shadow-elevated)",
        }}
      >
        {/* Header */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 20,
          }}
        >
          <div>
            <div style={{ fontSize: 16, fontWeight: 800, color: "var(--text-strong)" }}>
              Learning Mode
            </div>
            <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 2 }}>
              Hover over highlighted terms to see inline explanations.
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              fontSize: 18,
              color: "var(--text-muted)",
              lineHeight: 1,
              padding: "4px 8px",
            }}
          >
            ×
          </button>
        </div>

        {/* Toggle */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "12px 16px",
            borderRadius: 10,
            border: "1px solid var(--surface-border)",
            background: "var(--surface-soft)",
            marginBottom: 20,
          }}
        >
          <span style={{ fontSize: 13, fontWeight: 700, color: "var(--text-body)" }}>
            {enabled ? "Enabled — hover any underlined term" : "Disabled"}
          </span>
          <button
            type="button"
            onClick={toggle}
            style={{
              width: 44,
              height: 24,
              borderRadius: 12,
              border: "none",
              cursor: "pointer",
              background: enabled ? "var(--state-info)" : "var(--surface-border)",
              position: "relative",
              transition: "background 0.2s",
            }}
            aria-pressed={enabled}
            aria-label="Toggle learning mode"
          >
            <span
              style={{
                position: "absolute",
                top: 3,
                left: enabled ? 23 : 3,
                width: 18,
                height: 18,
                borderRadius: "50%",
                background: "var(--control-bg)",
                transition: "left 0.2s",
              }}
            />
          </button>
        </div>

        {/* Skill level selector */}
        <div style={{ marginBottom: 8 }}>
          <div
            style={{
              fontSize: 11,
              fontWeight: 700,
              textTransform: "uppercase",
              letterSpacing: 0.7,
              color: "var(--text-muted)",
              marginBottom: 10,
            }}
          >
            Skill Level
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            {LEVELS.map((l) => {
              const active = level === l.value;
              return (
                <button
                  key={l.value}
                  type="button"
                  onClick={() => setLevel(l.value)}
                  style={{
                    padding: "10px 14px",
                    borderRadius: 10,
                    border: `1px solid ${active ? "var(--state-info)" : "var(--surface-border)"}`,
                    background: active
                      ? "color-mix(in oklab, var(--state-info) 18%, var(--surface-soft))"
                      : "var(--surface-soft)",
                    textAlign: "left",
                    cursor: "pointer",
                    opacity: enabled ? 1 : 0.5,
                  }}
                  disabled={!enabled}
                >
                  <div
                    style={{
                      fontSize: 13,
                      fontWeight: 800,
                      color: active ? "var(--text-strong)" : "var(--text-body)",
                    }}
                  >
                    {l.label}
                  </div>
                  <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>
                    {l.desc}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
