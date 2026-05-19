import Link from "next/link";
import { ChartPanel, LineChart, SeriesToggle, TimeRangeBar, type ChartSeries, type TimeRange } from "../chart";
import { formatMarketTimeLabel, marketSessionLabel } from "../../lib/chartTime";

interface DashboardChartsSectionProps {
  notionalChartSeries: ChartSeries[];
  portfolioMovementSeries: ChartSeries[];
  hiddenSeries: Set<string>;
  movementHiddenSeries: Set<string>;
  onToggleSeries: (id: string) => void;
  onToggleMovementSeries: (id: string) => void;
  timeRange: TimeRange;
  onTimeRangeChange: (range: TimeRange) => void;
}

function filterByRange(data: { t: string; v: number }[], range: TimeRange): { t: string; v: number }[] {
  if (range === "ALL" || data.length === 0) return data;
  const latest = Date.parse(data[data.length - 1].t);
  if (!Number.isFinite(latest)) return data;
  const lookbackMs: Record<Exclude<TimeRange, "ALL">, number> = {
    "1D": 24 * 60 * 60 * 1000,
    "1W": 7 * 24 * 60 * 60 * 1000,
    "1M": 30 * 24 * 60 * 60 * 1000,
    "3M": 90 * 24 * 60 * 60 * 1000,
    "1Y": 365 * 24 * 60 * 60 * 1000,
  };
  const minTime = latest - lookbackMs[range];
  const filtered = data.filter((point) => Date.parse(point.t) >= minTime);
  return filtered.length > 1 ? filtered : data;
}

export function DashboardChartsSection({
  notionalChartSeries,
  portfolioMovementSeries,
  hiddenSeries,
  movementHiddenSeries,
  onToggleSeries,
  onToggleMovementSeries,
  timeRange,
  onTimeRangeChange,
}: DashboardChartsSectionProps) {
  return (
    <>
      <ChartPanel
        title="Notional Exposure by Asset"
        subtitle="Multi-series · top 5 assets · market-time labels"
        controls={
          <>
            <TimeRangeBar value={timeRange} onChange={onTimeRangeChange} />
            <Link href="/analytics" style={{ color: "var(--state-info)", fontSize: 12, textDecoration: "none", fontWeight: 700 }}>
              Full analytics
            </Link>
          </>
        }
        legend={<SeriesToggle series={notionalChartSeries} hidden={hiddenSeries} onToggle={onToggleSeries} />}
      >
        <LineChart
          series={notionalChartSeries.map((s) => ({
            ...s,
            data: filterByRange(s.data, timeRange),
          }))}
          hidden={hiddenSeries}
          height={220}
          yLabel="Notional"
          formatValue={(v) => `$${v >= 1000 ? `${(v / 1000).toFixed(1)}k` : v.toFixed(0)}`}
          formatTime={formatMarketTimeLabel}
          getTooltipContextRows={({ time }) => [
            { label: "Session", value: marketSessionLabel(time) },
            { label: "Window", value: timeRange },
            { label: "Surface", value: "Dashboard" },
          ]}
        />
      </ChartPanel>

      <ChartPanel
        title="Portfolio Movement"
        subtitle="Execution flow · smoothed trend · hover for exact values"
        legend={<SeriesToggle series={portfolioMovementSeries} hidden={movementHiddenSeries} onToggle={onToggleMovementSeries} />}
      >
        <LineChart
          series={portfolioMovementSeries}
          hidden={movementHiddenSeries}
          height={210}
          yLabel="Notional"
          formatValue={(v) => `$${v >= 1000 ? `${(v / 1000).toFixed(1)}k` : v.toFixed(0)}`}
          formatTime={formatMarketTimeLabel}
          getTooltipContextRows={({ time, series }) => [
            { label: "Session", value: marketSessionLabel(time) },
            { label: "Series", value: series.map((item) => item.label).join(" / ") },
          ]}
        />
      </ChartPanel>
    </>
  );
}
