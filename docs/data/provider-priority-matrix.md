# Provider Priority Matrix

This document defines the priority order for each data type when multiple providers are available.
The `ProviderDispatcherService` uses this ordering.

## Market Data (OHLCV Bars + Quotes)

| Priority | Provider | Coverage | Notes |
|----------|----------|----------|-------|
| 1 | IBKR (live) | Equities, ETFs, Futures, FX | Requires live IB Gateway; fastest for real-time |
| 2 | Tiingo | Equities, ETFs | Good historical depth; REST |
| 3 | Twelve Data | Equities, Forex, Crypto | Generous free tier |
| 4 | Mock | Test symbols | Only in test environments |

## News

| Priority | Provider | Coverage | Notes |
|----------|----------|----------|-------|
| 1 | Finnhub | US equities | Sentiment score included |
| 2 | Alpaca News | US equities | Tightly coupled to Alpaca broker |
| 3 | GDELT | Global events | Open, no API key required |
| 4 | Mock | Test tickers | Test only |

## Fundamentals

| Priority | Provider | Coverage | Notes |
|----------|----------|----------|-------|
| 1 | SEC EDGAR | US public companies | Free, authoritative |
| 2 | Mock | Any | Test only |

## Macro

| Priority | Provider | Coverage | Notes |
|----------|----------|----------|-------|
| 1 | FRED (St. Louis Fed) | US macroeconomic | Free API key required |
| 2 | Mock | Predefined series | Test only |
