#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LEARNING_VENV="${PROJECT_ROOT}/apps/learning/.venv/bin/python"
API_VENV="${PROJECT_ROOT}/apps/api/.venv/bin/python"

cd "${PROJECT_ROOT}"

if [[ -x "${LEARNING_VENV}" ]]; then
	PYTHON_BIN="${LEARNING_VENV}"
elif [[ -x "${API_VENV}" ]]; then
	PYTHON_BIN="${API_VENV}"
else
	echo "Expected Python >=3.12 at apps/learning/.venv/bin/python or apps/api/.venv/bin/python" >&2
	exit 1
fi

PYTHONPATH="${PROJECT_ROOT}" "${PYTHON_BIN}" -m pytest apps/learning/tests/ -q --tb=short "$@"
