#!/usr/bin/env bash
set -euo pipefail

# Run all test suites
# Usage: scripts/test/test-all.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo "=== Running all tests ==="

echo ""
echo "--- API tests ---"
cd "${PROJECT_ROOT}/apps/api"
python -m pytest tests/ -q --tb=short
API_RESULT=$?

echo ""
echo "--- Learning app tests ---"
cd "${PROJECT_ROOT}"
python -m pytest apps/learning/tests/ -q --tb=short
LEARNING_RESULT=$?

echo ""
if [[ $API_RESULT -eq 0 && $LEARNING_RESULT -eq 0 ]]; then
    echo "✓ All tests passed."
    exit 0
else
    echo "✗ Some tests failed."
    exit 1
fi
