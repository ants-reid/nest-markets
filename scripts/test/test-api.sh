#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
API_DIR="${PROJECT_ROOT}/apps/api"

cd "${API_DIR}"

if [[ ! -x .venv/bin/python ]]; then
	echo "Expected API interpreter at ${API_DIR}/.venv/bin/python" >&2
	exit 1
fi

.venv/bin/python -m pytest tests/ -q --tb=short "$@"
