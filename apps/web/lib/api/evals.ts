import { apiRequest } from "./core";

export interface EvalRun {
  id: string;
  provider_name: string | null;
  started_at: string | null;
  completed_at: string | null;
  summary_score: number | null;
  pass_rate: number | null;
  notes: string | null;
  created_at: string;
}

export async function getEvalRuns(limit = 50): Promise<EvalRun[]> {
  return apiRequest<EvalRun[]>(`/evals/runs?limit=${limit}`, { method: "GET" });
}
