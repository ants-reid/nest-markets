import styles from "./FilterBar.module.css";

interface FilterOption {
  value: string;
  label: string;
}

export interface FilterGroup {
  label?: string;
  options: FilterOption[];
  value: string;
  onChange: (value: string) => void;
}

interface FilterBarProps {
  searchValue?: string;
  onSearchChange?: (value: string) => void;
  searchPlaceholder?: string;
  filters?: FilterGroup[];
  actions?: React.ReactNode;
  className?: string;
}

export function FilterBar({
  searchValue,
  onSearchChange,
  searchPlaceholder = "Search…",
  filters,
  actions,
  className,
}: FilterBarProps) {
  return (
    <div className={[styles.bar, className].filter(Boolean).join(" ")}>
      {onSearchChange && (
        <div className={styles.searchWrap}>
          <span className={styles.searchIcon} aria-hidden="true">⌕</span>
          <input
            type="search"
            value={searchValue ?? ""}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder={searchPlaceholder}
            className={styles.searchInput}
            aria-label="Search"
          />
        </div>
      )}

      {filters?.map((group, i) => (
        <div key={i} className={styles.group} role="group" aria-label={group.label}>
          {group.label && <span className={styles.label}>{group.label}</span>}
          {group.options.map((opt) => (
            <button
              key={opt.value}
              type="button"
              className={[
                styles.groupBtn,
                group.value === opt.value ? styles.groupBtnActive : "",
              ]
                .filter(Boolean)
                .join(" ")}
              onClick={() => group.onChange(opt.value)}
            >
              {opt.label}
            </button>
          ))}
        </div>
      ))}

      {actions && <div className={styles.actions}>{actions}</div>}
    </div>
  );
}
