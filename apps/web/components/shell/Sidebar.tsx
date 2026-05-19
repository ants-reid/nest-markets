"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { SidebarSection } from "./SidebarSection";
import styles from "./Sidebar.module.css";

const SECTIONS = [
  {
    label: "Core",
    links: [
      { href: "/", label: "Home" },
      { href: "/dashboard", label: "Dashboard" },
      { href: "/workflow", label: "Workflow" },
      { href: "/execution", label: "Execution" },
      { href: "/broker", label: "Broker" },
    ],
  },
  {
    label: "Analytics",
    links: [
      { href: "/analytics", label: "Analytics" },
      { href: "/data-centre", label: "Data Centre" },
      { href: "/data-quality", label: "Data Quality" },
      { href: "/strategy-lab", label: "Strategy Lab" },
      { href: "/signals", label: "Signals" },
      { href: "/risk", label: "Risk" },
      { href: "/opportunities", label: "Opportunities" },
      { href: "/performance", label: "Performance" },
    ],
  },
  {
    label: "Admin",
    links: [
      { href: "/approvals", label: "Approvals" },
      { href: "/alerts", label: "Alerts" },
      { href: "/notifications", label: "Notifications" },
      { href: "/assets", label: "Assets" },
      { href: "/prompt-adaptations", label: "Prompt Adaptations" },
    ],
  },
];

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export function Sidebar({ isOpen, onClose }: SidebarProps) {
  const pathname = usePathname();

  function isActive(href: string) {
    return href === "/"
      ? pathname === "/"
      : pathname === href || pathname.startsWith(href + "/");
  }

  return (
    <>
      {isOpen && (
        <div
          className={styles.overlay}
          onClick={onClose}
          aria-hidden="true"
        />
      )}
      <aside
        className={[styles.sidebar, isOpen ? styles.open : ""].filter(Boolean).join(" ")}
        aria-label="Main navigation sidebar"
      >
        <div className={styles.logo}>
          <span className={styles.logoMark}>MH</span>
          <span className={styles.logoName}>Market Hunter</span>
        </div>
        <nav className={styles.nav} aria-label="Main navigation">
          {SECTIONS.map((section) => (
            <SidebarSection key={section.label} label={section.label}>
              {section.links.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className={[styles.link, isActive(link.href) ? styles.active : ""]
                    .filter(Boolean)
                    .join(" ")}
                  onClick={onClose}
                >
                  {link.label}
                </Link>
              ))}
            </SidebarSection>
          ))}
        </nav>
      </aside>
    </>
  );
}
