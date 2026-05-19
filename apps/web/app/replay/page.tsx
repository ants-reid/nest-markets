"use client";

export default function ReplayPage() {
  return (
    <main className="p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-semibold mb-2">Historical Replay Lab</h1>
      <p className="text-muted-foreground text-sm mb-6">
        Step through historical data to evaluate how signals and scores would have behaved.
      </p>
      <div className="border rounded-lg p-5">
        <p className="text-muted-foreground text-sm">
          Replay controls — connect to{" "}
          <code className="text-xs">/api/replay</code> to enable.
        </p>
      </div>
    </main>
  );
}
