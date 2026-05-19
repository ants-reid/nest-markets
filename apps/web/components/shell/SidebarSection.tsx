import styles from "./Sidebar.module.css";

interface SidebarSectionProps {
  label?: string;
  children: React.ReactNode;
}

export function SidebarSection({ label, children }: SidebarSectionProps) {
  return (
    <div className={styles.section}>
      {label && <span className={styles.sectionLabel}>{label}</span>}
      <div className={styles.sectionLinks}>{children}</div>
    </div>
  );
}
