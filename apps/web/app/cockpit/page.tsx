"use client";

// MH-COCKPIT-HUB-1 — Cockpit hub (read-only navigation).
//
// Top-level landing page that links to every existing `/cockpit/*`
// sub-page. Pure navigation surface — no API calls, no mutating actions,
// no trading toggles.
//
// Drift-lock guarantee: navigation only. Adding this page does not change
// the global Nav, the workers, the broker, trading_control, risk paths,
// or any enforcement state. Auto-paper, auto, and live trading remain OFF.

import Link from "next/link";

import styles from "../../styles/pages/cockpit-hub.module.css";

interface CockpitLink {
  href: string;
  title: string;
  description: string;
}

const SECTIONS: ReadonlyArray<{
  heading: string;
  items: ReadonlyArray<CockpitLink>;
}> = [
  {
    heading: "Operator overviews",
    items: [
      {
        href: "/cockpit/notifications",
        title: "Notifications digest",
        description:
          "Compact, severity-filtered digest of recent operator-relevant notifications.",
      },
      {
        href: "/cockpit/auto-paper-status",
        title: "Auto-paper status",
        description:
          "Read-only view of auto-paper enforcement state. Enforcement remains OFF.",
      },
      {
        href: "/cockpit/news",
        title: "News overview",
        description:
          "Compact news-feed cockpit view backed by recent news articles.",
      },
    ],
  },
  {
    heading: "Audit",
    items: [
      {
        href: "/cockpit/audit",
        title: "Audit hub",
        description:
          "Index of every cockpit audit tile (broker submit decisions, news-in-decision log, …).",
      },
    ],
  },
];

export default function CockpitHubPage() {
  return (
    <main className={styles.page}>
      <div className={styles.container}>
        <header className={styles.header}>
          <div>
            <h1 className={styles.title}>Cockpit</h1>
            <p className={styles.subtitle}>
              Operator-facing read-only surfaces. Every link below opens a
              page that does not modify any trading, broker, or risk state.
            </p>
          </div>
        </header>

        <div className={styles.driftLockNotice}>
          Drift lock: this hub adds no new toggles, no new mutating actions,
          and no auto/live trading controls. Auto-paper, auto, and live
          trading remain OFF.
        </div>

        {SECTIONS.map((section) => (
          <section key={section.heading} className={styles.section}>
            <h2 className={styles.sectionTitle}>{section.heading}</h2>
            <div className={styles.tileGrid}>
              {section.items.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={styles.tile}
                >
                  <div className={styles.tileHead}>
                    <h3 className={styles.tileTitle}>{item.title}</h3>
                    <span className={styles.tileBadge}>read-only</span>
                  </div>
                  <p className={styles.tileDesc}>{item.description}</p>
                  <div className={styles.tileFoot}>
                    <span className={styles.linkPath}>{item.href}</span>
                  </div>
                </Link>
              ))}
            </div>
          </section>
        ))}
      </div>
    </main>
  );
}
