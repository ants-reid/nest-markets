"use client";

import { useCallback, useRef, useState } from "react";
import type { ChartSeries, TooltipContextRow, TooltipData } from "./types";

interface LineChartProps {
  series: ChartSeries[];
  hidden?: Set<string>;
  height?: number;
  yLabel?: string;
  formatValue?: (v: number) => string;
  formatTime?: (t: string) => string;
  getTooltipContextRows?: (input: {
    time: string;
    series: { id: string; label: string; color: string; value: number }[];
  }) => TooltipContextRow[];
}

const PADDING = { top: 16, right: 16, bottom: 36, left: 52 };

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function formatDefault(v: number): string {
  if (Math.abs(v) >= 1_000_000) return `${(v / 1_000_000).toFixed(2)}M`;
  if (Math.abs(v) >= 1_000) return `${(v / 1_000).toFixed(1)}k`;
  return v.toFixed(2);
}

function formatTimeDefault(t: string): string {
  const d = new Date(t);
  if (!Number.isNaN(d.getTime())) {
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  }
  return t;
}

function compareTimeLabel(a: string, b: string): number {
  const aMs = Date.parse(a);
  const bMs = Date.parse(b);

  if (Number.isFinite(aMs) && Number.isFinite(bMs)) {
    return aMs - bMs;
  }
  return a.localeCompare(b);
}

