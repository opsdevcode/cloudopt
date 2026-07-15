#!/usr/bin/env bash
# Full-stack smoke: docker compose (postgres, redis, api, worker) + Hurl HTTP checks.
# Optional: RUN_PY_E2E=1 runs one thin Python finops smoke against the live API.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

API_URL="${CLOUDOPT_E2E_API_URL:-http://127.0.0.1:8000}"
COMPOSE_DOWN="${COMPOSE_DOWN:-1}"

cleanup() {
  if [[ "${COMPOSE_DOWN}" == "1" ]]; then
    docker compose down --remove-orphans >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

echo "Starting postgres + redis..."
docker compose up -d --wait postgres redis

echo "Running migrations..."
export CLOUDOPT_DATABASE_URL="${CLOUDOPT_DATABASE_URL:-postgresql+asyncpg://cloudopt:cloudopt@localhost:5432/cloudopt}"
export CLOUDOPT_DATABASE_URL_SYNC="${CLOUDOPT_DATABASE_URL_SYNC:-postgresql://cloudopt:cloudopt@localhost:5432/cloudopt}"
export CLOUDOPT_REDIS_URL="${CLOUDOPT_REDIS_URL:-redis://localhost:6379/0}"
export CLOUDOPT_LLM_MODE="${CLOUDOPT_LLM_MODE:-sandbox}"
pip install -e ".[dev]" -q
alembic upgrade head

echo "Starting api + worker..."
docker compose up -d --build api worker

echo "Waiting for API readiness at ${API_URL}/health/ready..."
deadline=$((SECONDS + 120))
until curl -sf "${API_URL}/health/ready" | grep -q '"ready"'; do
  if (( SECONDS > deadline )); then
    echo "API did not become ready in time" >&2
    docker compose logs api worker --tail 50 || true
    exit 1
  fi
  sleep 2
done

if command -v hurl >/dev/null 2>&1; then
  echo "Running Hurl stack smoke..."
  hurl --test --retry 0 e2e/hurl/smoke.hurl
else
  echo "hurl not found; installing via cargo or brew is recommended."
  echo "Falling back to curl smoke..."
  curl -sf "${API_URL}/health/ready" | grep -q '"ready"'
  scan_id="$(
    curl -sf -X POST "${API_URL}/api/v1/scans" \
      -H 'Content-Type: application/json' \
      -d '{"scan_kind":"finops","tenant_id":"shell-e2e"}' \
      | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])'
  )"
  for _ in $(seq 1 45); do
    status="$(
      curl -sf "${API_URL}/api/v1/scans/${scan_id}" \
        | python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])'
    )"
    if [[ "${status}" == "completed" || "${status}" == "failed" ]]; then
      break
    fi
    sleep 2
  done
  [[ "${status}" == "completed" ]] || { echo "scan did not complete: ${status}"; exit 1; }
fi

if [[ "${RUN_PY_E2E:-0}" == "1" ]]; then
  echo "Running optional Python finops e2e smoke..."
  export CLOUDOPT_E2E_LIVE_API="${CLOUDOPT_E2E_LIVE_API:-${API_URL}}"
  pytest tests/test_worker_integration.py::test_finops_scan_completes_live_api -q
fi

echo "Stack smoke passed."
