"use client";

interface RegimeEntry {
  regime: string;
  confidence: number;
  detected_at: string;
  ended_at?: string;
}

interface Props {
  history: RegimeEntry[];
}

export function RegimeHistory({ history }: Props) {
  if (history.length === 0) {
    return <p className="text-muted-foreground text-sm">No regime history recorded.</p>;
  }

  return (
    <ol className="space-y-2">
      {history.map((entry, i) => (
        <li key={i} className="border-l-4 border-muted pl-4 py-1">
          <div className="flex items-center justify-between">
            <span className="font-medium capitalize text-sm">
              {entry.regime.replace(/_/g, " ")}
            </span>
            <span className="text-xs text-muted-foreground">
              {(entry.confidence * 100).toFixed(0)}%
            </span>
          </div>
          <p className="text-xs text-muted-foreground">
            {entry.detected_at.slice(0, 10)}
            {entry.ended_at ? ` → ${entry.ended_at.slice(0, 10)}` : " → present"}
          </p>
        </li>
      ))}
    </ol>
  );
}
