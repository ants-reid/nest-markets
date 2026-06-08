#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
API_BASE="${MH_API_BASE:-http://127.0.0.1:8000}"
WEB_BASE="${MH_WEB_BASE:-http://127.0.0.1:3100}"
REQUIRE_RUN_NOW="${REQUIRE_RUN_NOW:-false}"
BROKER_READY_TIMEOUT_SECONDS="${BROKER_READY_TIMEOUT_SECONDS:-30}"
HISTORY_IMPORT_EXPECT_ENABLED="${HISTORY_IMPORT_EXPECT_ENABLED:-true}"

if [[ "${1:-}" == "--require-run-now" ]]; then
  REQUIRE_RUN_NOW="true"
fi

failures=0
warnings=0

pass() { echo "PASS: $1"; }
warn() { echo "WARN: $1"; warnings=$((warnings + 1)); }
fail() { echo "FAIL: $1"; failures=$((failures + 1)); }

json_get() {
  local expr="$1"
  python3 -c "import json,sys; j=json.load(sys.stdin); print(${expr})"
}

echo "=== Pre-open readiness check ==="
echo "api=$API_BASE"
echo "web=$WEB_BASE"

if curl -sS --max-time 5 "$API_BASE/health" >/dev/null; then
  pass "API health endpoint reachable"
else
  fail "API health endpoint unreachable"
  echo "=== Summary ==="
  echo "failures=$failures warnings=$warnings"
  exit 1
fi

if curl -sS --max-time 5 "$WEB_BASE/" >/dev/null; then
  pass "Web app reachable"
else
  warn "Web app not reachable (API checks still valid)"
fi

broker_json="$(curl -sS --max-time 8 "$API_BASE/broker/health" || echo '{}')"
overall="$(printf '%s' "$broker_json" | json_get "j.get('broker_readiness',{}).get('overall_status')")"
tws_state="$(printf '%s' "$broker_json" | json_get "j.get('tws_connection_state')")"
client_id="$(printf '%s' "$broker_json" | json_get "j.get('tws_runtime_client_id')")"

if [[ "$overall" != "green" ]]; then
  # Allow brief warm-up for broker initialization after API boot.
  for _ in $(seq 1 "$BROKER_READY_TIMEOUT_SECONDS"); do
    sleep 1
    broker_json="$(curl -sS --max-time 8 "$API_BASE/broker/health" || echo '{}')"
    overall="$(printf '%s' "$broker_json" | json_get "j.get('broker_readiness',{}).get('overall_status')")"
    tws_state="$(printf '%s' "$broker_json" | json_get "j.get('tws_connection_state')")"
    client_id="$(printf '%s' "$broker_json" | json_get "j.get('tws_runtime_client_id')")"
    if [[ "$overall" == "green" ]]; then
      break
    fi
  done
fi

if [[ "$overall" == "green" ]]; then
  pass "Broker readiness green (tws_state=$tws_state client_id=$client_id)"
elif [[ "$overall" == "yellow" ]]; then
  warn "Broker readiness yellow (overall=$overall tws_state=$tws_state client_id=$client_id)"
else
  warn "Broker readiness unavailable/not healthy (overall=$overall tws_state=$tws_state client_id=$client_id)"
fi

control_json="$(curl -sS --max-time 8 "$API_BASE/broker/control" || echo '{}')"
paper_allowed="$(printf '%s' "$control_json" | json_get "j.get('paper_order_submission_allowed')")"
live_allowed="$(printf '%s' "$control_json" | json_get "j.get('live_order_submission_allowed')")"
emergency_stop="$(printf '%s' "$control_json" | json_get "j.get('emergency_stop_active')")"

if [[ "$paper_allowed" == "True" ]]; then
  pass "Paper order submission allowed"
else
  fail "Paper order submission is disabled"
fi

if [[ "$live_allowed" == "False" ]]; then
  pass "Live order submission remains disabled"
else
  fail "Live order submission unexpectedly enabled"
fi

if [[ "$emergency_stop" == "False" ]]; then
  pass "Emergency stop is not active"
else
  fail "Emergency stop is active"
fi

auto_json="$(curl -sS --max-time 12 "$API_BASE/cockpit/auto-paper/status" || echo '{}')"
posture="$(printf '%s' "$auto_json" | json_get "j.get('posture')")"
can_run_now="$(printf '%s' "$auto_json" | json_get "j.get('next_run_guidance',{}).get('can_run_now')")"
blocking_gate="$(printf '%s' "$auto_json" | json_get "j.get('next_run_guidance',{}).get('primary_blocking_gate')")"
primary_reason="$(printf '%s' "$auto_json" | json_get "j.get('next_run_guidance',{}).get('primary_reason')")"
audit_status="$(printf '%s' "$auto_json" | json_get "j.get('audit_alignment',{}).get('status')")"
candidate_count="$(printf '%s' "$auto_json" | json_get "j.get('candidate_queue',{}).get('eligible_count')")"

if [[ "$posture" == "ok" ]]; then
  pass "Auto-paper posture ok"
else
  fail "Auto-paper posture not ok (posture=$posture)"
fi

if [[ "$audit_status" == "ok" ]]; then
  pass "Audit alignment ok"
else
  fail "Audit alignment not ok (status=$audit_status)"
fi

if [[ "$candidate_count" =~ ^[0-9]+$ ]] && (( candidate_count > 0 )); then
  pass "Candidate queue has eligible signals (count=$candidate_count)"
else
  warn "Candidate queue is empty"
fi

if [[ "$can_run_now" == "True" ]]; then
  pass "Auto-paper can run now"
else
  if [[ "$REQUIRE_RUN_NOW" == "true" ]]; then
    fail "Auto-paper cannot run now (gate=$blocking_gate reason=$primary_reason)"
  else
    warn "Auto-paper cannot run now (gate=$blocking_gate reason=$primary_reason)"
  fi
fi

if [[ "$HISTORY_IMPORT_EXPECT_ENABLED" == "true" ]]; then
  if [[ "${AUTO_HISTORY_IMPORT_ENABLED:-true}" == "true" ]]; then
    pass "Historical import automation enabled"
  else
    warn "Historical import automation disabled (AUTO_HISTORY_IMPORT_ENABLED=false)"
  fi
fi

if [[ "${AUTO_LEARNING_ENABLED:-true}" == "true" ]]; then
  pass "Auto-learning trainer enabled"
else
  warn "Auto-learning trainer disabled (AUTO_LEARNING_ENABLED=false)"
fi

echo "=== Summary ==="
echo "failures=$failures warnings=$warnings"

if (( failures > 0 )); then
  exit 1
fi
