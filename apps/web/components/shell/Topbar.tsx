"use client";

import { useEffect, useState } from "react";
import { useLearningMode } from "../../lib/learningMode";
import { getHealthStatus } from "../../lib/api";
import { LearningModePanel } from "../LearningModePanel";
import styles from "./Topbar.module.css";

interface TopbarProps {
  onMenuToggle: () => void;
}

const GLOBAL_EXECUTION_MODE_KEY = "dashboard:globalExecutionMode:v1";
const AUTO_PAPER_SETTINGS_KEY = "dashboard:autoPaperSettings:v2";
const AUTO_PAPER_NEXT_RUN_AT_KEY = "dashboard:autoPaperNextRunAt:v1";
type ExecutionMode = "paper" | "confirm_live" | "auto_live";
type ApiStatus = "checking" | "live" | "down";

export function Topbar({ onMenuToggle }: TopbarProps) {
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [showLearning, setShowLearning] = useState(false);
  const [apiStatus, setApiStatus] = useState<ApiStatus>("checking");
  const [executionMode, setExecutionMode] = useState<ExecutionMode>("paper");
  const [autoEnabled, setAutoEnabled] = useState(false);
  const [secondsUntilNextAuto, setSecondsUntilNextAuto] = useState<number | null>(null);
  const { enabled: learningEnabled } = useLearningMode();

  useEffect(() => {
    const root = document.documentElement;
    const current = root.getAttribute("data-theme");
    if (current === "light" || current === "dark") {
      setTheme(current);
      return;
    }
    const saved = window.localStorage.getItem("mh-theme");
    const next =
      saved === "light" || saved === "dark"
        ? saved
        : window.matchMedia("(prefers-color-scheme: light)").matches
          ? "light"
          : "dark";
    root.setAttribute("data-theme", next);
    setTheme(next);
  }, []);

  function toggleTheme() {
    const next = theme === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    window.localStorage.setItem("mh-theme", next);
    setTheme(next);
  }

  useEffect(() => {
    function refreshExecutionMode() {
      const saved = window.localStorage.getItem(GLOBAL_EXECUTION_MODE_KEY);
      if (saved === "paper" || saved === "confirm_live" || saved === "auto_live") {
        setExecutionMode(saved);
      }
    }

    refreshExecutionMode();
    const modeTimer = window.setInterval(refreshExecutionMode, 2000);
    return () => {
      window.clearInterval(modeTimer);
    };
  }, []);

  useEffect(() => {
    function refreshAutoState() {
      try {
        const raw = window.localStorage.getItem(AUTO_PAPER_SETTINGS_KEY);
        if (raw) {
          const parsed = JSON.parse(raw) as { autoEnabled?: boolean };
          setAutoEnabled(Boolean(parsed.autoEnabled));
        } else {
          setAutoEnabled(false);
        }

        const nextRunRaw = window.localStorage.getItem(AUTO_PAPER_NEXT_RUN_AT_KEY);
        if (!nextRunRaw) {
          setSecondsUntilNextAuto(null);
          return;
        }
        const nextRunTs = Date.parse(nextRunRaw);
        if (!Number.isFinite(nextRunTs)) {
          setSecondsUntilNextAuto(null);
          return;
        }
        const seconds = Math.max(0, Math.floor((nextRunTs - Date.now()) / 1000));
        setSecondsUntilNextAuto(seconds);
      } catch {
        setAutoEnabled(false);
        setSecondsUntilNextAuto(null);
      }
    }

    refreshAutoState();
    const autoTimer = window.setInterval(refreshAutoState, 1000);
    return () => {
      window.clearInterval(autoTimer);
    };
  }, []);

  useEffect(() => {
    let active = true;

    async function refreshHealth() {
      try {
        await getHealthStatus();
        if (active) setApiStatus("live");
      } catch {
        if (active) setApiStatus("down");
      }
    }

    void refreshHealth();
    const healthTimer = window.setInterval(() => {
      void refreshHealth();
    }, 15000);

    return () => {
      active = false;
      window.clearInterval(healthTimer);
    };
  }, []);

  const isRealMode = executionMode === "confirm_live" || executionMode === "auto_live";
  const tradeModeLabel = executionMode === "paper"
    ? "PAPER"
    : executionMode === "confirm_live"
      ? "REAL CONFIRM"
      : "REAL AUTO";

  const nextAutoCountdown = secondsUntilNextAuto === null
    ? "--:--"
    : `${Math.floor(secondsUntilNextAuto / 60).toString().padStart(2, "0")}:${Math.floor(secondsUntilNextAuto % 60).toString().padStart(2, "0")}`;

  return (
    <>
      <header className={styles.topbar}>
        <div className={styles.left}>
          <button
            type="button"
            className={styles.menuButton}
            onClick={onMenuToggle}
            aria-label="Toggle navigation menu"
          >
            <span className={styles.hamburger} />
            <span className={styles.hamburger} />
            <span className={styles.hamburger} />
          </button>
          <span className={styles.logoMark}>MH</span>
          <span className={styles.logoName}>Market Hunter</span>
        </div>
        <div className={styles.right}>
          <div className={styles.statusStrip} aria-label="Global system status">
            <span
              className={[
                styles.statusBadge,
                apiStatus === "live"
                  ? styles.statusLive
                  : apiStatus === "down"
                    ? styles.statusDown
                    : styles.statusChecking,
              ].join(" ")}
            >
              {apiStatus === "live" ? "API LIVE" : apiStatus === "down" ? "API DOWN" : "API CHECK"}
            </span>
            <span className={[styles.statusBadge, isRealMode ? styles.statusReal : styles.statusPaper].join(" ")}>
              {tradeModeLabel}
            </span>
            <span className={[styles.statusBadge, styles.statusAuto, autoEnabled ? styles.statusLive : styles.statusChecking].join(" ")}>
              {autoEnabled ? "AUTO ON" : "AUTO OFF"}
            </span>
            <span className={[styles.statusBadge, styles.statusNext, autoEnabled ? styles.statusInfo : styles.statusMuted].join(" ")}>
              NEXT {autoEnabled ? nextAutoCountdown : "--:--"}
            </span>
          </div>
          <button
            type="button"
            className={[styles.topbarBtn, learningEnabled ? styles.topbarBtnActive : ""]
              .filter(Boolean)
              .join(" ")}
            onClick={() => setShowLearning(true)}
            title="Learning Mode settings"
          >
            Learn
          </button>
          <button
            type="button"
            className={styles.topbarBtn}
            onClick={toggleTheme}
            title="Toggle theme"
          >
            {theme === "dark" ? "Light" : "Dark"}
          </button>
        </div>
      </header>
      {showLearning && <LearningModePanel onClose={() => setShowLearning(false)} />}
    </>
  );
}
