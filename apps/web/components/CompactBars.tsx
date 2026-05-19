"use client";

interface CompactBarItem {
  label: string;
  value: number;
  color?: string;
  suffix?: string;
}

interface CompactBarsProps {
  title: string;
  subtitle?: string;
  items: CompactBarItem[];
}

function safeNumber(value: number): number {
  if (!Number.isFinite(value) || value < 0) {
    return 0;
  }
  return value;
}

export function CompactBars({ title, subtitle, items }: CompactBarsProps) {
  const max = items.reduce((current, item) => Math.max(current, safeNumber(item.value)), 0);

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

      <div style={{ display: "grid", gap: 8 }}>
        {items.map((item) => {
          const value = safeNumber(item.value);
          const width = max > 0 ? Math.max(4, (value / max) * 100) : 0;
          return (
            <div key={item.label} style={{ display: "grid", gap: 4 }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center" }}>
                <span style={{ color: "var(--text-body)", fontSize: 12 }}>{item.label}</span>
                <span style={{ color: "var(--text-muted)", fontSize: 11, fontVariantNumeric: "tabular-nums" }}>
                  {value.toLocaleString("en-US", { maximumFractionDigits: 2 })}
                  {item.suffix ? ` ${item.suffix}` : ""}
                </span>
              </div>
              <div style={{ height: 8, borderRadius: 4, background: "var(--chart-track-bg)", overflow: "hidden" }}>
                <div
                  style={{
                    width: `${width}%`,
                    height: "100%",
                    borderRadius: 4,
                    background: item.color ?? "var(--state-info)",
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </article>
  );
}
