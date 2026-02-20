#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="${PROJECT_ROOT}/backend"
FRONTEND_DIR="${PROJECT_ROOT}/frontend"
LOG_DIR="${PROJECT_ROOT}/.run_logs_named"

BACKEND_PORT="${BACKEND_PORT:-8090}"
FRONTEND_PORT="${FRONTEND_PORT:-5050}"
CF_TUNNEL_TOKEN="${CF_TUNNEL_TOKEN:-}"
PUBLIC_API_BASE_URL="${PUBLIC_API_BASE_URL:-}"

BACKEND_LOG="${LOG_DIR}/backend.log"
FRONTEND_LOG="${LOG_DIR}/frontend.log"
TUNNEL_LOG="${LOG_DIR}/named_tunnel.log"

mkdir -p "${LOG_DIR}"
: > "${BACKEND_LOG}"
: > "${FRONTEND_LOG}"
: > "${TUNNEL_LOG}"

require_command() {
  local cmd="$1"
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    echo "Missing command: ${cmd}"
    exit 1
  fi
}

wait_for_http() {
  local url="$1"
  local timeout_seconds="${2:-90}"
  local elapsed=0

  while [ "${elapsed}" -lt "${timeout_seconds}" ]; do
    if curl -fsS "${url}" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done
  return 1
}

PIDS=()

register_pid() {
  local pid="$1"
  PIDS+=("${pid}")
}

cleanup() {
  for pid in "${PIDS[@]:-}"; do
    if [ -n "${pid}" ] && kill -0 "${pid}" >/dev/null 2>&1; then
      kill "${pid}" >/dev/null 2>&1 || true
    fi
  done
  sleep 1
  for pid in "${PIDS[@]:-}"; do
    if [ -n "${pid}" ] && kill -0 "${pid}" >/dev/null 2>&1; then
      kill -9 "${pid}" >/dev/null 2>&1 || true
    fi
  done
}

trap cleanup EXIT INT TERM

for cmd in uv npm cloudflared curl; do
  require_command "${cmd}"
done

if [ -z "${CF_TUNNEL_TOKEN}" ]; then
  cat <<EOF
CF_TUNNEL_TOKEN is required.

Usage example:
  CF_TUNNEL_TOKEN='xxxxx' \\
  PUBLIC_API_BASE_URL='https://api.example.com/api' \\
  ./run_public_cloudflare_named.sh
EOF
  exit 1
fi

if [ -z "${PUBLIC_API_BASE_URL}" ]; then
  PUBLIC_API_BASE_URL="http://127.0.0.1:${BACKEND_PORT}/api"
fi

echo "Starting backend on :${BACKEND_PORT}"
(
  cd "${BACKEND_DIR}"
  uv run uvicorn app.main:app --host 0.0.0.0 --port "${BACKEND_PORT}"
) >>"${BACKEND_LOG}" 2>&1 &
BACKEND_PID=$!
register_pid "${BACKEND_PID}"

if ! wait_for_http "http://127.0.0.1:${BACKEND_PORT}/health" 120; then
  echo "Backend health check failed. See ${BACKEND_LOG}"
  exit 1
fi

echo "Starting frontend on :${FRONTEND_PORT} (API=${PUBLIC_API_BASE_URL})"
(
  cd "${FRONTEND_DIR}"
  VITE_API_BASE_URL="${PUBLIC_API_BASE_URL}" npm run dev -- --host 0.0.0.0 --port "${FRONTEND_PORT}"
) >>"${FRONTEND_LOG}" 2>&1 &
FRONTEND_PID=$!
register_pid "${FRONTEND_PID}"

if ! wait_for_http "http://127.0.0.1:${FRONTEND_PORT}" 120; then
  echo "Frontend readiness check failed. See ${FRONTEND_LOG}"
  exit 1
fi

echo "Starting Cloudflare Named Tunnel"
cloudflared tunnel run --token "${CF_TUNNEL_TOKEN}" >>"${TUNNEL_LOG}" 2>&1 &
TUNNEL_PID=$!
register_pid "${TUNNEL_PID}"

cat <<EOF

========================================
AI Launch Studio Named Tunnel is running
========================================
Local Frontend:      http://127.0.0.1:${FRONTEND_PORT}
Local Backend:       http://127.0.0.1:${BACKEND_PORT}
Frontend API Base:   ${PUBLIC_API_BASE_URL}

Logs:
  ${BACKEND_LOG}
  ${FRONTEND_LOG}
  ${TUNNEL_LOG}

Note:
  - Fixed public URL is configured in Cloudflare Zero Trust Tunnel dashboard.
  - This script only runs local services + tunnel connector.

Press Ctrl+C to stop all processes.
EOF

while true; do
  if ! kill -0 "${BACKEND_PID}" >/dev/null 2>&1; then
    echo "Backend process exited. See ${BACKEND_LOG}"
    exit 1
  fi
  if ! kill -0 "${FRONTEND_PID}" >/dev/null 2>&1; then
    echo "Frontend process exited. See ${FRONTEND_LOG}"
    exit 1
  fi
  if ! kill -0 "${TUNNEL_PID}" >/dev/null 2>&1; then
    echo "Tunnel process exited. See ${TUNNEL_LOG}"
    exit 1
  fi
  sleep 2
done
