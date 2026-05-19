#!/usr/bin/env bash
set -euo pipefail

# Run historical bars backfill
# Usage: scripts/learning/backfill-bars.sh [--symbol AAPL] [--from 2020-01-01] [--to 2024-01-01]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

cd "${PROJECT_ROOT}"
python -m apps.learning.jobs.backfill_bars_job "$@"
