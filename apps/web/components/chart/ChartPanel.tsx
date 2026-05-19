"use client";

import type { ReactNode } from "react";
import { Panel } from "../ui/Panel";

interface ChartPanelProps {
  title: ReactNode;
  subtitle?: ReactNode;
  controls?: ReactNode;
  legend?: ReactNode;
  children: ReactNode;
  contentGap?: number;
}

export function ChartPanel({
  title,
  subtitle,
  controls,
  legend,
  children,
  contentGap = 12,
}: ChartPanelProps) {
  return (
    <Panel
      title={title}
      subtitle={subtitle}
      controls={controls}
      legend={legend}
      contentGap={contentGap}
    >
      {children}
    </Panel>
  );
}
