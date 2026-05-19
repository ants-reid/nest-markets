"use client";

interface RingSegment {
  label: string;
  value: number;
  color: string;
}

interface InfographicRingProps {
  title: string;
  subtitle?: string;
  segments: RingSegment[];
  centerLabel?: string;
  centerValue?: string;
}

function clampValue(value: number): number {
  if (!Number.isFinite(value) || value < 0) {
    return 0;
  }
  return value;
}

export function InfographicRing({
  title,
  subtitle,
  segments,
  centerLabel = "Total",
  centerValue,
}: InfographicRingProps) {
  const total = segments.reduce((sum, segment) => sum + clampValue(segment.value), 0);

  const validSegments = segments
    .map((segment) => ({ ...segment, value: clampValue(segment.value) }))
    .filter((segment) => segment.value > 0);

  const gradient = (() => {
    if (validSegments.length === 0 || total <= 0) {
      return "conic-gradient(color-mix(in oklab, var(--text-muted) 35%, transparent) 0deg 360deg)";
    }

    let cursor = 0;
    const stops: string[] = [];
    for (const segment of validSegments) {
      const sweep = (segment.value / total) * 360;
      const start = cursor;
      const end = cursor + sweep;
      stops.push(`${segment.color} ${start.toFixed(2)}deg ${end.toFixed(2)}deg`);
      cursor = end;
    }

    if (cursor < 360) {
      stops.push(`color-mix(in oklab, var(--text-muted) 35%, transparent) ${cursor.toFixed(2)}deg 360deg`);
    }

    return `conic-gradient(${stops.join(", ")})`;
  })();

  return (
    <article
      style={{
        display: "grid",
        gap: 14,
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

      <div style={{ display: "grid", gap: 12, gridTemplateColumns: "140px 1fr", alignItems: "center" }}>
        <div
          style={{
            width: 132,
            height: 132,
            borderRadius: "50%",
            background: gradient,
            display: "grid",
            placeItems: "center",
            margin: "0 auto",
            boxShadow: "inset 0 0 0 1px color-mix(in oklab, var(--text-strong) 28%, transparent)",
          }}
        >
          <div
            style={{
              width: 82,
              height: 82,
              borderRadius: "50%",
              background: "var(--surface-fill)",
              border: "1px solid var(--surface-border)",
              display: "grid",
              placeItems: "center",
              textAlign: "center",
              padding: 6,
            }}
          >
            <span style={{ color: "var(--text-muted)", fontSize: 10, textTransform: "uppercase", letterSpacing: 0.8 }}>
              {centerLabel}
            </span>
            <strong style={{ color: "var(--accent-highlight)", fontSize: 18, lineHeight: 1.1, fontVariantNumeric: "tabular-nums" }}>
              {centerValue ?? String(total)}
            </strong>
          </div>
        </div>

        <div style={{ display: "grid", gap: 8 }}>
          {segments.map((segment) => {
            const pct = total > 0 ? ((clampValue(segment.value) / total) * 100).toFixed(1) : "0.0";
            return (
              <div key={segment.label} style={{ display: "grid", gridTemplateColumns: "auto 1fr auto", gap: 8, alignItems: "center" }}>
                <span style={{ width: 9, height: 9, borderRadius: "50%", background: segment.color, display: "inline-block" }} />
                <span style={{ color: "var(--text-body)", fontSize: 12 }}>{segment.label}</span>
                <span style={{ color: "var(--text-muted)", fontSize: 11, fontVariantNumeric: "tabular-nums" }}>
                  {segment.value} ({pct}%)
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </article>
  );
}
