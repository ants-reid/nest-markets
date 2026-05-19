import type { PaperExecutionResponse, Timeframe } from "./types";

function timeframeToMinutes(timeframe?: string): number {
  const normalized = (timeframe ?? "1h").toLowerCase() as Timeframe;
  switch (normalized) {
    case "15m":
      return 15;
    case "1h":
      return 60;
    case "4h":
      return 240;
    case "1d":
      return 60 * 24;
    default:
      return 60;
  }
}

export function inferExecutionTimestamps(rows: PaperExecutionResponse[], nowMs = Date.now()): string[] {
  if (rows.length === 0) return [];

  // API rows are typically newest-first. Build timestamps oldest->newest, then map back.
  const oldestFirst = [...rows].reverse();
  const intervals = oldestFirst.map((row) => timeframeToMinutes(row.timeframe));
  const totalMinutes = intervals.slice(0, -1).reduce((sum, value) => sum + value, 0);

  let cursor = nowMs - totalMinutes * 60_000;
  const oldestFirstTimes: number[] = [];

  for (let i = 0; i < oldestFirst.length; i += 1) {
    oldestFirstTimes.push(cursor);
    cursor += intervals[i] * 60_000;
  }

  return oldestFirstTimes.reverse().map((ms) => new Date(ms).toISOString());
}

export function marketSessionLabel(isoTimestamp: string): string {
  const date = new Date(isoTimestamp);
  if (Number.isNaN(date.getTime())) return "Session";

  const hour = date.getUTCHours();
  if (hour >= 0 && hour < 7) return "Asia";
  if (hour >= 7 && hour < 13) return "Europe";
  if (hour >= 13 && hour < 21) return "US";
  return "After-hours";
}

export function formatMarketTimeLabel(isoTimestamp: string): string {
  const date = new Date(isoTimestamp);
  if (Number.isNaN(date.getTime())) return isoTimestamp;

  const day = date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  const time = date.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
  const session = marketSessionLabel(isoTimestamp);
  return `${day} ${time} · ${session}`;
}
