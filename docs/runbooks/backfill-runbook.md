# Backfill Runbook

## Overview

This runbook describes how to perform historical data backfills for Market Hunter.
All backfill jobs are idempotent and safe to re-run.

## Prerequisites

```bash
cd apps/learning
pip install -r requirements.txt
```

## Jobs

### 1. Backfill OHLCV Bars

```bash
python -m apps.learning.jobs.backfill_bars_job \
  --symbol AAPL \
  --timeframe 1D \
  --start 2015-01-01 \
  --end 2024-12-31
```

Supported timeframes: `1m`, `5m`, `15m`, `1H`, `4H`, `1D`, `1W`

### 2. Backfill News

```bash
python -m apps.learning.jobs.backfill_news_job \
  --symbols AAPL MSFT TSLA SPY QQQ \
  --limit 500
```

### 3. Backfill Macro Series

```bash
python -m apps.learning.jobs.backfill_macro_job \
  --series FEDFUNDS CPIAUCSL UNRATE DGS10 VIXCLS \
  --start 2010-01-01
```

Available series codes are defined in `FREDAdapter.list_series()`.

### 4. Backfill SEC Filings

```bash
python -m apps.learning.jobs.backfill_filings_job \
  --symbols AAPL MSFT \
  --form-types 10-K 10-Q 8-K
```

### 5. Refresh Instrument Universe

```bash
python -m apps.learning.jobs.refresh_universe_job
```

Run this first when setting up a new environment, or weekly to pick up new listings.

## Monitoring

- Check logs for `Backfilled N bars / records` confirmation lines.
- Re-run with overlapping date ranges if you suspect gaps — the upsert logic skips duplicates.
- Use `BarsBackfillService.list_gaps()` to inspect missing ranges programmatically.

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `NotImplementedError` | Provider not yet wired | Check `apps/api/app/clients/` for stub vs live adapter |
| `ConnectionRefusedError` | DB not running | Start PostgreSQL and check `DATABASE_URL` env var |
| Duplicate key violation | Idempotency gap | Safe to ignore — record already exists |
