"use client";

interface HeatCell {
  key: string;
  label: string;
  value: number;
  intensity: number;
}

interface HeatmapPanelProps {
  title: string;
  subtitle?: string;
  cells: HeatCell[];
  columns?: number;
}

function tintForIntensity(intensity: number): string {
  const clamped = Math.max(0, Math.min(1, intensity));
  const pct = Math.round((18 + clamped * 60) * 100) / 100;

  if (clamped >= 0.66) {
    return `color-mix(in oklab, var(--state-warning) ${pct}%, transparent)`;
  }
  if (clamped >= 0.33) {
    return `color-mix(in oklab, var(--state-info) ${pct}%, transparent)`;
  }
  return `color-mix(in oklab, var(--state-success) ${pct}%, transparent)`;
}

export function HeatmapPanel({ title, subtitle, cells, columns = 4 }: HeatmapPanelProps) {
  return (
    <article
      style={{
        display: "grid",
        gap: 12,
        padding: 16,
        borderRadius: 16,
        border: "1px solid var(--surface-border)",
        background: "var(--surface-soft)",
      }}
    >
      <div style={{ display: "grid", gap: 6 }}>
        <h3 style={{ margin: 0, color: "var(--text-strong)", fontSize: 14, fontWeight: 700 }}>{title}</h3>
        {subtitle ? <p style={{ margin: 0, color: "var(--text-muted)", fontSize: 12 }}>{subtitle}</p> : null}
      </div>

      <div style={{ display: "grid", gap: 8, gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }}>
        {cells.map((cell) => (
          <div
            key={cell.key}
            style={{
              display: "grid",
              gap: 4,
              padding: "10px 8px",
              borderRadius: 10,
              border: "1px solid var(--surface-border)",
              background: tintForIntensity(cell.intensity),
            }}
          >
            <span style={{ color: "var(--text-body)", fontSize: 11, lineHeight: 1.2 }}>{cell.label}</span>
            <strong style={{ color: "var(--text-strong)", fontSize: 14, fontVariantNumeric: "tabular-nums" }}>{cell.value}</strong>
          </div>
        ))}
      </div>
    </article>
  );
}