export function LineChart({
  series,
  hidden = new Set(),
  height = 280,
  yLabel,
  formatValue = formatDefault,
  formatTime = formatTimeDefault,
  getTooltipContextRows,
}: LineChartProps) {
  const containerRef = useRef<SVGSVGElement>(null);
  const [tooltip, setTooltip] = useState<TooltipData | null>(null);
  const [containerWidth, setContainerWidth] = useState(0);

  const resizeObserverRef = useRef<ResizeObserver | null>(null);
  const measuredRef = useCallback((node: HTMLDivElement | null) => {
    if (resizeObserverRef.current) {
      resizeObserverRef.current.disconnect();
    }
    if (node) {
      resizeObserverRef.current = new ResizeObserver((entries) => {
        const width = entries[0]?.contentRect.width;
        if (width) setContainerWidth(width);
      });
      resizeObserverRef.current.observe(node);
      setContainerWidth(node.getBoundingClientRect().width);
    }
  }, []);

  const visibleSeries = series.filter((s) => !hidden.has(s.id) && s.data.length > 0);

  const allPoints = visibleSeries.flatMap((s) => s.data);
  const allValues = allPoints.map((p) => p.v);
  const allTimes = allPoints.map((p) => p.t);

  const safeContainerWidth = Math.max(containerWidth, 1);
  const chartW = Math.max(safeContainerWidth - PADDING.left - PADDING.right, 1);
  const chartH = height - PADDING.top - PADDING.bottom;

  let minV = allValues.length > 0 ? Math.min(...allValues) : 0;
  let maxV = allValues.length > 0 ? Math.max(...allValues) : 1;
  if (minV === maxV) {
    minV = minV - 1;
    maxV = maxV + 1;
  }
  // add 5% padding to top
  const vPad = (maxV - minV) * 0.05;
  minV -= vPad;
  maxV += vPad;

  const uniqueTimes = Array.from(new Set(allTimes)).sort(compareTimeLabel);
  const timeIndexMap = new Map(uniqueTimes.map((t, i) => [t, i]));
  const tCount = Math.max(uniqueTimes.length - 1, 1);

  function toX(t: string): number {
    const idx = timeIndexMap.get(t) ?? 0;
    return PADDING.left + (idx / tCount) * chartW;
  }

  function toY(v: number): number {
    return PADDING.top + chartH - ((v - minV) / (maxV - minV)) * chartH;
  }

  function buildPath(data: { t: string; v: number }[]): string {
    const sorted = [...data].sort((a, b) => compareTimeLabel(a.t, b.t));
    return sorted
      .map((p, i) => `${i === 0 ? "M" : "L"}${toX(p.t).toFixed(1)},${toY(p.v).toFixed(1)}`)
      .join(" ");
  }

  // Y axis ticks
  const Y_TICKS = 5;
  const yTicks = Array.from({ length: Y_TICKS }, (_, i) => {
    const v = minV + ((maxV - minV) * i) / (Y_TICKS - 1);
    const y = toY(v);
    return { v, y };
  });

  // X axis ticks — pick ~6 evenly spaced
  const xTickCount = Math.min(6, uniqueTimes.length);
  const xTickIndices =
    xTickCount <= 1
      ? [0]
      : Array.from({ length: xTickCount }, (_, i) =>
          Math.round((i / (xTickCount - 1)) * (uniqueTimes.length - 1)),
        );
  const xTicks = xTickIndices.map((idx) => uniqueTimes[idx]).filter(Boolean) as string[];

  function handleMouseMove(event: React.MouseEvent<SVGSVGElement>) {
    if (visibleSeries.length === 0 || uniqueTimes.length === 0) return;

    const rect = event.currentTarget.getBoundingClientRect();
    const mouseX = event.clientX - rect.left - PADDING.left;
    const progress = clamp(mouseX / chartW, 0, 1);
    const idx = Math.round(progress * (uniqueTimes.length - 1));
    const t = uniqueTimes[idx];
    if (!t) return;

    const seriesValues = visibleSeries
      .map((s) => {
        const pt = s.data.find((p) => p.t === t) ?? s.data.reduce((closest, p) => {
          const pIdx = timeIndexMap.get(p.t) ?? 0;
          const cIdx = timeIndexMap.get(closest.t) ?? 0;
          const tIdx = timeIndexMap.get(t) ?? 0;
          return Math.abs(pIdx - tIdx) < Math.abs(cIdx - tIdx) ? p : closest;
        }, s.data[0]);
        return pt ? { id: s.id, label: s.label, color: s.color, value: pt.v } : null;
      })
      .filter((x): x is NonNullable<typeof x> => x !== null);

    const markerX = toX(t);
    setTooltip({ t, series: seriesValues, x: markerX, y: PADDING.top });
  }

  function handleMouseLeave() {
    setTooltip(null);
  }

  const isEmpty = series.length === 0;
  const allHidden = visibleSeries.length === 0 && series.length > 0;
  const emptyLineY = PADDING.top + chartH / 2;
  const emptyLineStartX = PADDING.left + Math.min(chartW * 0.18, 64);
  const emptyLineEndX = PADDING.left + chartW - Math.min(chartW * 0.18, 64);
  const emptyLineMidX = (emptyLineStartX + emptyLineEndX) / 2;

  if (isEmpty || allHidden) {
    return (
      <div ref={measuredRef} style={{ position: "relative", width: "100%", minWidth: 0 }}>
        <svg
          ref={containerRef}
          width={safeContainerWidth}
          height={height}
          style={{ display: "block", overflow: "visible" }}
          aria-label="Time series chart"
        >
          <rect
            x={PADDING.left}
            y={PADDING.top}
            width={chartW}
            height={chartH}
            fill="var(--surface-soft)"
            stroke="var(--surface-border)"
            strokeWidth={1}
            rx={4}
          />
          <path
            d={`M${emptyLineStartX.toFixed(1)},${emptyLineY.toFixed(1)} L${emptyLineMidX.toFixed(1)},${(emptyLineY - 10).toFixed(1)} L${emptyLineEndX.toFixed(1)},${emptyLineY.toFixed(1)}`}
            fill="none"
            stroke="var(--chart-series-2)"
            strokeWidth={2.4}
            strokeLinecap="round"
            strokeLinejoin="round"
            opacity={0.85}
          />
          <circle
            cx={emptyLineMidX}
            cy={emptyLineY - 10}
            r={4}
            fill="var(--chart-series-2)"
            stroke="var(--chart-point-stroke)"
            strokeWidth={2}
          />
          <text
            x={safeContainerWidth / 2}
            y={PADDING.top + chartH - 12}
            textAnchor="middle"
            fill="var(--text-muted)"
            fontSize={13}
            fontFamily="inherit"
          >
            {isEmpty ? "No data available." : "All series hidden — toggle one to show."}
          </text>
        </svg>
        <div
          style={{
            position: "absolute",
            inset: 0,
            pointerEvents: "none",
            borderRadius: 12,
          }}
        />
      </div>
    );
  }

  return (
    <div ref={measuredRef} style={{ position: "relative", width: "100%", minWidth: 0 }}>
      <svg
        ref={containerRef}
        width={safeContainerWidth}
        height={height}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
        style={{ display: "block", cursor: "crosshair", overflow: "visible" }}
        aria-label="Time series chart"
      >
        {/* Grid lines */}
        {yTicks.map(({ v, y }) => (
          <g key={v}>
            <line
              x1={PADDING.left}
              x2={PADDING.left + chartW}
              y1={y}
              y2={y}
              stroke="var(--chart-grid-line)"
              strokeWidth={1}
            />
            <text
              x={PADDING.left - 6}
              y={y + 4}
              textAnchor="end"
              fill="var(--chart-axis-text)"
              fontSize={10}
              fontFamily="inherit"
            >
              {formatValue(v)}
            </text>
          </g>
        ))}

        {/* X axis labels */}
        {xTicks.map((t) => (
          <text
            key={t}
            x={toX(t)}
            y={height - 6}
            textAnchor="middle"
            fill="var(--chart-axis-text)"
            fontSize={10}
            fontFamily="inherit"
          >
            {formatTime(t)}
          </text>
        ))}

        {yLabel ? (
          <text
            x={14}
            y={PADDING.top + chartH / 2}
            transform={`rotate(-90 14 ${PADDING.top + chartH / 2})`}
            fill="var(--chart-axis-text)"
            fontSize={10}
            fontFamily="inherit"
            textAnchor="middle"
            style={{ letterSpacing: 0.6, textTransform: "uppercase" }}
          >
            {yLabel}
          </text>
        ) : null}

        {/* Chart border */}
        <rect
          x={PADDING.left}
          y={PADDING.top}
          width={chartW}
          height={chartH}
          fill="none"
          stroke="var(--surface-border)"
          strokeWidth={1}
          rx={4}
        />

        {/* Series lines */}
        {visibleSeries.map((s) => {
          const sorted = [...s.data].sort((a, b) => compareTimeLabel(a.t, b.t));
          if (sorted.length === 1) {
            const only = sorted[0];
            const x = toX(only.t);
            const y = toY(only.v);
            const stubStart = Math.max(PADDING.left + 2, x - 12);
            const stubEnd = Math.min(containerWidth - PADDING.right - 2, x + 12);
            return (
              <g key={s.id}>
                <line
                  x1={stubStart}
                  y1={y}
                  x2={stubEnd}
                  y2={y}
                  stroke="var(--chart-line-halo)"
                  strokeWidth={6}
                  strokeLinecap="round"
                />
                <line
                  x1={stubStart}
                  y1={y}
                  x2={stubEnd}
                  y2={y}
                  stroke={s.color}
                  strokeWidth={3.2}
                  strokeLinecap="round"
                />
                <circle
                  cx={x}
                  cy={y}
                  r={6}
                  fill="var(--chart-line-halo)"
                />
                <circle
                  cx={x}
                  cy={y}
                  r={4}
                  fill={s.color}
                  stroke="var(--chart-point-stroke)"
                  strokeWidth={1.5}
                />
              </g>
            );
          }

          const path = buildPath(sorted);
          return (
            <g key={s.id}>
              <path
                d={path}
                fill="none"
                stroke="var(--chart-line-halo)"
                strokeWidth={4}
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeDasharray={s.dashed ? "5 4" : undefined}
              />
              <path
                d={path}
                fill="none"
                stroke={s.color}
                strokeWidth={2.6}
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeDasharray={s.dashed ? "5 4" : undefined}
              />
            </g>
          );
        })}

        {/* Hover vertical line */}
        {tooltip ? (
          <line
            x1={tooltip.x}
            x2={tooltip.x}
            y1={PADDING.top}
            y2={PADDING.top + chartH}
            stroke="var(--chart-guide-line)"
            strokeWidth={1}
            strokeDasharray="3 3"
          />
        ) : null}

        {/* Hover dots */}
        {tooltip
          ? visibleSeries.map((s) => {
              const pt = s.data.find((p) => p.t === tooltip.t) ?? null;
              if (!pt) return null;
              return (
                <circle
                  key={s.id}
                  cx={toX(pt.t)}
                  cy={toY(pt.v)}
                  r={4}
                  fill={s.color}
                  stroke="var(--chart-point-stroke)"
                  strokeWidth={2}
                />
              );
            })
          : null}
      </svg>

      {/* Tooltip */}
      {tooltip ? (
        (() => {
          const contextRows = getTooltipContextRows
            ? getTooltipContextRows({ time: tooltip.t, series: tooltip.series })
            : [];

          return (
            <div
              style={{
                position: "absolute",
                top: PADDING.top,
                left: Math.max(12, Math.min(tooltip.x + 12, containerWidth - 220)),
                background: "var(--surface-fill)",
                border: "1px solid var(--surface-border)",
                borderRadius: 10,
                padding: "8px 12px",
                pointerEvents: "none",
                minWidth: 160,
                boxShadow: "var(--surface-shadow)",
                zIndex: 10,
              }}
            >
              <div
                style={{
                  fontSize: 10,
                  color: "var(--text-muted)",
                  fontWeight: 700,
                  textTransform: "uppercase",
                  letterSpacing: 0.8,
                  marginBottom: 6,
                }}
              >
                {formatTime(tooltip.t)}
              </div>

              {contextRows.length > 0 ? (
                <div style={{ display: "grid", gap: 4, marginBottom: 6, paddingBottom: 6, borderBottom: "1px solid var(--surface-border)" }}>
                  {contextRows.map((row) => (
                    <div key={`${row.label}-${row.value}`} style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
                      <span style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: 0.6 }}>
                        {row.label}
                      </span>
                      <span style={{ fontSize: 11, color: "var(--text-strong)", fontWeight: 600 }}>{row.value}</span>
                    </div>
                  ))}
                </div>
              ) : null}

              {tooltip.series.map((sv) => (
                <div
                  key={sv.id}
                  style={{ display: "flex", justifyContent: "space-between", gap: 10, marginBottom: 4 }}
                >
                  <span style={{ display: "flex", alignItems: "center", gap: 5 }}>
                    <span
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: "50%",
                        background: sv.color,
                        display: "inline-block",
                        flexShrink: 0,
                      }}
                    />
                    <span style={{ fontSize: 11, color: "var(--text-muted)" }}>{sv.label}</span>
                  </span>
                  <strong style={{ fontSize: 12, color: "var(--text-strong)", fontVariantNumeric: "tabular-nums" }}>
                    {formatValue(sv.value)}
                  </strong>
                </div>
              ))}
            </div>
          );
        })()
      ) : null}
    </div>
  );
}
