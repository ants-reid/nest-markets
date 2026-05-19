# Sample Size Policy

## Purpose

Prevent model training on insufficient data, which would yield unreliable performance estimates and overfit models.

## Thresholds

These are enforced at runtime by `SampleSizePolicyService`:

| Model Type | Minimum Samples | Rationale |
|------------|----------------|-----------|
| `regime_model` | 500 | Need sufficient regime transitions across market cycles |
| `scoring_model` | 1,000 | Binary classification requires more samples for stable AUC |
| `execution_model` | 500 | Grade distribution must be well-represented |
| `walk_forward_per_fold` | 200 | Each fold needs enough test samples for meaningful metrics |

## Enforcement

Before any training pipeline runs, call:

```python
from app.services.validation.sample_size_policy_service import SampleSizePolicyService

svc = SampleSizePolicyService()
result = svc.check("scoring_model", n_samples=len(labeled_rows))
if not result.passed:
    raise RuntimeError(result.reason)
```

## Updating Thresholds

Thresholds can be adjusted via `SampleSizePolicy` dataclass. Any change must be reviewed by the ML team and documented here with rationale.
