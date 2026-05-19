/** Execution mode options available in the paper trading system */
export const EXECUTION_MODES = {
  paper: {
    label: "Paper Trading",
    description: "Simulated trades with no real capital at risk.",
  },
  live: {
    label: "Live Trading",
    description: "Real trades executed via connected broker.",
  },
} as const;

export type ExecutionMode = keyof typeof EXECUTION_MODES;
