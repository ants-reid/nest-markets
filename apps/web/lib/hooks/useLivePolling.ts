"use client";

import { useEffect, useRef } from "react";

interface LivePollingOptions {
  enabled?: boolean;
  runImmediately?: boolean;
}

export function useLivePolling(
  callback: () => void | Promise<void>,
  intervalMs: number,
  options: LivePollingOptions = {},
): void {
  const { enabled = true, runImmediately = true } = options;
  const callbackRef = useRef(callback);

  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  useEffect(() => {
    if (!enabled || intervalMs <= 0) return;

    const run = () => {
      if (typeof document !== "undefined" && document.visibilityState === "hidden") {
        return;
      }
      void callbackRef.current();
    };

    if (runImmediately) {
      run();
    }

    const timer = window.setInterval(run, intervalMs);
    const onVisible = () => {
      if (document.visibilityState === "visible") {
        run();
      }
    };

    document.addEventListener("visibilitychange", onVisible);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [enabled, intervalMs, runImmediately]);
}
