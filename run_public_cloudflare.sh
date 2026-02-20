#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="${PROJECT_ROOT}/backend"
FRONTEND_DIR="${PROJECT_ROOT}/frontend"
LOG_DIR="${PROJECT_ROOT}/.run_logs"

BACKEND_PORT="${BACKEND_PORT:-8090}"
FRONTEND_PORT="${FRONTEND_PORT:-5050}"

BACKEND_LOG="${LOG_DIR}/backend.log"
FRONTEND_LOG="${LOG_DIR}/frontend.log"
BACKEND_TUNNEL_LOG="${LOG_DIR}/backend_tunnel.log"
FRONTEND_TUNNEL_LOG="${LOG_DIR}/frontend_tunnel.log"

mkdir -p "${LOG_DIR}"
: > "${BACKEND_LOG}"
: > "${FRONTEND_LOG}"
: > "${BACKEND_TUNNEL_LOG}"
: > "${FRONTEND_TUNNEL_LOG}"

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

wait_for_tunnel_url() {
  local log_file="$1"
  local timeout_seconds="${2:-90}"
  local elapsed=0
  local url=""

  while [ "${elapsed}" -lt "${timeout_seconds}" ]; do
    url="$(rg -o "https://[a-z0-9-]+\\.trycloudflare\\.com" "${log_file}" | head -n 1 || true)"
    if [ -n "${url}" ]; then
      printf "%s" "${url}"
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

for cmd in uv npm cloudflared rg curl; do
  require_command "${cmd}"
done

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

echo "Starting backend Cloudflare tunnel"
cloudflared tunnel --url "http://127.0.0.1:${BACKEND_PORT}" >>"${BACKEND_TUNNEL_LOG}" 2>&1 &
BACKEND_TUNNEL_PID=$!
register_pid "${BACKEND_TUNNEL_PID}"

BACKEND_PUBLIC_URL="$(wait_for_tunnel_url "${BACKEND_TUNNEL_LOG}" 120 || true)"
if [ -z "${BACKEND_PUBLIC_URL}" ]; then
  echo "Failed to get backend Cloudflare URL. See ${BACKEND_TUNNEL_LOG}"
  exit 1
fi

echo "Starting frontend on :${FRONTEND_PORT} (API=${BACKEND_PUBLIC_URL}/api)"
(
  cd "${FRONTEND_DIR}"
  VITE_API_BASE_URL="${BACKEND_PUBLIC_URL}/api" npm run dev -- --host 0.0.0.0 --port "${FRONTEND_PORT}"
) >>"${FRONTEND_LOG}" 2>&1 &
FRONTEND_PID=$!
register_pid "${FRONTEND_PID}"

if ! wait_for_http "http://127.0.0.1:${FRONTEND_PORT}" 120; then
  echo "Frontend readiness check failed. See ${FRONTEND_LOG}"
  exit 1
fi

echo "Starting frontend Cloudflare tunnel"
cloudflared tunnel --url "http://127.0.0.1:${FRONTEND_PORT}" >>"${FRONTEND_TUNNEL_LOG}" 2>&1 &
FRONTEND_TUNNEL_PID=$!
register_pid "${FRONTEND_TUNNEL_PID}"

FRONTEND_PUBLIC_URL="$(wait_for_tunnel_url "${FRONTEND_TUNNEL_LOG}" 120 || true)"
if [ -z "${FRONTEND_PUBLIC_URL}" ]; then
  echo "Failed to get frontend Cloudflare URL. See ${FRONTEND_TUNNEL_LOG}"
  exit 1
fi

cat <<EOF

========================================
AI Launch Studio Public Demo is running
========================================
Frontend Public URL: ${FRONTEND_PUBLIC_URL}
Backend Public URL:  ${BACKEND_PUBLIC_URL}

Local Frontend:      http://127.0.0.1:${FRONTEND_PORT}
Local Backend:       http://127.0.0.1:${BACKEND_PORT}

Logs:
  ${BACKEND_LOG}
  ${FRONTEND_LOG}
  ${BACKEND_TUNNEL_LOG}
  ${FRONTEND_TUNNEL_LOG}

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
  if ! kill -0 "${BACKEND_TUNNEL_PID}" >/dev/null 2>&1; then
    echo "Backend tunnel exited. See ${BACKEND_TUNNEL_LOG}"
    exit 1
  fi
  if ! kill -0 "${FRONTEND_TUNNEL_PID}" >/dev/null 2>&1; then
    echo "Frontend tunnel exited. See ${FRONTEND_TUNNEL_LOG}"
    exit 1
  fi
  sleep 2
done
