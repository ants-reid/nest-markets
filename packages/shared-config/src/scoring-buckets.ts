/** Win-rate scoring buckets used for color/grade assignment */
export const SCORING_BUCKETS = [
  { min: 0, max: 0.4, grade: "F", label: "Poor" },
  { min: 0.4, max: 0.5, grade: "D", label: "Below Average" },
  { min: 0.5, max: 0.6, grade: "C", label: "Average" },
  { min: 0.6, max: 0.7, grade: "B", label: "Good" },
  { min: 0.7, max: 0.8, grade: "A", label: "Excellent" },
  { min: 0.8, max: 1.0, grade: "S", label: "Outstanding" },
] as const;

export type ScoringGrade = (typeof SCORING_BUCKETS)[number]["grade"];

export function getScoringGrade(winRate: number): ScoringGrade {
  const bucket = SCORING_BUCKETS.find((b) => winRate >= b.min && winRate < b.max);
  return bucket?.grade ?? "F";
}
