"use client";

interface CalibrationPoint {
  bucket_low: number;
  bucket_high: number;
  mean_predicted: number;
  mean_actual: number;
  n_samples: number;
}

interface Props {
  points: CalibrationPoint[];
}

export function CalibrationPlots({ points }: Props) {
  if (points.length === 0) {
    return (
      <p className="text-muted-foreground text-sm">
        No calibration data available.
      </p>
    );
  }

  return (
    <div className="space-y-2">
      <div className="grid grid-cols-5 text-xs font-medium text-muted-foreground px-2">
        <span>Bucket</span>
        <span className="text-right">Predicted</span>
        <span className="text-right">Actual</span>
        <span className="text-right">Error</span>
        <span className="text-right">N</span>
      </div>
      {points.map((p, i) => {
        const error = Math.abs(p.mean_predicted - p.mean_actual);
        const errorColor =
          error > 0.1
            ? "text-red-600"
            : error > 0.05
              ? "text-yellow-600"
              : "text-green-600";
        return (
          <div
            key={i}
            className="grid grid-cols-5 text-xs px-2 py-1 border rounded"
          >
            <span className="text-muted-foreground">
              {p.bucket_low.toFixed(1)}–{p.bucket_high.toFixed(1)}
            </span>
            <span className="text-right tabular-nums">
              {(p.mean_predicted * 100).toFixed(1)}%
            </span>
            <span className="text-right tabular-nums">
              {(p.mean_actual * 100).toFixed(1)}%
            </span>
            <span className={`text-right tabular-nums font-medium ${errorColor}`}>
              {(error * 100).toFixed(1)}%
            </span>
            <span className="text-right tabular-nums text-muted-foreground">
              {p.n_samples}
            </span>
          </div>
        );
      })}
    </div>
  );
}
