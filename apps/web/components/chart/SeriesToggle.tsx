"use client";

import { ChartSeries } from "./types";

interface SeriesToggleProps {
  series: ChartSeries[];
  hidden: Set<string>;
  onToggle: (id: string) => void;
}

export function SeriesToggle({ series, hidden, onToggle }: SeriesToggleProps) {
  if (series.length === 0) return null;

  return (
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center", marginTop: 2 }}>
      {series.map((s) => {
        const isHidden = hidden.has(s.id);
        return (
          <button
            key={s.id}
            type="button"
            onClick={() => onToggle(s.id)}
            title={isHidden ? `Show ${s.label}` : `Hide ${s.label}`}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              padding: "8px 11px",
              borderRadius: 9,
              border: `1px solid ${isHidden ? "var(--surface-border)" : s.color}`,
              background: isHidden
                ? "var(--surface-soft)"
                : `color-mix(in oklab, ${s.color} 18%, var(--surface-soft))`,
              cursor: "pointer",
              opacity: isHidden ? 0.58 : 1,
              transition: "opacity 120ms ease, transform 120ms ease",
            }}
          >
            <span
              style={{
                width: 10,
                height: 10,
                borderRadius: "50%",
                background: isHidden ? "var(--text-muted)" : s.color,
                flexShrink: 0,
                ...(s.dashed
                  ? {
                      borderRadius: 2,
                      background: "transparent",
                      border: `2px dashed ${isHidden ? "var(--text-muted)" : s.color}`,
                    }
                  : {}),
              }}
            />
            <span
              style={{
                fontSize: 11,
                fontWeight: 700,
                color: isHidden ? "var(--text-muted)" : "var(--text-strong)",
                whiteSpace: "nowrap",
                letterSpacing: 0.2,
              }}
            >
              {s.label}
            </span>
          </button>
        );
      })}
    </div>
  );
}
