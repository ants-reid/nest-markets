#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
API_DIR="${PROJECT_ROOT}/apps/api"
LOCAL_DB_DIR="${API_DIR}/.local/postgres-test"
LOCAL_DB_LOG="${API_DIR}/.local/postgres.log"

if [[ ! -x "${API_DIR}/.venv/bin/alembic" ]]; then
  echo "Expected Alembic at ${API_DIR}/.venv/bin/alembic. Create the API virtualenv first." >&2
  exit 1
fi

cd "${API_DIR}"

if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  docker compose up -d postgres
elif command -v initdb >/dev/null 2>&1 && command -v pg_ctl >/dev/null 2>&1 && command -v createdb >/dev/null 2>&1; then
  mkdir -p .local
  if [[ ! -d "${LOCAL_DB_DIR}" ]]; then
    initdb -D "${LOCAL_DB_DIR}" -U postgres --auth=trust --auth-host=trust >/dev/null
  fi

  if ! pg_ctl -D "${LOCAL_DB_DIR}" status >/dev/null 2>&1; then
    pg_ctl -D "${LOCAL_DB_DIR}" -l "${LOCAL_DB_LOG}" -o "-p 5432" start >/dev/null
  fi

  createdb -h localhost -p 5432 -U postgres market_hunter 2>/dev/null || true
else
  echo "Neither a working Docker daemon nor native PostgreSQL tools were found." >&2
  echo "Install/start Docker, or ensure initdb/pg_ctl/createdb are on PATH, then retry." >&2
  exit 1
fi

.venv/bin/alembic upgrade head

echo
echo "Test database is ready at postgresql+psycopg://postgres:postgres@localhost:5432/market_hunter"