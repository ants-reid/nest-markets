#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
API_BASE="${MH_API_BASE:-http://127.0.0.1:8000}"
YEARS="${AUTO_HISTORY_IMPORT_REQUESTED_YEARS:-3}"
PROVIDER="${AUTO_HISTORY_IMPORT_PROVIDER:-yfinance}"
TIMEFRAMES_CSV="${AUTO_HISTORY_IMPORT_TIMEFRAMES:-1d}"
RUN_AUTO_PAPER_NOW="${RUN_AUTO_PAPER_NOW:-false}"

if [[ "${1:-}" == "--run-auto-paper-now" ]]; then
  RUN_AUTO_PAPER_NOW="true"
fi

cd "$ROOT_DIR"

# Ensure API is up with detached paper-safe + automation defaults.
scripts/deploy/start-api-paper-detached.sh >/dev/null

python3 - <<'PY' "$API_BASE" "$YEARS" "$PROVIDER" "$TIMEFRAMES_CSV" "$RUN_AUTO_PAPER_NOW"
import json
import sys
import urllib.request

api_base, years, provider, timeframes_csv, run_auto_paper_now = sys.argv[1:]


def get_json(path: str):
    req = urllib.request.Request(api_base + path, method="GET")
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def post_json(path: str, payload: dict):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        api_base + path,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=1800) as resp:
        return json.loads(resp.read().decode("utf-8"))


coverage = get_json("/research/data/assets")
assets = [item["asset_symbol"] for item in coverage.get("items", []) if item.get("is_active")]
if not assets:
    print("No active assets found; skipping historical bootstrap.")
    sys.exit(0)

timeframes = [tf.strip() for tf in timeframes_csv.split(",") if tf.strip()]
if not timeframes:
    timeframes = ["1d"]

import_payload = {
    "assets": assets,
    "timeframes": timeframes,
    "providers": [provider],
    "requested_years": int(years),
    "dry_run": False,
}

print(f"Historical import bootstrap: assets={len(assets)} provider={provider} years={years} timeframes={','.join(timeframes)}")
import_result = post_json("/research/data/import", import_payload)
print(f"Import status={import_result.get('status')} candles={import_result.get('total_candles_imported')}")

quality_payload = {
    "assets": assets,
    "timeframes": timeframes,
    "providers": [provider],
}
quality_result = post_json("/research/data/quality/recalculate", quality_payload)
print(f"Quality recalculated: succeeded={quality_result.get('succeeded')} failed={quality_result.get('failed')}")

sweep_result = post_json("/opportunities/sweep/run", {})
print(f"Sweep run: status={sweep_result.get('status')} message={sweep_result.get('message')}")

if run_auto_paper_now.lower() == "true":
    run_result = post_json("/market-data/auto-paper/run?source=bootstrap_open", {})
    print(f"Auto-paper run: status={run_result.get('status')} message={run_result.get('message')}")
else:
    print("Auto-paper run not forced; background scheduler will execute on cadence.")
PY

echo "Bootstrap complete."
