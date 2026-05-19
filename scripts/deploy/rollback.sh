#!/usr/bin/env bash
set -euo pipefail
IMAGE_TAG="${1:?Usage: rollback.sh <image_tag>}"
echo "Rolling back to image tag: ${IMAGE_TAG}"
echo "Configure rollback command for your target platform here."
echo "Example (Kubernetes): kubectl set image deployment/market-hunter-api api=market-hunter-api:${IMAGE_TAG}"
