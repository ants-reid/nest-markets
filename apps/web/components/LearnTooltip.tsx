"use client";

import { useEffect, useRef, useState } from "react";
import { useLearningMode, type SkillLevel } from "../lib/learningMode";

interface Explanations {
  beginner: string;
  intermediate: string;
  experienced: string;
  expert: string;
}

interface LearnTooltipProps {
  /** The explanation for each skill level. Can also pass a single string applied to all levels. */
  explain: string | Explanations;
  children: React.ReactNode;
  /** Position preference for the popup. Default: "top". */
  placement?: "top" | "bottom" | "right" | "left";
}

function getText(explain: string | Explanations, level: SkillLevel): string {
  if (typeof explain === "string") return explain;
  return explain[level];
}

export function LearnTooltip({ explain, children, placement = "top" }: LearnTooltipProps) {
  const { enabled, level } = useLearningMode();
  const [visible, setVisible] = useState(false);
  const wrapRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!enabled) setVisible(false);
  }, [enabled]);

  if (!enabled) {
    return <>{children}</>;
  }

  const text = getText(explain, level);

  const placementStyle = (): React.CSSProperties => {
    const base: React.CSSProperties = {
      position: "absolute",
      zIndex: 200,
      maxWidth: 280,
      background: "var(--surface-fill)",
      border: "1px solid var(--state-info)",
      borderRadius: 10,
      padding: "8px 12px",
      fontSize: 12,
      color: "var(--text-body)",
      lineHeight: 1.5,
      boxShadow: "var(--shadow-tooltip)",
      pointerEvents: "none",
      whiteSpace: "normal",
    };
    switch (placement) {
      case "bottom":
        return { ...base, top: "calc(100% + 8px)", left: "50%", transform: "translateX(-50%)" };
      case "right":
        return { ...base, top: "50%", left: "calc(100% + 8px)", transform: "translateY(-50%)" };
      case "left":
        return { ...base, top: "50%", right: "calc(100% + 8px)", transform: "translateY(-50%)" };
      case "top":
      default:
        return { ...base, bottom: "calc(100% + 8px)", left: "50%", transform: "translateX(-50%)" };
    }
  };

  return (
    <span
      ref={wrapRef}
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
      onFocus={() => setVisible(true)}
      onBlur={() => setVisible(false)}
      style={{ position: "relative", display: "inline-block", cursor: "help" }}
    >
      {/* Subtle underline indicator */}
      <span
        style={{
          borderBottom: "1px dashed var(--state-info)",
          paddingBottom: 1,
        }}
      >
        {children}
      </span>

      {visible && text ? (
        <span role="tooltip" style={placementStyle()}>
          <span
            style={{
              display: "flex",
              alignItems: "center",
              gap: 5,
              marginBottom: 4,
            }}
          >
            <span
              style={{
                fontSize: 10,
                fontWeight: 800,
                letterSpacing: 0.6,
                textTransform: "uppercase",
                color: "var(--state-info)",
              }}
            >
              Learning Mode
            </span>
            <span
              style={{
                fontSize: 9,
                fontWeight: 700,
                textTransform: "capitalize",
                letterSpacing: 0.5,
                color: "var(--text-muted)",
              }}
            >
              · {level}
            </span>
          </span>
          {text}
        </span>
      ) : null}
    </span>
  );
}
