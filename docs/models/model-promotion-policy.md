# Model Promotion Policy

## Overview

A candidate model must pass all the following gates before it can be promoted to the active slot.

## Gate 1: Sample Size

Minimum labeled samples required (enforced by `SampleSizePolicyService`):

| Model | Minimum Samples |
|-------|----------------|
| Regime | 500 |
| Scoring | 1,000 |
| Execution | 500 |
| Walk-Forward Per Fold | 200 |

## Gate 2: Walk-Forward Validation

- Minimum 3 folds required
- Mean primary metric must meet threshold (see Gate 3)
- No look-ahead leakage (validated by `WalkForwardValidator`)

## Gate 3: Primary Metric Threshold

| Model | Metric | Minimum |
|-------|--------|---------|
| Regime | Accuracy | 0.65 |
| Scoring | AUC-ROC | 0.62 |
| Execution | Accuracy | 0.65 |

## Gate 4: Calibration (Scoring and Regime only)

Maximum Brier score:

| Model | Max Brier Score |
|-------|----------------|
| Regime | 0.22 |
| Scoring | 0.22 |
| Execution | 0.25 |

## Gate 5: Shadow Comparison

- Candidate must be run in shadow mode against live opportunities
- Shadow metric must not regress vs active model (improvement ≥ 0%)
- Minimum 100 shadow records required

## Promotion Workflow

1. Train → `RegimeModelTrainer` / `ScoringModelTrainer` / `ExecutionModelTrainer`
2. Walk-forward validate → `WalkForwardValidatorService`
3. Publish candidate → `CandidateModelPublisher`
4. Shadow compare → `ShadowModelCompareService`
5. Policy check → `ModelPolicyService.evaluate()`
6. Human approval in Promotions UI (`/promotions`)
7. API promotion → `POST /governance/promote`
8. Monitor on Grafana Model Drift dashboard
