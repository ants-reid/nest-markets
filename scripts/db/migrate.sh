#!/usr/bin/env bash
set -euo pipefail

# Run Alembic database migrations
# Usage: scripts/db/migrate.sh [revision]
#   revision: optional Alembic revision (default: head)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
REVISION="${1:-head}"

echo "Running migrations to: ${REVISION}"
cd "${PROJECT_ROOT}/apps/api"
alembic upgrade "${REVISION}"
echo "Migrations complete."
