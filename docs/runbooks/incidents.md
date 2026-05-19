# Incident Response Guide

## Severity Levels

| Level | Description | Response Time | Example |
|-------|-------------|---------------|---------|
| P0 | Trading halted, broker disconnected | Immediate | BrokerDisconnected alert |
| P1 | Data pipeline failure, stale signals | < 15 min | IngestionLagCritical |
| P2 | Model drift detected, degraded quality | < 1 hour | FeatureDriftCritical |
| P3 | Non-critical warning, investigate | < 4 hours | ProviderHighLag |

## P0: Broker Disconnected

1. Check Grafana **Broker Health** dashboard
2. Verify IBKR TWS / IB Gateway is running: `scripts/deploy/deploy-api.sh --health`
3. Check API logs: `docker logs market-hunter-api --tail 100`
4. If credential issue: rotate API keys, redeploy with `scripts/deploy/deploy-api.sh`
5. If network issue: check connectivity to broker endpoint
6. Page on-call engineer if not resolved within 5 minutes

## P1: Ingestion Lag Critical

1. Check Grafana **Ingestion Lag** dashboard
2. Identify which provider is lagging
3. Check provider status pages
4. Restart ingestion workers: `docker restart market-hunter-learning`
5. If provider outage: see [Provider Failure Runbook](provider-failure.md)

## P2: Model Drift Critical

See [Model Rollback Runbook](model-rollback.md)

## On-Call Escalation

1. PagerDuty alert fires automatically from AlertManager
2. On-call engineer acknowledges within 5 minutes
3. Escalate to lead engineer after 30 minutes if unresolved
4. Post-incident review within 24 hours for P0/P1
