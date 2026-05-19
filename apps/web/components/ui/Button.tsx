import Link from "next/link";
import styles from "./Button.module.css";

type ButtonVariant = "primary" | "secondary" | "ghost";
type ButtonSize = "sm" | "md" | "lg";

interface ButtonBaseProps {
  variant?: ButtonVariant;
  size?: ButtonSize;
  disabled?: boolean;
  loading?: boolean;
  icon?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}

interface ButtonAsButtonProps extends ButtonBaseProps {
  asLink?: undefined;
  href?: undefined;
  type?: "button" | "submit" | "reset";
  onClick?: React.MouseEventHandler<HTMLButtonElement>;
}

interface ButtonAsLinkProps extends ButtonBaseProps {
  asLink: true;
  href: string;
  type?: undefined;
  onClick?: undefined;
}

type ButtonProps = ButtonAsButtonProps | ButtonAsLinkProps;

export function Button({
  variant = "secondary",
  size = "md",
  disabled = false,
  loading = false,
  icon,
  children,
  className,
  ...rest
}: ButtonProps) {
  const classes = [
    styles.btn,
    styles[variant],
    styles[size],
    loading ? styles.loading : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  const inner = (
    <>
      {loading ? <span className={styles.spinner} aria-hidden="true" /> : icon ? <span className={styles.icon}>{icon}</span> : null}
      <span>{children}</span>
    </>
  );

  if (rest.asLink) {
    return (
      <Link href={rest.href} className={classes}>
        {inner}
      </Link>
    );
  }

  return (
    <button
      type={rest.type ?? "button"}
      className={classes}
      disabled={disabled || loading}
      onClick={rest.onClick}
    >
      {inner}
    </button>
  );
}
