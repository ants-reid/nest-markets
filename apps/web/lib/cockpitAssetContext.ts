export interface AssetContextLike {
  asset_id?: string | null;
  asset_name?: string | null;
  asset_symbol?: string | null;
  asset_detail_path?: string | null;
  has_asset_context?: boolean;
}

export function buildAssetDetailPath(context: AssetContextLike): string | null {
  if (context.asset_detail_path) {
    return context.asset_detail_path;
  }
  if (context.asset_id) {
    return `/asset-cards/${encodeURIComponent(context.asset_id)}`;
  }
  return null;
}

export function hasAssetContext(context: AssetContextLike): boolean {
  return Boolean(context.has_asset_context && buildAssetDetailPath(context));
}

export function formatAssetContextLabel(
  context: AssetContextLike,
  fallbackSymbol?: string,
): string {
  if (context.asset_symbol) {
    return context.asset_symbol;
  }
  if (fallbackSymbol) {
    return fallbackSymbol;
  }
  return "Asset";
}
