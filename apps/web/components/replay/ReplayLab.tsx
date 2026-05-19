"use client";

interface ReplayFrame {
  timestamp: string;
  symbol: string;
  score: number;
  regime: string;
  action: string;
}

interface ReplayResult {
  frames: ReplayFrame[];
  total_pnl_pct: number;
  win_rate: number;
}

interface Props {
  result: ReplayResult | null;
  onStart?: () => void;
}

export function ReplayLab({ result, onStart }: Props) {
  return (
    <div className="space-y-4">
      <button
        onClick={onStart}
        className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium"
      >
        Start Replay
      </button>

      {result && (
        <>
          <div className="grid grid-cols-2 gap-3">
            <div className="border rounded p-3 text-center">
              <p className="text-2xl font-semibold tabular-nums">
                {(result.total_pnl_pct * 100).toFixed(1)}%
              </p>
              <p className="text-xs text-muted-foreground mt-1">Total PnL</p>
            </div>
            <div className="border rounded p-3 text-center">
              <p className="text-2xl font-semibold tabular-nums">
                {(result.win_rate * 100).toFixed(1)}%
              </p>
              <p className="text-xs text-muted-foreground mt-1">Win Rate</p>
            </div>
          </div>

          <div className="border rounded overflow-hidden">
            <table className="w-full text-xs">
              <thead className="bg-muted">
                <tr>
                  {["Time", "Symbol", "Score", "Regime", "Action"].map((h) => (
                    <th key={h} className="px-3 py-2 text-left font-medium">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.frames.map((f, i) => (
                  <tr key={i} className="border-t">
                    <td className="px-3 py-1.5 text-muted-foreground">
                      {f.timestamp.slice(0, 16)}
                    </td>
                    <td className="px-3 py-1.5 font-medium">{f.symbol}</td>
                    <td className="px-3 py-1.5 tabular-nums">
                      {f.score.toFixed(3)}
                    </td>
                    <td className="px-3 py-1.5 capitalize">
                      {f.regime.replace(/_/g, " ")}
                    </td>
                    <td className="px-3 py-1.5">{f.action}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
