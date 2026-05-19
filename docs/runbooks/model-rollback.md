# Model Rollback Procedure

## When to Roll Back

Roll back when any of the following are true:
- `FeatureDriftCritical` alert fires and retraining is not imminent
- `ScoreDistributionShift` alert fires and root cause is unknown
- Live trading outcomes degrade significantly after a model promotion
- Model calibration Brier score exceeds 0.25

## Steps

### 1. Identify Current Active Model

```bash
curl -s http://localhost:8000/models/active | python -m json.tool
```

Note the `id` and check when it was promoted.

### 2. Roll Back via API

```bash
curl -sf -X POST http://localhost:8000/governance/rollback | python -m json.tool
```

The API will:
1. Find the previous active model from the audit log
2. Deactivate the current model
3. Promote the previous model to active

### 3. Verify Rollback

```bash
curl -s http://localhost:8000/models/active | python -m json.tool
# Confirm the model_version_id has changed
```

### 4. Monitor After Rollback

Watch for 15 minutes on Grafana dashboards:
- **Model Drift**: confirm drift alerts clear
- **API Latency**: confirm scoring latency is normal
- **Score Distribution**: confirm distribution normalises

### 5. Post-Rollback

1. File an incident ticket with the timeline
2. Investigate the promoted model for the root cause
3. Do not re-promote without fixing the underlying issue
4. Re-run walk-forward validation with the same data before next promotion
