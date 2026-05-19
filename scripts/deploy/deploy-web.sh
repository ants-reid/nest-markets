#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
IMAGE_TAG="${1:-$(git -C "${PROJECT_ROOT}" rev-parse --short HEAD)}"
echo "Deploying web app image: market-hunter-web:${IMAGE_TAG}"
echo "Configure target platform deployment in this script (Kubernetes / ECS / etc.)"
