#!/usr/bin/env bash
set -euo pipefail

# Seed database with default configuration data
# Usage: scripts/db/seed.sh

DATABASE_URL="${DATABASE_URL:-postgresql://markethunter:markethunter@localhost:5432/markethunter}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SEEDS_DIR="${PROJECT_ROOT}/infra/db/seeds"

echo "Seeding database..."
psql "${DATABASE_URL}" -f "${SEEDS_DIR}/default_scoring_config.sql"
psql "${DATABASE_URL}" -f "${SEEDS_DIR}/default_risk_profiles.sql"
echo "Seeding complete."
