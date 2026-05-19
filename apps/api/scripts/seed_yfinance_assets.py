"""Seed the yfinance core import universe into the assets table.

Covers all symbols required before running the first yfinance daily import:
  - US Equities: AAPL MSFT NVDA AMZN META TSLA GOOGL AMD
  - ETFs:        SPY  QQQ  IWM  GLD  TLT
  - Forex:       EURUSD GBPUSD USDJPY AUDUSD NZDUSD
  - Crypto:      BTC-USD ETH-USD SOL-USD
  - Indexes:     ^GSPC ^IXIC ^DJI ^VIX

Idempotent rules:
  - If the row does not exist → INSERT (counted as "created").
  - If the row exists and any nullable field is NULL while the seed has a
    value → UPDATE that field (counted as "updated").
  - If the row exists and all fields already match → no change ("skipped").

Usage (from apps/api/):
    PYTHONPATH=$PWD python scripts/seed_yfinance_assets.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.enums import AssetClass
from app.db.models.asset import Asset
from app.db.session import SessionLocal

# ---------------------------------------------------------------------------
# Universe
# ---------------------------------------------------------------------------

_UNIVERSE: list[dict] = [
    # ------------------------------------------------------------------
    # US Equities
    # ------------------------------------------------------------------
    {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "asset_class": AssetClass.EQUITY,
        "exchange": "NASDAQ",
        "base_currency": "USD",
        "sector": "Technology",
        "industry": "Consumer Electronics",
    },
    {
        "symbol": "MSFT",
        "name": "Microsoft Corporation",
        "asset_class": AssetClass.EQUITY,
        "exchange": "NASDAQ",
        "base_currency": "USD",
        "sector": "Technology",
        "industry": "Software",
    },
    {
        "symbol": "NVDA",
        "name": "NVIDIA Corporation",
        "asset_class": AssetClass.EQUITY,
        "exchange": "NASDAQ",
        "base_currency": "USD",
        "sector": "Technology",
        "industry": "Semiconductors",
    },
    {
        "symbol": "AMZN",
        "name": "Amazon.com Inc.",
        "asset_class": AssetClass.EQUITY,
        "exchange": "NASDAQ",
        "base_currency": "USD",
        "sector": "Consumer Cyclical",
        "industry": "Internet Retail",
    },
    {
        "symbol": "META",
        "name": "Meta Platforms Inc.",
        "asset_class": AssetClass.EQUITY,
        "exchange": "NASDAQ",
        "base_currency": "USD",
        "sector": "Communication Services",
        "industry": "Internet Content & Information",
    },
    {
        "symbol": "TSLA",
        "name": "Tesla Inc.",
        "asset_class": AssetClass.EQUITY,
        "exchange": "NASDAQ",
        "base_currency": "USD",
        "sector": "Consumer Cyclical",
        "industry": "Auto Manufacturers",
    },
    {
        "symbol": "GOOGL",
        "name": "Alphabet Inc.",
        "asset_class": AssetClass.EQUITY,
        "exchange": "NASDAQ",
        "base_currency": "USD",
        "sector": "Communication Services",
        "industry": "Internet Content & Information",
    },
    {
        "symbol": "AMD",
        "name": "Advanced Micro Devices Inc.",
        "asset_class": AssetClass.EQUITY,
        "exchange": "NASDAQ",
        "base_currency": "USD",
        "sector": "Technology",
        "industry": "Semiconductors",
    },
    # ------------------------------------------------------------------
    # ETFs / Index proxies
    # ------------------------------------------------------------------
    {
        "symbol": "SPY",
        "name": "SPDR S&P 500 ETF Trust",
        "asset_class": AssetClass.ETF,
        "exchange": "NYSE",
        "base_currency": "USD",
        "sector": "Broad Market",
        "industry": "Large Cap Blend",
    },
    {
        "symbol": "QQQ",
        "name": "Invesco QQQ Trust",
        "asset_class": AssetClass.ETF,
        "exchange": "NASDAQ",
        "base_currency": "USD",
        "sector": "Broad Market",
        "industry": "Large Cap Growth",
    },
    {
        "symbol": "IWM",
        "name": "iShares Russell 2000 ETF",
        "asset_class": AssetClass.ETF,
        "exchange": "NYSE",
        "base_currency": "USD",
        "sector": "Broad Market",
        "industry": "Small Cap Blend",
    },
    {
        "symbol": "GLD",
        "name": "SPDR Gold Shares",
        "asset_class": AssetClass.ETF,
        "exchange": "NYSE",
        "base_currency": "USD",
        "sector": "Commodities",
        "industry": "Gold",
    },
    {
        "symbol": "TLT",
        "name": "iShares 20+ Year Treasury Bond ETF",
        "asset_class": AssetClass.ETF,
        "exchange": "NASDAQ",
        "base_currency": "USD",
        "sector": "Fixed Income",
        "industry": "Government Bonds",
    },
    # ------------------------------------------------------------------
    # Forex  (internal symbol; YFinanceClient maps to SYMBOL=X)
    # ------------------------------------------------------------------
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
        "symbol": "NZDUSD",
        "name": "New Zealand Dollar / US Dollar",
        "asset_class": AssetClass.FX,
        "base_currency": "NZD",
        "quote_currency": "USD",
    },
    # ------------------------------------------------------------------
    # Crypto  (yfinance format: SYMBOL-USD)
    # ------------------------------------------------------------------
    {
        "symbol": "BTC-USD",
        "name": "Bitcoin / US Dollar",
        "asset_class": AssetClass.CRYPTO,
        "base_currency": "BTC",
        "quote_currency": "USD",
    },
    {
        "symbol": "ETH-USD",
        "name": "Ethereum / US Dollar",
        "asset_class": AssetClass.CRYPTO,
        "base_currency": "ETH",
        "quote_currency": "USD",
    },
    {
        "symbol": "SOL-USD",
        "name": "Solana / US Dollar",
        "asset_class": AssetClass.CRYPTO,
        "base_currency": "SOL",
        "quote_currency": "USD",
    },
    # ------------------------------------------------------------------
    # Indexes  (yfinance format: ^SYMBOL)
    # ------------------------------------------------------------------
    {
        "symbol": "^GSPC",
        "name": "S&P 500 Index",
        "asset_class": AssetClass.INDEX_PROXY,
        "exchange": "NYSE",
        "base_currency": "USD",
        "sector": "Broad Market",
        "industry": "Large Cap Blend",
    },
    {
        "symbol": "^IXIC",
        "name": "NASDAQ Composite Index",
        "asset_class": AssetClass.INDEX_PROXY,
        "exchange": "NASDAQ",
        "base_currency": "USD",
        "sector": "Broad Market",
        "industry": "Large Cap Growth",
    },
    {
        "symbol": "^DJI",
        "name": "Dow Jones Industrial Average",
        "asset_class": AssetClass.INDEX_PROXY,
        "exchange": "NYSE",
        "base_currency": "USD",
        "sector": "Broad Market",
        "industry": "Large Cap Blend",
    },
    {
        "symbol": "^VIX",
        "name": "CBOE Volatility Index",
        "asset_class": AssetClass.INDEX_PROXY,
        "exchange": "CBOE",
        "base_currency": "USD",
        "sector": "Volatility",
        "industry": "Volatility Index",
    },
]

# Fields that can be filled in on an existing row if currently NULL
_NULLABLE_FIELDS = ("name", "exchange", "base_currency", "quote_currency", "sector", "industry")


def seed_yfinance_assets(session=None) -> dict[str, int]:
    """Upsert the yfinance core universe into the assets table.

    Returns counts: {'created': int, 'updated': int, 'skipped': int}
    """
    own_session = session is None
    if own_session:
        session = SessionLocal()

    created = updated = skipped = 0

    try:
        for row in _UNIVERSE:
            existing = session.query(Asset).filter_by(symbol=row["symbol"]).first()

            if existing is None:
                session.add(Asset(**row))
                created += 1
                print(f"  [CREATE] {row['symbol']:12s}  ({row['asset_class'].value})")
            else:
                changed_fields: list[str] = []
                for field in _NULLABLE_FIELDS:
                    seed_value = row.get(field)
                    if seed_value is not None and getattr(existing, field) is None:
                        setattr(existing, field, seed_value)
                        changed_fields.append(field)

                if changed_fields:
                    updated += 1
                    print(f"  [UPDATE] {existing.symbol:12s}  filled: {', '.join(changed_fields)}")
                else:
                    skipped += 1
                    print(f"  [SKIP]   {existing.symbol:12s}  already complete")

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()

    return {"created": created, "updated": updated, "skipped": skipped}


if __name__ == "__main__":
    print("Seeding yfinance asset universe...\n")
    result = seed_yfinance_assets()
    total = result["created"] + result["updated"] + result["skipped"]
    print(
        f"\nDone: {result['created']} created, "
        f"{result['updated']} updated, "
        f"{result['skipped']} skipped "
        f"({total} total in universe)."
    )
