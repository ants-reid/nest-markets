import Link from "next/link";

import {
  buildAssetDetailPath,
  formatAssetContextLabel,
  hasAssetContext,
  type AssetContextLike,
} from "../../lib/cockpitAssetContext";
import styles from "./AssetContextLink.module.css";

interface AssetContextLinkProps {
  context: AssetContextLike;
  fallbackSymbol?: string;
  linkText?: string;
  unavailableText?: string;
}

export function AssetContextLink({
  context,
  fallbackSymbol,
  linkText = "View asset context",
  unavailableText = "Asset context unavailable",
}: AssetContextLinkProps) {
  const href = buildAssetDetailPath(context);
  const label = formatAssetContextLabel(context, fallbackSymbol);

  if (!hasAssetContext(context) || !href) {
    return <span className={styles.unavailable}>{unavailableText}</span>;
  }

  return (
    <span className={styles.wrap}>
      <span className={styles.name}>{context.asset_name ?? label}</span>
      <Link className={styles.link} href={href}>
        {linkText}
      </Link>
    </span>
  );
}
