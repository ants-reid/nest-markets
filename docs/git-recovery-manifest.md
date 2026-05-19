# Git Recovery Manifest

Date: 2026-05-19 21:02:28

## Source And Backup

- Source folder: `/Users/ants/Documents/market-hunter-mvp`
- Backup folder: `/Users/ants/Documents/market-hunter-mvp-release-ready-backup-20260519-210228`

## Why Recovery Is Needed

This working folder contains the release-ready Market Hunter state but has no local Git metadata.

Confirmed recovery trigger:

- no `.git` directory
- no `.git` file
- `git rev-parse --show-toplevel` fails
- `git status` fails
- no alternate Git-backed Market Hunter checkout was found locally during bounded searches

## Release Evidence Summary

- backend Ruff passed
- backend pytest passed: `2301`
- learning passed: `99`
- frontend lint/build passed
- smoke passed: `20/20`
- full Playwright passed: `272/272`
- Gate 1 green
- Gate 2 green
- Gate 3 green
- Gate 7 green
- RC2-Gate 2 green
- release-control docs present, including `docs/release-candidate-handoff.md`

## Backup Method

The safety backup was created before Git initialization using `rsync` to a timestamped folder outside the working tree.

Excluded from backup because they are generated or heavy and safe to regenerate:

- `node_modules`
- `.next`
- `test-results`
- `playwright-report`
- `.venv`
- `__pycache__`
- `.pytest_cache`
- `dist`
- `build`

## Must Not Be Overwritten

Do not overwrite or discard without explicit review:

- source code under `apps/`
- docs under `docs/`
- tests under `apps/**/tests/` and `learning/tests/`
- Alembic migrations and database scripts
- visual snapshots
- config files, lockfiles, and package manifests

## Safe Next Steps

1. Initialize local Git only.
2. Confirm root `.gitignore` excludes generated folders and keeps release artifacts visible.
3. Review `git status` before any commit.
4. Make the first local recovery commit only after reviewing the candidate file set.
5. Do not add or contact any remote until the local recovery commit is accepted.
