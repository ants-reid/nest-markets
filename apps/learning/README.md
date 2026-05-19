# Learning App

Standalone Python package for historical backfill, feature engineering, regime classification, labeling, and model training pipelines.

## Package layout

```
apps/learning/
├── jobs/               # CLI entry-point jobs (backfill, refresh)
├── features/           # Feature computation modules
├── services/
│   ├── backfill/       # Bars / news / macro ingestion coordination
│   ├── normalization/  # Symbol and news normalisation
│   ├── storage/        # Persistence helpers
│   ├── regime/         # Regime classification engine (Phase 7)
│   ├── features/       # Feature building + caching (Phase 7)
│   └── labeling/       # Outcome labeling (Phase 9)
├── pipelines/          # Training and validation pipelines (Phase 10)
└── tests/
```

## Running a backfill

```bash
python -m apps.learning.jobs.backfill_bars_job --symbol AAPL --start 2020-01-01
```

See `docs/runbooks/backfill-runbook.md` for full instructions.
