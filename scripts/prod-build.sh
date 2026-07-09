#!/usr/bin/env bash
set -euo pipefail

# --- 1. Configurations ---
IMAGE_NAME="ouslan/python-app"
IMAGE_TAG="${GITHUB_SHA:-latest}" # Defaults to 'latest' if not in GitHub Actions

echo "🚀 Starting Production Container Build Pipeline..."

# --- 2. Docker Hub Authentication ---
if [ -z "${DOCKER_PASSWORD:-}" ] || [ -z "${DOCKER_USERNAME:-}" ]; then
  echo "⚠️ Warning: DOCKER_HUB_USERNAME or DOCKER_HUB_TOKEN not set. Skipping authentication. (Assuming already logged in)"
else
  echo "🔐 Logging into Docker Hub..."
  echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin
fi

# --- 3. Build & Push via Docker ---
echo "📦 Building Docker image..."
# We pass python and uv versions down as build arguments if needed,
# ensuring your Dockerfile precisely targets what Nix specified.
docker build \
  --build-arg UV_VERSION="latest" \
  -t "${IMAGE_NAME}:${IMAGE_TAG}" \
  -t "${IMAGE_NAME}:latest" .

echo "📤 Pushing images to Docker Hub..."
docker push "${IMAGE_NAME}:${IMAGE_TAG}"
docker push "${IMAGE_NAME}:latest"

echo "✅ Deployment completed successfully!"
