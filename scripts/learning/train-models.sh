#!/usr/bin/env bash
set -euo pipefail

# Train all models (regime, scoring, execution)
# Usage: scripts/learning/train-models.sh [--model regime|scoring|execution|all]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
MODEL="${1:-all}"

cd "${PROJECT_ROOT}"

echo "Training models: ${MODEL}"

if [[ "${MODEL}" == "all" || "${MODEL}" == "regime" ]]; then
    echo "→ Training regime model..."
    python -c "from apps.learning.pipelines.train_regime_model import RegimeModelTrainer; print('Regime training stub executed')"
fi

if [[ "${MODEL}" == "all" || "${MODEL}" == "scoring" ]]; then
    echo "→ Training scoring model..."
    python -c "from apps.learning.pipelines.train_scoring_model import ScoringModelTrainer; print('Scoring training stub executed')"
fi

if [[ "${MODEL}" == "all" || "${MODEL}" == "execution" ]]; then
    echo "→ Training execution model..."
    python -c "from apps.learning.pipelines.train_execution_model import ExecutionModelTrainer; print('Execution training stub executed')"
fi

echo "Training complete."
