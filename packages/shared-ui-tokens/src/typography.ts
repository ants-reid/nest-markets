/** Typography tokens (map to CSS vars in globals.css) */
export const typography = {
  fontFamily: "var(--font-family)",
  fontMono: "var(--font-mono)",

  // Sizes
  textXs: "var(--text-xs)",
  textSm: "var(--text-sm)",
  textBase: "var(--text-base)",
  textLg: "var(--text-lg)",
  textXl: "var(--text-xl)",
  text2xl: "var(--text-2xl)",

  // Weights
  fontNormal: "400",
  fontMedium: "500",
  fontSemibold: "600",
  fontBold: "700",
} as const;

export type TypographyToken = keyof typeof typography;
