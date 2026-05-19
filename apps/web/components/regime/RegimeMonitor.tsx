"use client";

interface RegimeSnapshot {
  regime: string;
  confidence: number;
  detected_at: string;
}

interface Props {
  snapshot: RegimeSnapshot | null;
}

const REGIME_COLOURS: Record<string, string> = {
  risk_on: "bg-green-100 text-green-800",
  risk_off: "bg-red-100 text-red-800",
  high_vol: "bg-orange-100 text-orange-800",
  low_vol: "bg-blue-100 text-blue-800",
  chop: "bg-yellow-100 text-yellow-800",
  trend: "bg-purple-100 text-purple-800",
};

export function RegimeMonitor({ snapshot }: Props) {
  if (!snapshot) {
    return <p className="text-muted-foreground text-sm">No regime data available.</p>;
  }

  const colour = REGIME_COLOURS[snapshot.regime] ?? "bg-gray-100 text-gray-700";

  return (
    <div className="border rounded-lg p-5 space-y-3">
      <div className="flex items-center gap-3">
        <span className={`px-3 py-1 rounded-full text-sm font-semibold capitalize ${colour}`}>
          {snapshot.regime.replace(/_/g, " ")}
        </span>
        <span className="text-sm text-muted-foreground">
          {(snapshot.confidence * 100).toFixed(0)}% confidence
        </span>
      </div>
      <p className="text-xs text-muted-foreground">
        As of {snapshot.detected_at.slice(0, 19).replace("T", " ")} UTC
      </p>
    </div>
  );
}
