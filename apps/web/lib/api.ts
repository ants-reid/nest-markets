// Re-export everything from the split API modules.
// This shim exists so that existing imports of "lib/api" continue to resolve
// while the canonical source lives in lib/api/ (indexed via lib/api/index.ts).
export * from "./api/index";
