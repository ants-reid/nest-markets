#!/usr/bin/env bash
set -euo pipefail

# Init development database
# Usage: scripts/db/init-dev.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
API_DIR="${PROJECT_ROOT}/apps/api"
DATABASE_URL="${DATABASE_URL:-postgresql://postgres:postgres@localhost:5432/market_hunter}"

if [[ ! -x "${API_DIR}/.venv/bin/alembic" ]]; then
	echo "Expected Alembic at ${API_DIR}/.venv/bin/alembic. Create the API virtualenv first." >&2
	exit 1
fi

echo "Initializing development database..."
psql "${DATABASE_URL}" -f "${PROJECT_ROOT}/infra/db/init.sql"

echo "Running Alembic migrations..."
cd "${API_DIR}"
.venv/bin/alembic upgrade head

echo "Database initialization complete."
