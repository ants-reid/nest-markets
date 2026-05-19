# Tradeable Universe

## Equity Universe (default)

| Symbol | Name | Exchange | Asset Class |
|--------|------|----------|-------------|
| SPY | SPDR S&P 500 ETF | NYSE Arca | ETF |
| QQQ | Invesco QQQ Trust | NASDAQ | ETF |
| IWM | iShares Russell 2000 ETF | NYSE Arca | ETF |
| AAPL | Apple Inc. | NASDAQ | Equity |
| MSFT | Microsoft Corp. | NASDAQ | Equity |
| NVDA | NVIDIA Corp. | NASDAQ | Equity |
| TSLA | Tesla Inc. | NASDAQ | Equity |
| AMZN | Amazon.com Inc. | NASDAQ | Equity |
| META | Meta Platforms Inc. | NASDAQ | Equity |
| GOOGL | Alphabet Inc. (Class A) | NASDAQ | Equity |

## Macro Series

| Code | Description | Source | Frequency |
|------|-------------|--------|-----------|
| FEDFUNDS | Federal Funds Effective Rate | FRED | Daily |
| CPIAUCSL | CPI All Urban Consumers | FRED | Monthly |
| UNRATE | Unemployment Rate | FRED | Monthly |
| DGS10 | 10-Year Treasury Constant Maturity Rate | FRED | Daily |
| VIXCLS | CBOE Volatility Index (VIX) | FRED | Daily |

## Adding to the Universe

1. Add the symbol to the table above.
2. Run `refresh_universe_job` to register it in the DB.
3. Run `backfill_bars_job` for the new symbol with `--start 2015-01-01`.
