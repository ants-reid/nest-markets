"use client";

interface Candidate {
  candidate_id: string;
  model_type: string;
  status: string;
  metrics: Record<string, number>;
  notes: string;
}

interface Props {
  candidates: Candidate[];
  onApprove?: (candidateId: string) => void;
  onReject?: (candidateId: string) => void;
}

export function PromotionQueue({ candidates, onApprove, onReject }: Props) {
  if (candidates.length === 0) {
    return (
      <p className="text-muted-foreground text-sm">No pending promotions.</p>
    );
  }

  return (
    <ul className="space-y-3">
      {candidates.map((c) => (
        <li key={c.candidate_id} className="border rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <span className="font-medium capitalize text-sm">{c.model_type} model</span>
              {c.notes && (
                <p className="text-xs italic text-muted-foreground mt-0.5">{c.notes}</p>
              )}
              <p className="text-xs text-muted-foreground font-mono mt-1 truncate">
                {c.candidate_id}
              </p>
            </div>
            <div className="flex gap-2 shrink-0">
              <button
                onClick={() => onApprove?.(c.candidate_id)}
                className="px-3 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700"
              >
                Approve
              </button>
              <button
                onClick={() => onReject?.(c.candidate_id)}
                className="px-3 py-1 text-xs border border-red-300 text-red-700 rounded hover:bg-red-50"
              >
                Reject
              </button>
            </div>
          </div>
        </li>
      ))}
    </ul>
  );
}
