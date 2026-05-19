"use client";

interface MetricEntry {
  label: string;
  value: number;
  format?: "pct" | "decimal" | "raw";
}

interface Props {
  metrics: MetricEntry[];
}

function fmt(value: number, format: MetricEntry["format"] = "decimal"): string {
  if (format === "pct") return `${(value * 100).toFixed(1)}%`;
  if (format === "decimal") return value.toFixed(4);
  return String(value);
}

export function ModelMetrics({ metrics }: Props) {
  if (metrics.length === 0) {
    return <p className="text-muted-foreground text-sm">No metrics available.</p>;
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
      {metrics.map((m) => (
        <div key={m.label} className="border rounded p-3 text-center">
          <p className="text-2xl font-semibold tabular-nums">
            {fmt(m.value, m.format)}
          </p>
          <p className="text-xs text-muted-foreground mt-1">{m.label}</p>
        </div>
      ))}
    </div>
  );
}
