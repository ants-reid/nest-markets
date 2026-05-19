"""Seed the asset universe for Market Hunter MVP.

Inserts 20 representative assets across FX, equity, ETF, commodity proxy,
crypto, and index proxy asset classes.  Re-running is fully idempotent —
existing rows are left unchanged (ON CONFLICT DO NOTHING via upsert).

Usage (from apps/api/):
    PYTHONPATH=$PWD python scripts/seed_assets.py

Environment variable DATABASE_URL must be set (or .env loaded via the app
config) before running.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the app package is importable when run from the CLI
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.enums import AssetClass
from app.db.models.asset import Asset
from app.db.session import SessionLocal

# ---------------------------------------------------------------------------
# Universe definition
# ---------------------------------------------------------------------------
_UNIVERSE: list[dict] = [
    # FX pairs
    {
        "symbol": "EURUSD",
        "name": "Euro / US Dollar",
        "asset_class": AssetClass.FX,
        "base_currency": "EUR",
        "quote_currency": "USD",
    },
    {
        "symbol": "GBPUSD",
        "name": "British Pound / US Dollar",
        "asset_class": AssetClass.FX,
        "base_currency": "GBP",
        "quote_currency": "USD",
    },
    {
        "symbol": "USDJPY",
        "name": "US Dollar / Japanese Yen",
        "asset_class": AssetClass.FX,
        "base_currency": "USD",
        "quote_currency": "JPY",
    },
    {
        "symbol": "AUDUSD",
        "name": "Australian Dollar / US Dollar",
        "asset_class": AssetClass.FX,
        "base_currency": "AUD",
        "quote_currency": "USD",
    },
    {
        "symbol": "USDCAD",
        "name": "US Dollar / Canadian Dollar",
        "asset_class": AssetClass.FX,
        "base_currency": "USD",
        "quote_currency": "CAD",
    },
    {
        "symbol": "USDCHF",
        "name": "US Dollar / Swiss Franc",
        "asset_class": AssetClass.FX,
        "base_currency": "USD",
        "quote_currency": "CHF",
    },
    # US equities
    {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "asset_class": AssetClass.EQUITY,
        "exchange": "NASDAQ",
        "sector": "Technology",
        "industry": "Consumer Electronics",
    },
    {
        "symbol": "MSFT",
        "name": "Microsoft Corporation",
        "asset_class": AssetClass.EQUITY,
        "exchange": "NASDAQ",
        "sector": "Technology",
        "industry": "Software",
    },
    {
        "symbol": "NVDA",
        "name": "NVIDIA Corporation",
        "asset_class": AssetClass.EQUITY,
        "exchange": "NASDAQ",
        "sector": "Technology",
        "industry": "Semiconductors",
    },
    {
        "symbol": "JPM",
        "name": "JPMorgan Chase & Co.",
        "asset_class": AssetClass.EQUITY,
        "exchange": "NYSE",
        "sector": "Financial Services",
        "industry": "Banks",
    },
    {
        "symbol": "XOM",
        "name": "Exxon Mobil Corporation",
        "asset_class": AssetClass.EQUITY,
        "exchange": "NYSE",
        "sector": "Energy",
        "industry": "Oil & Gas Integrated",
    },
    # Commodity proxies (ETFs tracking physical commodities)
    {
        "symbol": "GLD",
        "name": "SPDR Gold Shares",
        "asset_class": AssetClass.COMMODITY_PROXY,
        "exchange": "NYSE",
        "sector": "Commodities",
        "industry": "Gold",
    },
    {
        "symbol": "SLV",
        "name": "iShares Silver Trust",
        "asset_class": AssetClass.COMMODITY_PROXY,
        "exchange": "NYSE",
        "sector": "Commodities",
        "industry": "Silver",
    },
    {
        "symbol": "USO",
        "name": "United States Oil Fund",
        "asset_class": AssetClass.COMMODITY_PROXY,
        "exchange": "NYSE",
        "sector": "Commodities",
        "industry": "Crude Oil",
    },
    # Energy ETFs
    {
        "symbol": "XLE",
        "name": "Energy Select Sector SPDR Fund",
        "asset_class": AssetClass.ETF,
        "exchange": "NYSE",
        "sector": "Energy",
        "industry": "Oil & Gas",
    },
    {
        "symbol": "VDE",
        "name": "Vanguard Energy ETF",
        "asset_class": AssetClass.ETF,
        "exchange": "NYSE",
        "sector": "Energy",
        "industry": "Oil & Gas",
    },
    # Crypto
    {
        "symbol": "BTCUSD",
        "name": "Bitcoin / US Dollar",
        "asset_class": AssetClass.CRYPTO,
        "base_currency": "BTC",
        "quote_currency": "USD",
    },
    {
        "symbol": "ETHUSD",
        "name": "Ethereum / US Dollar",
        "asset_class": AssetClass.CRYPTO,
        "base_currency": "ETH",
        "quote_currency": "USD",
    },
    # Index proxies
    {
        "symbol": "SPY",
        "name": "SPDR S&P 500 ETF Trust",
        "asset_class": AssetClass.INDEX_PROXY,
        "exchange": "NYSE",
        "sector": "Broad Market",
        "industry": "Large Cap Blend",
    },
    {
        "symbol": "QQQ",
        "name": "Invesco QQQ Trust",
        "asset_class": AssetClass.INDEX_PROXY,
        "exchange": "NASDAQ",
        "sector": "Broad Market",
        "industry": "Large Cap Growth",
    },
]


def seed_assets(session=None) -> dict[str, int]:
    """Insert the standard 20-asset universe.

    Returns a dict with 'inserted' and 'skipped' counts.
    """
    own_session = session is None
    if own_session:
        session = SessionLocal()

    inserted = 0
    skipped = 0

    try:
        for row in _UNIVERSE:
            existing = session.query(Asset).filter_by(symbol=row["symbol"]).first()
            if existing is not None:
                skipped += 1
                continue
            asset = Asset(**row)
            session.add(asset)
            inserted += 1

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()

    return {"inserted": inserted, "skipped": skipped}


if __name__ == "__main__":
    result = seed_assets()
    print(f"Seed complete: {result['inserted']} inserted, {result['skipped']} skipped.")
