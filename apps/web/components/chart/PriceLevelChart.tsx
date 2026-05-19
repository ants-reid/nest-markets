"use client";

interface PriceLevelChartProps {
  fill: number;
  stop: number;
  target: number;
  side: string;
  status: string;
  asset: string;
  qty: number;
}

function fmt(v: number): string {
  if (v >= 1000) return v.toFixed(2);
  if (v >= 10) return v.toFixed(4);
  return v.toFixed(5);
}

function fmtPct(v: number): string {
  return `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`;
}

export function PriceLevelChart({ fill, stop, target, side, status, asset, qty }: PriceLevelChartProps) {
  const isLong = side.toLowerCase() === "long" || side.toLowerCase() === "buy";
  const isClosed = ["closed", "rejected", "canceled", "expired"].includes(status.toLowerCase());

  const riskPerUnit = Math.abs(fill - stop);
  const rewardPerUnit = Math.abs(target - fill);
  const rrRatio = riskPerUnit > 0 ? rewardPerUnit / riskPerUnit : null;

  const low = Math.min(stop, fill, target) * 0.9995;
  const high = Math.max(stop, fill, target) * 1.0005;
  const range = high - low;

  const HEIGHT = 200;
  const WIDTH = 260;
  const PL = 64; // padding left (for labels)
  const PR = 12;
  const PT = 14;
  const PB = 14;
  const chartH = HEIGHT - PT - PB;
  const chartW = WIDTH - PL - PR;

  function toY(price: number): number {
    // top = high, bottom = low
    return PT + chartH - ((price - low) / range) * chartH;
  }

  const fillY = toY(fill);
  const stopY = toY(stop);
  const targetY = toY(target);

  // Profit zone (between fill and target)
  const profitTop = Math.min(fillY, targetY);
  const profitH = Math.abs(fillY - targetY);
  // Loss zone (between fill and stop)
  const lossTop = Math.min(fillY, stopY);
  const lossH = Math.abs(fillY - stopY);

  const stopPct = fill > 0 ? ((stop - fill) / fill) * 100 : 0;
  const targetPct = fill > 0 ? ((target - fill) / fill) * 100 : 0;

  const levels = [
    { price: target, y: targetY, label: "Target", color: "var(--state-success)", pct: targetPct },
    { price: fill, y: fillY, label: "Fill", color: "var(--state-info)", pct: 0 },
    { price: stop, y: stopY, label: "Stop", color: "var(--state-danger)", pct: stopPct },
  ];

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8 }}>
        <span style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: 1.2, color: "var(--text-muted)", fontWeight: 700 }}>
          Price Levels · {asset}
        </span>
        {rrRatio !== null ? (
          <span
            style={{
              padding: "4px 10px",
              borderRadius: 8,
              background: rrRatio >= 2 ? "color-mix(in oklab, var(--state-success) 18%, var(--surface-soft))" : rrRatio >= 1 ? "color-mix(in oklab, var(--state-warning) 18%, var(--surface-soft))" : "color-mix(in oklab, var(--state-danger) 18%, var(--surface-soft))",
              border: `1px solid ${rrRatio >= 2 ? "var(--state-success)" : rrRatio >= 1 ? "var(--state-warning)" : "var(--state-danger)"}`,
              fontSize: 12,
              fontWeight: 800,
              color: rrRatio >= 2 ? "var(--state-success)" : rrRatio >= 1 ? "var(--state-warning)" : "var(--state-danger)",
              fontVariantNumeric: "tabular-nums",
            }}
          >
            R:R {rrRatio.toFixed(2)}
          </span>
        ) : null}
      </div>

      <svg
        width={WIDTH}
        height={HEIGHT}
        style={{ display: "block", overflow: "visible" }}
        aria-label={`Price level chart for ${asset}`}
      >
        {/* Chart background */}
        <rect
          x={PL}
          y={PT}
          width={chartW}
          height={chartH}
          fill="var(--surface-soft)"
          rx={6}
        />

        {/* Profit zone */}
        <rect
          x={PL}
          y={profitTop}
          width={chartW}
          height={profitH}
          fill={isClosed ? "color-mix(in oklab, var(--text-muted) 16%, transparent)" : "color-mix(in oklab, var(--state-success) 10%, transparent)"}
          rx={0}
        />

        {/* Loss zone */}
        <rect
          x={PL}
          y={lossTop}
          width={chartW}
          height={lossH}
          fill={isClosed ? "color-mix(in oklab, var(--text-muted) 16%, transparent)" : "color-mix(in oklab, var(--state-danger) 10%, transparent)"}
          rx={0}
        />

        {/* Price level lines */}
        {levels.map((level) => (
          <g key={level.label}>
            <line
              x1={PL}
              x2={PL + chartW}
              y1={level.y}
              y2={level.y}
              stroke={isClosed ? "var(--text-muted)" : level.color}
              strokeWidth={level.label === "Fill" ? 2 : 1.5}
              strokeDasharray={level.label !== "Fill" ? "4 3" : undefined}
            />
            {/* Label on left */}
            <text
              x={PL - 4}
              y={level.y + 4}
              textAnchor="end"
              fill={isClosed ? "var(--text-muted)" : level.color}
              fontSize={9}
              fontWeight={700}
              fontFamily="inherit"
            >
              {level.label}
            </text>
            {/* Price on right */}
            <text
              x={PL + chartW + 4}
              y={level.y + 4}
              textAnchor="start"
              fill="var(--text-muted)"
              fontSize={9}
              fontFamily="inherit"
              style={{ fontVariantNumeric: "tabular-nums" }}
            >
              {fmt(level.price)}
            </text>
          </g>
        ))}

        {/* Tick marks on left axis for fill price */}
        <text x={PL - 4} y={fillY - 6} textAnchor="end" fill="var(--text-muted)" fontSize={8} fontFamily="inherit" style={{ fontVariantNumeric: "tabular-nums" }}>
          entry
        </text>
      </svg>

      {/* Summary row */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, fontSize: 12 }}>
        <div style={{ padding: "8px 10px", borderRadius: 8, border: "1px solid var(--surface-border)", background: "var(--surface-soft)" }}>
          <span style={{ display: "block", color: "var(--text-muted)", fontSize: 10, textTransform: "uppercase", letterSpacing: 0.8, fontWeight: 700, marginBottom: 3 }}>Stop distance</span>
          <strong style={{ color: "var(--state-danger)", fontVariantNumeric: "tabular-nums" }}>{fmtPct(stopPct)}</strong>
          <span style={{ color: "var(--text-muted)", fontSize: 11, marginLeft: 4 }}>/ {(riskPerUnit * qty).toFixed(2)} notional</span>
        </div>
        <div style={{ padding: "8px 10px", borderRadius: 8, border: "1px solid var(--surface-border)", background: "var(--surface-soft)" }}>
          <span style={{ display: "block", color: "var(--text-muted)", fontSize: 10, textTransform: "uppercase", letterSpacing: 0.8, fontWeight: 700, marginBottom: 3 }}>Target distance</span>
          <strong style={{ color: "var(--state-success)", fontVariantNumeric: "tabular-nums" }}>{fmtPct(targetPct)}</strong>
          <span style={{ color: "var(--text-muted)", fontSize: 11, marginLeft: 4 }}>/ {(rewardPerUnit * qty).toFixed(2)} notional</span>
        </div>
      </div>
    </div>
  );
}
