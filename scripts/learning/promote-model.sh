#!/usr/bin/env bash
set -euo pipefail

# Promote a candidate model to active
# Usage: scripts/learning/promote-model.sh <candidate_id>

CANDIDATE_ID="${1:?Usage: promote-model.sh <candidate_id>}"
API_URL="${API_URL:-http://localhost:8000}"

echo "Promoting candidate: ${CANDIDATE_ID}"

curl -sf -X POST "${API_URL}/governance/promote" \
  -H "Content-Type: application/json" \
  -d "{\"model_version_id\": \"${CANDIDATE_ID}\"}" | python -m json.tool

echo "Promotion request sent."
