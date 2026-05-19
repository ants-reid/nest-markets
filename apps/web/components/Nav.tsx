"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { useLearningMode } from "../lib/learningMode";
import { LearningModePanel } from "./LearningModePanel";

const links = [
  { href: "/", label: "Home" },
  { href: "/dashboard", label: "Dashboard" },
  { href: "/broker", label: "Portfolio" },
  { href: "/analytics", label: "Analytics" },
  { href: "/workflow", label: "Workflow" },
  { href: "/signals", label: "Signals" },
  { href: "/risk", label: "Risk" },
  { href: "/approvals", label: "Approvals" },
  { href: "/execution", label: "Execution" },
  { href: "/alerts", label: "Alerts" },
  { href: "/notifications", label: "Notifications" },
  { href: "/cockpit", label: "Cockpit" },
  { href: "/assets", label: "Assets" },
  { href: "/opportunities", label: "Opportunities" },
  { href: "/performance", label: "Performance" },
  { href: "/prompt-adaptations", label: "Prompt Adaptations" },
];

export function Nav() {
  const pathname = usePathname();
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [showLearning, setShowLearning] = useState(false);
  const { enabled: learningEnabled } = useLearningMode();

  useEffect(() => {
    const root = document.documentElement;
    const current = root.getAttribute("data-theme");
    if (current === "light" || current === "dark") {
      setTheme(current);
      return;
    }

    const saved = window.localStorage.getItem("mh-theme");
    const nextTheme = saved === "light" || saved === "dark"
      ? saved
      : window.matchMedia("(prefers-color-scheme: light)").matches
        ? "light"
        : "dark";

    root.setAttribute("data-theme", nextTheme);
    setTheme(nextTheme);
  }, []);

  function toggleTheme() {
    const nextTheme = theme === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", nextTheme);
    window.localStorage.setItem("mh-theme", nextTheme);
    setTheme(nextTheme);
  }

  return (
    <nav
      style={{
        display: "flex",
        flexDirection: "column",
        width: "100%",
        maxWidth: "100%",
        boxSizing: "border-box",
        gap: 8,
        padding: "14px 18px",
        border: "1px solid var(--surface-border)",
        borderRadius: 16,
        background: "var(--surface-fill)",
        boxShadow: "var(--surface-shadow)",
      }}
    >
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 8,
        }}
      >
        <span
          style={{
            color: "var(--text-muted)",
            fontSize: 12,
            fontWeight: 900,
            letterSpacing: 1.7,
            textTransform: "uppercase",
            userSelect: "none",
            border: "1px solid var(--surface-border)",
            borderRadius: 999,
            padding: "5px 9px",
            background: "var(--surface-soft)",
          }}
        >
          MH
        </span>
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: 8,
            justifyContent: "flex-end",
          }}
        >
          <button
            type="button"
            onClick={() => setShowLearning(true)}
            title="Learning Mode settings"
            style={{
              border: `1px solid ${learningEnabled ? "var(--state-info)" : "var(--surface-border)"}`,
              borderRadius: 999,
              padding: "7px 12px",
              background: learningEnabled
                ? "color-mix(in oklab, var(--state-info) 18%, var(--surface-soft))"
                : "var(--surface-soft)",
              color: learningEnabled ? "var(--state-info)" : "var(--text-body)",
              fontWeight: 700,
              fontSize: 12,
              cursor: "pointer",
            }}
          >
            Learn
          </button>
          <button
            type="button"
            onClick={toggleTheme}
            style={{
              border: "1px solid var(--surface-border)",
              borderRadius: 999,
              padding: "7px 12px",
              background: "var(--surface-soft)",
              color: "var(--text-body)",
              fontWeight: 700,
              fontSize: 12,
              cursor: "pointer",
            }}
          >
            {theme === "dark" ? "Light" : "Dark"}
          </button>
        </div>
      </div>
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 8,
        }}
      >
        {links.map((link) => {
          const isActive =
            link.href === "/" ? pathname === "/" : pathname === link.href || pathname.startsWith(link.href + "/");
          return (
            <Link
              key={link.href}
              href={link.href}
              style={{
                textDecoration: "none",
                color: isActive ? "var(--text-strong)" : "var(--text-body)",
                fontWeight: 700,
                fontSize: 13,
                letterSpacing: 0.2,
                padding: "7px 14px",
                borderRadius: 999,
                background: isActive ? "var(--surface-soft)" : "transparent",
                border: `1px solid ${isActive ? "var(--accent-secondary)" : "var(--surface-border)"}`,
                boxShadow: isActive ? "0 0 0 1px color-mix(in oklab, var(--accent-secondary) 30%, transparent)" : "none",
              }}
            >
              {link.label}
            </Link>
          );
        })}
      </div>
      {showLearning && <LearningModePanel onClose={() => setShowLearning(false)} />}
    </nav>
  );
}