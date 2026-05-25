#!/bin/bash
set -euo pipefail

ENV_FILE=".env.staging"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing ${ENV_FILE}. Copy .env.staging.example and fill in rotated credentials." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL is required in ${ENV_FILE}." >&2
  exit 1
fi

if [[ "${DATABASE_URL}" == *"URL_ENCODED_PASSWORD"* || "${DATABASE_URL}" == *"<"* ]]; then
  echo "DATABASE_URL still contains placeholder values." >&2
  exit 1
fi

echo "Injecting secrets into cloudcommander-staging..."
kubectl create secret generic cloudcommander-secrets \
  --from-literal=DATABASE_URL="${DATABASE_URL}" \
  -n cloudcommander-staging \
  --dry-run=client -o yaml | kubectl apply -f -

echo "Secrets applied."
