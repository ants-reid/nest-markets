"use client";

import { useEffect, useState } from "react";
import { runAutoPaperTrader } from "../../lib/api";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";
import styles from "./AppShell.module.css";

interface AppShellProps {
  children: React.ReactNode;
}

const AUTO_PAPER_SETTINGS_KEY = "dashboard:autoPaperSettings:v2";
const AUTO_PAPER_NEXT_RUN_AT_KEY = "dashboard:autoPaperNextRunAt:v1";
const AUTO_PAPER_DEFAULT_INTERVAL_MINUTES = 15;

export function AppShell({ children }: AppShellProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    let active = true;
    let runInFlight = false;

    async function tickAutoPaper() {
      if (!active || typeof window === "undefined") return;

      let autoEnabled = false;
      let intervalMinutes = AUTO_PAPER_DEFAULT_INTERVAL_MINUTES;
      try {
        const raw = window.localStorage.getItem(AUTO_PAPER_SETTINGS_KEY);
        if (raw) {
          const parsed = JSON.parse(raw) as { autoEnabled?: boolean; intervalMinutes?: number };
          autoEnabled = Boolean(parsed.autoEnabled);
          if (typeof parsed.intervalMinutes === "number" && parsed.intervalMinutes > 0) {
            intervalMinutes = parsed.intervalMinutes;
          }
        }
      } catch {
        autoEnabled = false;
      }

      if (!autoEnabled) {
        window.localStorage.removeItem(AUTO_PAPER_NEXT_RUN_AT_KEY);
        return;
      }

      const now = Date.now();
      const nextRunRaw = window.localStorage.getItem(AUTO_PAPER_NEXT_RUN_AT_KEY);
      const nextRunTs = nextRunRaw ? Date.parse(nextRunRaw) : NaN;

      if (!Number.isFinite(nextRunTs)) {
        const seeded = new Date(now + intervalMinutes * 60 * 1000).toISOString();
        window.localStorage.setItem(AUTO_PAPER_NEXT_RUN_AT_KEY, seeded);
        return;
      }

      if (now < nextRunTs || runInFlight) return;

      runInFlight = true;
      try {
        await runAutoPaperTrader("scheduled");
      } catch {
        // Keep cadence moving even if one run fails.
      } finally {
        if (active) {
          const next = new Date(Date.now() + intervalMinutes * 60 * 1000).toISOString();
          window.localStorage.setItem(AUTO_PAPER_NEXT_RUN_AT_KEY, next);
        }
        runInFlight = false;
      }
    }

    void tickAutoPaper();
    const timer = window.setInterval(() => {
      void tickAutoPaper();
    }, 1000);

    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, []);

  return (
    <div className={styles.shell}>
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <Topbar onMenuToggle={() => setSidebarOpen((prev) => !prev)} />
      <main className={styles.main}>{children}</main>
    </div>
  );
}
