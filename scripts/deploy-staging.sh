#!/bin/bash
set -euo pipefail

SHA=$(git rev-parse --short HEAD)
API_IMAGE="jakeyy8/cloudcommander-api:${SHA}"
WORKER_IMAGE="jakeyy8/cloudcommander-worker:${SHA}"

echo "Building images for commit ${SHA}..."
docker build -t "${API_IMAGE}" -f Dockerfile.api .
docker build -t "${WORKER_IMAGE}" -f Dockerfile.worker .

echo "Pushing images..."
docker push "${API_IMAGE}"
docker push "${WORKER_IMAGE}"

echo "Patching manifests and deploying..."
sed -i "s|image: jakeyy8/cloudcommander-api:.*|image: ${API_IMAGE}|g" k8s/staging/api-deployment.yaml
sed -i "s|image: jakeyy8/cloudcommander-worker:.*|image: ${WORKER_IMAGE}|g" k8s/staging/worker-deployment.yaml
sed -i "s|image: jakeyy8/cloudcommander-api:.*|image: ${API_IMAGE}|g" k8s/staging/migration-job.yaml

kubectl apply -f k8s/staging/api-deployment.yaml
kubectl apply -f k8s/staging/worker-deployment.yaml

echo "Rollout initiated."
kubectl rollout status deployment/cloudcommander-api -n cloudcommander-staging
kubectl rollout status deployment/cloudcommander-worker -n cloudcommander-staging
