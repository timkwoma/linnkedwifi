#!/usr/bin/env bash
set -euo pipefail

BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://127.0.0.1:3000}"
PUBLIC_URL="${PUBLIC_URL:-}"

pass() {
  printf "[PASS] %s\n" "$1"
}

fail() {
  printf "[FAIL] %s\n" "$1"
  exit 1
}

check_json_status() {
  local url="$1"
  local expected="$2"
  local name="$3"
  local body
  body="$(curl -fsS "$url")" || fail "$name unreachable: $url"
  printf "%s" "$body" | grep -q "\"status\":\"$expected\"" || fail "$name unexpected body: $body"
  pass "$name"
}

check_http_ok() {
  local url="$1"
  local name="$2"
  curl -fsS "$url" >/dev/null || fail "$name unreachable: $url"
  pass "$name"
}

echo "Running LinkedWiFi smoke checks..."
echo "BACKEND_URL=$BACKEND_URL"
echo "FRONTEND_URL=$FRONTEND_URL"
[ -n "$PUBLIC_URL" ] && echo "PUBLIC_URL=$PUBLIC_URL"

check_json_status "$BACKEND_URL/health" "ok" "Backend health"
check_json_status "$BACKEND_URL/health/ready" "ready" "Backend readiness"
check_http_ok "$FRONTEND_URL" "Frontend root"

if [ -n "$PUBLIC_URL" ]; then
  check_http_ok "$PUBLIC_URL/health/ready" "Public readiness route"
fi

echo "All smoke checks passed."
