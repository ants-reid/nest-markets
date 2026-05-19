# Provider Outage Handling

## Affected Providers

| Provider | Data Type | Fallback |
|----------|-----------|----------|
| IBKR | Market data (live) | Tiingo (delayed) |
| Twelve Data | Bars / quotes | Tiingo |
| Tiingo | Bars / quotes | None |
| Finnhub | News | Alpaca News |
| Alpaca News | News | GDELT |
| GDELT | Events | None (degrade gracefully) |
| SEC EDGAR | Filings | Cached last-known |
| FRED | Macro data | Cached last-known |

## Runbook

### 1. Confirm Outage

Check the `ProviderIngestionStopped` or `ProviderHighLag` alert in AlertManager.

Verify by checking provider status pages:
- Twelve Data: https://status.twelvedata.com
- Tiingo: https://api.tiingo.com/documentation/general/overview
- Finnhub: https://finnhub.io/docs/api

### 2. Switch to Fallback

The `ProviderDispatcherService` automatically tries fallback providers.
If auto-failover is not working:

```bash
# Inspect dispatcher configuration
curl -s http://localhost:8000/market-data/providers | python -m json.tool
```

### 3. Alert Users

If the outage affects live signals, notify trading operations team.

### 4. Resume Normal Operations

Once the primary provider recovers:
1. Confirm ingestion lag has returned to < 30 seconds
2. Run a backfill for the gap period:
   ```bash
   scripts/learning/backfill-bars.sh --from <outage_start> --to <outage_end>
   ```
3. Close the incident ticket
