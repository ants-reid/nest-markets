"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

export type SkillLevel = "beginner" | "intermediate" | "experienced" | "expert";

interface LearningModeContext {
  enabled: boolean;
  level: SkillLevel;
  toggle: () => void;
  setLevel: (level: SkillLevel) => void;
}

const Ctx = createContext<LearningModeContext>({
  enabled: false,
  level: "beginner",
  toggle: () => {},
  setLevel: () => {},
});

const STORAGE_ENABLED = "mh_learning_enabled";
const STORAGE_LEVEL = "mh_learning_level";

export function LearningModeProvider({ children }: { children: React.ReactNode }) {
  const [enabled, setEnabled] = useState(false);
  const [level, setLevelState] = useState<SkillLevel>("beginner");

  useEffect(() => {
    const storedEnabled = localStorage.getItem(STORAGE_ENABLED);
    const storedLevel = localStorage.getItem(STORAGE_LEVEL) as SkillLevel | null;
    if (storedEnabled === "true") setEnabled(true);
    if (storedLevel) setLevelState(storedLevel);
  }, []);

  const toggle = useCallback(() => {
    setEnabled((prev) => {
      const next = !prev;
      localStorage.setItem(STORAGE_ENABLED, String(next));
      return next;
    });
  }, []);

  const setLevel = useCallback((l: SkillLevel) => {
    setLevelState(l);
    localStorage.setItem(STORAGE_LEVEL, l);
  }, []);

  return <Ctx.Provider value={{ enabled, level, toggle, setLevel }}>{children}</Ctx.Provider>;
}

export function useLearningMode(): LearningModeContext {
  return useContext(Ctx);
}
