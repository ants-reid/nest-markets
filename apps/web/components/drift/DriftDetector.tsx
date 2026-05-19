"use client";

interface DriftAlert {
  feature: string;
  drift_score: number;
  status: "ok" | "warning" | "critical";
  last_checked: string;
}

interface Props {
  alerts: DriftAlert[];
}

const STATUS_COLOUR: Record<DriftAlert["status"], string> = {
  ok: "text-green-600",
  warning: "text-yellow-600",
  critical: "text-red-600",
};

export function DriftDetector({ alerts }: Props) {
  if (alerts.length === 0) {
    return (
      <p className="text-muted-foreground text-sm">No drift alerts at this time.</p>
    );
  }

  return (
    <div className="space-y-2">
      {alerts.map((a, i) => (
        <div key={i} className="border rounded p-3 flex items-center justify-between">
          <div>
            <span className="font-medium text-sm">{a.feature}</span>
            <p className="text-xs text-muted-foreground">
              Drift score: {a.drift_score.toFixed(4)} · checked{" "}
              {a.last_checked.slice(0, 10)}
            </p>
          </div>
          <span className={`text-xs font-semibold uppercase ${STATUS_COLOUR[a.status]}`}>
            {a.status}
          </span>
        </div>
      ))}
    </div>
  );
}
