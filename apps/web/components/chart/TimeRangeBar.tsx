"use client";

import { TimeRange } from "./types";

const RANGES: TimeRange[] = ["1D", "1W", "1M", "3M", "1Y", "ALL"];

interface TimeRangeBarProps {
  value: TimeRange;
  onChange: (range: TimeRange) => void;
}

export function TimeRangeBar({ value, onChange }: TimeRangeBarProps) {
  return (
    <div
      role="group"
      aria-label="Time range"
      style={{ display: "flex", gap: 6, flexWrap: "wrap" }}
    >
      {RANGES.map((range) => {
        const active = range === value;
        return (
          <button
            key={range}
            type="button"
            onClick={() => onChange(range)}
            style={{
              padding: "8px 10px",
              borderRadius: 9,
              border: `1px solid ${active ? "var(--state-info)" : "var(--surface-border)"}`,
              background: active
                ? "color-mix(in oklab, var(--state-info) 22%, var(--surface-soft))"
                : "var(--surface-soft)",
              color: active ? "var(--text-strong)" : "var(--text-muted)",
              fontSize: 11,
              fontWeight: 700,
              cursor: "pointer",
              letterSpacing: 0.4,
            }}
          >
            {range}
          </button>
        );
      })}
    </div>
  );
}
